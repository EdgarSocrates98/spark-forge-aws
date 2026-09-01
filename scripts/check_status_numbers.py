#!/usr/bin/env python3
"""Gate de lastro da tabela *Números correntes* de `docs/superpowers/STATUS.md`.

## Por que este gate existe, e por que ele NAO e parte de `check_vnext_claims.py`

`check_vnext_claims.py` audita `docs/vnext/` e `docs/harness/`. Ele **nao**
audita o `STATUS.md` -- que e a fonte da verdade sobre onde o projeto esta.

A auditoria de 2026-09-01 mediu a consequencia: **oito** numeros da tabela
*Numeros correntes* estavam errados, e o gate saiu `exit 0`. Entre eles, um
publicado **sem produtor nenhum** ("62 de 116", cuja coluna "Onde conferir"
apontava um teste que nunca contou nem 62 nem 116).

Estender `check_vnext_claims.py` ao `STATUS.md` foi medido antes de ser
recusado, e o numero decide:

| Recorte | Alegacoes que o extrator produz |
|---|---|
| `STATUS.md` inteiro | **1797** -- 2,5x o manifesto inteiro de hoje (717) |
| So a secao *Numeros correntes* | **189** -- o extrator pega TODO numero,
  inclusive os que sao explicacao de defeito passado, na coluna de prosa |
| **A coluna `Valor`, uma por dimensao** | **24** -- e e essa a alegacao de verdade |

Os 1214 numeros das secoes de fase sao de EPOCA: o proprio arquivo declara que
fase e registro do que se pretendia numa data. Audita-los contra o HOJE seria
errado por construcao.

Entao este gate tem um recorte que `check_vnext_claims.py` nao tem -- secao,
tabela e coluna -- e uma forma de prova que ele nao tem: a medicao e CODIGO
aqui, e o valor publicado esta no `STATUS.md`. Nao ha terceiro arquivo de
verdade, e por isso nao ha manifesto: o par (medida, publicado) e o contrato.

## Como acrescentar dimensao

Escreva a medida em `MEDIDAS`. Se a tabela ganhar linha que nenhuma medida
cobre, `--strict` reprova nomeando-a -- e isso e de proposito: linha publicada
sem produtor e o defeito que este gate existe para pegar.

Uso:
    python scripts/check_status_numbers.py            # audita; sai 1 se divergir
    python scripts/check_status_numbers.py --strict   # tambem reprova linha sem medida
    python scripts/check_status_numbers.py --list     # so mostra medido x publicado
"""

from __future__ import annotations

import argparse
import glob
import importlib
import json
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "docs" / "superpowers" / "STATUS.md"

SECAO = "## Números correntes"
# A tabela termina onde comeca a proxima secao de nivel 2.
FIM = re.compile(r"^## ")


def _catalogo() -> list[dict]:
    sys.path.insert(0, str(ROOT))
    from sparkforge.rules.loader import load_catalog

    return list(load_catalog())


def _modulos_de_fact() -> list[object]:
    sys.path.insert(0, str(ROOT))
    modulos = []
    for caminho in sorted((ROOT / "sparkforge" / "facts").glob("*.py")):
        if caminho.stem == "__init__":
            continue
        modulos.append(importlib.import_module(f"sparkforge.facts.{caminho.stem}"))
    return modulos


def _extratores() -> list[object]:
    """Modulo de `facts/` que EMITE kind. Os que so carregam conhecimento
    (`runtime_matrix`, `pricing`, ...) nao sao extrator, e a linha da tabela
    diz isso por escrito."""
    return [m for m in _modulos_de_fact() if getattr(m, "EMITTED_KINDS", None)]


def _kinds() -> set[str]:
    uniao: set[str] = set()
    for modulo in _extratores():
        uniao |= set(getattr(modulo, "EMITTED_KINDS", ()) or ())
    return uniao


def _tools() -> dict:
    sys.path.insert(0, str(ROOT))
    from sparkforge.adapters.tools import TOOLS

    return TOOLS


def _skills_despachaveis() -> list[Path]:
    achadas = []
    for caminho in sorted((ROOT / ".agents" / "skills").glob("*/SKILL.md")):
        if re.search(r"^subagent:\s*true", caminho.read_text(encoding="utf-8"), re.M):
            achadas.append(caminho)
    return achadas


