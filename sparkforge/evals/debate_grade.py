"""Pontua um debate rodado contra o gabarito do caso -- so le arquivo.

Decisao 7 do DESIGN do executor de debate: o grader mora na AVALIACAO, e o
runtime nao o importa (`tests/test_harness_boundary.py`). A dependencia corre no
sentido permitido: este modulo le o que `scripts/run_debate.py` gravou e o
extrator `sparkforge.facts.host_transcript`.

Por caso, quatro medidas, cada uma no seu campo, e NENHUMA nota composta -- peso
entre elas seria convencao vestida de medida, o mesmo defeito que `grade.py`
recusa:

  * `outcome` -- a `Decision` gravada contra `expected.yaml`:

      correct_winner      o gabarito tem vencedor, e a Decision nomeia ele
      wrong_winner        o gabarito tem vencedor, e a Decision nomeia o outro
      missed_resolution   o gabarito tem vencedor, e a Decision e `unresolved`
      correct_unresolved  o gabarito e `unresolved`, e a Decision tambem
      false_resolution    o gabarito e `unresolved`, e a Decision elegeu alguem

    `false_resolution` e o erro caro: fechar onde a medida nao separa as duas
    acoes e o que o `referee` existe para impedir, e a unica defesa que sobra
    quando o protocolo foi cumprido e a conclusao nao tem lastro e o lado nao
    conceder o que nao foi medido.
  * `rounds` e `refused_submissions` -- o que o debate custou em protocolo.
    Recusa inclui a resposta sem bloco JSON (`no_json_block`): para o executor
    ela nem chegou, e para o budget do driver ela contou igual.
  * `decisive_fact` -- o fact que o gabarito nomeia em `decided_by` foi
    REEXTRAIDO no debate, e a Decision o cita? Separa "acertou pela medida" de
    "acertou por sorte"; nao entra no `outcome`.
  * `cost` -- somado dos transcripts dos lados (`<n>-<lado>.jsonl`), com byte
    e token em campos separados, nunca somados (regra 22). Turno sem usage no
    transcript sai contado em `tokens_unresolved_turns` (regra 24), e o total
    de tokens so soma os turnos que TEM a medida -- declarado, nunca estimado.

Caso sem `result.json`, ou cujo debate nao fechou, sai `ungraded` com a razao,
nunca com um `outcome`: medicao que falha nao vira nota ruim (regra 27).
"""
from __future__ import annotations

import json
import os
import re
import statistics
from pathlib import Path
from typing import Any

import yaml

from sparkforge.evals.grade import _TOKENS
from sparkforge.facts.host_transcript import extract_host_transcript_path
from sparkforge.findings.models import Fact

SCHEMA_VERSION = 1
EXPECTED_FILE = "expected.yaml"
RESULT_FILE = "result.json"
DEBATE_FACTS_FILE = "debate_facts.jsonl"
GRADE_FILE = "grade.json"

OUTCOMES = (
    "correct_winner",
    "wrong_winner",
    "missed_resolution",
    "correct_unresolved",
    "false_resolution",
)
# Tentativa do lado que o executor nao aceitou. `host_failed` fica de fora: o
# host nao respondeu, e isso nao e submissao do lado.
_RECUSADAS = frozenset({"refused", "no_json_block"})
# `<n>-<lado>.jsonl`: o nome que o driver grava. Qualquer outro `.jsonl` no
# diretorio do caso nao e turno de lado e nao entra no custo.
_TRANSCRIPT = re.compile(r"^(\d+)-([AB])\.jsonl$")


class DebateGradeError(ValueError):
    """Gabarito ou suite malformados -- defeito do repositorio, nao do debate."""


# --------------------------------------------------------------------------
# Gabarito
# --------------------------------------------------------------------------


def load_expected(case_dir: Path | str) -> dict[str, Any]:
    """O `expected.yaml` do caso, conferido. Levanta `DebateGradeError`."""
    caminho = Path(case_dir) / EXPECTED_FILE
    try:
        dado = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise DebateGradeError(f"{caminho}: ilegivel: {exc}") from exc
    if not isinstance(dado, dict) or dado.get("schema_version") != SCHEMA_VERSION:
        raise DebateGradeError(f"{caminho}: schema_version deve ser {SCHEMA_VERSION}")
    regras = dado.get("rules")
    if not isinstance(regras, list) or len(regras) != 2 or len(set(regras)) != 2:
        raise DebateGradeError(f"{caminho}: `rules` deve ter duas regras distintas")
    desfecho = dado.get("outcome")
    vencedor = dado.get("winner")
    if desfecho == "winner":
        if vencedor not in regras:
            raise DebateGradeError(f"{caminho}: `winner` deve ser uma das `rules`")
    elif desfecho == "unresolved":
        if vencedor is not None:
            raise DebateGradeError(f"{caminho}: `outcome: unresolved` exige `winner: null`")
    else:
        raise DebateGradeError(f"{caminho}: `outcome` deve ser `winner` ou `unresolved`")
    decisivo = dado.get("decided_by")
    if not isinstance(decisivo, dict) or not str(decisivo.get("kind") or "").strip():
        raise DebateGradeError(f"{caminho}: `decided_by.kind` e obrigatorio")
    return dado


