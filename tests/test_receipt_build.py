"""Montagem do Execution Receipt (§14) com entrada sintetica.

O modulo nao le findings, report, spans nem transcript: recebe o que o adapter
ja leu. Por isso estes testes montam um case em `tmp_path` e passam spans com
`span_id` fixo, o que torna o recibo deterministico sem ledger nenhum.
"""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.case.store import SCHEMA_VERSION, save_case
from sparkforge.receipt import RECEIPT_VERSION, build
from sparkforge.receipt._hash import receipt_id_of, text_sha256
from sparkforge.receipt.build import EMIT_TOOL, PROVES, SPAN_COLUMNS

NOW = "2026-09-12T00:00:00Z"
SEGREDO_EM_MEASURES = 987654321

FACTS = [
    {"id": "aaa111", "kind": "pyspark.write", "measures": {"rows": SEGREDO_EM_MEASURES}},
    {"id": "bbb222", "kind": "funcval.analyzed", "measures": {}},
    {"id": "ccc333", "kind": "bench.stage_delta", "measures": {}},
]
FINDINGS_PARTS = {
    "fact_ids": ["aaa111"],
    "rule_ids": ["SF-X-001"],
    "catalog_version": 3,
    "schema_version": 1,
}
ASSINATURA = "sig_" + "0" * 64


def montar_case(root: Path) -> Path:
    save_case({"schema_version": SCHEMA_VERSION, "case_id": "c1"}, root)
    (root / "facts").mkdir()
    (root / "facts" / "a.json").write_text(json.dumps(FACTS), encoding="utf-8")
    (root / "findings.json").write_text("[]\n", encoding="utf-8")
    (root / "report.md").write_text("# relatorio\n", encoding="utf-8")
    quadro = root / ".sparkforge" / "blackboard"
    (quadro / "adr").mkdir(parents=True)
    (quadro / "claims.jsonl").write_text('{"id": "clm_1"}\n{"id": "clm_2"}\n', encoding="utf-8")
    decisao = {"id": "dec_1", "rollback": "reverter a configuracao"}
    (quadro / "decisions.jsonl").write_text(json.dumps(decisao) + "\n", encoding="utf-8")
    (quadro / "adr" / "ADR-dec_1.md").write_text("# ADR\n", encoding="utf-8")
    debate = root / ".sparkforge" / "debate" / "dbt_0000abcd"
    debate.mkdir(parents=True)
    (debate / "plan.json").write_text('{"rules": []}\n', encoding="utf-8")
    return root


def emitir(root: Path, **extra) -> dict:
    argumentos = {
        "now": NOW,
        "case_id": "c1",
        "facts_files": [{"path": "facts/a.json", "fact_count": len(FACTS)}],
        "facts": FACTS,
        "findings_path": "findings.json",
        "findings_parts": FINDINGS_PARTS,
        "report": {"path": "report.md", "signature": ASSINATURA},
    }
    argumentos.update(extra)
    return build(root, **argumentos)


def campos_unresolved(doc: dict) -> dict[str, str]:
    return {item["field"]: item["reason"] for item in doc["unresolved"]}


def test_mesma_entrada_e_mesmo_now_dao_o_mesmo_recibo(tmp_path):
    montar_case(tmp_path)
    primeiro, segundo = emitir(tmp_path), emitir(tmp_path)
    assert primeiro == segundo
    assert primeiro["receipt_id"].startswith("rcpt_")
    assert len(primeiro["receipt_id"]) == len("rcpt_") + 64


def test_now_diferente_muda_o_id(tmp_path):
    montar_case(tmp_path)
    assert emitir(tmp_path)["receipt_id"] != emitir(tmp_path, now="2026-09-13T00:00:00Z")[
        "receipt_id"
    ]


