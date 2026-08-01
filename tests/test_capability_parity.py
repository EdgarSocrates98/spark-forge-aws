from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("claude_code", "devin_desktop", "devin_cli", "codex", "copilot_ci")
MECHANISMS = ("mcp", "cli", "files", "playbook")


def manifest():
    return yaml.safe_load((ROOT / "parity.yaml").read_text(encoding="utf-8"))


class TestManifestShape:
    def test_exists(self):
        assert (ROOT / "parity.yaml").is_file()

    def test_declares_the_five_platforms(self):
        assert tuple(manifest()["platforms"]) == PLATFORMS

    def test_declares_the_four_mechanisms(self):
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


class TestNoCliVerbIsAnUndeclaredMcpGap:
    """A reciproca de `TestManifestMatchesReality`: nao basta cada verbo
    DECLARADO em parity.yaml existir de verdade -- todo verbo que a CLI real
    (`build_parser()`) de fato expoe precisa aparecer em alguma capacidade do
    manifesto, e essa capacidade precisa ter pelo menos um tool MCP, a menos
    que a ausencia esteja documentada e justificada aqui. Sem este teste, um
    verbo novo pode ser adicionado a `cli.py` sem que nada perceba que ficou
    fora do alcance do MCP -- exatamente a classe de drift que esta fase
    existe para fechar."""

    ALLOWED_CLI_ONLY = {
        # `resume` e `handoff` sao a MESMA capacidade em parity.yaml (o mesmo
        # payload de `_core.resume_case`): `handoff` so acrescenta a escrita
        # de um markdown em disco para commit no git, o que nao faz sentido
        # para um cliente MCP -- ele ja recebe o payload estruturado direto
        # via `sparkforge_resume`, sem precisar de um artefato em arquivo.
        "handoff": (
            "mesma capacidade que 'resume'; escreve markdown em disco, sem uso "
            "para um cliente MCP."
        ),
        # CLI `validate` valida um ARQUIVO de findings (JSON no disco);
        # `sparkforge_validate_output` valida um finding inline -- mesma
        # `_core.validate_output` por baixo, granularidade de I/O diferente
        # porque um cliente MCP ja tem o finding em mao, nunca um arquivo no
        # disco do lado do host MCP.
        "validate": (
            "mesma _core.validate_output que sparkforge_validate_output, so que "
            "sobre arquivo."
        ),
    }

    def _leaf_cli_verbs(self):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        sub = next(
            a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
        )
        leaves = []
        for name, subparser in sub.choices.items():
            nested = next(
                (
                    a
                    for a in subparser._actions  # noqa: SLF001
                    if hasattr(a, "choices") and a.choices
                ),
                None,
            )
            if nested:
                leaves.extend(f"{name} {leaf}" for leaf in sorted(nested.choices))
            else:
                leaves.append(name)
        return leaves

    def test_every_cli_verb_has_an_mcp_tool_or_a_declared_reason(self):
        from sparkforge.adapters.tools import TOOLS

        declared_cli_to_tools: dict[str, set[str]] = {}
        for capability in manifest()["capabilities"]:
            tools = set(capability.get("tools") or [])
            for verb in capability.get("cli") or []:
                declared_cli_to_tools.setdefault(verb, set()).update(tools)

        gaps = []
        for verb in self._leaf_cli_verbs():
            if verb in self.ALLOWED_CLI_ONLY:
                continue
            tools = declared_cli_to_tools.get(verb) or set()
            if not (tools & set(TOOLS)):
                gaps.append(verb)
        assert not gaps, gaps