def _fontes() -> int:
    lock = json.loads((ROOT / "knowledge" / "sources.lock.json").read_text(encoding="utf-8"))
    return len(lock.get("sources", lock))


def _rotas() -> int:
    texto = (ROOT / "rules" / "catalog" / "routing.yaml").read_text(encoding="utf-8")
    return sum(1 for linha in texto.splitlines() if re.match(r"^  - id: ", linha))


def _regras_do_protocolo() -> int:
    """Itens numerados DENTRO da secao `## Regras` do `AGENT_PROTOCOL.md`.

    O escopo por secao nao e detalhe: a primeira versao desta medida contava
    todo item numerado do arquivo e devolvia **15**, porque ha uma segunda
    lista de 1 a 5 mais adiante. O gate acusou a divergencia contra os 10
    publicados, e a investigacao mostrou que quem estava errado era a MEDIDA,
    nao o numero -- que e o desfecho que este gate existe para produzir.
    """
    linhas = (ROOT / "AGENT_PROTOCOL.md").read_text(encoding="utf-8").splitlines()
    inicio = next(i for i, linha in enumerate(linhas) if linha.strip() == "## Regras")
    total = 0
    for linha in linhas[inicio + 1 :]:
        if linha.startswith("## "):
            break
        if re.match(r"^\d+\.\s", linha):
            total += 1
    return total


def _gates_do_case() -> int:
    import yaml

    doc = yaml.safe_load((ROOT / "rules" / "catalog" / "routing.yaml").read_text(encoding="utf-8"))
    return len(doc.get("gates") or [])


# A medida de cada dimensao. A chave e o texto EXATO da coluna `Dimensão`.
#
# Cada valor e um `Callable[[], int]` -- medicao, nao numero. O numero mora no
# `STATUS.md`, e a divergencia entre os dois e o que este gate reprova.
MEDIDAS: dict[str, Callable[[], int]] = {
    "Regras de diagnóstico": lambda: len(_catalogo()),
    "Regras bloqueadas (`blocked_on`)": lambda: sum(
        1 for r in _catalogo() if r.get("blocked_on")
    ),
    "Regras com `runtime_scope` não-vazio": lambda: sum(
        1 for r in _catalogo() if r.get("runtime_scope")
    ),
    "Regras com eixo de resultado no `validation`": lambda: sum(
        1 for r in _catalogo() if r.get("validation")
    ),
    "Tools MCP": lambda: len(_tools()),
    "Extratores de facts": lambda: len(_extratores()),
    "Fact kinds distintos emitidos": lambda: len(_kinds()),
    "Coordenadores": lambda: len(glob.glob(str(ROOT / "agents" / "*.md"))),
    "Executores": lambda: len(glob.glob(str(ROOT / "agents" / "executors" / "*.md"))),
    "Skills": lambda: len(glob.glob(str(ROOT / "skills" / "*" / "SKILL.md"))),
    "Skills que declaram despacho": lambda: len(_skills_despachaveis()),
    "Fixtures golden": lambda: len(
        [d for d in glob.glob(str(ROOT / "fixtures" / "*" / "*" / "")) if os.path.isdir(d)]
    ),
    "Fontes oficiais vigiadas": _fontes,
    "Rotas determinísticas": _rotas,
    "Gates do case": _gates_do_case,
    "Regras do `AGENT_PROTOCOL.md`": lambda: _regras_do_protocolo(),
}