def test_id_e_o_digest_do_resto(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    assert receipt_id_of(doc) == doc["receipt_id"]
    assert doc["receipt_version"] == RECEIPT_VERSION


def test_crlf_e_lf_dao_o_mesmo_sha256(tmp_path):
    lf, crlf = tmp_path / "lf.json", tmp_path / "crlf.json"
    lf.write_bytes(b'{\n  "a": 1\n}\n')
    crlf.write_bytes(b'{\r\n  "a": 1\r\n}\r\n')
    assert text_sha256(lf) == text_sha256(crlf)


def test_caminhos_relativos_em_posix(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    assert doc["case"]["path"] == ".sparkforge/case.yaml"
    assert doc["evidence"]["facts_files"][0]["path"] == "facts/a.json"
    assert all("\\" not in item["path"] for item in doc["decision"]["blackboard"])


def test_recusas_fixas_e_limite_declarado(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    assert {item["field"] for item in doc["refused"]} == {"authorship", "tool_io"}
    assert doc["proves"] == PROVES
    assert doc["actions"] == {"autonomy": "L0", "applied_changes": False, "items": []}


def test_sem_host_sem_run_e_sem_report_as_lacunas_tem_nome(tmp_path):
    montar_case(tmp_path)
    lacunas = campos_unresolved(emitir(tmp_path, report=None))
    assert lacunas["tools"] == "run_id_nao_declarado"
    assert lacunas["host.provider"] == "provider_nao_declarado"
    assert lacunas["host.model"] == "transcript_ausente"
    assert lacunas["host.agent"] == "transcript_ausente"
    assert lacunas["judgment.report"] == "report_nao_declarado"


def test_host_sai_dos_facts_do_transcript(tmp_path):
    montar_case(tmp_path)
    transcript = tmp_path / "sessao.jsonl"
    transcript.write_text('{"type": "user"}\n', encoding="utf-8")
    fato = {
        "kind": "host.transcript",
        "attrs": {"models": ["claude-x"], "source": "claude_code", "host_versions": ["2.1.0"]},
    }
    doc = emitir(tmp_path, host_transcript=transcript, host_facts=[fato], provider="anthropic")
    assert doc["host"] == {
        "provider": "anthropic",
        "model": "claude-x",
        "agent": "claude_code",
        "agent_version": "2.1.0",
        "transcript_sha256": text_sha256(transcript),
    }
    assert not [c for c in campos_unresolved(doc) if c.startswith("host.")]
    assert str(transcript) not in json.dumps(doc)


def test_dois_modelos_viram_lacuna_e_nao_escolha(tmp_path):
    montar_case(tmp_path)
    transcript = tmp_path / "sessao.jsonl"
    transcript.write_text("{}\n", encoding="utf-8")
    fato = {"kind": "host.transcript", "attrs": {"models": ["a", "b"], "source": "claude_code"}}
    doc = emitir(tmp_path, host_transcript=transcript, host_facts=[fato])
    assert doc["host"]["model"] is None
    assert campos_unresolved(doc)["host.model"] == "modelos_multiplos"
    assert campos_unresolved(doc)["host.agent_version"] == "versao_ausente"


def test_spans_so_com_as_colunas_escolhidas_e_em_ordem(tmp_path):
    montar_case(tmp_path)
    spans = [
        {"span_id": "span_b", "name": "t2", "start_time": 2.0, "metadata_json": '{"x": 1}'},
        {"span_id": "span_a", "name": "t1", "start_time": 1.0, "input_tokens": 9},
    ]
    doc = emitir(tmp_path, run_id="run_1", spans=spans)
    assert [s["span_id"] for s in doc["tools"]["spans"]] == ["span_a", "span_b"]
    assert all(set(s) == set(SPAN_COLUMNS) for s in doc["tools"]["spans"])
    assert doc["tools"]["spans_sha256"]
    assert doc["tools"]["excluded"][0]["name"] == EMIT_TOOL
    assert "metadata_json" not in json.dumps(doc)


def test_run_declarado_sem_span_e_lacuna(tmp_path):
    montar_case(tmp_path)
    assert campos_unresolved(emitir(tmp_path, run_id="run_1", spans=[]))["tools"] == "run_sem_spans"


def test_nenhum_valor_de_measures_entra_no_recibo(tmp_path):
    montar_case(tmp_path)
    assert str(SEGREDO_EM_MEASURES) not in json.dumps(emitir(tmp_path))


def test_prova_so_aponta_ids_por_prefixo(tmp_path):
    montar_case(tmp_path)
    doc = emitir(tmp_path)
    assert doc["proof"] == {"tests": ["bbb222"], "before_after": ["ccc333"]}


def test_sem_prova_as_duas_lacunas_tem_nome(tmp_path):
    montar_case(tmp_path)
    so_escrita = [FACTS[0]]
    lacunas = campos_unresolved(emitir(tmp_path, facts=so_escrita))
    assert lacunas["proof.tests"] == "sem_prova_funcional"
    assert lacunas["proof.before_after"] == "sem_benchmark"


def test_decisao_com_blackboard_adr_e_debate(tmp_path):
    montar_case(tmp_path)
    decisao = emitir(tmp_path)["decision"]
    arquivos = {item["path"]: item["count"] for item in decisao["blackboard"]}
    assert arquivos == {
        ".sparkforge/blackboard/claims.jsonl": 2,
        ".sparkforge/blackboard/decisions.jsonl": 1,
    }
    assert decisao["decision_ids"] == ["dec_1"]
    assert decisao["adrs"][0]["rollback_present"] is True
    assert decisao["debates"][0]["id"] == "dbt_0000abcd"


def test_adr_ausente_vira_lacuna_e_nao_item(tmp_path):
    montar_case(tmp_path)
    (tmp_path / ".sparkforge" / "blackboard" / "adr" / "ADR-dec_1.md").unlink()
    doc = emitir(tmp_path)
    assert doc["decision"]["adrs"] == []
    assert campos_unresolved(doc)["decision.adr.dec_1"] == "adr_ausente"


def test_sem_arbitragem_e_lacuna(tmp_path):
    save_case({"schema_version": SCHEMA_VERSION, "case_id": "c1"}, tmp_path)
    (tmp_path / "facts").mkdir()
    (tmp_path / "facts" / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "findings.json").write_text("[]", encoding="utf-8")
    doc = emitir(tmp_path, report=None)
    assert campos_unresolved(doc)["decision"] == "sem_arbitragem"
