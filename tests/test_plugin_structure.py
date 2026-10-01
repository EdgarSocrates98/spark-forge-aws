import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ("sf-open", "sf-next", "sf-resume", "sf-handoff")


class TestManifest:
    def test_manifest_is_in_the_dot_directory(self):
        assert (ROOT / ".claude-plugin" / "plugin.json").is_file()

    def test_manifest_declares_kebab_case_name_and_version(self):
        """A versao e comparada com o pacote, nao com um literal.

        Literal aqui significa que todo bump quebra este teste sem revelar nada:
        a falha que importa e o plugin anunciar uma versao diferente da que o
        `pip install` entrega. A concordancia das quatro fontes esta em
        `tests/test_package_importable.py`.
        """
        import sparkforge

        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        assert data["name"] == "sparkforge-aws"
        assert data["version"] == sparkforge.__version__
        assert data["description"]

    def test_component_dirs_are_at_root_not_inside_dot_directory(self):
        for name in ("skills", "commands"):
            assert (ROOT / name).is_dir()
            assert not (ROOT / ".claude-plugin" / name).exists()


class TestMcpConfig:
    def _config(self):
        return json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))

    def test_declares_the_sparkforge_server(self):
        assert "sparkforge" in self._config()["mcpServers"]

    def test_uses_plugin_root_variable_never_an_absolute_path(self):
        text = (ROOT / ".mcp.json").read_text(encoding="utf-8")
        assert "${CLAUDE_PLUGIN_ROOT}" in text
        assert "C:\\" not in text
        assert "/Users/" not in text
        assert "E:/" not in text

    def test_invokes_the_mcp_module_over_stdio(self):
        server = self._config()["mcpServers"]["sparkforge"]
        assert server["args"][:2] == ["-m", "sparkforge.adapters.mcp"]
        assert "stdio" in server["args"]


class TestCommands:
    def test_all_four_case_commands_exist(self):
        names = {p.stem for p in (ROOT / "commands").glob("*.md")}
        assert set(COMMANDS).issubset(names)

    def test_each_command_has_frontmatter_with_name_and_description(self):
        for name in COMMANDS:
            text = (ROOT / "commands" / f"{name}.md").read_text(encoding="utf-8")
            assert text.startswith("---")
            assert f"name: {name}" in text
            assert "description:" in text

    def test_commands_reference_the_cli_not_a_hardcoded_path(self):
        for name in COMMANDS:
            text = (ROOT / "commands" / f"{name}.md").read_text(encoding="utf-8")
            assert "sparkforge " in text
            assert "E:/" not in text