def suite_cases(suite_dir: Path | str) -> list[str]:
    """Os casos da suite: subdiretorios com `expected.yaml`, na ordem do nome.

    `os.scandir` plano, e nao `glob` (reprovado por AST em
    `tests/test_facts_scan.py`).
    """
    base = Path(suite_dir)
    if not base.is_dir():
        raise DebateGradeError(f"suite ausente: {base}")
    with os.scandir(base) as entradas:
        return sorted(
            e.name for e in entradas if e.is_dir() and (base / e.name / EXPECTED_FILE).is_file()
        )


# --------------------------------------------------------------------------
# Um caso
# --------------------------------------------------------------------------


def outcome_of(expected: dict[str, Any], done: dict[str, Any]) -> str:
    """O desfecho de um debate FECHADO contra o gabarito."""
    eleito = done.get("winner_rule") if done.get("outcome") == "winner" else None
    if expected["outcome"] == "winner":
        if eleito is None:
            return "missed_resolution"
        return "correct_winner" if eleito == expected["winner"] else "wrong_winner"
    return "false_resolution" if eleito is not None else "correct_unresolved"


def _le_jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.is_file():
        return []
    registros: list[dict[str, Any]] = []
    with caminho.open("r", encoding="utf-8") as fh:
        for linha in fh:
            if linha.strip():
                registros.append(json.loads(linha))
    return registros


def _decisive_fact(
    expected: dict[str, Any], done: dict[str, Any] | None, debate_facts: list[dict[str, Any]]
) -> dict[str, Any]:
    """O fact de `decided_by` foi reextraido? E a Decision o cita?

    Casa por `kind` e, quando o gabarito declara, por `attr == value`. O id
    sozinho nao serve: e content-addressed sobre o sujeito, e o mesmo sujeito
    pode ter medidas diferentes em casos diferentes.
    """
    alvo = expected["decided_by"]
    kind = str(alvo["kind"])
    tem_attr = "attr" in alvo
    ids = {
        str(r["fact"]["id"])
        for r in debate_facts
        if isinstance(r.get("fact"), dict)
        and r["fact"].get("kind") == kind
        and (not tem_attr or (r["fact"].get("attrs") or {}).get(alvo["attr"]) == alvo.get("value"))
    }
    citados = set((done or {}).get("decision", {}).get("evidence_refs") or [])
    return {
        "kind": kind,
        "extracted": bool(ids),
        "cited_by_decision": bool(ids & citados),
    }


def _cost(transcripts: list[list[Fact]], esperados: int) -> dict[str, Any]:
    """Custo somado dos turnos. Byte e token em campos separados (regra 22)."""
    chamadas = [f for fs in transcripts for f in fs if f.kind == "host.tool_call"]
    com_usage = [
        next(f for f in fs if f.kind == "host.usage")
        for fs in transcripts
        if any(f.kind == "host.usage" for f in fs)
    ]
    custo: dict[str, Any] = {
        "turns_expected": esperados,
        "transcripts_found": len(transcripts),
        "tool_calls": len(chamadas),
        "tool_result_bytes": sum(int(c.measures.get("result_bytes", 0)) for c in chamadas),
        "tokens_unresolved_turns": len(transcripts) - len(com_usage),
    }
    if com_usage:
        custo["tokens"] = {
            nome: sum(int(u.measures.get(chave, 0)) for u in com_usage) for nome, chave in _TOKENS
        }
    else:
        custo["tokens"] = None
    custo["tokens_unresolved"] = (
        custo["tokens_unresolved_turns"] > 0 or len(transcripts) < esperados
    )
    return custo


def _transcripts(case_run: Path) -> tuple[list[list[Fact]], set[str], set[str]]:
    """Os turnos `<n>-<lado>.jsonl` do caso, extraidos, e os modelos e versoes."""
    if not case_run.is_dir():
        return [], set(), set()
    with os.scandir(case_run) as entradas:
        nomes = sorted(
            (e.name for e in entradas if e.is_file() and _TRANSCRIPT.match(e.name)),
            key=lambda n: (int(_TRANSCRIPT.match(n).group(1)), n),  # type: ignore[union-attr]
        )
    extraidos = [extract_host_transcript_path(case_run / nome) for nome in nomes]
    modelos: set[str] = set()
    versoes: set[str] = set()
    for fs in extraidos:
        for f in fs:
            if f.kind == "host.transcript":
                modelos.update(str(m) for m in f.attrs.get("models") or [])
                versoes.update(str(v) for v in f.attrs.get("host_versions") or [])
    return extraidos, modelos, versoes


