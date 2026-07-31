import json
from pathlib import Path

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class TestReadme:
    README = None

    @classmethod
    def setup_class(cls):
        cls.README = _read("README.md")

    def test_documents_the_four_distribution_channels(self):
        for channel in ("Claude Code", "MCP", "pip", "markdown"):
            assert channel.lower() in self.README.lower(), channel

    def test_documents_devin_and_copilot_as_mcp_clients(self):
        assert "Devin" in self.README
        assert "Copilot" in self.README

    def test_documents_the_cli(self):
        assert "sparkforge" in self.README
        assert "runtime detect" in self.README
        assert "analyze pyspark" in self.README
        assert "judge" in self.README
        assert "next-step" in self.README

    def test_documents_the_handoff_flow(self):
        assert "handoff" in self.README.lower()
        assert "git add" in self.README
        assert ".sparkforge" in self.README

    def test_documents_why_artifacts_are_not_committed(self):
        assert "artifacts/**" in self.README or "artifacts/" in self.README
        assert "sha256" in self.README.lower()


class TestGuia:
    GUIA = None

    @classmethod
    def setup_class(cls):
        cls.GUIA = _read("GUIA_DE_USO.md")

    def test_documents_sparkforge_resume(self):
        assert "sparkforge resume" in self.GUIA

    def test_documents_what_is_committed_versus_not(self):
        lowered = self.GUIA.lower()
        assert "committ" in lowered
        assert "artifacts" in lowered or "artefatos" in lowered

    def test_documents_the_no_mcp_no_python_fallback(self):
        assert "rules/catalog" in self.GUIA


class TestPromptMestre:
    PROMPT = None

    @classmethod
    def setup_class(cls):
        cls.PROMPT = _read("PROMPT_INICIAL_MESTRE.md")

    def test_requires_opening_a_case(self):
        assert "case open" in self.PROMPT or "abrir o case" in self.PROMPT.lower()

    def test_references_agent_protocol(self):
        assert "AGENT_PROTOCOL.md" in self.PROMPT

    def test_requires_runtime_detection_first(self):
        assert "SF-ENV-001" in self.PROMPT

    def test_requires_fact_id_traceability(self):
        assert "fact_id" in self.PROMPT


class TestAgentsMd:
    AGENTS = None

    @classmethod
    def setup_class(cls):
        cls.AGENTS = _read("AGENTS.md")

    def test_references_agent_protocol_and_fact_finding_model(self):
        assert "AGENT_PROTOCOL.md" in self.AGENTS
        assert "Fact" in self.AGENTS
        assert "Finding" in self.AGENTS


class TestSourcesMd:
    SOURCES = None

    @classmethod
    def setup_class(cls):
        cls.SOURCES = _read("SOURCES.md")

    def test_documents_field_heuristic_origin(self):
        assert "field-heuristic" in self.SOURCES

    def test_lists_unreconfirmed_items(self):
        assert "2026-07-29" in self.SOURCES


class TestManifest:
    def test_version_is_0_4_0(self):
        manifest = json.loads(_read("manifest.json"))
        assert manifest["version"] == "0.4.0"

    def test_tools_list_equals_the_real_tools_keys(self):
        manifest = json.loads(_read("manifest.json"))
        assert set(manifest["tools"]) == set(TOOLS.keys())
        assert len(manifest["tools"]) == len(TOOLS)
