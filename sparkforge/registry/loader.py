"""Canonical Registry Loader.

Loads, parses, and validates canonical manifests for agents, skills, tools, teams, and workflows.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.registry.models import (
    AgentManifest,
    EvalManifest,
    KnowledgeManifest,
    PolicyManifest,
    RiskLevel,
    SkillManifest,
    TeamManifest,
    ToolManifest,
    WorkflowManifest,
)


class RegistryError(Exception):
    """Raised when a registry manifest is invalid or missing."""


class CanonicalRegistry:
    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or Path.cwd()
        self.agents: dict[str, AgentManifest] = {}
        self.skills: dict[str, SkillManifest] = {}
        self.tools: dict[str, ToolManifest] = {}
        self.teams: dict[str, TeamManifest] = {}
        self.workflows: dict[str, WorkflowManifest] = {}
        self.knowledge: dict[str, KnowledgeManifest] = {}
        self.policies: dict[str, PolicyManifest] = {}
        self.evals: dict[str, EvalManifest] = {}

    def register_agent(self, agent: AgentManifest) -> None:
        self.agents[agent.id] = agent

    def register_skill(self, skill: SkillManifest) -> None:
        self.skills[skill.id] = skill

    def register_tool(self, tool: ToolManifest) -> None:
        self.tools[tool.id] = tool

    def register_team(self, team: TeamManifest) -> None:
        self.teams[team.id] = team

    def register_workflow(self, workflow: WorkflowManifest) -> None:
        self.workflows[workflow.id] = workflow

    def get_agent(self, agent_id: str) -> AgentManifest | None:
        return self.agents.get(agent_id)

    def get_skill(self, skill_id: str) -> SkillManifest | None:
        return self.skills.get(skill_id)

    def get_tool(self, tool_id: str) -> ToolManifest | None:
        return self.tools.get(tool_id)

    def get_team(self, team_id: str) -> TeamManifest | None:
        return self.teams.get(team_id)

    def get_workflow(self, workflow_id: str) -> WorkflowManifest | None:
        return self.workflows.get(workflow_id)

    def load_from_configs(self) -> None:
        """Loads and converts existing configs into canonical models."""
        # 1. Load config/agents.yaml
        agents_yaml_path = self.root_dir / "config" / "agents.yaml"
        if agents_yaml_path.is_file():
            try:
                data = yaml.safe_load(agents_yaml_path.read_text(encoding="utf-8")) or {}
                raw_agents = data.get("agents", [])
                for a in raw_agents:
                    agent_id = a.get("name", "")
                    if not agent_id:
                        continue
                    manifest = AgentManifest(
                        id=agent_id,
                        name=agent_id,
                        version="1.0.0",
                        description=f"Agent specialist for {a.get('role', 'data engineering')}",
                        purpose=a.get("role", "data engineering"),
                        role=a.get("role", "specialist"),
                        allowed_tools=a.get("allowed_tools", []),
                        knowledge_refs=a.get("knowledge_refs", []),
                        risk_level=RiskLevel.READ_ONLY,
                    )
                    self.register_agent(manifest)
            except Exception as e:
                raise RegistryError(f"Failed to load {agents_yaml_path}: {e}") from e

        # 1b. Load agents from agents/*.md
        agents_dir = self.root_dir / "agents"
        if agents_dir.is_dir():
            for agent_file in agents_dir.glob("*.md"):
                agent_id = agent_file.stem
                if agent_id not in self.agents:
                    manifest = AgentManifest(
                        id=agent_id,
                        name=agent_id,
                        version="1.0.0",
                        description=f"Coordinator agent for {agent_id}",
                        purpose=agent_id,
                        role="coordinator",
                        risk_level=RiskLevel.READ_ONLY,
                    )
                    self.register_agent(manifest)

        # 2. Load config/teams-expansion.yaml
        teams_yaml_path = self.root_dir / "config" / "teams-expansion.yaml"
        if teams_yaml_path.is_file():
            try:
                data = yaml.safe_load(teams_yaml_path.read_text(encoding="utf-8")) or {}
                raw_teams = data.get("teams", [])
                for t in raw_teams:
                    team_id = t.get("name", "")
                    if not team_id:
                        continue
                    manifest = TeamManifest(
                        id=team_id,
                        name=team_id,
                        coordinator=t.get("coordinator", ""),
                        members=t.get("members", []),
                        handoffs=t.get("handoffs", []),
                    )
                    self.register_team(manifest)
            except Exception as e:
                raise RegistryError(f"Failed to load {teams_yaml_path}: {e}") from e

        # 3. Load skills from skills/ directory
        skills_dir = self.root_dir / "skills"
        if skills_dir.is_dir():
            for skill_path in sorted(skills_dir.iterdir()):
                if skill_path.is_dir():
                    skill_file = skill_path / "SKILL.md"
                    skill_id = skill_path.name
                    desc = f"Skill {skill_id} for AWS and PySpark data workloads."
                    if skill_file.is_file():
                        # Extract first paragraph as description
                        content = skill_file.read_text(encoding="utf-8", errors="ignore")
                        lines = [
                            ln.strip()
                            for ln in content.splitlines()
                            if ln.strip() and not ln.startswith("#")
                        ]
                        if lines:
                            desc = lines[0][:150]
                    manifest = SkillManifest(
                        id=skill_id,
                        name=skill_id,
                        version="1.0.0",
                        description=desc,
                        procedure_path=str(skill_file.relative_to(self.root_dir))
                        if skill_file.is_file()
                        else "",
                    )
                    self.register_skill(manifest)


_DEFAULT_REGISTRY: CanonicalRegistry | None = None


def get_default_registry(root_dir: Path | None = None) -> CanonicalRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        reg = CanonicalRegistry(root_dir=root_dir)
        reg.load_from_configs()
        _DEFAULT_REGISTRY = reg
    return _DEFAULT_REGISTRY