class TestOrchestrationParity:
    """A capacidade que faltava no manifesto.

    Os 3 agentes eram espelhados com byte-identidade travada, mas nada
    verificava que "coordenar investigacao" tinha caminho por plataforma --
    exatamente o que o gate da secao 8.4 da Fase 0 existe para pegar. Agentes
    escaparam dele porque agente nao era mecanismo declarado.
    """

    def test_codex_is_a_declared_platform(self):
        assert "codex" in manifest()["platforms"]

    def test_playbook_is_a_declared_mechanism(self):
        assert "playbook" in manifest()["mechanisms"]

    def test_coordination_capability_exists(self):
        names = [c["name"] for c in manifest()["capabilities"]]
        assert any("coorden" in n.lower() for n in names), names

    def test_coordination_reaches_every_platform(self):
        capability = next(
            c for c in manifest()["capabilities"] if "coorden" in c["name"].lower()
        )
        for platform in manifest()["platforms"]:
            assert capability["platforms"].get(platform), platform

    def test_only_claude_code_claims_subagent_dispatch(self):
        """Despacho de subagente e capacidade de HARNESS. Declarar para outra
        plataforma seria afirmar paridade que nao existe -- o defeito exato do
        transporte HTTP na Fase 1, que `parity.yaml` afirmava e nenhum teste
        tocava."""
        capability = next(
            c for c in manifest()["capabilities"] if "coorden" in c["name"].lower()
        )
        for platform, mechanisms in capability["platforms"].items():
            if platform != "claude_code":
                assert "subagent" not in mechanisms, platform


class TestNoRuntimeAxisIsAnUndeclaredFlagGap:
    """Paridade um nivel abaixo do verbo: a SUPERFICIE DE CADA VERBO.

    `TestNoCliVerbIsAnUndeclaredMcpGap` pergunta se todo verbo alcanca o MCP, e
    nao percebeu que `--emr` faltava nos tres verbos que aceitam runtime -- o
    eixo `emr` entrou em `RuntimeContext` na Fase 5b e ficou so como saida.
    Assimetria de superficie e o tipo de coisa que ninguem percebe ate
    precisar: quem SABE a release e nao tem dump nao tinha como declara-la, nem
    pela CLI nem pelo MCP.

    O conjunto esperado e derivado do proprio `RuntimeContext`, nunca de uma
    lista literal aqui: eixo novo no contexto passa a exigir flag e propriedade
    de tool no mesmo commit, em vez de virar a mesma divida de novo.
    """

    # verbo da CLI -> tool MCP que espelha a mesma funcao de `_core`.
    VERBS = {
        ("judge",): "sparkforge_judge",
        ("case", "open"): "sparkforge_case_open",
        ("runtime", "detect"): "sparkforge_runtime_detect",
    }

    def _runtime_axes(self):
        from sparkforge.findings.models import RuntimeContext

        # `detected_from` e `divergences` sao SAIDA -- o que a deteccao concluiu
        # sobre si mesma --, nunca entrada declaravel.
        return set(RuntimeContext().to_dict()) - {"detected_from", "divergences"}

    def _subparser(self, path):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        for name in path:
            sub = next(
                a for a in parser._actions if hasattr(a, "choices") and a.choices  # noqa: SLF001
            )
            parser = sub.choices[name]
        return parser

    def test_every_runtime_axis_is_declarable_on_the_cli(self):
        axes = self._runtime_axes()
        for path in self.VERBS:
            flags = {
                option.lstrip("-")
                for action in self._subparser(path)._actions  # noqa: SLF001
                for option in action.option_strings
            }
            assert axes <= flags, (" ".join(path), sorted(axes - flags))

    def test_every_runtime_axis_is_declarable_over_mcp(self):
        from sparkforge.adapters.tools import TOOLS

        axes = self._runtime_axes()
        for tool in self.VERBS.values():
            properties = set(TOOLS[tool]["inputSchema"]["properties"])
            assert axes <= properties, (tool, sorted(axes - properties))

    def test_the_cli_and_the_tool_expose_the_same_axes(self):
        """Nao basta os dois cobrirem o contexto: eles precisam cobrir o MESMO
        conjunto. Um eixo so na CLI e a assimetria de novo, virada do avesso."""
        from sparkforge.adapters.tools import TOOLS

        axes = self._runtime_axes()
        for path, tool in self.VERBS.items():
            flags = {
                option.lstrip("-")
                for action in self._subparser(path)._actions  # noqa: SLF001
                for option in action.option_strings
            } & axes
            properties = set(TOOLS[tool]["inputSchema"]["properties"]) & axes
            assert flags == properties, (" ".join(path), tool)
