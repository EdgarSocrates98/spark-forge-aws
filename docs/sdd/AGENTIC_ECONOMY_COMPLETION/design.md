---
sdd: 1
feature: AGENTIC_ECONOMY_COMPLETION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/AGENTIC_ECONOMY_COMPLETION/define.md
  sha256: "09ed7d9a4d2afc67aad54aa898a4421c4e865847d46388eef2aef650f3e8a577"
files:
  - {path: sparkforge/workspace/federation.py, action: create, reason: "compositor público para SemanticGraph, live artifact e bridges explícitas"}
  - {path: sparkforge/workspace/__init__.py, action: modify, reason: "exportar compose_workspace_graph"}
  - {path: sparkforge/workspace/manifest.py, action: modify, reason: "validar bridges declaradas no workspace manifest"}
  - {path: tests/test_workspace_federation.py, action: create, reason: "AC1: união static/live sem inferência"}
  - {path: sparkforge/knowledge_engine/packs.py, action: modify, reason: "cachear assinatura de descriptors e evitar releitura de corpos"}
  - {path: tests/test_knowledge_compiler.py, action: modify, reason: "AC2: hit e invalidação do cache de descriptors"}
  - {path: sparkforge/adapters/mcp_compact.py, action: modify, reason: "publicar execute_read e execute_mutation com annotations distintas"}
  - {path: sparkforge/adapters/mcp.py, action: modify, reason: "mensagem e catálogo da nova superfície compacta"}
  - {path: fixtures/mcp_parity/compact_tools_list.json, action: modify, reason: "golden dos nomes compactos"}
  - {path: fixtures/mcp_parity/compact_calls.json, action: modify, reason: "casos de parity do executor read"}
  - {path: tests/test_adapters_mcp_compact.py, action: modify, reason: "AC3: annotations, roteamento e refusals por intenção"}
  - {path: tests/test_adapters_mcp_compact_parity.py, action: modify, reason: "parity do executor read e refusals estruturadas"}
  - {path: tests/test_adapters_mcp.py, action: modify, reason: "superfície MCP publicada pelo servidor"}
  - {path: tests/test_host_surface_contracts.py, action: modify, reason: "contagem compacta e contrato de envelope"}
  - {path: docs/surface.lock.json, action: modify, reason: "declarar crescimento deliberado da superfície compacta"}
decisions:
  - id: D1
    choice: "Receber bridges como registros explícitos no manifest e compor um fragment separado de origem manifest."
    rejected: ["casar dataset static com Glue/S3 por nome, que inventaria relação", "fundir live no SemanticGraph, que perderia provenance de source"]
    rollback: "git revert do commit da federation pública e remover a chave federated_links do manifest"
  - id: D2
    choice: "Usar assinatura de metadados de filesystem para hit de descriptors e recalcular SHA somente quando ela mudar."
    rejected: ["ler todos os bytes a cada chamada, que mantém o custo atual", "cache sem assinatura, que pode servir source_hash obsoleto"]
    rollback: "git revert do commit de PackRegistry e remover os campos de cache"
  - id: D3
    choice: "Substituir execute genérico por duas operações compactas, execute_read e execute_mutation, mantendo o dispatcher full único."
    rejected: ["um execute com mode dinâmico, que não permite annotation MCP por intenção", "manter execute único, que conserva prompt de autorização ambíguo"]
    rollback: "git revert do commit da superfície compacta e restaurar o golden de seis operações"
covers:
  - {part: "workspace federation", acceptance: [AC1]}
  - {part: "pack descriptor cache", acceptance: [AC2]}
  - {part: "compact execution split", acceptance: [AC3]}
  - {part: "monolithic validation", acceptance: [AC4]}
---

# AGENTIC_ECONOMY_COMPLETION — desenho

## Arquitetura

```text
SemanticGraph ── explicit adapter ─┐
                                   ├── compose_workspace_graph ── FederatedGraph
live graph artifact ─ adapter ─────┤             ▲
manifest federated_links ─ bridge ┘             └── bounded impact/unresolved

PackRegistry ── filesystem signature ── descriptor cache ── load/compile

execute_read ── readOnlyHint=true  ─┐
                                    ├── shared schema/policy/full dispatcher
execute_mutation ── readOnlyHint=false ┘
```

## Contratos

- `compose_workspace_graph(static_graph, live_artifact, bridges=...)` converte
  cada fonte em `GraphFragment` e adiciona bridges somente com `source`,
  `relation`, `target` declarados. O compositor existente continua responsável
  por bounds, conflitos, endpoints e unresolved.
- `WorkspaceManifest.federated_links` é uma tupla imutável de `GraphLink`; ids
  vazios, relações vazias e duplicatas são recusados.
- `PackRegistry.descriptors()` guarda a assinatura ordenada de caminhos,
  tamanho e `st_mtime_ns`; hit não lê corpos, miss recalcula SHA e atualiza
  descriptor cache.
- `execute_read` só despacha capability com `readOnlyHint=True`; `execute_mutation`
  só despacha capability com `readOnlyHint=False`. Ambos usam o mesmo validation,
  policy e `execute_full`.

## Rollback operacional

Cada tarefa tem commit isolado. Reverter a tarefa correspondente remove apenas
o compositor, o cache ou a nova superfície; o `FederatedGraph`, dispatcher full
e catálogo de packs existentes permanecem disponíveis.
