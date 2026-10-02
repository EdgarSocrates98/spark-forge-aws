---
sdd: 1
feature: STREAMING_TRANSPORT_DIAGNOSTICS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TRANSPORT_DIAGNOSTICS/define.md
  sha256: "c304b6cfe1eb62cea2c86443b054c10b01fb9a768688bf2b351199ca7cf763a2"
decisions:
  - id: D1
    choice: "Um módulo transport.py com artifact obrigatório kafka|msk|kinesis e kinds específicos por domínio."
    rejected: ["um namespace genérico transport.* que esconderia diferenças operacionais"]
  - id: D2
    choice: "Facts carregam somente campos literais observados; campos ausentes viram unresolved e não zero."
    rejected: ["defaults de SDK", "inferir versão MSK a partir de Kafka upstream"]
  - id: D3
    choice: "`analyze transport` é read-only e CLI/MCP chamam a mesma função core."
    rejected: ["collector implícito dentro de analyze", "tool separada por serviço nesta onda"]
files:
  - {path: sparkforge/facts/transport.py, action: create, reason: "extrator JSON/JSONL offline"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "envelope do analyzer"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "verbo analyze transport"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "tool MCP"}
  - {path: rules/catalog/routing.yaml, action: none, reason: "sem finding nesta onda"}
  - {path: fixtures/transport, action: create, reason: "corpus golden"}
  - {path: knowledge/transport-diagnostics.md, action: create, reason: "limites e fontes oficiais"}
  - {path: docs/surface.lock.json, action: generated, reason: "surface"}
risks:
  - "Formato de dump não é universal entre versões de CLI/serviço."
  - "Métrica ausente pode ser confundida com zero se o schema não preservar unresolved."
  - "Adicionar tool altera contagens/parity/goldens derivados."
rollback: "Reverter commits da feature em ordem inversa e remover surface/fixtures/knowledge junto com o extrator."
---

# STREAMING_TRANSPORT_DIAGNOSTICS — desenho

O contrato preserva a diferença entre declaração (`topic`, `cluster`, `stream`),
observação medida (`lag`, `iterator_age_ms`, offsets) e ponto cego
(`unresolved`). Nenhum finding de causa entra antes de existir uma regra com
evidência suficiente.
