"""Testes do runtime abstraction."""

from __future__ import annotations

from sparkforge.agentic.runtime import (
    RuntimeName,
    can_debate,
    can_spawn_parallel,
    execution_strategy,
    get_capabilities,
)


class TestRuntimeCapabilities:
    def test_claude_code_can_spawn(self):
        caps = get_capabilities(RuntimeName.CLAUDE_CODE)
        assert caps.spawn_agent
        assert caps.parallel_agents
        assert not caps.nested_agents  # subagents cannot spawn subagents

    def test_devin_cli_can_spawn(self):
        caps = get_capabilities(RuntimeName.DEVIN_CLI)
        assert caps.spawn_agent
        assert caps.parallel_agents

    def test_copilot_ci_cannot_spawn(self):
        caps = get_capabilities(RuntimeName.COPILOT_CI)
        assert not caps.spawn_agent
        assert not caps.parallel_agents

    def test_generic_is_most_restricted(self):
        caps = get_capabilities(RuntimeName.GENERIC)
        assert not caps.spawn_agent
        assert caps.max_concurrent_agents == 1

    def test_codex_cannot_spawn(self):
        caps = get_capabilities(RuntimeName.CODEX)
        assert not caps.spawn_agent


class TestCanSpawnParallel:
    def test_claude_3_agents(self):
        assert can_spawn_parallel(RuntimeName.CLAUDE_CODE, 3)

    def test_copilot_any_agents(self):
        assert not can_spawn_parallel(RuntimeName.COPILOT_CI, 2)

    def test_claude_too_many(self):
        # max_concurrent is 10
        assert not can_spawn_parallel(RuntimeName.CLAUDE_CODE, 11)


class TestCanDebate:
    def test_claude_can_debate(self):
        assert can_debate(RuntimeName.CLAUDE_CODE)

    def test_copilot_cannot_debate(self):
        assert not can_debate(RuntimeName.COPILOT_CI)

    def test_codex_cannot_debate(self):
        assert not can_debate(RuntimeName.CODEX)


class TestExecutionStrategy:
    def test_claude_parallel(self):
        assert execution_strategy(RuntimeName.CLAUDE_CODE, 3) == "parallel"

    def test_copilot_playbook(self):
        assert execution_strategy(RuntimeName.COPILOT_CI, 1) == "playbook"

    def test_codex_playbook(self):
        assert execution_strategy(RuntimeName.CODEX, 1) == "playbook"

    def test_claude_too_many_becomes_sequential(self):
        # max_concurrent=10, ask for 15 -> sequential
        assert execution_strategy(RuntimeName.CLAUDE_CODE, 15) == "sequential"


class TestParityBinding:
    """`parity.yaml` e `_MEASURED_CAPABILITIES` nao podem divergir em silencio.

    O modulo `runtime.py` declarava "parity.yaml e a fonte canonica" num
    comentario, e nada verificava: as duas fontes podiam divergir para sempre
    sem que nenhum teste caisse. Este teste amarra os DOIS campos que sao
    derivaveis do manifesto, e so eles:

    - `spawn_agent`  <-> a plataforma declara o mecanismo `subagent`
    - `tool_calling` <-> a plataforma declara o mecanismo `mcp`

    Os demais campos nao existem em `parity.yaml` (ele fala de mecanismo de
    entrega, nao de propriedade de harness) e por isso nao sao amarrados aqui
    -- afirmar que sao seria a mesma divergencia com outro nome.
    """

    @staticmethod
    def _plataformas_por_mecanismo(mecanismo: str) -> set[str]:
        import pathlib

        import yaml

        raiz = pathlib.Path(__file__).resolve().parents[1]
        manifesto = yaml.safe_load((raiz / "parity.yaml").read_text(encoding="utf-8"))
        encontradas: set[str] = set()
        for capacidade in manifesto["capabilities"]:
            for plataforma, mecanismos in (capacidade.get("platforms") or {}).items():
                if mecanismo in (mecanismos or []):
                    encontradas.add(plataforma)
        return encontradas

    def test_spawn_agent_casa_com_o_mecanismo_subagent(self):
        declara_subagent = self._plataformas_por_mecanismo("subagent")
        for runtime in RuntimeName:
            if runtime is RuntimeName.GENERIC:
                continue  # GENERIC nao e plataforma do manifesto: e o piso
            caps = get_capabilities(runtime)
            assert caps.spawn_agent == (runtime.value in declara_subagent), (
                f"{runtime.value}: runtime.py diz spawn_agent={caps.spawn_agent}, "
                f"parity.yaml {'declara' if runtime.value in declara_subagent else 'nao declara'} "
                f"o mecanismo `subagent`"
            )

    def test_tool_calling_casa_com_o_mecanismo_mcp(self):
        declara_mcp = self._plataformas_por_mecanismo("mcp")
        for runtime in RuntimeName:
            if runtime is RuntimeName.GENERIC:
                continue
            caps = get_capabilities(runtime)
            assert caps.tool_calling == (runtime.value in declara_mcp), (
                f"{runtime.value}: runtime.py diz tool_calling={caps.tool_calling}, "
                f"parity.yaml {'declara' if runtime.value in declara_mcp else 'nao declara'} "
                f"o mecanismo `mcp`"
            )

    def test_todo_runtime_menos_generic_e_plataforma_do_manifesto(self):
        import pathlib

        import yaml

        raiz = pathlib.Path(__file__).resolve().parents[1]
        manifesto = yaml.safe_load((raiz / "parity.yaml").read_text(encoding="utf-8"))
        plataformas = set(manifesto["platforms"])
        for runtime in RuntimeName:
            if runtime is RuntimeName.GENERIC:
                continue
            assert runtime.value in plataformas, (
                f"{runtime.value} existe em RuntimeName e nao em parity.yaml.platforms"
            )

    def test_paralelismo_exige_spawn(self):
        # Invariante interna: nao ha agente paralelo sem despacho de agente.
        for runtime in RuntimeName:
            caps = get_capabilities(runtime)
            if caps.parallel_agents:
                assert caps.spawn_agent, f"{runtime.value}: parallel_agents sem spawn_agent"