def grade_case(name: str, expected: dict[str, Any], case_run: Path | str) -> dict[str, Any]:
    """A linha de um caso: desfecho, protocolo, fact decisivo e custo."""
    diretorio = Path(case_run)
    extraidos, modelos, versoes = _transcripts(diretorio)
    arquivo = diretorio / RESULT_FILE
    if not arquivo.is_file():
        return {
            "case": name,
            "status": "ungraded",
            "reason": "result_not_found",
            "cost": _cost(extraidos, len(extraidos)),
            "_models": modelos,
            "_versions": versoes,
        }
    resultado = json.loads(arquivo.read_text(encoding="utf-8"))
    tentativas = [t for t in resultado.get("attempts") or [] if isinstance(t, dict)]
    chamadas = sum(1 for t in tentativas if t.get("status") != "driver_pass")
    done = resultado.get("done")
    fechado = isinstance(done, dict) and done.get("status") == "done"
    linha: dict[str, Any] = {
        "case": name,
        "status": "graded" if fechado else "ungraded",
        "expected": {"outcome": expected["outcome"], "winner": expected["winner"]},
        "outcome": outcome_of(expected, done) if fechado else None,
        "decision": (
            {
                "outcome": done.get("outcome"),
                "winner_rule": done.get("winner_rule"),
                "closed_by": done.get("closed_by"),
                "referee_upheld": (done.get("referee") or {}).get("upheld"),
            }
            if fechado
            else None
        ),
        "rounds": int(done.get("rounds_completed", 0)) if fechado else None,
        "refused_submissions": sum(1 for t in tentativas if t.get("status") in _RECUSADAS),
        "host_failures": sum(1 for t in tentativas if t.get("status") == "host_failed"),
        "driver_passes": sum(1 for t in tentativas if t.get("status") == "driver_pass"),
        "decisive_fact": _decisive_fact(
            expected, done if fechado else None, _le_jsonl(diretorio / DEBATE_FACTS_FILE)
        ),
        "cost": _cost(extraidos, chamadas),
        "_models": modelos,
        "_versions": versoes,
    }
    if not fechado:
        linha["reason"] = str(resultado.get("status") or "debate_not_closed")
    return linha


# --------------------------------------------------------------------------
# A execucao inteira
# --------------------------------------------------------------------------


def _spread(valores: list[int]) -> dict[str, int] | None:
    if not valores:
        return None
    return {"median_low": statistics.median_low(valores), "max": max(valores)}


def grade_debate_run(suite_dir: Path | str, run_dir: Path | str) -> dict[str, Any]:
    """O placar de uma execucao: uma linha por caso da suite, na ordem do nome.

    Caso da suite que a execucao nao rodou (`--only`) sai `not_run` e fica fora
    dos totais -- ausencia nao e nem acerto nem erro.
    """
    suite = Path(suite_dir)
    execucao = Path(run_dir)
    linhas: list[dict[str, Any]] = []
    modelos: set[str] = set()
    versoes: set[str] = set()
    for nome in suite_cases(suite):
        esperado = load_expected(suite / nome)
        if not (execucao / nome).is_dir():
            linhas.append({"case": nome, "status": "not_run"})
            continue
        linha = grade_case(nome, esperado, execucao / nome)
        modelos |= linha.pop("_models")
        versoes |= linha.pop("_versions")
        linhas.append(linha)

    pontuados = [linha for linha in linhas if linha["status"] == "graded"]
    rodados = [linha for linha in linhas if linha["status"] != "not_run"]
    com_tokens = [linha for linha in rodados if linha["cost"]["tokens"] is not None]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "debate.grade",
        "run": {
            "id": execucao.resolve().name,
            "models": sorted(modelos),
            "host_versions": sorted(versoes),
        },
        "cases": linhas,
        "totals": {
            "cases": len(linhas),
            "not_run": len(linhas) - len(rodados),
            "graded": len(pontuados),
            "ungraded": len(rodados) - len(pontuados),
            "outcomes": {o: sum(1 for p in pontuados if p["outcome"] == o) for o in OUTCOMES},
            "refused_submissions": sum(p.get("refused_submissions", 0) for p in rodados),
            "tokens_unresolved_cases": sum(1 for p in rodados if p["cost"]["tokens_unresolved"]),
            "cost": {
                "tool_result_bytes": _spread([p["cost"]["tool_result_bytes"] for p in rodados]),
                "output_tokens": _spread([p["cost"]["tokens"]["output"] for p in com_tokens]),
            },
        },
    }
