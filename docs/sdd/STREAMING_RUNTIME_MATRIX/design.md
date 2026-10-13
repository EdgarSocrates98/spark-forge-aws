---
sdd: 1
feature: STREAMING_RUNTIME_MATRIX
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_RUNTIME_MATRIX/define.md
  sha256: "0c618a595fc23d8002f38c280d36af9b39f0d9e2429808018c26686c83937fe8"
files:
  - {path: knowledge/streaming/runtime-matrix.md, action: create, reason: "matriz evidence-first de runtimes streaming"}
  - {path: knowledge/INDEX.md, action: modify, reason: "indexar matriz"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "vigiar fontes da matriz"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "incluir documento no bundle offline"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "ligar cobertura aos estados da matriz"}
  - {path: tests/test_streaming_runtime_matrix.py, action: create, reason: "regressão de estados, lock e bundle"}
decisions:
  - id: D1
    choice: "Conhecimento markdown com fontes oficiais e limites declarados."
    rejected: ["YAML consumido como runtime efetivo sem artefato", "copiar release upstream para serviço managed"]
    rollback: "Remover o documento, sua entrada no índice/manifesto/lock e o teste; manter analyzers existentes."
  - id: D2
    choice: "UNRESOLVED para MSK/Managed Flink quando região ou serviço não está evidenciado localmente."
    rejected: ["inventar versão atual", "usar latest upstream como proxy managed"]
    rollback: "Reverter somente as linhas de conhecimento e seus hashes."
covers:
  - {part: "matrix state and boundaries", acceptance: [AC1]}
  - {part: "sources and offline bundle", acceptance: [AC2, AC3]}
---

# STREAMING_RUNTIME_MATRIX — design
