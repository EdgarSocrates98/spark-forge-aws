"""O que mudou, por pergunta, entre dois conjuntos de scorecards.

Funcao PURA sobre os dicts que `sparkforge.evals.grade.grade` produz. Cada lado
e uma LISTA de scorecards -- N execucoes da mesma suite --, porque agente nao e
deterministico e uma execucao de cada lado nao separa mudanca de ruido.

Por pergunta e por lado, `k/N` sobre as execucoes em que ela foi pontuada vira
uma classe fechada: `pass` (k == N), `fail` (k == 0), `mixed` (o resto) e
`ungraded` (N == 0). A saida e a transicao entre as classes, com os `k/N` crus
ao lado. Nao ha veredito agregado, delta percentual de "qualidade" nem
significancia: o harness lista o que mudou e quem le decide (regra 30).

Tres recusas por nome, com `questions` vazio:

  * `empty_side` -- um lado sem scorecard;
  * `suite_mismatch_within_side` -- scorecards de gabaritos diferentes no mesmo
    lado;
  * `suite_mismatch` -- os dois lados pontuados contra gabaritos diferentes. E
    o `different_input_volume` do eval: mudar a resposta esperada e comparar a
    nota mediria a mudanca do gabarito, nao a do agente.

`single_sample` nao e recusa: com N == 1 o compare roda e o cabecalho avisa.
Modelo ou versao de host diferentes entre os lados tambem nao -- trocar o
modelo costuma ser justamente o que se quer comparar -- e aparecem em `differs`.
"""
from __future__ import annotations

import statistics
from collections.abc import Sequence
from typing import Any

SCHEMA_VERSION = 1


def _refused(reason: str, **detalhe: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "refused": {"reason": reason, **detalhe},
        "single_sample": False,
        "questions": [],
    }


def _hashes(lado: Sequence[dict[str, Any]]) -> list[str]:
    return sorted({str((s.get("suite") or {}).get("sha256", "")) for s in lado})


def _classe(k: int, n: int) -> str:
    if n == 0:
        return "ungraded"
    if k == n:
        return "pass"
    if k == 0:
        return "fail"
    return "mixed"


def _por_pergunta(lado: Sequence[dict[str, Any]], qid: str) -> list[dict[str, Any]]:
    return [p for s in lado for p in s.get("questions", []) if p.get("id") == qid]


def _correct(p: dict[str, Any]) -> bool:
    return p.get("answer") == "correct"


def _abstained(p: dict[str, Any]) -> bool:
    return p.get("abstention") == "abstained"


def _tools_ok(p: dict[str, Any]) -> bool:
    return (p.get("tools") or {}).get("verdict") == "ok"


def _medida(entradas: list[dict[str, Any]], acerto) -> tuple[int, int, int]:
    pontuadas = [p for p in entradas if p.get("status") == "graded"]
    k = sum(1 for p in pontuadas if acerto(p))
    return k, len(pontuadas), len(entradas) - len(pontuadas)


def _linha(base: tuple[int, int, int], cand: tuple[int, int, int]) -> dict[str, str]:
    return {
        "baseline": f"{base[0]}/{base[1]}",
        "candidate": f"{cand[0]}/{cand[1]}",
        "transition": f"{_classe(base[0], base[1])}->{_classe(cand[0], cand[1])}",
    }


def _uniao(lado: Sequence[dict[str, Any]], campo: str) -> list[str]:
    return sorted({str(v) for s in lado for v in (s.get("run") or {}).get(campo) or []})


def _custo(lado: Sequence[dict[str, Any]]) -> dict[str, Any]:
    chamadas = [
        int(p["cost"]["tool_calls"])
        for s in lado
        for p in s.get("questions", [])
        if p.get("status") == "graded" and p.get("cost")
    ]
    if not chamadas:
        return {"tool_calls": None}
    return {"tool_calls": {"median_low": statistics.median_low(chamadas), "max": max(chamadas)}}


def compare(
    baseline: Sequence[dict[str, Any]], candidate: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    if not baseline or not candidate:
        lados_vazios = (("baseline", baseline), ("candidate", candidate))
        vazios = [nome for nome, lado in lados_vazios if not lado]
        return _refused("empty_side", sides=vazios)
    hash_base, hash_cand = _hashes(baseline), _hashes(candidate)
    if len(hash_base) > 1 or len(hash_cand) > 1:
        lados = [n for n, h in (("baseline", hash_base), ("candidate", hash_cand)) if len(h) > 1]
        return _refused("suite_mismatch_within_side", sides=lados)
    if hash_base != hash_cand:
        return _refused(
            "suite_mismatch", baseline_sha256=hash_base[0], candidate_sha256=hash_cand[0]
        )

    ids = [p["id"] for p in baseline[0].get("questions", [])]
    abstencao = {
        p["id"]
        for s in [*baseline, *candidate]
        for p in s.get("questions", [])
        if p.get("abstention") is not None
    }
    perguntas = []
    for qid in ids:
        base, cand = _por_pergunta(baseline, qid), _por_pergunta(candidate, qid)
        metrica = "abstained" if qid in abstencao else "correct"
        acerto = _abstained if qid in abstencao else _correct
        mb, mc = _medida(base, acerto), _medida(cand, acerto)
        perguntas.append(
            {
                "id": qid,
                "metric": metrica,
                "answer": _linha(mb, mc),
                "tools_ok": _linha(_medida(base, _tools_ok), _medida(cand, _tools_ok)),
                "ungraded": {"baseline": mb[2], "candidate": mc[2]},
            }
        )

    lados = {
        nome: {
            "n": len(lado),
            "models": _uniao(lado, "models"),
            "host_versions": _uniao(lado, "host_versions"),
        }
        for nome, lado in (("baseline", baseline), ("candidate", candidate))
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "refused": None,
        "single_sample": len(baseline) == 1 or len(candidate) == 1,
        "suite": {"id": (baseline[0].get("suite") or {}).get("id"), "sha256": hash_base[0]},
        "baseline": lados["baseline"],
        "candidate": lados["candidate"],
        "differs": {
            "models": lados["baseline"]["models"] != lados["candidate"]["models"],
            "host_versions": lados["baseline"]["host_versions"]
            != lados["candidate"]["host_versions"],
        },
        "questions": perguntas,
        "cost": {"baseline": _custo(baseline), "candidate": _custo(candidate)},
    }
