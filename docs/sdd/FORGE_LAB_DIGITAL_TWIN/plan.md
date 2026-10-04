---
sdd: 1
feature: FORGE_LAB_DIGITAL_TWIN
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/FORGE_LAB_DIGITAL_TWIN/design.md
  sha256: "5f31ec5b3a12de463f6b77b6ef32e318cf1d92cea2222b5cf2f8cff9fd15580b"
tasks:
  - id: T1
    files: [sparkforge/lab/__init__.py, sparkforge/lab/spec.py, labs/forge-lab/lab.yaml, tests/test_forge_lab.py]
    covers: [AC1]
    test: {path: tests/test_forge_lab.py, name: test_forge_lab_validates_topology_and_scenarios}
  - id: T2
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, parity.yaml, labs/forge-lab/compose.yaml]
    covers: [AC2]
    test: {path: tests/test_forge_lab.py, name: test_forge_lab_analysis_is_offline_and_structured}
  - id: T3
    files: [labs/forge-lab/README.md, docs/knowledge/forge-lab-digital-twin.md]
    covers: [AC2]
    test: {path: tests/test_forge_lab.py, name: test_forge_lab_docs_match_declared_scenarios}
---

# FORGE_LAB_DIGITAL_TWIN — plano

## T1 — contrato offline

Criar loader YAML, validar referências, produzir ordem topológica e preservar
unresolved. Escrever teste antes de implementação; não executar suíte nesta
rodada.

Commit: `feat(lab): add forge lab topology contract`

## T2 — análise e blueprint

Adicionar CLI/MCP compartilhados, declarar paridade e criar Compose com profiles
Kafka, Flink, Spark, Iceberg REST, Polaris, MinIO, PostgreSQL/Debezium e
Prometheus. Imagens ficam parametrizadas por variáveis do operador.

Commit: `feat(lab): expose offline forge lab analysis`

## T3 — operação segura

Documentar quickstart, cenários e limites; nenhum comando do SparkForge executa
failure injection.

Commit: `docs(lab): document forge lab digital twin`
