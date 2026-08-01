import filecmp
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
NAMES = tuple(sorted(p.stem for p in AGENTS.glob("*.md")))


class TestSingleSource:
    def test_agents_dir_is_not_empty(self):
        """Antes este teste fixava os tres nomes literais. Lista fixa obriga a
        editar o teste a cada coordenador novo, e -- pior -- nao pega o caso que
        importa, que e um agente parar de ser espelhado. A byte-identidade dos
        espelhos e o invariante; o nome nao e."""
        assert len(NAMES) >= 3

    def test_each_agent_has_name_description_and_tools(self):
        for name in NAMES:
            text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
            assert text.startswith("---")
            assert f"name: {name}" in text
            assert "description:" in text
            assert "tools:" in text

    def test_each_agent_references_the_protocol(self):
        for name in NAMES:
            assert "AGENT_PROTOCOL.md" in (AGENTS / f"{name}.md").read_text(encoding="utf-8")

    def test_copilot_name_drift_is_gone(self):
        """spark-performance-engineer era o nome divergente no Copilot."""
        assert not (ROOT / ".github" / "agents" / "spark-performance-engineer.agent.md").exists()


class TestProtocol:
    def _text(self):
        return (ROOT / "AGENT_PROTOCOL.md").read_text(encoding="utf-8")

    def test_protocol_exists(self):
        assert (ROOT / "AGENT_PROTOCOL.md").is_file()

    def test_declares_the_nine_hard_rules(self):
        text = self._text()
        for marker in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."):
            assert marker in text

    def test_forbids_numbers_without_a_fact(self):
        assert "fact_id" in self._text()

    def test_requires_next_step_before_choosing_a_skill(self):
        assert "next_step" in self._text()

    def test_requires_rules_lookup_instead_of_memory(self):
        assert "rules_lookup" in self._text()

    def test_requires_validate_output_before_presenting(self):
        assert "validate_output" in self._text()

    def test_requires_reporting_unresolved(self):
        assert "unresolved" in self._text()

    def test_requires_explicit_confirmation_for_destructive_maintenance(self):
        text = self._text()
        assert "expire_snapshots" in text
        assert "remove_orphan_files" in text


class TestMirrors:
    def test_sync_check_passes_after_sync(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_skills.py")],
            check=True, capture_output=True, cwd=ROOT,
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_skills.py"), "--check"],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0, result.stdout

    def test_claude_agents_mirror_matches_source(self):
        for name in NAMES:
            dst = ROOT / ".claude" / "agents" / f"{name}.md"
            assert dst.is_file()
            assert filecmp.cmp(AGENTS / f"{name}.md", dst, shallow=False), name

    def test_copilot_agents_mirror_exists_with_agent_md_suffix(self):
        for name in NAMES:
            assert (ROOT / ".github" / "agents" / f"{name}.agent.md").is_file()

    def test_devin_agents_mirror_matches_source(self):
        for name in NAMES:
            dst = ROOT / ".agents" / "agents" / f"{name}.md"
            assert filecmp.cmp(AGENTS / f"{name}.md", dst, shallow=False), name


class TestNoPlatformKnowledge:
    """Conhecimento nao pode viver em diretorio de plataforma, senao o drift volta."""

    FORBIDDEN = ("threshold:", "runtime_scope:", "retrieved:")

    def test_platform_dirs_carry_no_thresholds_or_sources(self):
        offenders = []
        for platform in (".claude", ".agents", ".github"):
            for path in (ROOT / platform).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for marker in self.FORBIDDEN:
                    if marker in text:
                        offenders.append(f"{path.relative_to(ROOT)}: {marker}")
        assert not offenders, offenders
