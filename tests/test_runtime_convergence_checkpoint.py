"""FASE 9 do prompt_evo_runtime: checkpoint/resume REAL entre processos.

§80-81: runtime A checkpointa e morre; runtime B carrega e retoma o estado
deterministico -- facts, decisions, unresolved, next actions, budget,
routing, security -- igual por comparacao, nao por convencao.

§82: checkpoint carrega estado semantico, nao transcript.
§83: compactacao remove superseded/stale mantendo o que ainda importa.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from sparkforge_aws.agentic.checkpoint import SemanticCheckpoint

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str, **env_extra) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT), **env_extra)
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        cwd=ROOT,
        check=True,
        timeout=60,
    )


_STATE = dict(
    objective="diagnose glue OOM",
    state="investigating",
    facts=("f1: skew on key", "f2: 2 executors"),
    decisions=("d1: repartition",),
    unknowns=("u1: actual skew degree",),
    memory_refs=("mem:42",),
    next_actions=("rerun with salting",),
    budget={"max_tokens": 8000, "consumed": 1200},
    routing={"mode": "shadow", "selected": "p/m"},
    security_state={"tainted_inputs": 1},
)


class TestResumeRealCrossProcess:
    def test_checkpoint_atravessa_processos_sem_perda(self, tmp_path):
        destino = tmp_path / "ckpt.json"
        # Runtime A: constroi o estado semantico, checkpointa, termina.
        script_a = f"""
import json
from sparkforge_aws.agentic.checkpoint import SemanticCheckpoint
state = {json.dumps(_STATE)}
ck = SemanticCheckpoint(**state)
ck.save({str(destino)!r}.replace('\\\\', '\\\\'))
print(ck.id)
"""
        a = _run(script_a)
        checkpoint_id_a = a.stdout.strip()
        assert destino.exists()

        # Runtime B: processo novo, sem nada em memoria -- carrega e retoma.
        script_b = f"""
import json, sys
from sparkforge_aws.agentic.checkpoint import SemanticCheckpoint
ck = SemanticCheckpoint.load({str(destino)!r}.replace('\\\\', '\\\\'))
print(json.dumps(ck.to_dict(), sort_keys=True))
"""
        b = _run(script_b)
        resumed = json.loads(b.stdout)
        assert resumed["id"] == checkpoint_id_a  # content-addressed atravessa
        for campo in (
            "facts",
            "decisions",
            "unknowns",
            "next_actions",
            "budget",
            "routing",
            "security_state",
        ):
            assert resumed[campo] == (
                list(_STATE[campo]) if isinstance(_STATE[campo], tuple) else _STATE[campo]
            ), campo

    def test_content_addressed_detecta_adulteracao(self, tmp_path):
        ck = SemanticCheckpoint(**_STATE)
        destino = tmp_path / "ck.json"
        ck.save(destino)
        bruto = json.loads(destino.read_text(encoding="utf-8"))
        bruto["facts"].append("f_alien")
        adulterado = SemanticCheckpoint.from_dict(bruto)
        assert adulterado.id != ck.id  # o id muda porque o conteudo mudou


class TestCheckpointNaoCarregaTranscript:
    def test_sem_transcript_nem_conversa(self):
        campos = set(
            SemanticCheckpoint(objective="", state="").to_dict(include_id=False)
        )
        assert "transcript" not in campos
        assert "messages" not in campos
        assert "conversation" not in campos


class TestCompaction:
    def test_compact_remove_superseded_e_stale(self, tmp_path):
        ck = SemanticCheckpoint(
            **_STATE,
            artifact_refs=("art:stale", "art:live"),
        )
        compacto = ck.compacted(
            superseded_facts=("f1: skew on key",),
            stale_artifacts=("art:stale",),
            reason="f2 provou outra causa",
        )
        assert "f1: skew on key" not in compacto.facts
        assert "art:stale" not in compacto.artifact_refs
        assert "f2: 2 executors" in compacto.facts
        assert "art:live" in compacto.artifact_refs
        assert compacto.facts != ck.facts
        # Decisoes e unknowns sobrevivem -- nao sao descarte automatico.
        assert compacto.decisions == ck.decisions
        assert compacto.unknowns == ck.unknowns
