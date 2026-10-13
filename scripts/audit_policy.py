#!/usr/bin/env python3
"""Aplica a politica de auditoria de dependencia sobre a saida do `pip-audit`.

Por que este arquivo existe
===========================

`pip-audit` sabe descobrir vulnerabilidade; ele nao sabe o que ESTE repositorio
decidiu fazer com cada tipo de achado. Sem uma politica escrita, o resultado e
sempre um dos dois defeitos: ou tudo derruba o CI e o time aprende a ignorar
vermelho, ou nada derruba e o scan vira enfeite.

A politica, inteira
===================

**Derruba o job** -- vulnerabilidade com correcao publicada (`fix_versions` nao
vazio). Existe versao para onde ir, o lock e nosso, e subir a versao no lock e
uma linha. Nao subir passa a ser uma DECISAO explicita, e nao um esquecimento.

**So reporta** -- vulnerabilidade sem correcao publicada. Nao ha para onde
subir; derrubar o CI aqui nao acelera correcao nenhuma, so treina o time a
ignorar. Ela aparece no log, com id e pacote, e volta a aparecer a cada
execucao ate ganhar correcao -- e no dia em que ganhar, ela migra sozinha para
a categoria de cima e passa a derrubar.

**Derruba o job** -- base nao consultada. Relatorio ausente, ilegivel, sem a
chave `dependencies`, ou com TODOS os pacotes pulados. Este e o caso que mais
importa acertar: "nao consegui perguntar" nao e "nao ha nada". Um scan que
degrada em silencio para de vigiar sem avisar, que e o mesmo defeito que este
repositorio combate em `pyspark.unresolved` e em indice velho respondendo
"nenhum simbolo".

**So reporta** -- pacote pulado individualmente (`skip_reason`), com os demais
auditados. E cobertura parcial declarada, nao ausencia de cobertura.

**Derruba o job** -- relatorio que nao cobre o lock. Com `--lock`, a politica
confere que todo pacote do lock aparece no relatorio, auditado ou pulado. Um
relatorio bem formado sobre OUTRA coisa -- caminho errado no comando, arquivo
velho que sobrou de uma execucao anterior -- passaria por todas as checagens
acima e nao teria respondido nada sobre o que se queria auditar. Esta e a unica
checagem que compara o relatorio com o alvo em vez de olhar so para dentro dele.

Rede
====

Este script NAO usa rede: ele le um arquivo JSON. Quem usa rede e o `pip-audit`
que o produziu, e e por isso que ele roda num job separado do CI -- consultar
base externa de vulnerabilidade e, por natureza, uma operacao que a queda de um
servico de terceiro faz falhar. Separado, uma indisponibilidade da base pinta o
job de auditoria de vermelho e deixa o gate de teste intacto.

Que o script nao use rede e o que torna a POLITICA testavel offline: a suite
alimenta relatorios sinteticos e mede a classificacao, sem depender de existir
vulnerabilidade real em algum pacote hoje.

Uso
===

    pip-audit --require-hashes --disable-pip -r locks/py3.11.txt \
        --format json --output audit.json
    python scripts/audit_policy.py audit.json --lock locks/py3.11.txt

Codigos de saida:
    0  nada a corrigir (pode haver achado sem correcao, reportado)
    1  vulnerabilidade com correcao publicada
    2  ausencia de resposta -- base nao consultada, ou relatorio que nao cobre
       o lock. Nunca aprovacao.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXIT_OK = 0
EXIT_FIXABLE = 1
EXIT_NOT_CONSULTED = 2


class Verdict:
    """O que a politica decidiu, e por que. Objeto em vez de tupla porque o
    teste pergunta cada campo pelo nome -- e um teste que indexa `[2]` deixa de
    dizer o que esta medindo."""

    __slots__ = ("audited", "exit_code", "fixable", "lines", "skipped", "unfixable")

    def __init__(
        self,
        exit_code: int,
        lines: list[str],
        fixable: list[str],
        unfixable: list[str],
        skipped: list[str],
        audited: int,
    ) -> None:
        self.exit_code = exit_code
        self.lines = lines
        self.fixable = fixable
        self.unfixable = unfixable
        self.skipped = skipped
        self.audited = audited


def _canonical(name: str) -> str:
    """Nome canonico de pacote (PEP 503). O `pip-audit` ja devolve
    `canonical_name`, mas o lock guarda o nome como o indice o publica
    (`PyYAML`, `rpds-py`, `pydantic_core`) -- comparar sem normalizar acusaria
    ausencia onde o pacote esta la, com outra grafia."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _vuln_label(name: str, version: str, vuln: dict) -> str:
    fixes = ", ".join(vuln.get("fix_versions") or []) or "sem correcao publicada"
    aliases = ", ".join(vuln.get("aliases") or [])
    sufixo = f" (aliases: {aliases})" if aliases else ""
    return f"{name}=={version}: {vuln.get('id', '?')} -- corrige em: {fixes}{sufixo}"


