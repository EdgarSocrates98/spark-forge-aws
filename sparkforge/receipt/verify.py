"""Verificacao do recibo, parte por parte, contra o disco.

A ordem e fixa -- `version`, `integrity`, `case`, `evidence`, `judgment`,
`decision`, `proof`, `tools`, `host` -- para que a mesma divergencia saia igual
entre execucoes. `version` vem primeiro porque qualifica o resto: com a regra
de normalizacao mudada, "o hash nao bate" deixa de significar "o artefato
mudou", e as partes que dependem dela saem `not_evaluable` em vez de acusadas.

Estados por parte: `match`, `diverged`, `missing` (arquivo declarado que nao
existe mais -- apagado nao e adulterado), `not_rechecked` (a fonte nao esta
aqui: `traces.db` ausente em outra maquina, transcript fora do repo),
`not_evaluable` e `not_declared`. `not_rechecked` nao derruba `valid`, mas sai
listado: e a diferenca entre "nao sei" e "nao perguntei".

Os spans sao reconferidos pelos `span_id` que o recibo listou, nunca por
"todos os spans do run": o run continua ganhando spans depois do emit (o
proprio emit, verifies, `next_step`), e esses sao contados em
`spans_after_emit` sem entrar na comparacao.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from sparkforge.receipt._hash import RECEIPT_VERSION, digest_of, receipt_id_of, text_sha256
from sparkforge.receipt.build import project_spans

PARTS: tuple[str, ...] = (
    "version",
    "integrity",
    "case",
    "evidence",
    "judgment",
    "decision",
    "proof",
    "tools",
    "host",
)

_HASHED_PARTS = frozenset(
    {"integrity", "case", "evidence", "judgment", "decision", "tools", "host"}
)


def _item_state(root: Path, item: Mapping[str, Any]) -> dict[str, Any]:
    """O recibo e dado nao confiavel: caminho que escapa do repo nunca e lido."""
    alvo = (root / str(item["path"])).resolve()
    if not alvo.is_relative_to(root.resolve()):
        return {"path": item["path"], "state": "diverged", "reason": "outside_repo"}
    if not alvo.is_file():
        return {"path": item["path"], "state": "missing"}
    igual = text_sha256(alvo) == item.get("sha256")
    return {"path": item["path"], "state": "match" if igual else "diverged"}


def _aggregate(items: Sequence[Mapping[str, Any]]) -> str:
    estados = {item["state"] for item in items}
    if "missing" in estados:
        return "missing"
    if "diverged" in estados:
        return "diverged"
    return "match"


def _files_check(root: Path, items: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    conferidos = [_item_state(root, item) for item in items]
    return {"state": _aggregate(conferidos), "items": conferidos}


def _case_check(root: Path, doc: Mapping[str, Any]) -> dict[str, Any]:
    caso = doc["case"]
    if caso.get("sha256") is None:
        return {"state": "not_declared", "items": []}
    return _files_check(root, [caso])


def _evidence_check(
    root: Path, doc: Mapping[str, Any], union_fact_ids: Sequence[str] | None
) -> dict[str, Any]:
    evidencia = doc["evidence"]
    check = _files_check(root, evidencia["facts_files"])
    if check["state"] == "match" and union_fact_ids is not None:
        if digest_of(sorted(set(union_fact_ids))) != evidencia["fact_ids_sha256"]:
            check["state"] = "diverged"
            check["detail"] = "fact_ids_sha256 nao fecha com a uniao dos arquivos declarados"
    return check


def _judgment_check(root: Path, doc: Mapping[str, Any]) -> dict[str, Any]:
    julgamento = doc["judgment"]
    itens = [julgamento["findings"]]
    if julgamento.get("report"):
        itens.append(julgamento["report"])
    check = _files_check(root, itens)
    if julgamento.get("report"):
        check["detail"] = (
            "o sha256 do report cobre o arquivo; a assinatura dele se confere com "
            "`sparkforge report verify`"
        )
    return check


def _decision_check(root: Path, doc: Mapping[str, Any]) -> dict[str, Any]:
    decisao = doc["decision"]
    itens = list(decisao["blackboard"]) + list(decisao["adrs"])
    for debate in decisao["debates"]:
        itens.extend(debate["files"])
    if not itens:
        return {"state": "not_declared", "items": []}
    return _files_check(root, itens)


def _proof_check(doc: Mapping[str, Any], union_fact_ids: Sequence[str] | None) -> dict[str, Any]:
    prova = doc["proof"]
    citados = sorted({*prova.get("tests", []), *prova.get("before_after", [])})
    if not citados:
        return {"state": "not_declared", "missing_fact_ids": []}
    if union_fact_ids is None:
        return {"state": "not_rechecked", "reason": "evidencia_ilegivel", "missing_fact_ids": []}
    faltam = sorted(set(citados) - set(union_fact_ids))
    return {"state": "diverged" if faltam else "match", "missing_fact_ids": faltam}


def _tools_check(
    doc: Mapping[str, Any], spans_of_run: Sequence[Mapping[str, Any]] | None
) -> dict[str, Any]:
    ferramentas = doc["tools"]
    if not ferramentas.get("spans"):
        return {"state": "not_declared", "spans_after_emit": 0}
    if spans_of_run is None:
        return {"state": "not_rechecked", "reason": "traces_db_ausente", "spans_after_emit": 0}
    ids = {str(span["span_id"]) for span in ferramentas["spans"]}
    presentes = [span for span in spans_of_run if str(span.get("span_id")) in ids]
    depois = len(spans_of_run) - len(presentes)
    if not presentes:
        return {"state": "not_rechecked", "reason": "run_ausente", "spans_after_emit": depois}
    faltam = sorted(ids - {str(span.get("span_id")) for span in presentes})
    if faltam:
        return {"state": "diverged", "missing_span_ids": faltam, "spans_after_emit": depois}
    igual = digest_of(project_spans(presentes)) == ferramentas["spans_sha256"]
    return {"state": "match" if igual else "diverged", "spans_after_emit": depois}


def _host_check(doc: Mapping[str, Any], host_transcript: Path | str | None) -> dict[str, Any]:
    declarado = doc["host"].get("transcript_sha256")
    if declarado is None:
        return {"state": "not_declared"}
    if host_transcript is None:
        return {"state": "not_rechecked", "reason": "transcript_fora_do_repo"}
    alvo = Path(host_transcript)
    if not alvo.is_file():
        return {"state": "missing"}
    return {"state": "match" if text_sha256(alvo) == declarado else "diverged"}


def _parts_in(checks: Mapping[str, Mapping[str, Any]], estado: str) -> list[str]:
    return [parte for parte in PARTS if checks[parte]["state"] == estado]


def verify(
    doc: Mapping[str, Any],
    root: Path | str,
    *,
    union_fact_ids: Sequence[str] | None = None,
    spans_of_run: Sequence[Mapping[str, Any]] | None = None,
    host_transcript: Path | str | None = None,
) -> dict[str, Any]:
    """O veredito por parte.

    `union_fact_ids` sao os ids da uniao dos arquivos de facts DECLARADOS no
    recibo, lidos agora pelo adapter (`None` se algum nao pode ser lido).
    `spans_of_run` e o que o ledger devolve para o `run_id` do recibo, ou
    `None` sem `traces.db`. `host_transcript` so quando o operador o passa de
    novo.
    """
    raiz = Path(root)
    versao_ok = doc.get("receipt_version") == RECEIPT_VERSION
    checks: dict[str, dict[str, Any]] = {
        "version": {
            "state": "match" if versao_ok else "diverged",
            "declared": doc.get("receipt_version"),
            "build": RECEIPT_VERSION,
        }
    }
    esperado = receipt_id_of(dict(doc)) if versao_ok else None
    checks["integrity"] = {
        "state": "match" if esperado == doc.get("receipt_id") else "diverged",
        "receipt_id": doc.get("receipt_id"),
        "expected_receipt_id": esperado,
    }
    checks["case"] = _case_check(raiz, doc)
    checks["evidence"] = _evidence_check(raiz, doc, union_fact_ids)
    checks["judgment"] = _judgment_check(raiz, doc)
    checks["decision"] = _decision_check(raiz, doc)
    checks["proof"] = _proof_check(doc, union_fact_ids)
    checks["tools"] = _tools_check(doc, spans_of_run)
    checks["host"] = _host_check(doc, host_transcript)

    if not versao_ok:
        for parte in _HASHED_PARTS:
            checks[parte] = {"state": "not_evaluable", "reason": "receipt_version_diferente"}

    diverged = _parts_in(checks, "diverged")
    missing = _parts_in(checks, "missing")
    valid = versao_ok and not diverged and not missing
    if not versao_ok:
        status = "version_mismatch"
    elif checks["integrity"]["state"] != "match":
        status = "integrity_failed"
    elif diverged or missing:
        status = "diverged"
    else:
        status = "valid"
    return {
        "receipt_id": doc.get("receipt_id"),
        "valid": valid,
        "status": status,
        "diverged": diverged,
        "missing": missing,
        "not_rechecked": _parts_in(checks, "not_rechecked"),
        "not_evaluable": _parts_in(checks, "not_evaluable"),
        "checks": checks,
    }
