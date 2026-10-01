"""L3 do §15 (propose change): o pacote de um PR a partir do sandbox ja rodado.

O pacote MONTA e o host EXECUTA. Nada aqui chama git, gh, subprocess ou
provider: `commands.md` e texto, e quem o roda e o operador -- ou o host, pela
skill `propose-change-pr`, que para antes de `git push` e de `gh pr create`.

A entrada e o sandbox do L2 (`.sparkforge/sandbox/<id>/`), e nao o diff: o que
se propoe e exatamente o que passou pelo scan antes e depois. Por isso as
recusas saem antes de qualquer byte gravado:

  - `sandbox_inexistente` e `sandbox_nao_aplicado`: nao ha o que propor;
  - `sandbox_desatualizado`: a arvore de hoje nao e a `before/` sobre a qual o
    diff foi validado, e a prova do sandbox nao vale para ela;
  - `achado_novo_bloqueante`: o diff faz aparecer achado P0 ou P1 (ou achado
    novo cuja severidade nao se acha, que conta como bloqueante).

A assinatura do corpo e o recibo sao injetados por quem chama, para este modulo
nao importar `adapters`. O corpo do PR nao afirma ganho (regra 13): benchmark e
funcval so entram como medida anexada, ou como obrigacao PENDENTE com o verbo
que as produz.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from sparkforge.change.apply import apply_patches, parse_unified_diff
from sparkforge.change.plan import diff_unificado
from sparkforge.change.refusals import (
    ACHADO_NOVO_BLOQUEANTE,
    CAMINHO_FORA_DA_RAIZ,
    SANDBOX_DESATUALIZADO,
    SANDBOX_INEXISTENTE,
    SANDBOX_NAO_APLICADO,
    ChangeError,
)
from sparkforge.change.sandbox import SANDBOX_DIR, inventariar
from sparkforge.paths import resolve_within

STAGE_PROPOSAL = "propose_change"
PROPOSAL_DIR = PurePosixPath(".sparkforge/proposal")
SCAN_DIR = PurePosixPath(".sparkforge/scan")
BLOQUEANTES = frozenset({"P0", "P1"})
MAX_CAMINHOS = 20
MEDIDAS = ("benchmark", "funcval")

# corpo sem assinatura, findings de `after/` -> corpo assinado, ou None sem achado
Assinar = Callable[[str, Path], "str | None"]
# `after/` -> recibo, ou None sem achado
Recibo = Callable[[Path], "Mapping[str, Any] | None"]

_PENDENTE = {
    "benchmark": (
        "dois runs medidos, antes e depois da mudanca, comparados com `sparkforge benchmark`: "
        "a diferenca de achados nao e desempenho"
    ),
    "funcval": (
        "o resultado continua o mesmo -- contagem, schema, chaves e agregados --, com "
        "`sparkforge funcval plan` e `sparkforge funcval compare`"
    ),
}
_NAO_AFIRMA = (
    "ganho de desempenho, de custo ou de DPU: a diferenca de achados diz o que o motor deixa "
    "de ver, e nao quanto o job melhora (regra 13)",
    "que o resultado do job continua o mesmo, alem do que um funcval anexado mediu",
    "efeito em producao: o scan roda sobre o repositorio, e nao sobre um run",
)


class ProposalDefect(RuntimeError):
    """O patch regenerado nao reproduz `after/`: defeito, e nao recusa."""


def _vazio() -> dict[str, Any]:
    return {
        "stage": STAGE_PROPOSAL,
        "applied": False,
        "git_run": False,
        "main_tree_touched": False,
        "refused": [],
        "proposal": None,
        "id": None,
        "files": [],
        "branch": None,
        "blocking_findings": [],
        "attention_findings": [],
        "pending_measures": [],
        "signed": False,
        "receipt_id": None,
    }


def recusa(exc: ChangeError) -> dict[str, Any]:
    return {**_vazio(), "refused": [exc.to_dict()]}


def _diretorio(raiz: Path, base: PurePosixPath, ident: str) -> Path:
    alvo = resolve_within(raiz, (base / ident).as_posix())
    if alvo is None:
        raise ChangeError(CAMINHO_FORA_DA_RAIZ, f"{base} resolve para fora de {raiz}")
    return alvo


def ler_sandbox(raiz: Path, ident: str) -> tuple[Path, dict[str, Any]]:
    base = _diretorio(raiz, SANDBOX_DIR, ident)
    relatorio = base / "report.json"
    if not relatorio.is_file():
        raise ChangeError(
            SANDBOX_INEXISTENTE, f"{(SANDBOX_DIR / ident).as_posix()}/report.json nao existe"
        )
    dados = json.loads(relatorio.read_text(encoding="utf-8"))
    if not dados.get("applied"):
        motivos = ", ".join(str(r.get("reason")) for r in dados.get("refused") or []) or "?"
        raise ChangeError(SANDBOX_NAO_APLICADO, f"o sandbox {ident} nao aplicou o diff ({motivos})")
    return base, dados


def desatualizados(raiz: Path, antes: Path) -> list[str]:
    """Os caminhos em que a arvore de hoje difere da copia `before/` validada.

    O inventario e o do proprio sandbox, com as mesmas podas: `.sparkforge` fica
    fora dos dois lados (o scan de `before/` grava la dentro), e so os artefatos
    coletados entram.
    """
    atual = dict(inventariar(raiz).manifesto)
    validado = dict(inventariar(antes).manifesto)
    return sorted(
        rel for rel in atual.keys() | validado.keys() if atual.get(rel) != validado.get(rel)
    )


def _achados(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.is_file():
        return []
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [dict(f) for f in dados] if isinstance(dados, list) else []


def _chave(rule_id: Any, subject: Any) -> tuple[str, str]:
    return str(rule_id), json.dumps(subject or {}, sort_keys=True)


def classificar(
    novos: Sequence[Mapping[str, Any]], achados_depois: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa os achados novos em bloqueantes (P0/P1) e atencao (P2/P3).

    A severidade vem do finding de `after/`, porque o `report.json` do sandbox
    so guarda a chave estavel. Achado novo sem finding correspondente fica sem
    severidade e bloqueia: nao saber a gravidade nao e o mesmo que ela ser baixa.
    """
    por_chave = {_chave(f.get("rule_id"), f.get("subject")): f for f in achados_depois}
    bloqueantes: list[dict[str, Any]] = []
    atencao: list[dict[str, Any]] = []
    for item in novos:
        achado = por_chave.get(_chave(item.get("rule_id"), item.get("subject"))) or {}
        linha = {
            "rule_id": str(item.get("rule_id")),
            "severity": str(achado.get("severity") or ""),
            "title": str(achado.get("title") or ""),
            "subject": dict(item.get("subject") or {}),
        }
        if linha["severity"] in BLOQUEANTES or not linha["severity"]:
            bloqueantes.append(linha)
        else:
            atencao.append(linha)
    return bloqueantes, atencao


