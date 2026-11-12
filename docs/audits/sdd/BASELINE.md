# SDD Baseline — spark-forge-aws (Onda 0)

- SHA `37d0791c67e7` · branch `release/cycle-2.7-patch-version` · `.git` present · ~135 dirty files (pré-existentes)
- Python ≥3.10 · ~118 testes test_sdd.py + ac_vermelho(9) + operator(7) + skills(12) + migration(5) + eval_suite(5) + fixtures(5)
- SDD maduro: `sparkforge_aws/sdd/` checks(874ln)/load/stamp/status/schema(7)/change_kinds(19) — contrato travado por AST test
- 6 skills canônicas completas (SKILL.md + evals + refs + scripts); mirrors via sync_skills.py; parity CI
- CLI `sdd {check|status|stamp}` + MCP `sparkforge_aws_sdd_*` (readOnly + journaled stamp)

## Findings (gaps vs checklist do prompt)

| # | Sev | Finding | Evidência |
|---|---|---|---|
| G1 | P1 | Sem convergência: `ship.deviations` free-text; sem taxonomia missing/partial/contradicts/unrequested/unverified/stale; sem release receipt | ship gate; sdd-ship SKILL:78 |
| G2 | P1 | `plan.files` não conferido vs `design.files` — "plano não inventa arquivo" é prosa | checks.py:773 (sem gate) |
| G3 | P1 | Build evidence declarativa — red/green hand-written; gate checa citação, não execução; sem TestExecutionReceipt/baseline SHA/checkpoint | CONTRATO.md:123 admite |
| G4 | P1 | Explore sem decision tree/frontier/modes/facts-vs-decisions/contradições/resume | sdd-explore SKILL |
| G5 | P1 | Design sem ADR/threat model/contracts/data model/research/quickstart/impact artifact | sdd-design SKILL |
| G6 | P1 | Define sem user stories/FR-NFR IDs/constitution/quality checklist | sdd-define SKILL |
| G7 | P1 | Plan sem DAG/depends_on/safe parallelism/risk class | sdd-plan SKILL |
| D1 | P2 | README lista `sparkforge_sdd_*` mas tools são `sparkforge_aws_sdd_*` | docs/sdd/README.md:40 |
| D2 | P2 | evals.json das 6 skills = boilerplate idêntico (2 evals genéricos) | skills/sdd-*/evals/ |
| D3 | P2 | dev-profile task com proof+sem test → double refusal (um defeito, dois códigos) | checks.py:466-477 |
| D4 | P2 | README "64 features" stale vs ~80 | docs/sdd/README.md:30 |
| D5 | P2 | acceptance_never_red conta pytest exit 3/4 como red — documentado | checks.py:526 |
| D6 | P2 | eval baseline N=2 | evals/agentic/sdd/README |

## Capacidades preservadas

Engine de gates completa (25+ refusal codes catalogados), AST contract lock, hash cascade, TDD red-gate, operator profile + sandbox + case/change/funcval, MCP tools + journal, sync_skills byte-parity, sem-git support.