# Dimensoes que a tabela publica e que este gate NAO mede, com a razao. Sem
# esta lista, `--strict` reprovaria por elas -- e a recusa precisa ter nome,
# como toda recusa neste repositorio.
SEM_MEDIDA: dict[str, str] = {
    "Testes": (
        "a suite inteira num processo so nao sobrevive; medir aqui exigiria "
        "rodar os nove lotes de `tests/test_suite_batches.py`, que leva mais de "
        "30 minutos. O guarda que existe e o proprio `test_suite_batches.py`, "
        "que prova que a receita cobre todo arquivo"
    ),
    "Tools alcançáveis a partir de algum coordenador": (
        "medido por `tests/test_agent_coverage.py`, que ja reprova quando uma "
        "tool fica orfa. Duplicar a travessia aqui seria segundo mecanismo para "
        "a mesma pergunta"
    ),
    "Regras com golden que dispara": (
        "medido por `tests/test_fixtures_kind_coverage.py`, que ja reprova "
        "quando uma regra executavel nao tem fixture que a dispare"
    ),
    "Ramos de severidade com golden que os produz": (
        "mesma razao da linha acima, no mesmo arquivo de teste"
    ),
    "Plataformas que despacham subagente": (
        "o numero sai de `parity.yaml`, e o mecanismo que o guarda e "
        "`tests/test_capability_parity.py`, que e data-driven sobre ele"
    ),
    "Pares de eval": "medido por `scripts/check_evals.py`",
    "Arquivos de terceiro vendorizados": "medido por `python scripts/vendor_caveman.py --check`",
    "Plugins de agente ligados por padrão": (
        "sai de `.claude/settings.json`, que nao e produto -- e configuracao "
        "local de quem desenvolve"
    ),
}


def linhas_da_tabela() -> list[tuple[int, str, str]]:
    """(numero da linha, dimensao, valor publicado) da tabela *Números correntes*."""
    linhas = STATUS.read_text(encoding="utf-8").splitlines()
    inicio = next(i for i, linha in enumerate(linhas) if linha.startswith(SECAO))
    saida: list[tuple[int, str, str]] = []
    for numero in range(inicio + 1, len(linhas)):
        linha = linhas[numero]
        if FIM.match(linha):
            break
        if not linha.startswith("|"):
            continue
        colunas = [c.strip() for c in linha.strip("|").split("|")]
        if len(colunas) < 3:
            continue
        if colunas[0] == "Dimensão" or set("".join(colunas)) <= set("- :"):
            continue
        saida.append((numero + 1, colunas[0], colunas[1]))
    return saida


def _publicado(valor: str) -> int | None:
    """O PRIMEIRO numero da coluna `Valor` -- a alegacao. O resto da celula e
    argumento, e argumento nao e alegacao."""
    achado = re.search(r"(\d[\d.]*)", valor.replace("**", ""))
    return int(achado.group(1).replace(".", "")) if achado else None


def auditar(strict: bool = False) -> list[str]:
    problemas: list[str] = []
    vistas: set[str] = set()
    for numero, dimensao, valor in linhas_da_tabela():
        vistas.add(dimensao)
        medida = MEDIDAS.get(dimensao)
        if medida is None:
            if dimensao in SEM_MEDIDA:
                continue
            if strict:
                problemas.append(
                    f"STATUS.md:{numero}: dimensao `{dimensao}` publicada e sem medida. "
                    f"Ou escreva a medida em `MEDIDAS`, ou declare a razao em `SEM_MEDIDA` "
                    f"-- numero publicado sem produtor e o defeito que este gate pega."
                )
            continue
        esperado = _publicado(valor)
        if esperado is None:
            problemas.append(f"STATUS.md:{numero}: `{dimensao}` sem numero na coluna Valor")
            continue
        obtido = medida()
        if obtido != esperado:
            problemas.append(
                f"STATUS.md:{numero}: `{dimensao}` publica {esperado}, medido {obtido}"
            )
    orfas = sorted(set(MEDIDAS) - vistas)
    if orfas:
        problemas.append(
            f"medidas sem linha na tabela: {orfas}. A dimensao sumiu do STATUS.md e a "
            f"medida ficou -- fail-closed nos dois sentidos, como `check_vnext_claims.py`."
        )
    return problemas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="reprova linha sem medida")
    parser.add_argument("--list", action="store_true", help="mostra medido x publicado")
    args = parser.parse_args()

    if args.list:
        for numero, dimensao, valor in linhas_da_tabela():
            medida = MEDIDAS.get(dimensao)
            obtido = medida() if medida else None
            marca = "sem medida" if obtido is None else str(obtido)
            print(f"{numero:5} {dimensao[:46]:48} publicado={_publicado(valor)} medido={marca}")
        return 0

    problemas = auditar(strict=args.strict)
    for p in problemas:
        print(p)
    print(f"{len(problemas)} divergencia(s).")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
