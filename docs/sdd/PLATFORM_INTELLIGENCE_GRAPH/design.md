---
sdd: 1
feature: PLATFORM_INTELLIGENCE_GRAPH
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/PLATFORM_INTELLIGENCE_GRAPH/define.md
  sha256: "e6511c626dcfe203680354e7c8ebf72f15fd2d3cf959f5b0a1ee6e07becabfe6"
files:
  - {path: sparkforge/platform/__init__.py, action: create, reason: "API pública do núcleo de inteligência da plataforma."}
  - {path: sparkforge/platform/graph.py, action: create, reason: "Loader, validador, compositor, fingerprint e impacto determinísticos."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Ponto comum para CLI e MCP analisar o grafo de plataforma."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Verbo analyze platform-graph e paginação/saída estruturada."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Contrato MCP e handler parity com CLI."}
  - {path: parity.yaml, action: modify, reason: "Declara paridade CLI/MCP e integração nas plataformas suportadas."}
  - {path: contracts/platform-graph-v1.schema.json, action: create, reason: "Contrato publicável para manifests de Metadata Graph."}
  - {path: fixtures/platform/graph.yaml, action: create, reason: "Fixture sintético para smoke command e documentação."}
  - {path: tests/test_platform_graph.py, action: create, reason: "Casos de fingerprint, impacto explícito e unresolved."}
  - {path: docs/knowledge/platform-intelligence-graph.md, action: create, reason: "Guia operacional do contrato e limites."}
  - {path: docs/surface.lock.json, action: modify, reason: "Registro exigido por novo tool MCP."}
  - {path: docs/guia/referencia/README.md, action: modify, reason: "Índice da referência gerada."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada do verbo CLI."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado das tools MCP."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_platform_graph.md, action: create, reason: "Referência gerada do contrato MCP."}
decisions:
  - id: D1
    choice: "Reusar GraphFragment/FederatedGraph como primitives de composição e adicionar PlatformGraph como contrato de domínio."
    rejected: ["Grafo paralelo sem interoperabilidade", "alterar FederatedGraph para assumir semântica de plataforma"]
    rollback: "git revert do commit da feature; o compositor federado anterior continua disponível."
  - id: D2
    choice: "Impacto segue somente arestas explícitas e carrega paths limitados."
    rejected: ["resolver por nome/label", "consultar serviços externos durante analyze"]
    rollback: "git revert do commit do analisador; nenhuma coleta externa será executada."
  - id: D3
    choice: "CLI e MCP chamam a mesma função _core e o MCP declara schema fechado no topo."
    rejected: ["implementar lógica separada no handler MCP", "retornar texto sem contrato"]
    rollback: "remover registro da ferramenta, regenerar referência e surface lock."
covers:
  - {part: "platform graph core", acceptance: [AC1, AC2]}
  - {part: "CLI/MCP boundary", acceptance: [AC3]}
---

# PLATFORM_INTELLIGENCE_GRAPH — desenho

## Fluxo

```text
manifest JSON/YAML
        |
        v
PlatformGraph loader -> validation -> canonical fingerprint
        |
        +--> explicit lineage edges + provenance + unresolved
        |
        +--> bounded impact(root, direction, depth, attribute)
        |
        +--> _core -> CLI / MCP (same result)
```

## Regras de composição

IDs são a única chave de junção. Duplicatas com conteúdo divergente viram
`platform_node_conflict` ou `platform_edge_conflict`. Endpoint ausente não é
descartado silenciosamente: gera `platform_edge_unresolved`. `inferred` é aceito
como estado declarado do produtor, mas nunca criado pelo analisador.

## Conhecimento consultado

O contrato SDD e a implementação existente foram consultados por
`sparkforge sdd check`, `sparkforge code search graph` e
`sparkforge code symbol sparkforge/workspace/federated.py::compose_federated_graph`.
Não há afirmação de comportamento externo de Spark/Glue nesta fase.