def classify(report: object, esperados: set[str] | None = None) -> Verdict:
    """Aplica a politica a um relatorio ja carregado.

    Recebe `object` e nao `dict` de proposito: um relatorio truncado carrega uma
    lista, um numero ou `None`, e a funcao precisa dizer "nao consultada" em vez
    de estourar `AttributeError` -- que o chamador leria como defeito do gate, e
    nao como o que e, ausencia de dado.

    `esperados` sao os nomes canonicos que o relatorio DEVERIA cobrir (o lock).
    `None` desliga a checagem de cobertura; um conjunto liga o unico teste desta
    funcao que olha para fora do relatorio.
    """
    if not isinstance(report, dict) or "dependencies" not in report:
        return Verdict(
            EXIT_NOT_CONSULTED,
            ["base nao consultada: relatorio sem a chave `dependencies`"],
            [],
            [],
            [],
            0,
        )

    dependencies = report.get("dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        return Verdict(
            EXIT_NOT_CONSULTED,
            ["base nao consultada: relatorio sem nenhum pacote"],
            [],
            [],
            [],
            0,
        )

    fixable: list[str] = []
    unfixable: list[str] = []
    skipped: list[str] = []
    vistos: set[str] = set()
    audited = 0

    for dependency in dependencies:
        if not isinstance(dependency, dict):
            skipped.append(f"entrada nao reconhecida no relatorio: {dependency!r}")
            continue
        name = dependency.get("name", "?")
        vistos.add(_canonical(name))
        if "skip_reason" in dependency:
            skipped.append(f"{name}: pulado ({dependency['skip_reason']})")
            continue
        audited += 1
        version = dependency.get("version", "?")
        for vuln in dependency.get("vulns") or []:
            label = _vuln_label(name, version, vuln)
            if vuln.get("fix_versions"):
                fixable.append(label)
            else:
                unfixable.append(label)

    if audited == 0:
        return Verdict(
            EXIT_NOT_CONSULTED,
            ["base nao consultada: todos os pacotes foram pulados", *skipped],
            [],
            [],
            skipped,
            0,
        )

    if esperados is not None:
        ausentes = sorted(esperados - vistos)
        if ausentes:
            return Verdict(
                EXIT_NOT_CONSULTED,
                [
                    f"relatorio nao cobre {len(ausentes)} pacote(s) do lock -- ele responde "
                    "sobre outra coisa, e isso nao e aprovacao:",
                    *(f"  {nome}" for nome in ausentes),
                ],
                [],
                [],
                skipped,
                audited,
            )

    lines: list[str] = [f"{audited} pacote(s) auditado(s)."]
    if skipped:
        lines.append(f"{len(skipped)} pulado(s) -- cobertura parcial, nao ausencia:")
        lines.extend(f"  {item}" for item in skipped)
    if unfixable:
        lines.append(
            f"{len(unfixable)} achado(s) SEM correcao publicada -- reportado, nao bloqueia:"
        )
        lines.extend(f"  {item}" for item in unfixable)
    if fixable:
        lines.append(f"{len(fixable)} achado(s) COM correcao publicada -- bloqueia:")
        lines.extend(f"  {item}" for item in fixable)
        lines.append("Suba a versao em locks/ com: pip install uv && python scripts/gen_lock.py")
    if not fixable and not unfixable:
        lines.append("Nenhuma vulnerabilidade conhecida.")

    return Verdict(
        EXIT_FIXABLE if fixable else EXIT_OK,
        lines,
        fixable,
        unfixable,
        skipped,
        audited,
    )


def expected_from_lock(lock: Path) -> set[str]:
    """Os nomes canonicos que o relatorio deveria cobrir, lidos do lock.

    Le o arquivo com `scripts/gen_lock.py`, e nao com uma expressao regular
    propria: o formato do lock ja tem um parser, e um segundo entendimento do
    mesmo arquivo diverge do primeiro no dia em que o formato mudar.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.gen_lock import canonical, parse  # noqa: PLC0415

    return {canonical(pkg.name) for pkg in parse(lock.read_text(encoding="utf-8"))}


def classify_path(path: Path, lock: Path | None = None) -> Verdict:
    """Le o relatorio do disco. Arquivo ausente ou ilegivel e ausencia de dado,
    nunca aprovacao -- e a razao pela qual um `try` largo aqui devolve
    `EXIT_NOT_CONSULTED` em vez de deixar o traceback subir: o operador precisa
    ler a CAUSA, e nao um rastro de pilha que ele interpretaria como bug."""
    if not path.is_file():
        return Verdict(
            EXIT_NOT_CONSULTED,
            [f"base nao consultada: relatorio ausente em {path}"],
            [],
            [],
            [],
            0,
        )
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        return Verdict(
            EXIT_NOT_CONSULTED,
            [f"base nao consultada: relatorio ilegivel em {path} ({error})"],
            [],
            [],
            [],
            0,
        )
    esperados = expected_from_lock(lock) if lock is not None else None
    return classify(report, esperados)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("report", type=Path, help="JSON produzido por `pip-audit --format json`.")
    parser.add_argument(
        "--lock",
        type=Path,
        default=None,
        help="Lock que o relatorio deveria cobrir. Sem ele, a cobertura nao e conferida.",
    )
    args = parser.parse_args(argv)

    verdict = classify_path(args.report, args.lock)
    stream = sys.stdout if verdict.exit_code == EXIT_OK else sys.stderr
    for line in verdict.lines:
        print(line, file=stream)
    return verdict.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
