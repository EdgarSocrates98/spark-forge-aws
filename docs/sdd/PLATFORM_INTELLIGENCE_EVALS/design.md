---
sdd: 1
feature: PLATFORM_INTELLIGENCE_EVALS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_EVALS/define.md
  sha256: "311f6b09cbd8bac73f08ea1f52b71b5df81081d77e36e2a21ac2b2ad4e74f58b"
files:
  - {path: evals/platform_intelligence/suite.yaml, action: create, reason: "Contrato e seed pack de evals do Control Plane."}
  - {path: scripts/check_platform_eval_contract.py, action: create, reason: "Validador offline do contrato de eval."}
  - {path: tests/test_platform_evals.py, action: create, reason: "Guarda do shape da suite."}
  - {path: docs/knowledge/platform-intelligence-evals.md, action: create, reason: "Política de qualidade/economia."}
decisions:
  - id: D1
    choice: "Seed cases preservam gabarito de fatos/finding proibido/unresolved/evidence/routing."
    rejected: ["score somente texto final", "gabarito implícito por LLM"]
    rollback: "git revert do contrato e do script."
  - id: D2
    choice: "Provider token depende de transcript do host; bytes não viram tokens por fórmula."
    rejected: ["estimar token por tamanho", "atribuir custo sem cost_basis"]
    rollback: "git revert da política de economia."
covers:
  - {part: "eval contract", acceptance: [AC1, AC2]}
---

# PLATFORM_INTELLIGENCE_EVALS — desenho

```text
suite.yaml -> offline contract checker -> valid/invalid case report
                                      -> quality axes + economy axes
                                      -> future runner / host transcript
```
