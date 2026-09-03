"""Testes do runtime abstraction."""
from __future__ import annotations

from sparkforge.agentic.runtime import (
    RuntimeCapabilities,
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
