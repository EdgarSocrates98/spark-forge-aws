---
sdd: 1
feature: STREAMING_GLUE_SOURCE_SINK_ARTIFACTS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_SOURCE_SINK_ARTIFACTS/define.md
  sha256: ""
files:
  - {path: tests/test_facts_glue_streaming.py, action: modify, reason: "Cobrir objeto/lista, aliases, campos escalares, ausência e formato inválido."}
  - {path: sparkforge/facts/glue_streaming.py, action: modify, reason: "Emitir facts explícitos de source/sink e unresolved nomeado."}
  - {path: fixtures/glue_streaming, action: modify, reason: "Adicionar endpoints ao corpus positivo e regenerar goldens/metas."}
  - {path: scripts/regen_glue_streaming_fixtures.py, action: modify, reason: "Manter regeneração determinística do corpus."}
  - {path: knowledge/glue-streaming-rtm.md, action: modify, reason: "Documentar endpoints e limites de observação."}
  - {path: skills/review-glue-streaming/SKILL.md, action: modify, reason: "Orientar leitura dos novos kinds e unresolved."}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "Registrar fechamento parcial de source/sink Glue."}
  - {path: README.md, action: modify, reason: "Publicar contrato de análise Glue Streaming."}
  - {path: GUIA_DE_USO.md, action: modify, reason: "Atualizar fluxo de análise Glue Streaming."}
  - {path: docs/guia/03-cli.md, action: modify, reason: "Documentar a saída do analyzer existente."}
  - {path: docs/guia/04-mcp.md, action: modify, reason: "Documentar paridade MCP sem nova operação."}
  - {path: docs/guia/06-extrair-julgar-compor.md, action: modify, reason: "Explicitar separação entre job e endpoint."}
  - {path: knowledge/INDEX.md, action: modify, reason: "Atualizar descrição do conhecimento Glue."}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "Cobrar contrato nos docs e no SDD."}
decisions:
  - id: D1
    choice: "Adicionar glue.streaming.source e glue.streaming.sink ao extrator existente, sob o bloco stream."
    rejected: ["Criar extrator Glue paralelo ou novo modelo de connector."]
    rollback: "Remover helper e kinds novos; facts de job/runtime/analyzed permanecem válidos."
  - id: D2
    choice: "Aceitar objeto ou lista em sources/source e sinks/sink, usando primeira chave presente."
    rejected: ["Aceitar apenas lista, que recusaria dumps compactos."]
    rollback: "Retirar aliases singulares e regenerar goldens."
  - id: D3
    choice: "Preservar whitelist de atributos escalares e listas fechadas de medidas numéricas por papel."
    rejected: ["Copiar registro inteiro, que transportaria estruturas e confundiria declaração com medida."]
    rollback: "Reverter filtro e regenerar goldens; nenhuma regra depende dos novos kinds."
  - id: D4
    choice: "Emitir unresolved para ausência, formato inválido, registro inválido ou sem campos úteis."
    rejected: ["Omitir endpoint silenciosamente ou preencher métricas ausentes com zero."]
    rollback: "Remover motivos novos; manter facts de endpoint válidos."
  - id: D5
    choice: "Não criar rule, CLI ou MCP nesta wave."
    rejected: ["Criar threshold de backlog/lag sem timestamp, janela e baseline."]
    rollback: "Reverter documentação da cobertura; analyzer existente continua único caminho."
covers:
  - {part: "parser de endpoints", acceptance: [AC1, AC2, AC3]}
  - {part: "corpus e documentação", acceptance: [AC4, AC5]}
---

# STREAMING_GLUE_SOURCE_SINK_ARTIFACTS — desenho

O parser lê o bloco `stream` já usado pelo contrato Glue. Para cada papel,
normaliza singular/plural, converte objeto para lista e preserva somente campos
escalares de identidade/configuração e uma lista fechada de números. Registros
sem qualquer campo útil viram unresolved; endpoint com identidade mas sem
métrica também recebe unresolved de métrica, sem perder a identidade declarada.

O analyzer permanece offline e read-only. `judge` só recebe esses facts se o
operador o chamar. Nenhuma regra nova é criada porque a wave não estabelece
limiar temporal ou causal para backlog, lag, commits ou throughput.
