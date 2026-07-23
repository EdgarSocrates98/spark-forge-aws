from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_all_skills_have_skill_md():
    skill_dirs = [p for p in (ROOT / "skills").iterdir() if p.is_dir()]
    assert skill_dirs
    for directory in skill_dirs:
        assert (directory / "SKILL.md").exists()

def test_platform_adapters_exist():
    assert (ROOT / ".claude" / "skills").exists()
    assert (ROOT / ".agents" / "skills").exists()
    assert (ROOT / ".github" / "copilot-instructions.md").exists()
