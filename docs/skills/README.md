# SparkForge skills — quality contract

`skills/` is canonical. `.claude/skills/` and `.agents/skills/` are rendered by
`python scripts/sync_skills.py`; never edit those mirrors by hand.

The catalog currently contains 52 skills. Every skill now publishes:

- `metadata.sparkforge_aws_contract: v1` with primary verbs and local references;
- a shared evidence-first delivery contract in its `SKILL.md`;
- `references/README.md` linking the shared contract and versioned repository
  knowledge;
- `scripts/validate_evidence.py`, an offline recommendation-envelope checker;
- `evals/evals.json`, two realistic cases in the `skill-creator` schema.

## Gates

```bash
python scripts/upgrade_skills.py --check
python scripts/audit_skills.py --strict
python scripts/check_skill_evals.py --strict
python scripts/run_skill_evals.py --offline --out .sparkforge_aws/skill-evals.json
python scripts/sync_skills.py --check
```

Validate frontmatter with local `skill-creator` checker:

```powershell
Get-ChildItem skills -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } | ForEach-Object { python -X utf8 $env:USERPROFILE\.agents\skills\skill-creator\scripts\quick_validate.py $_.FullName }
```

`run_skill_evals.py` is a deterministic contract gate. It does not invoke a
provider, AWS, MCP, or network. A real model benchmark needs separate
with-skill/baseline transcripts, a grader, and a review of assertion quality;
this repository does not turn the offline pass count into a model-quality or
cost claim.

## Authoring a new skill

1. Add canonical `skills/<name>/SKILL.md` with `Use quando` trigger description.
2. Run `python scripts/upgrade_skills.py` to create the shared assets.
3. Replace generic eval prompts with artifact-specific cases and assertions.
4. Run the gates above, then `python scripts/sync_skills.py`.
5. Regenerate reference pages and surface locks required by the change map.

Use `skills/_shared/references/evidence-first.md` for fact/finding boundaries,
`operational-safety.md` for AWS writes and authorization, and
`evaluation-contract.md` for eval design.
