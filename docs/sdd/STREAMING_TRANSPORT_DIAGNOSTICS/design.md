---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TRANSPORT_DIAGNOSTICS/define.md
  sha256: "20ae0f83cd346a75bd4474cb0b3803177e19fd6e8e0a5fb18e13f9a330cbc0b8"
decisions:
  - id: D1
    choice: "Um módulo transport.py com artifact obrigatório kafka|msk|kinesis e kinds específicos por domínio."
    rejected: ["um namespace genérico transport.* que esconderia diferenças operacionais"]
    rollback: "Reverter o commit do extrator e remover o módulo transport.py."
  - id: D2
    choice: "Facts carregam somente campos literais observados; campos ausentes viram unresolved e não zero."
    rejected: ["defaults de SDK", "inferir versão MSK a partir de Kafka upstream"]
    rollback: "Reverter o commit do extrator e restaurar o contrato anterior de facts."
  - id: D3
    choice: "`analyze transport` é read-only e CLI/MCP chamam a mesma função core."
    rejected: ["collector implícito dentro de analyze", "tool separada por serviço nesta onda"]
    rollback: "Reverter o commit dos adapters e remover a entrada de surface regenerada."
files:
  - {path: sparkforge/facts/transport.py, action: create, reason: "extrator JSON/JSONL offline"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "envelope do analyzer"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "verbo analyze transport"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "tool MCP"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "nenhuma regra nova; verificar que a rota existente permanece inalterada"}
  - {path: fixtures/transport, action: create, reason: "corpus golden"}
  - {path: knowledge/transport-diagnostics.md, action: create, reason: "limites e fontes oficiais"}
  - {path: docs/surface.lock.json, action: modify, reason: "registrar tool nova e superfície regenerada"}
covers:
  - {part: "facts de transporte", acceptance: [AC1, AC2, AC3]}
  - {part: "CLI e MCP", acceptance: [AC4]}
  - {part: "goldens e conhecimento", acceptance: [AC5]}
  - {part: "surface pública", acceptance: [AC6]}
---

# STREAMING_TRANSPORT_DIAGNOSTICS — desenho

O contrato preserva a diferença entre declaração (`topic`, `cluster`, `stream`),
observação medida (`lag`, `iterator_age_ms`, offsets) e ponto cego
(`unresolved`). Nenhum finding de causa entra antes de existir uma regra com
evidência suficiente.
