# Skill evals

Every canonical skill under `skills/*/` owns a `evals/evals.json` manifest in
the `skill-creator` schema shape: two realistic prompts, expected output, and
verifiable expectations.

The repository gate is intentionally offline:

```bash
python scripts/audit_skills.py --strict
python scripts/check_skill_evals.py --strict
python scripts/run_skill_evals.py --offline --out .sparkforge_aws/skill-evals.json
```

The runner checks catalog completeness and contract assertions. It does not
run a model, call AWS, estimate tokens, or claim that a skill improved model
quality. A provider benchmark requires a recorded baseline, with-skill and
without-skill transcripts, a grader, and an explicit review of assertions.
