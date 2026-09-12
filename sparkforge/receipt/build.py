"""Montagem do recibo a partir do que o adapter ja leu.

Cada parte do recibo guarda caminho relativo (POSIX), sha256, ids e contagens,
e nunca o conteudo: `.sparkforge/` pode ser commitado, e caso real nao entra em
arquivo. Toda lacuna sai nomeada em `unresolved`, e as duas recusas fixas
(`authorship` e `tool_io`) saem sempre em `refused`.

Os spans chegam ja lidos de `shared_ledger().spans_of(run_id)`: `call_tool`
grava o span DEPOIS que o handler devolve e so num buffer em memoria, entao o
span do proprio emit ainda nao existe quando este modulo roda, e fica fora sem
filtro nenhum. O `span_id` entra no recibo porque o run continua crescendo
depois do emit, e o verify precisa reconferir exatamente os spans listados.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sparkforge.agentic.blackboard import _ENTITY_FILES, blackboard_path
from sparkforge.agentic.executor.debate_run import (
    _ID_VALIDO,
    DEBATE_DIR,
    DECISION_FILE,
    PLAN_FILE,
    SUBMISSIONS_FILE,
)
from sparkforge.agentic.executor.run import DIR_DE_ADR
from sparkforge.case.store import CASE_DIR, case_path
from sparkforge.receipt._hash import RECEIPT_VERSION, digest_of, receipt_id_of, text_sha256

PROVES = "correspondencia entre este recibo e estes artefatos -- nunca autoria"

REFUSED: tuple[dict[str, str], ...] = (
    {"field": "authorship", "reason": "content_addressed_sem_chave"},
    {"field": "tool_io", "reason": "span_sem_hash_de_io"},
)

SPAN_COLUMNS: tuple[str, ...] = (
    "span_id",
    "name",
    "status",
    "outcome",
    "payload_bytes",
    "detail_level",
    "start_time",
    "end_time",
)

EMIT_TOOL = "sparkforge_receipt_emit"
EXCLUDED_EMIT = {"name": EMIT_TOOL, "reason": "gravado_depois_do_handler"}

PROOF_KINDS: tuple[tuple[str, str, str], ...] = (
    ("tests", "funcval.", "sem_prova_funcional"),
    ("before_after", "bench.", "sem_benchmark"),
)

DEBATE_FILES: tuple[str, ...] = (PLAN_FILE, SUBMISSIONS_FILE, DECISION_FILE)

ACTIONS_L0 = {"autonomy": "L0", "applied_changes": False, "items": []}


def artifact(root: Path, relative: str) -> dict[str, Any]:
    """Caminho relativo e sha256 de um artefato que existe."""
    return {"path": relative, "sha256": text_sha256(root / relative)}


def relative_posix(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def project_spans(spans: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """So as colunas escolhidas, em ordem estavel; `metadata_json` nunca entra."""
    linhas = [{coluna: span.get(coluna) for coluna in SPAN_COLUMNS} for span in spans]
    return sorted(linhas, key=lambda s: (s["start_time"] or 0, str(s["span_id"])))


def _count_lines(path: Path) -> int:
    return sum(1 for linha in path.read_text(encoding="utf-8").splitlines() if linha.strip())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    registros: list[dict[str, Any]] = []
    for linha in path.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            registro = json.loads(linha)
            if isinstance(registro, dict):
                registros.append(registro)
    return registros


def _case_part(
    root: Path, case_id: str | None, unresolved: list[dict[str, str]]
) -> dict[str, Any]:
    caminho = case_path(root)
    if not caminho.is_file():
        unresolved.append({"field": "case", "reason": "case_ausente"})
        return {"path": relative_posix(root, caminho), "sha256": None, "case_id": None}
    return {**artifact(root, relative_posix(root, caminho)), "case_id": case_id}


def _evidence_part(
    root: Path,
    facts_files: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    arquivos = [
        {**artifact(root, str(item["path"])), "fact_count": int(item["fact_count"])}
        for item in facts_files
    ]
    ids = sorted({str(fact["id"]) for fact in facts})
    return {"facts_files": arquivos, "fact_count": len(ids), "fact_ids_sha256": digest_of(ids)}


def _judgment_part(
    root: Path,
    findings_path: str,
    findings_parts: Mapping[str, Any],
    report: Mapping[str, Any] | None,
    unresolved: list[dict[str, str]],
) -> dict[str, Any]:
    parte: dict[str, Any] = {
        "findings": artifact(root, findings_path),
        "rule_ids": sorted(findings_parts["rule_ids"]),
        "fact_ids": sorted(findings_parts["fact_ids"]),
        "catalog_version": findings_parts["catalog_version"],
        "schema_version": findings_parts["schema_version"],
        "report": None,
    }
    if report is None:
        unresolved.append({"field": "judgment.report", "reason": "report_nao_declarado"})
    else:
        assinatura = report.get("signature")
        parte["report"] = {**artifact(root, str(report["path"])), "signature": assinatura}
        if assinatura is None:
            unresolved.append(
                {"field": "judgment.report.signature", "reason": "report_sem_assinatura"}
            )
    return parte


def _blackboard_items(root: Path) -> list[dict[str, Any]]:
    base = blackboard_path(root)
    itens: list[dict[str, Any]] = []
    for nome in sorted(set(_ENTITY_FILES.values())):
        arquivo = base / nome
        if arquivo.is_file():
            relativo = relative_posix(root, arquivo)
            itens.append({**artifact(root, relativo), "count": _count_lines(arquivo)})
    return itens


def _adr_items(
    root: Path, decisions: Sequence[Mapping[str, Any]], unresolved: list[dict[str, str]]
) -> list[dict[str, Any]]:
    base = blackboard_path(root) / DIR_DE_ADR
    itens: list[dict[str, Any]] = []
    for decisao in decisions:
        arquivo = base / f"ADR-{decisao['id']}.md"
        if not arquivo.is_file():
            unresolved.append({"field": f"decision.adr.{decisao['id']}", "reason": "adr_ausente"})
            continue
        itens.append(
            {
                **artifact(root, relative_posix(root, arquivo)),
                "decision_id": str(decisao["id"]),
                "rollback_present": bool(str(decisao.get("rollback") or "").strip()),
            }
        )
    return itens


def _debate_items(root: Path) -> list[dict[str, Any]]:
    base = Path(root) / CASE_DIR / DEBATE_DIR
    if not base.is_dir():
        return []
    with os.scandir(base) as entradas:
        ids = sorted(e.name for e in entradas if e.is_dir() and _ID_VALIDO.match(e.name))
    debates: list[dict[str, Any]] = []
    for debate_id in ids:
        arquivos = [
            artifact(root, relative_posix(root, base / debate_id / nome))
            for nome in DEBATE_FILES
            if (base / debate_id / nome).is_file()
        ]
        debates.append({"id": debate_id, "files": arquivos})
    return debates


def _decision_part(root: Path, unresolved: list[dict[str, str]]) -> dict[str, Any]:
    arquivo_de_decisoes = blackboard_path(root) / _ENTITY_FILES["decision"]
    decisoes = [
        registro
        for registro in (_read_jsonl(arquivo_de_decisoes) if arquivo_de_decisoes.is_file() else [])
        if registro.get("id")
    ]
    blackboard = _blackboard_items(root)
    debates = _debate_items(root)
    if not blackboard and not debates:
        unresolved.append({"field": "decision", "reason": "sem_arbitragem"})
    return {
        "blackboard": blackboard,
        "decision_ids": sorted(str(d["id"]) for d in decisoes),
        "adrs": _adr_items(root, decisoes, unresolved),
        "debates": debates,
    }


def _proof_part(
    facts: Sequence[Mapping[str, Any]], unresolved: list[dict[str, str]]
) -> dict[str, list[str]]:
    parte: dict[str, list[str]] = {}
    for campo, prefixo, razao in PROOF_KINDS:
        ids = sorted({str(f["id"]) for f in facts if str(f.get("kind", "")).startswith(prefixo)})
        parte[campo] = ids
        if not ids:
            unresolved.append({"field": f"proof.{campo}", "reason": razao})
    return parte


def _tools_part(
    run_id: str | None,
    spans: Sequence[Mapping[str, Any]] | None,
    unresolved: list[dict[str, str]],
) -> dict[str, Any]:
    parte: dict[str, Any] = {
        "run_id": run_id,
        "spans": [],
        "spans_sha256": None,
        "excluded": [dict(EXCLUDED_EMIT)],
    }
    if run_id is None:
        unresolved.append({"field": "tools", "reason": "run_id_nao_declarado"})
        return parte
    projetados = project_spans(spans or [])
    if not projetados:
        unresolved.append({"field": "tools", "reason": "run_sem_spans"})
        return parte
    parte["spans"] = projetados
    parte["spans_sha256"] = digest_of(projetados)
    return parte


def _single(valores: Sequence[Any]) -> tuple[Any, str | None]:
    limpos = sorted({str(v) for v in valores if isinstance(v, str) and v})
    if not limpos:
        return None, "ausente"
    if len(limpos) > 1:
        return None, "multiplos"
    return limpos[0], None


def _host_part(
    host_transcript: Path | str | None,
    host_facts: Sequence[Mapping[str, Any]] | None,
    provider: str | None,
    unresolved: list[dict[str, str]],
) -> dict[str, Any]:
    parte: dict[str, Any] = {
        "provider": provider,
        "model": None,
        "agent": None,
        "agent_version": None,
        "transcript_sha256": None,
    }
    if provider is None:
        unresolved.append({"field": "host.provider", "reason": "provider_nao_declarado"})
    if host_transcript is None:
        for campo in ("host.model", "host.agent", "host.agent_version"):
            unresolved.append({"field": campo, "reason": "transcript_ausente"})
        return parte
    parte["transcript_sha256"] = text_sha256(host_transcript)
    transcritos = [f for f in host_facts or [] if f.get("kind") == "host.transcript"]
    attrs = [f.get("attrs") or {} for f in transcritos]
    modelos, motivo_modelo = _single([m for a in attrs for m in a.get("models") or []])
    agente, motivo_agente = _single([a.get("source") for a in attrs])
    versao, motivo_versao = _single([v for a in attrs for v in a.get("host_versions") or []])
    parte.update({"model": modelos, "agent": agente, "agent_version": versao})
    for campo, motivo, razoes in (
        ("host.model", motivo_modelo, ("modelo_ausente", "modelos_multiplos")),
        ("host.agent", motivo_agente, ("agente_ausente", "agentes_multiplos")),
        ("host.agent_version", motivo_versao, ("versao_ausente", "versoes_multiplas")),
    ):
        if motivo is not None:
            razao = razoes[0] if motivo == "ausente" else razoes[1]
            unresolved.append({"field": campo, "reason": razao})
    return parte


def build(
    root: Path | str,
    *,
    now: str,
    case_id: str | None,
    facts_files: Sequence[Mapping[str, Any]],
    facts: Sequence[Mapping[str, Any]],
    findings_path: str,
    findings_parts: Mapping[str, Any],
    report: Mapping[str, Any] | None = None,
    run_id: str | None = None,
    spans: Sequence[Mapping[str, Any]] | None = None,
    host_transcript: Path | str | None = None,
    host_facts: Sequence[Mapping[str, Any]] | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    """O recibo inteiro, com `receipt_id` calculado sobre o resto.

    `facts_files`, `findings_path` e `report["path"]` sao relativos a `root`
    e ja confinados pelo adapter. `facts` e a UNIAO (cada item com `id` e
    `kind`). `spans` e `None` quando nao ha run declarado.
    """
    raiz = Path(root)
    unresolved: list[dict[str, str]] = []
    doc: dict[str, Any] = {
        "receipt_version": RECEIPT_VERSION,
        "emitted_at": now,
        "case": _case_part(raiz, case_id, unresolved),
        "evidence": _evidence_part(raiz, facts_files, facts),
        "judgment": _judgment_part(raiz, findings_path, findings_parts, report, unresolved),
        "decision": _decision_part(raiz, unresolved),
        "proof": _proof_part(facts, unresolved),
        "tools": _tools_part(run_id, spans, unresolved),
        "host": _host_part(host_transcript, host_facts, provider, unresolved),
        "actions": dict(ACTIONS_L0),
        "unresolved": unresolved,
        "refused": [dict(item) for item in REFUSED],
        "proves": PROVES,
    }
    doc["receipt_id"] = receipt_id_of(doc)
    return doc
