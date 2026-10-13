"""FASE 14 — adapter A2A experimental sobre o Forge Protocol (§110-114).

O Forge Protocol permanece o contrato; o adapter so traduz formas
(AgentCard, task submit/status, artifacts) para `protocols/forge.py`.
Nenhum SDK A2A entra no core (§112): o adapter e stdlib-puro e o pacote
`a2a` nao pode ser importado por `sparkforge_aws/`.
"""

from __future__ import annotations

import pytest

from sparkforge_aws.protocols.a2a_adapter import (
    A2A_EXPERIMENTAL,
    agent_card,
    forge_to_a2a_state,
    result_to_a2a_task,
    submit_task,
)
from sparkforge_aws.protocols.forge import (
    ForgeCapability,
    ForgeEvidenceBundle,
    ForgeResult,
    ForgeTask,
    ForgeTaskStatus,
)


class TestNomenclatura:
    def test_adapter_se_declara_a2a_ready_nao_implementacao(self) -> None:
        assert A2A_EXPERIMENTAL["compatibility"] == "a2a-ready"
        assert A2A_EXPERIMENTAL["experimental"] is True


class TestAgentCard:
    def test_card_expoe_capabilities_do_forge(self) -> None:
        card = agent_card(
            (ForgeCapability(name="finops", domains=("glue",), operations=("read",)),),
            name="spark-forge",
            version="0.5.0",
            url="forge://local",
        )
        assert card["name"] == "spark-forge"
        assert card["capabilities"][0]["name"] == "finops"
        # A2A-ready: a forma do card segue a spec (skills/defaultInputModes),
        # mas o conteudo vem do ForgeCapability, nunca do contrario.
        assert card["skills"][0]["id"] == "finops"
        assert card["defaultInputModes"] == ["application/forge-task+json"]

    def test_card_recusa_capability_nao_forge(self) -> None:
        with pytest.raises(TypeError):
            agent_card(({"name": "x"},), name="n", version="1", url="u")


class TestSubmitTask:
    def test_a2a_message_vira_forge_task(self) -> None:
        task = submit_task(
            {
                "message": {
                    "parts": [
                        {"kind": "text", "text": "auditar o job glue-x"},
                        {"kind": "data", "data": {"run_id": "jr-1"}},
                    ]
                },
                "metadata": {"requested_by": "the-forger", "risk": "read_only"},
            }
        )
        assert isinstance(task, ForgeTask)
        assert task.objective == "auditar o job glue-x"
        assert task.inputs == {"run_id": "jr-1"}
        assert task.requested_by == "the-forger"
        assert task.risk == "read_only"

    def test_sem_texto_e_recusado(self) -> None:
        with pytest.raises(ValueError, match="objective"):
            submit_task({"message": {"parts": [{"kind": "data", "data": {}}]}})


class TestStateMapping:
    @pytest.mark.parametrize(
        "forge,a2a",
        [
            (ForgeTaskStatus.ACCEPTED, "submitted"),
            (ForgeTaskStatus.RUNNING, "working"),
            (ForgeTaskStatus.SUCCEEDED, "completed"),
            (ForgeTaskStatus.FAILED, "failed"),
            (ForgeTaskStatus.BLOCKED, "rejected"),
            (ForgeTaskStatus.UNRESOLVED, "unknown"),
        ],
    )
    def test_estados(self, forge: ForgeTaskStatus, a2a: str) -> None:
        assert forge_to_a2a_state(forge) == a2a


class TestResultToTask:
    def test_resultado_vira_task_com_artifacts_e_unresolved(self) -> None:
        result = ForgeResult(
            task_id="forge_task_abc",
            status=ForgeTaskStatus.UNRESOLVED,
            summary="falta o dump do catalogo",
            evidence=ForgeEvidenceBundle(
                facts=("f1",), unresolved=("catalogo.dump",)
            ),
        )
        task = result_to_a2a_task(result)
        assert task["id"] == "forge_task_abc"
        assert task["status"]["state"] == "unknown"
        kinds = {a["name"] for a in task["artifacts"]}
        assert "evidence_bundle" in kinds
        assert "unresolved" in kinds
        # unresolved NUNCA vira resultado bem-sucedido
        assert task["status"]["state"] != "completed"
