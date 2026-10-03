---
sdd: 1
feature: FORGE_LAB_PRODUCT
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_PRODUCT/explore.md
  sha256: "2478f85928783656bea23d23691a4be2a21d16806935ad2008e1600c75c0d307"
hypothesis:
  claim: "Contratos declarativos e um runtime CLI-first tornam o Forge Lab uma fábrica reproduzível de evidências sem iniciar infraestrutura de forma implícita."
  prediction: "O mesmo cenário produzirá planos equivalentes para Compose e Testcontainers, receipts content-addressed, oracle independente e classificação explícita; ações mutáveis sem confirmação serão recusadas."
  experiment: "Validar registry, cenários, compilador, doctor, action plans, capture/oracle/receipt e CLI offline com fixtures sintéticas; executar a suíte completa somente ao final desta entrega."
acceptance:
  - id: AC1
    statement: "Registry, fidelidade, profiles, modes e imagens sem latest são validados por um contrato único."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli lab doctor --repo ."}
  - id: AC2
    statement: "Golden 20 e cenários DSL carregam, compilam para actions reutilizáveis e mantêm oracle, baseline, recovery e artefatos declarados."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli lab scenarios --repo . --json"}
  - id: AC3
    statement: "Compose e Testcontainers geram planos do mesmo cenário e nenhuma ação mutável executa sem execute e confirm explícitos."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli lab plan kafka-consumer-lag-001 --repo ."}
  - id: AC4
    statement: "Capture, receipt, oracle, promoção de fixture, classificação de resultado, blast radius e equivalência multi-engine possuem contratos offline verificáveis."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli lab verify --repo ."}
  - id: AC5
    statement: "CLI expõe doctor, profiles, scenarios, describe, plan, run, inspect, analyze, compare, promote-fixture, reproduce, up, down, gc e shell com guardas operacionais."
    verified_by: {kind: command, ref: "python -m sparkforge.adapters.cli lab --help"}
success:
  - id: SC1
    metric: "Cenários válidos / cenários declarados"
    source: "saída de sparkforge lab scenarios --json"
  - id: SC2
    metric: "Fidelidade, confirmação e unresolved preservados no plan/receipt"
    source: "JSON de lab plan e receipt"
  - id: SC3
    metric: "Comandos mutáveis recusados sem confirmação"
    source: "saída estruturada dos comandos lab up/down/run/gc/shell"
out_of_scope:
  - "Provar performance absoluta de AWS usando Docker local."
  - "Executar AWS L3, Terraform ou janitor contra contas sem opt-in, budget, TTL, região e prefixo."
  - "Baixar imagens, iniciar Docker ou acessar serviços externos durante análise offline."
  - "Alegar compatibilidade de versões não medida pelo lab."
unknowns:
  - id: U1
    blocks: [AC1, AC3]
    unlock: "Operador deve fornecer imagens pinadas e validar disponibilidade/arquitetura no host."
  - id: U2
    blocks: [AC4]
    unlock: "Uma execução L1 real deve gerar artifacts, facts, findings e receipt para promoção."
change_kinds: [extractor, tool_or_verb, dependency, knowledge_doc]
---

# FORGE_LAB_PRODUCT — requisitos

O produto deve cobrir os dez estágios do prompt: foundation, runtime, Spark/Iceberg,
Kafka/streaming, faults, Flink, CDC, observability, multi-engine lakehouse e
hardening. O núcleo deve funcionar offline em L0 e permanecer explícito sobre o
que só L1/L2/L3 pode provar.
