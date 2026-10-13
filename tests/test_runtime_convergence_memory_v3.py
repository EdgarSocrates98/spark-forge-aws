"""FASE 7 do prompt_evo_runtime: Memory v3.

- §39/§40: `expires_at`/`freshness` governam o retrieval -- expired sai por
  default ou volta como stale/untrusted, nunca igual a fresh.
- §41/§42: `RuntimeCompatibilityPolicy` estruturada -- "Spark 3.5" pedido
  contra "3.5.2" gravado nao e igualdade literal nem incompatibilidade.
- §43/§44: `MemoryConflict` quando memorias relevantes divergem, com
  resolucao prefer/review/unresolved.
- §35: uma so autoridade de quarentena -- `decisions.jsonl` com `status`
  canonico; `quarantine.jsonl` legado e lido apenas para nao perder
  historico, nunca escrito de novo.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sparkforge_aws.agentic.memory import (
    DECISIONS_FILE,
    QUARANTINE_FILE,
    DecisionMemoryRecord,
    RuntimeCompatibilityPolicy,
    classify_memory_candidate,
    detect_memory_conflicts,
    evaluate_runtime,
    freshness_state,
    memory_path,
    memory_stats,
    persist_memory_candidate,
    retrieve_memory,
)


def _record(**kw) -> dict:
    base = {
        "id": "m1",
        "case_id": "c1",
        "problem": "glue job OOM on large shuffle",
        "problem_fingerprint": "fp",
        "environment_fingerprint": "env",
        "status": "accepted",
        "trust": "provisional",
        "freshness": "fresh",
        "decision": "increase workers",
        "decision_evidence": ["f1"],
        "runtime": {"spark": "3.5.2", "glue": "5.1"},
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(kw)
    return base


def _write(root: Path, records: list[dict], file: str = DECISIONS_FILE) -> None:
    path = memory_path(root)
    path.mkdir(parents=True, exist_ok=True)
    with (path / file).open("a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")


class TestFreshnessGovernandoRetrieval:
    def test_expirado_sai_do_retrieval_por_default(self, tmp_path):
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        _write(tmp_path, [_record(expires_at=ontem)])
        resultado = retrieve_memory("glue job OOM", tmp_path)
        assert resultado == []

    def test_expirado_volta_como_stale_quando_policy_permite(self, tmp_path):
        ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        _write(tmp_path, [_record(expires_at=ontem)])
        resultado = retrieve_memory("glue job OOM", tmp_path, expired="stale")
        assert len(resultado) == 1
        assert resultado[0]["retrieval"]["freshness"] == "expired"
        assert resultado[0]["trust"] == "stale"

    def test_stale_ranqueia_abaixo_de_fresh(self, tmp_path):
        _write(
            tmp_path,
            [
                _record(id="old", freshness="stale"),
                _record(id="new", freshness="fresh"),
            ],
        )
        resultado = retrieve_memory("glue job OOM", tmp_path)
        assert [r["id"] for r in resultado] == ["new", "old"]
        assert resultado[1]["retrieval"]["freshness"] == "stale"

    def test_freshness_state_expired_prevalece_sobre_campo(self):
        rec = _record(
            freshness="fresh",
            expires_at="2020-01-01T00:00:00+00:00",
        )
        assert freshness_state(rec, now="2026-01-01T00:00:00+00:00") == "expired"


class TestRuntimeCompatibilityPolicy:
    def test_prefixo_de_versao_e_compativel_nao_igual(self):
        resultado = evaluate_runtime(
            {"spark": "3.5.2", "glue": "5.1"},
            {"spark": "3.5", "glue": "5.1"},
        )
        assert resultado["spark"] == "compatible"
        assert resultado["glue"] == "exact"
        assert RuntimeCompatibilityPolicy().verdict(resultado) == "compatible"

    def test_maior_divergente_e_incompativel(self):
        resultado = evaluate_runtime({"spark": "3.5.2"}, {"spark": "4.0"})
        assert resultado["spark"] == "incompatible"
        assert RuntimeCompatibilityPolicy().verdict(resultado) == "incompatible"

    def test_campo_ausente_no_registro_e_unresolved_nao_incompativel(self):
        resultado = evaluate_runtime({"spark": "3.5.2"}, {"spark": "3.5", "iceberg": "1.9"})
        assert resultado["iceberg"] == "unresolved"
        assert RuntimeCompatibilityPolicy().verdict(resultado) == "partial"

    def test_retrieval_exclui_incompativel_e_reporta_estado(self, tmp_path):
        _write(tmp_path, [_record()])
        assert retrieve_memory(
            "glue job OOM", tmp_path, runtime={"spark": "4.0"}
        ) == []
        resultado = retrieve_memory(
            "glue job OOM", tmp_path, runtime={"spark": "3.5", "glue": "5.1"}
        )
        assert resultado[0]["retrieval"]["runtime_compatibility"] == "compatible"


class TestQuarantineCanonico:
    def test_persistencia_nova_escreve_so_no_ledger(self, tmp_path):
        candidate = classify_memory_candidate(
            DecisionMemoryRecord(
                id="q1",
                case_id="c",
                problem="x",
                problem_fingerprint="f",
                environment_fingerprint="e",
            )
        )
        assert not candidate.persistable
        alvo = persist_memory_candidate(candidate, tmp_path)
        assert alvo.name == DECISIONS_FILE
        assert not (memory_path(tmp_path) / QUARANTINE_FILE).exists()

    def test_stats_le_quarantine_legada_sem_dupla_autoridade(self, tmp_path):
        _write(tmp_path, [_record(id="ok")])
        _write(tmp_path, [_record(id="legado", status="quarantine")], file=QUARANTINE_FILE)
        stats = memory_stats(tmp_path)
        assert stats.quarantined_decisions == 1
        assert stats.total_decisions == 2


class TestMemoryConflicts:
    def test_mesmo_problema_decisao_divergente_gera_conflito(self, tmp_path):
        _write(
            tmp_path,
            [
                _record(id="a", decision="increase workers"),
                _record(id="b", decision="enable shuffle offload"),
            ],
        )
        conflicts = detect_memory_conflicts(tmp_path)
        assert len(conflicts) == 1
        assert set(conflicts[0].record_ids) == {"a", "b"}

    def test_verificado_prevalece_sobre_provisional(self, tmp_path):
        _write(
            tmp_path,
            [
                _record(id="a", decision="increase workers", trust="verified",
                        outcome="success", outcome_evidence=["e1"]),
                _record(id="b", decision="enable shuffle offload",
                        trust="provisional"),
            ],
        )
        conflict = detect_memory_conflicts(tmp_path)[0]
        assert conflict.resolution == "prefer"
        assert conflict.preferred == "a"

    def test_empate_sem_evidencia_diferenciadora_vira_review(self, tmp_path):
        _write(
            tmp_path,
            [
                _record(id="a", decision="x"),
                _record(id="b", decision="y"),
            ],
        )
        conflict = detect_memory_conflicts(tmp_path)[0]
        assert conflict.resolution == "review"
        assert conflict.preferred is None

    def test_memorias_identicas_nao_sao_conflito(self, tmp_path):
        _write(
            tmp_path,
            [
                _record(id="a", decision="same"),
                _record(id="b", decision="same"),
            ],
        )
        assert detect_memory_conflicts(tmp_path) == []
