---
sdd: 1
feature: PLATFORM_INTELLIGENCE_GRAPH
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_GRAPH/design.md
  sha256: "f1cf1e23f7b7332b61aecde452a0d4865daff898961e85f8a466f550ff125722"
tasks:
  - id: T1
    files: [sparkforge/platform/__init__.py, sparkforge/platform/graph.py, contracts/platform-graph-v1.schema.json, fixtures/platform/graph.yaml, tests/test_platform_graph.py]
    covers: [AC1, AC2]
    test: {path: tests/test_platform_graph.py, name: test_platform_graph_loads_and_fingerprints_deterministically}
  - id: T2
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py]
    covers: [AC3]
    test: {path: tests/test_platform_graph.py, name: test_platform_graph_cli_and_mcp_share_contract}
  - id: T3
    files: [docs/knowledge/platform-intelligence-graph.md, docs/surface.lock.json, docs/reference/mcp.md]
    covers: [AC3]
    test: {path: tests/test_platform_graph.py, name: test_platform_graph_reference_is_registered}
---

# PLATFORM_INTELLIGENCE_GRAPH — plano

## T1 — contrato e núcleo

Escrever testes de carga canônica, fingerprint, validação de endpoints e impacto
bounded. Implementar loader offline para JSON/YAML e fixture sintético. O teste
planejado é `python -m pytest tests/test_platform_graph.py::test_platform_graph_loads_and_fingerprints_deterministically -q`;
esta sessão não executa suíte por instrução do operador.

Commit: `feat(platform): add deterministic platform graph core`

## T2 — superfície comum

Adicionar `analyze platform-graph` e `sparkforge_analyze_platform_graph`; ambos
delegam ao mesmo `_core.analyze_platform_graph`. O teste planejado é
`python -m pytest tests/test_platform_graph.py::test_platform_graph_cli_and_mcp_share_contract -q`;
não executar nesta rodada.

Commit: `feat(platform): expose platform graph analysis surfaces`

## T3 — conhecimento e registros

Documentar contrato, registrar superfície e regenerar referência. O teste
planejado é `python -m pytest tests/test_platform_graph.py::test_platform_graph_reference_is_registered -q`;
não executar nesta rodada.

Commit: `docs(platform): document platform graph contract`
