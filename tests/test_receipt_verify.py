"""Verificacao do Execution Receipt (§14), parte por parte.

Cada adulteracao toca um artefato so, e o veredito precisa nomear exatamente
aquela parte -- e nenhuma outra. Apagado e `missing`, nunca `diverged`; fonte
que nao esta aqui (`traces.db`, transcript) e `not_rechecked` e nao derruba
`valid`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.receipt import verify
from tests.test_receipt_build import FACTS, emitir, montar_case

SPANS = [
    {"span_id": "span_a", "name": "t1", "status": "ok", "payload_bytes": 10, "start_time": 1.0},
    {"span_id": "span_b", "name": "t2", "status": "ok", "payload_bytes": 20, "start_time": 2.0},
]
IDS = [fact["id"] for fact in FACTS]

ADULTERACOES = {
    "case": ".sparkforge/case.yaml",
    "evidence": "facts/a.json",
    "judgment": "findings.json",
    "decision": ".sparkforge/blackboard/claims.jsonl",
}


def conferir(doc: dict, root: Path, **extra) -> dict:
    argumentos = {"union_fact_ids": IDS, "spans_of_run": None, "host_transcript": None}
    argumentos.update(extra)
    return verify(doc, root, **argumentos)


def acrescentar(caminho: Path) -> None:
    caminho.write_text(caminho.read_text(encoding="utf-8") + "x\n", encoding="utf-8")


def test_recibo_intacto_e_valido(tmp_path):
    montar_case(tmp_path)
    veredito = conferir(emitir(tmp_path), tmp_path)
    assert veredito["valid"] is True
    assert veredito["status"] == "valid"
    assert veredito["diverged"] == [] and veredito["missing"] == []


@pytest.mark.parametrize("parte", sorted(ADULTERACOES))
def test_adulterar_um_artefato_acusa_so_a_parte_dele(tmp_path, parte):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    acrescentar(tmp_path / ADULTERACOES[parte])
    veredito = conferir(doc, tmp_path)
    assert veredito["diverged"] == [parte]
    assert veredito["valid"] is False


@pytest.mark.parametrize(
    "arquivo",
    [".sparkforge/blackboard/adr/ADR-dec_1.md", ".sparkforge/debate/dbt_0000abcd/plan.json"],
)
def test_adr_e_debate_caem_na_parte_decisao(tmp_path, arquivo):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    acrescentar(tmp_path / arquivo)
    assert conferir(doc, tmp_path)["diverged"] == ["decision"]


def test_report_editado_cai_no_julgamento(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    acrescentar(tmp_path / "report.md")
    assert conferir(doc, tmp_path)["diverged"] == ["judgment"]


def test_artefato_apagado_e_missing(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    (tmp_path / ".sparkforge" / "blackboard" / "adr" / "ADR-dec_1.md").unlink()
    veredito = conferir(doc, tmp_path)
    assert veredito["missing"] == ["decision"]
    assert veredito["diverged"] == []
    assert veredito["valid"] is False


def test_crlf_no_disco_nao_diverge(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    facts = tmp_path / "facts" / "a.json"
    facts.write_bytes(facts.read_bytes().replace(b"\n", b"\r\n"))
    assert conferir(doc, tmp_path)["valid"] is True


def test_recibo_editado_falha_na_integridade(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    doc["emitted_at"] = "2030-01-01T00:00:00Z"
    veredito = conferir(doc, tmp_path)
    assert "integrity" in veredito["diverged"]
    assert veredito["status"] == "integrity_failed"


def test_reformatar_o_arquivo_nao_quebra(tmp_path):
    montar_case(tmp_path)
    doc = json.loads(json.dumps(emitir(tmp_path), indent=4))
    assert conferir(doc, tmp_path)["valid"] is True


def test_versao_diferente_nao_acusa_adulteracao(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    doc["receipt_version"] = 2
    veredito = conferir(doc, tmp_path)
    assert veredito["status"] == "version_mismatch"
    assert "case" in veredito["not_evaluable"] and "integrity" in veredito["not_evaluable"]
    assert veredito["diverged"] == ["version"]
    assert veredito["checks"]["proof"]["state"] == "match"


def test_prova_citando_fact_fora_da_uniao_diverge(tmp_path):
    """A prova sai da uniao na emissao, entao um fact citado que sumiu da uniao
    so acontece se a evidencia mudou: `evidence` diverge junto, e e o certo."""
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    veredito = conferir(doc, tmp_path, union_fact_ids=[i for i in IDS if i != "bbb222"])
    assert veredito["diverged"] == ["evidence", "proof"]
    assert veredito["checks"]["proof"]["missing_fact_ids"] == ["bbb222"]


def test_spans_todos_presentes_conferem(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path, run_id="run_1", spans=SPANS)
    assert conferir(doc, tmp_path, spans_of_run=SPANS)["checks"]["tools"]["state"] == "match"


def test_spans_depois_do_emit_nao_entram_na_comparacao(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path, run_id="run_1", spans=SPANS)
    depois = [*SPANS, {"span_id": "span_emit", "name": "sparkforge_receipt_emit"}]
    tools = conferir(doc, tmp_path, spans_of_run=depois)["checks"]["tools"]
    assert tools["state"] == "match"
    assert tools["spans_after_emit"] == 1


def test_sem_traces_db_nao_reconfere_e_continua_valido(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path, run_id="run_1", spans=SPANS)
    veredito = conferir(doc, tmp_path, spans_of_run=[])
    assert veredito["not_rechecked"] == ["tools"]
    assert veredito["valid"] is True


def test_span_alterado_diverge(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path, run_id="run_1", spans=SPANS)
    alterado = [{**SPANS[0], "payload_bytes": 99}, SPANS[1]]
    assert conferir(doc, tmp_path, spans_of_run=alterado)["diverged"] == ["tools"]


def test_span_faltando_diverge_e_nomeia(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path, run_id="run_1", spans=SPANS)
    tools = conferir(doc, tmp_path, spans_of_run=SPANS[:1])["checks"]["tools"]
    assert tools["state"] == "diverged"
    assert tools["missing_span_ids"] == ["span_b"]


def test_transcript_fora_do_repo_nao_e_reconferido(tmp_path):
    montar_case(tmp_path)
    transcript = tmp_path / "sessao.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    doc = emitir(tmp_path, host_transcript=transcript, host_facts=[])
    veredito = conferir(doc, tmp_path)
    assert veredito["not_rechecked"] == ["host"]
    assert veredito["valid"] is True
    acrescentar(transcript)
    assert conferir(doc, tmp_path, host_transcript=transcript)["diverged"] == ["host"]