def _sujeito(subject: Mapping[str, Any]) -> str:
    arquivo = subject.get("file")
    if arquivo:
        linha = subject.get("line")
        return f"{arquivo}:{linha}" if linha else str(arquivo)
    return str(subject.get("symbol") or subject.get("type") or "?")


def _patches(antes: Path, depois: Path, arquivos: Sequence[str]) -> tuple[str, str]:
    """`change.patch` e `rollback.patch`, provados pelo aplicador estrito do L2.

    O diff original nao fica guardado no sandbox; o regenerado de `before/` para
    `after/` so vale se, aplicado, reproduzir `after/` byte a byte -- e o
    inverso, `before/`.
    """
    originais = {rel: (antes / rel).read_bytes() for rel in arquivos}
    novos = {rel: (depois / rel).read_bytes() for rel in arquivos}
    ida = "".join(
        diff_unificado(rel, originais[rel].decode("utf-8"), novos[rel].decode("utf-8"))
        for rel in arquivos
    )
    volta = "".join(
        diff_unificado(rel, novos[rel].decode("utf-8"), originais[rel].decode("utf-8"))
        for rel in arquivos
    )
    for nome, texto, de, para in (
        ("change.patch", ida, originais, novos),
        ("rollback.patch", volta, novos, originais),
    ):
        try:
            aplicado = apply_patches(dict(de), parse_unified_diff(texto))
        except ChangeError as exc:
            raise ProposalDefect(f"{nome} nao aplica sobre a copia validada: {exc}") from exc
        if any(aplicado.get(rel, de[rel]) != para[rel] for rel in arquivos):
            raise ProposalDefect(f"{nome} nao reproduz a copia validada")
    return ida, volta


def _linhas_de_medida(fatos: Sequence[Mapping[str, Any]]) -> list[str]:
    saida = []
    for fato in sorted(fatos, key=lambda f: str(f.get("id") or "")):
        medidas = fato.get("measures") or {}
        pares = ", ".join(f"{k}={medidas[k]}" for k in sorted(medidas)[:8])
        saida.append(
            f"- `{fato.get('kind')}` `{fato.get('id')}` em "
            f"`{_sujeito(fato.get('subject') or {})}`" + (f": {pares}" if pares else "")
        )
    return saida


