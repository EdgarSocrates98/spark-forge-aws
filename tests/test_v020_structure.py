from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "design-incremental-processing",
    "optimize-latest-per-key",
    "analyze-batch-loop",
    "analyze-library-call-graph",
    "review-glue-terraform",
    "diagnose-oom",
    "optimize-variable-volume-job",
    "glue-incremental-performance-architect",
]

def test_master_prompt_exists():
    assert (ROOT / "PROMPT_INICIAL_MESTRE.md").exists()
    assert (ROOT / "GUIA_DE_USO.md").exists()

def test_advanced_skills_exist_on_all_platforms():
    for skill in REQUIRED:
        assert (ROOT / "skills" / skill / "SKILL.md").exists()
        assert (ROOT / ".claude" / "skills" / skill / "SKILL.md").exists()
        assert (ROOT / ".agents" / "skills" / skill / "SKILL.md").exists()

def test_orchestrator_agents_exist():
    name = "glue-incremental-performance-architect"
    assert (ROOT / ".claude" / "agents" / f"{name}.md").exists()
    assert (ROOT / ".github" / "agents" / f"{name}.agent.md").exists()
