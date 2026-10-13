---
sdd: 1
feature: STREAMING_OPERATIONS_AND_SERVING
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Extrator offline único para SLO, FinOps, segurança, serving e lakehouse, com redaction e unresolved por domínio."
    tradeoffs: ["contrato precisa ser declarado", "não prova eficácia live"]
  - id: B
    summary: "Collectors live e cálculo automático de custo/segurança nesta wave."
    tradeoffs: ["cobertura aparente", "mistura credenciais, medição e julgamento no core offline"]
chosen: A
---

# STREAMING_OPERATIONS_AND_SERVING — exploração

O prompt exige operação real, mas o contrato do SparkForge separa fatos offline
de coleta live. A wave entrega um artefato declarativo auditável para SLO,
FinOps, controles de segurança, serving e formatos lakehouse; valores sensíveis,
preços e eficácia runtime permanecem unresolved.

Escopo: extrator, CLI/MCP read-only, regras, fixtures, conhecimento, skill,
matriz de serving e SDD. Fora: mutação AWS, IAM/KMS/VPC collector, benchmark e
atribuição causal de custo.
