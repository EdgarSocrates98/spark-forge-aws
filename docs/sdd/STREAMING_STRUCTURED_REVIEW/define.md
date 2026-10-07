---
sdd: 1
feature: STREAMING_STRUCTURED_REVIEW
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_STRUCTURED_REVIEW/explore.md
  sha256: "7c61a172527b1628f3b8282db88da1f5d7b58edbb83c0e8bcddfc42e15991811"
hypothesis:
  claim: "Um workflow dedicado reduz diagnóstico incompleto ao separar declaração, medida temporal e resultado funcional."
  prediction: "A skill orienta os analyzers corretos, preserva unresolved e impede claims de exactly-once/ganho sem prova."
  experiment: "Eval manifest, auditoria de skill, renderização dos mirrors e smoke dos verbs documentados."
acceptance:
  - id: AC1
    statement: "A skill referencia source, progress, integrations e judge com limites offline claros."
    verified_by: {kind: command, ref: python scripts/audit_skills.py --strict}
  - id: AC2
    statement: "Skill tem evals executáveis pelo contrato e validador de evidence."
    verified_by: {kind: command, ref: python scripts/check_skill_evals.py --strict}
  - id: AC3
    statement: "Coordenador e mirrors publicam o workflow sem drift."
    verified_by: {kind: command, ref: python scripts/sync_skills.py --check}
  - id: AC4
    statement: "Contagens, superfície, documentação e SDD permanecem verdes."
    verified_by: {kind: command, ref: python scripts/check_status_numbers.py --strict}
success:
  - id: SC1
    metric: "AC1–AC4 verdes"
    source: "gates determinísticos do repositório"
out_of_scope:
  - "execução Spark, AWS/Kafka/Flink live, replay e benchmark"
  - "prova funcional end-to-end sem artefato de resultado"
unknowns:
  - id: U1
    blocks: [AC4]
    unlock: "Regenerar mirrors, referências e surface/status counts."
change_kinds: [agent_or_skill, status_numbers]
---

# STREAMING_STRUCTURED_REVIEW — definição