def corpo(
    ident: str,
    titulo: str,
    relatorio: Mapping[str, Any],
    patch: str,
    atencao: Sequence[Mapping[str, Any]],
    anexos: Mapping[str, Sequence[Mapping[str, Any]]],
) -> str:
    """O corpo do PR sem a assinatura; termina no titulo da secao dela."""
    pasta = (PROPOSAL_DIR / ident).as_posix()
    linhas = [
        f"# {titulo}",
        "",
        f"Proposta montada por `sparkforge change propose` a partir do sandbox `{ident}`. "
        "O pacote nao aplica nada e nao roda git: quem abre e quem revisa este PR sao pessoas.",
        "",
        "## O que muda",
        "",
        "```diff",
        patch.rstrip("\n"),
        "```",
        "",
        "## Achados que deixam de aparecer",
        "",
    ]
    resolvidos = list(relatorio.get("resolved") or [])
    linhas += [
        f"- `{r.get('rule_id')}` em `{_sujeito(r.get('subject') or {})}`" for r in resolvidos
    ] or ["Nenhum: a mudanca nao tira achado do scan."]
    deslocados = list(relatorio.get("moved_candidates") or [])
    if deslocados:
        linhas += [
            "",
            "O mesmo achado com a linha deslocada NAO e resolucao:",
            *(
                f"- `{d.get('rule_id')}` em `{d.get('file')}`: linha {d.get('before_line')} "
                f"-> {d.get('after_line')}"
                for d in deslocados
            ),
        ]
    linhas += ["", "## Atencao: achados novos", ""]
    linhas += [
        f"- `{a['rule_id']}` ({a['severity']}) em `{_sujeito(a['subject'])}`"
        + (f": {a['title']}" if a["title"] else "")
        for a in atencao
    ] or ["Nenhum."]
    linhas += ["", "## Obrigacoes de prova", ""]
    obrigacoes = list(relatorio.get("proof_obligations") or [])
    if not obrigacoes:
        linhas.append("Nenhuma regra tocada.")
    for obrigacao in obrigacoes:
        linhas += ["", f"### `{obrigacao.get('rule_id')}` ({obrigacao.get('side')})", ""]
        linhas += [f"- Validar: {v}" for v in obrigacao.get("validation") or []]
        linhas += [f"- Rollback: {r}" for r in obrigacao.get("rollback") or []]
    linhas += ["", "## Medidas", ""]
    for tipo in MEDIDAS:
        fatos = list(anexos.get(tipo) or [])
        if fatos:
            linhas += [f"### {tipo}: anexado", "", *_linhas_de_medida(fatos), ""]
        else:
            linhas += [f"### {tipo}: PENDENTE", "", f"Falta medir: {_PENDENTE[tipo]}.", ""]
    linhas += ["## O que esta proposta nao afirma", ""]
    linhas += [f"- {item}." for item in _NAO_AFIRMA]
    linhas += [
        "",
        "## Rollback",
        "",
        f"Antes do merge: `git apply -R {pasta}/change.patch` (ou `git apply "
        f"{pasta}/rollback.patch`). Depois dele: `git revert` do commit.",
        "",
        "## Assinatura",
        "",
    ]
    return "\n".join(linhas)


def comandos(ident: str, branch: str, titulo: str, arquivos: Sequence[str]) -> str:
    pasta = (PROPOSAL_DIR / ident).as_posix()
    return "\n".join(
        [
            "# Como abrir este PR",
            "",
            "Rode a partir da raiz do repositorio. O pacote nao executou nada disto.",
            "",
            f"1. `git switch -c {branch}`",
            f"2. `git apply --check {pasta}/change.patch`",
            f"3. `git apply {pasta}/change.patch`",
            f"4. `git add {' '.join(arquivos)}`",
            f"5. `git commit -F {pasta}/commit_message.txt`",
            "6. PARE: confirme com o operador antes de publicar a branch.",
            f"7. `git push -u origin {branch}`",
            "8. PARE: confirme com o operador antes de abrir o PR.",
            f'9. `gh pr create --title "{titulo}" --body-file {pasta}/pr_body.md`',
            "",
            "## Rollback",
            "",
            f"- Antes do commit: `git apply -R {pasta}/change.patch`.",
            f"- Depois do commit, antes do merge: `git apply {pasta}/rollback.patch` e um commit "
            "novo.",
            "- Depois do merge: `git revert <commit>`.",
            "",
        ]
    )


