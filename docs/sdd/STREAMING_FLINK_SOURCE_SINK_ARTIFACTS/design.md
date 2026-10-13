---
sdd: 1
feature: STREAMING_FLINK_SOURCE_SINK_ARTIFACTS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_FLINK_SOURCE_SINK_ARTIFACTS/define.md
  sha256: "d147889d0ba15964d10ad81f0e9f64de7ee5cd5ec0ac0f615fdc0e07fac541d3"
files:
  - {path: tests/test_facts_flink.py, action: modify, reason: "Cobrir objeto/lista, aliases, ausência e isolamento de source/sink."}
  - {path: sparkforge_aws/facts/flink.py, action: modify, reason: "Emitir facts explícitos de source/sink e unresolved nomeado."}
  - {path: fixtures/flink/flink_positive/input/dump.json, action: modify, reason: "Adicionar source Kafka e sink Iceberg observados ao golden positivo."}
  - {path: fixtures/flink, action: modify, reason: "Regenerar facts/findings e metas do corpus offline."}
  - {path: scripts/regen_flink_fixtures.py, action: modify, reason: "Manter regeneração determinística do corpus."}
  - {path: knowledge/flink-streaming.md, action: modify, reason: "Documentar source/sink, métricas e limites de evidência."}
  - {path: skills/analyze-flink-job/SKILL.md, action: modify, reason: "Atualizar procedimento da skill para os novos kinds."}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "Registrar fechamento parcial de source/sink Flink."}
  - {path: README.md, action: modify, reason: "Publicar uso e limites do contrato Flink."}
  - {path: GUIA_DE_USO.md, action: modify, reason: "Adicionar fluxo operacional de análise Flink."}
  - {path: docs/guia/03-cli.md, action: modify, reason: "Documentar CLI existente para endpoints Flink."}
  - {path: docs/guia/04-mcp.md, action: modify, reason: "Documentar paridade MCP sem nova tool."}
  - {path: docs/guia/06-extrair-julgar-compor.md, action: modify, reason: "Documentar extração e limites no guia conceitual."}
  - {path: knowledge/INDEX.md, action: modify, reason: "Atualizar índice de conhecimento Flink."}
  - {path: tests/test_docs_coverage.py, action: modify, reason: "Cobrar presença do contrato em docs, skill e SDD."}
decisions:
  - id: D1
    choice: "Adicionar kinds flink.source e flink.sink ao mesmo extrator offline."
    rejected: ["Criar extrator separado sem formato de artefato distinto."]
    rollback: "Remover os dois kinds e a chamada auxiliar; facts job/operator/checkpoint/state continuam válidos."
  - id: D2
    choice: "Aceitar objeto ou lista nas chaves sources/source e sinks/sink."
    rejected: ["Aceitar somente lista, que recusaria dumps compactos válidos."]
    rollback: "Retirar aliases singular/plural e manter somente o formato original documentado."
  - id: D3
    choice: "Preservar somente atributos escalares e uma lista fechada de medidas numéricas."
    rejected: ["Copiar o registro inteiro, que transportaria estruturas arbitrárias e confundiria texto com medida."]
    rollback: "Reverter o filtro de campos e regenerar goldens; nenhuma regra depende dos novos kinds."
  - id: D4
    choice: "Emitir unresolved para chave ausente, lista inválida, registro inválido ou registro sem campos."
    rejected: ["Omitir o endpoint silenciosamente ou preencher métricas ausentes com zero."]
    rollback: "Retirar os motivos novos; manter somente facts de endpoint que já existam."
  - id: D5
    choice: "Não criar rule, CLI ou MCP nesta wave."
    rejected: ["Criar limiar para backlog/commit isolado, que exigiria janela e baseline não presentes."]
    rollback: "Reverter documentação de superfície; `sparkforge_analyze_flink` permanece o único caminho."
covers:
  - {part: "parser de endpoints", acceptance: [AC1, AC2, AC3]}
  - {part: "isolamento de namespace", acceptance: [AC4]}
  - {part: "corpus e documentação", acceptance: [AC5, AC6]}
---

# STREAMING_FLINK_SOURCE_SINK_ARTIFACTS — desenho

O contrato mantém os endpoints no mesmo provenance do dump. Para cada papel,
o parser aceita objeto ou lista, normaliza aliases declarados, filtra atributos
escalares e extrai somente a lista fechada de números do contrato. Um registro
sem qualquer campo útil não vira `flink.source`/`flink.sink`: vira unresolved.

O analyzer continua read-only e offline. `judge` só recebe esses fatos se o
operador o chamar; nenhuma regra nova é adicionada porque a wave não estabelece
limiar temporal ou causal para backlog, lag ou commits.

Contrato: `flink.source` e `flink.sink` carregam identidade (`*_id`, nome, uid,
tipo, connector e delivery semantics) e as medidas numéricas fechadas do
extrator. Source aceita parallelism, contadores, backlog/lag, busy,
backpressure e idle; sink aceita parallelism, contadores, commits, falhas,
busy, backpressure e idle. Os motivos unresolved são nomeados por papel e
formato. O desenho não mapeia connector para garantia semântica nem usa um
fact isolado para concluir saúde.
