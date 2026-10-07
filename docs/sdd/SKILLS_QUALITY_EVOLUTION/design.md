---
sdd: 1
feature: SKILLS_QUALITY_EVOLUTION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/SKILLS_QUALITY_EVOLUTION/define.md
  sha256: "9331532ae7a17c6039b2ea55edc1a145391b51265475845b5ac97f50fcdce128"
files:
  - {path: skills, action: modify, reason: "contrato v1 e assets de todas as skills canônicas"}
  - {path: skills/_shared, action: create, reason: "referências e validador compartilhados"}
  - {path: scripts/upgrade_skills.py, action: create, reason: "geração determinística e idempotente dos assets"}
  - {path: scripts/audit_skills.py, action: create, reason: "auditoria fail-closed do catálogo"}
  - {path: scripts/check_skill_evals.py, action: create, reason: "gate do schema e cobertura de evals"}
  - {path: scripts/run_skill_evals.py, action: create, reason: "runner offline sem provider/AWS"}
  - {path: evals/skills, action: create, reason: "documentação do contrato de eval"}
  - {path: docs/skills, action: create, reason: "guia e relatório de qualidade"}
  - {path: tests/test_skill_quality.py, action: create, reason: "regressão dos 52 contratos e 104 casos"}
  - {path: .claude/skills, action: modify, reason: "espelho gerado"}
  - {path: .agents/skills, action: modify, reason: "espelho gerado com despacho"}
  - {path: docs/guia/referencia/skills, action: modify, reason: "referências geradas a partir da fonte"}
  - {path: docs/surface.lock.json, action: modify, reason: "bytes da superfície atualizados"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "métricas de código relidas após scripts Python"}
  - {path: docs/claims.lock.json, action: modify, reason: "claims e provas atualizados"}
decisions:
  - id: D1
    choice: "Manter skills específicas e adicionar contrato v1 comum, em vez de substituir cada procedimento por um template genérico."
    rejected: ["Reescrever as 52 skills do zero; perderia conhecimento e aumentaria risco de drift sem prova."]
    rollback: "git revert dos commits da feature e python scripts/sync_skills.py"
  - id: D2
    choice: "Usar evals/evals.json por skill no schema skill-creator e um runner offline de contrato."
    rejected: ["Afirmar benchmark de modelo sem transcripts; não mede qualidade e violaria o offline-first."]
    rollback: "Remover evals/skills, manifests gerados e scripts de eval; manter apenas as skills fonte se desejado."
  - id: D3
    choice: "Gerar espelhos, páginas e locks por scripts existentes e novos gates."
    rejected: ["Editar espelhos à mão; isso cria drift silencioso entre Claude, Devin e fonte."]
    rollback: "python scripts/sync_skills.py e git revert dos artefatos gerados"
covers:
  - {part: "contrato comum e auditoria", acceptance: [AC1]}
  - {part: "manifests e runner offline", acceptance: [AC2, AC3]}
  - {part: "espelhos", acceptance: [AC4]}
  - {part: "docs e locks", acceptance: [AC5]}
  - {part: "bateria final", acceptance: [AC6]}
---

# SKILLS_QUALITY_EVOLUTION — desenho

O desenho é offline-first e fail-closed: `skills/` é fonte, `upgrade_skills.py`
é idempotente, `sync_skills.py` renderiza os alvos e os scripts de auditoria
validam caminhos, schema, cobertura e ausência de `expected_gain`.

Conhecimento usado: `docs/sdd/README.md`,
`skills/_shared/references/evidence-first.md`,
`knowledge/offline-policy.md` e o schema local do skill-creator.