def _mensagem(ident: str, titulo: str, arquivos: Sequence[str], resolvidos: int,
              atencao: int, pendentes: Sequence[str]) -> str:
    medidas = f"pendentes: {', '.join(pendentes)}" if pendentes else "anexadas"
    return "\n".join(
        [
            titulo,
            "",
            f"Proposta sparkforge change {ident}: {len(arquivos)} arquivo(s). Achados que deixam "
            f"de aparecer no scan: {resolvidos}; novos P2/P3: {atencao}.",
            f"Nenhuma afirmacao de ganho; medidas {medidas}.",
            "",
        ]
    )


def _json(dados: Any) -> bytes:
    return (json.dumps(dados, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def _gravar(destino: Path, pacote: Mapping[str, bytes]) -> None:
    """Tudo num temporario ao lado, depois uma troca: nunca um pacote pela metade."""
    temporario = destino.with_name(f".{destino.name}.tmp")
    shutil.rmtree(temporario, ignore_errors=True)
    try:
        for rel, dados in pacote.items():
            alvo = temporario / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(dados)
        if destino.exists():
            shutil.rmtree(destino)
        temporario.replace(destino)
    except Exception:
        shutil.rmtree(temporario, ignore_errors=True)
        raise


def montar(
    repo: Path | str,
    ident: str,
    *,
    assinar: Assinar,
    recibo: Recibo,
    anexos: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    raiz = Path(repo).expanduser()
    try:
        base, relatorio = ler_sandbox(raiz, ident)
        antes, depois = base / "before", base / "after"
        mudados = desatualizados(raiz, antes)
        if mudados:
            extra = f" e mais {len(mudados) - MAX_CAMINHOS}" if len(mudados) > MAX_CAMINHOS else ""
            raise ChangeError(
                SANDBOX_DESATUALIZADO,
                f"{len(mudados)} arquivo(s) diferem da copia validada: "
                f"{', '.join(mudados[:MAX_CAMINHOS])}{extra}",
            )
        achados_depois = depois / SCAN_DIR / "findings.json"
        bloqueantes, atencao = classificar(relatorio.get("new") or [], _achados(achados_depois))
        if bloqueantes:
            resultado = recusa(
                ChangeError(
                    ACHADO_NOVO_BLOQUEANTE,
                    "; ".join(
                        f"{b['rule_id']} ({b['severity'] or 'sem severidade'}) em "
                        f"{_sujeito(b['subject'])}"
                        for b in bloqueantes
                    ),
                )
            )
            resultado["blocking_findings"] = bloqueantes
            return resultado
        destino = _diretorio(raiz, PROPOSAL_DIR, ident)
    except ChangeError as exc:
        return recusa(exc)

    arquivos = [str(rel) for rel in relatorio.get("files_changed") or []]
    ida, volta = _patches(antes, depois, arquivos)
    branch = f"sparkforge/change-{ident[:8]}"
    titulo = f"config: {', '.join(arquivos)} (sparkforge change {ident[:8]})"
    pendentes = [tipo for tipo in MEDIDAS if not anexos.get(tipo)]

    texto = corpo(ident, titulo, relatorio, ida, atencao, anexos)
    assinado = assinar(texto, achados_depois)
    if assinado is None:
        texto += "O scan de `after/` nao deixou achado nenhum: nao ha evidencia para assinar.\n"
    else:
        texto = assinado
    doc_recibo = recibo(depois)

    pacote: dict[str, bytes] = {
        "change.patch": ida.encode("utf-8"),
        "rollback.patch": volta.encode("utf-8"),
        "pr_body.md": texto.encode("utf-8"),
        "commit_message.txt": _mensagem(
            ident, titulo, arquivos, len(relatorio.get("resolved") or []), len(atencao), pendentes
        ).encode("utf-8"),
        "branch.txt": f"{branch}\n".encode(),
        "commands.md": comandos(ident, branch, titulo, arquivos).encode("utf-8"),
        "evidence/sandbox_report.json": _json(relatorio),
    }
    if doc_recibo is not None:
        pacote["evidence/receipt.json"] = _json(doc_recibo)
    pacote["manifest.json"] = _json(
        {
            "id": ident,
            "stage": STAGE_PROPOSAL,
            "sandbox": (SANDBOX_DIR / ident).as_posix(),
            "files": [
                {"path": rel, "sha256": hashlib.sha256(dados).hexdigest()}
                for rel, dados in sorted(pacote.items())
            ],
        }
    )
    _gravar(destino, pacote)
    return {
        **_vazio(),
        "proposal": (PROPOSAL_DIR / ident).as_posix(),
        "id": ident,
        "files": sorted(pacote),
        "branch": branch,
        "attention_findings": atencao,
        "pending_measures": pendentes,
        "signed": assinado is not None,
        "receipt_id": (doc_recibo or {}).get("receipt_id"),
    }
