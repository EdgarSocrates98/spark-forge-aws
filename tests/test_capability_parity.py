from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("claude_code", "devin_desktop", "devin_cli", "copilot_ci")
MECHANISMS = ("mcp", "cli", "files")


def manifest():
    return yaml.safe_load((ROOT / "parity.yaml").read_text(encoding="utf-8"))


class TestManifestShape:
    def test_exists(self):
        assert (ROOT / "parity.yaml").is_file()

    def test_declares_the_four_platforms(self):
        assert tuple(manifest()["platforms"]) == PLATFORMS

    def test_declares_the_three_mechanisms(self):
        assert tuple(manifest()["mechanisms"]) == MECHANISMS


class TestEveryCapabilityHasAPathEverywhere:
    def test_no_capability_is_missing_a_platform(self):
        gaps = []
        for capability in manifest()["capabilities"]:
            for platform in PLATFORMS:
                if not capability["platforms"].get(platform):
                    gaps.append(f"{capability['name']} sem {platform}")
        assert not gaps, gaps

    def test_every_declared_mechanism_is_known(self):
        for capability in manifest()["capabilities"]:
            for platform, mechanisms in capability["platforms"].items():
                for mechanism in mechanisms:
                    assert mechanism in MECHANISMS, (capability["name"], platform, mechanism)

    def test_every_capability_reaches_the_files_rung(self):
        """Terceiro degrau: sem MCP e sem Python, o conhecimento ainda chega."""
        for capability in manifest()["capabilities"]:
            for platform in PLATFORMS:
                assert "files" in capability["platforms"][platform], capability["name"]


class TestManifestMatchesReality:
    def test_every_declared_tool_exists_in_the_tool_surface(self):
        from sparkforge.adapters.tools import TOOLS

        for capability in manifest()["capabilities"]:
            for tool in capability.get("tools") or []:
                assert tool in TOOLS, tool

    def test_every_declared_cli_verb_is_reachable(self):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        subparsers = next(
            a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
        )
        available = set(subparsers.choices)
        for capability in manifest()["capabilities"]:
            for verb in capability.get("cli") or []:
                assert verb.split()[0] in available, verb

    def test_every_declared_knowledge_file_exists(self):
        for capability in manifest()["capabilities"]:
            for path in capability.get("knowledge") or []:
                assert (ROOT / path).is_file(), path

    def test_every_phase_zero_tool_appears_in_some_capability(self):
        """Tool que nao aparece no manifesto e capacidade nao declarada."""
        from sparkforge.adapters.tools import TOOLS

        declared = {t for c in manifest()["capabilities"] for t in (c.get("tools") or [])}
        assert set(TOOLS) - declared == set()
