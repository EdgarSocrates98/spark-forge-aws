"""O estado das fontes nos verbos: `judge`, `rules_lookup`, `knowledge_path` e
`report github`, sempre opt-in (`source_freshness`).

Sem a flag, a resposta e a de antes -- e o que mantem a promessa do
`rules_lookup` ("sempre a mesma resposta") e o golden de paridade MCP. Com ela,
os campos novos validam contra o schema da tool, cobrem so as fontes da pagina
devolvida, e um lock ausente vira `unresolved` em vez de derrubar o verbo.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import jsonschema
import pytest

from sparkforge.adapters import _core
from sparkforge.adapters.tools import TOOLS, call_tool

ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-09-11"
CAMPOS = {"source_freshness", "freshness_policy"}


@pytest.fixture(autouse=True)
def _ledger_isolado(tmp_path, monkeypatch):
    from sparkforge.observability import context_ledger

    monkeypatch.setattr(
        context_ledger,
        "_SHARED_LEDGER",
        context_ledger.ContextLedger(db_path=tmp_path / "traces.db", run_id="run_teste"),
    )


def _valida(nome: str, resultado: dict) -> None:
    jsonschema.validate(resultado, TOOLS[nome]["outputSchema"])


def _urls_das_fontes(itens: list[dict]) -> set[str]:
    return {f["url"] for i in itens for f in i.get("sources") or [] if f.get("url")}


class TestRulesLookup:
    def test_sem_a_flag_nada_muda(self):
        resultado = call_tool("sparkforge_rules_lookup", {"id": ["SF-ENV-001"]})
        assert not CAMPOS & set(resultado)

    def test_com_a_flag_cobre_so_as_fontes_da_pagina(self):
        resultado = call_tool(
            "sparkforge_rules_lookup",
            {"id": ["SF-ENV-001", "SF-TIMEOUT-002"], "source_freshness": True, "as_of": AS_OF},
        )
        _valida("sparkforge_rules_lookup", resultado)
        assert set(resultado["source_freshness"]) == _urls_das_fontes(resultado["rules"])
        politica = resultado["freshness_policy"]
        assert politica["as_of"] == AS_OF
        assert sum(v for k, v in politica["counts"].items() if k != "sem_url") == len(
            resultado["source_freshness"]
        )

    def test_mesmo_as_of_mesma_resposta(self):
        args = {"id": ["SF-ENV-001"], "source_freshness": True, "as_of": AS_OF}
        assert call_tool("sparkforge_rules_lookup", args) == call_tool(
            "sparkforge_rules_lookup", args
        )

    def test_as_of_invalido_e_erro_de_uso(self):
        resultado = call_tool(
            "sparkforge_rules_lookup",
            {"id": ["SF-ENV-001"], "source_freshness": True, "as_of": "2026-13-45"},
        )
        assert resultado["exit_code"] == 2
        assert "sparkforge" in resultado["error"]

    def test_sem_lock_tudo_unresolved_e_o_verbo_responde(self, tmp_path, monkeypatch):
        sem_lock = tmp_path / "knowledge"
        shutil.copytree(ROOT / "knowledge", sem_lock)
        (sem_lock / "sources.lock.json").unlink()
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(sem_lock))
        resultado = _core.rules_lookup(id=["SF-ENV-001"], source_freshness=True, as_of=AS_OF)
        estados = {e["state"] for e in resultado["source_freshness"].values()}
        assert estados == {"unresolved"}
        assert {e["reason"] for e in resultado["source_freshness"].values()} == {"lock_ausente"}
        assert resultado["rules"]


class TestJudge:
    FACTS = ROOT / "fixtures" / "pyspark" / "collect_unbounded" / "expected" / "facts.json"

    def test_sem_a_flag_os_findings_sao_os_de_antes(self):
        base = call_tool("sparkforge_judge", {"facts_path": str(self.FACTS), "glue": "5.0"})
        com = call_tool(
            "sparkforge_judge",
            {
                "facts_path": str(self.FACTS),
                "glue": "5.0",
                "source_freshness": True,
                "as_of": AS_OF,
            },
        )
        assert not CAMPOS & set(base)
        assert com["items"] == base["items"]
        _valida("sparkforge_judge", com)
        assert set(com["source_freshness"]) == _urls_das_fontes(com["items"])

    def test_cli_e_tool_concordam_com_a_flag(self, capsys):
        from sparkforge.adapters import cli

        argv = [
            "judge",
            "--facts",
            str(self.FACTS),
            "--glue",
            "5.0",
            "--source-freshness",
            "--as-of",
            AS_OF,
        ]
        assert cli.main(argv) == 0
        pela_cli = json.loads(capsys.readouterr().out)
        pela_tool = call_tool(
            "sparkforge_judge",
            {
                "facts_path": [str(self.FACTS)],
                "glue": "5.0",
                "source_freshness": True,
                "as_of": AS_OF,
            },
        )
        assert pela_cli["source_freshness"] == pela_tool["source_freshness"]
        assert pela_cli["freshness_policy"] == pela_tool["freshness_policy"]


class TestKnowledgePath:
    def test_sem_a_flag_nada_muda(self):
        assert set(call_tool("sparkforge_knowledge_path", {})) == {"root", "file", "available"}

    def test_documento_usa_a_data_que_ele_declara(self):
        resultado = call_tool(
            "sparkforge_knowledge_path",
            {"file": "glue/workers-and-capacity.md", "source_freshness": True, "as_of": AS_OF},
        )
        _valida("sparkforge_knowledge_path", resultado)
        assert resultado["source_freshness"]
        assert all("state" in e for e in resultado["source_freshness"].values())

    def test_sem_file_conta_por_documento(self):
        resultado = call_tool(
            "sparkforge_knowledge_path", {"source_freshness": True, "as_of": AS_OF}
        )
        _valida("sparkforge_knowledge_path", resultado)
        assert "knowledge/glue/workers-and-capacity.md" in resultado["freshness_by_doc"]
        assert "source_freshness" not in resultado
