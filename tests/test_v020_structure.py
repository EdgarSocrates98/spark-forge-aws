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
    assert (ROOT / ".claude" / "agents" / "glue-incremental-performance-architect.md").exists()
    assert (ROOT / ".github" / "agents" / "glue-incremental-performance-architect.agent.md").exists()
