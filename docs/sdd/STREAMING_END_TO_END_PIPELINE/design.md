---
sdd: 1
feature: STREAMING_END_TO_END_PIPELINE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_END_TO_END_PIPELINE/define.md
  sha256: "4a3a14eebfa500642e41e935dc4612bb2884c1ecf6fbfff208dfb61ad2232d3b"
files:
  - {path: tests/test_streaming_pipeline.py, action: create, reason: "contrato, seleção, paridade e regra do modo pipeline"}
  - {path: sparkforge/facts/streaming_pipeline.py, action: create, reason: "composição pura de contrato declarativo sobre Facts existentes"}
  - {path: sparkforge/facts/streaming_composition.py, action: modify, reason: "registrar modo pipeline sem duplicar compositor"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "ler pipeline_path explicitamente e encaminhar ao compositor"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "expor pipeline como modalidade do verbo existente"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "declarar pipeline_path e enum no contrato MCP existente"}
  - {path: rules/catalog/streaming.yaml, action: modify, reason: "julgar blind spot observado de aresta pipeline"}
  - {path: tests/test_fixtures_golden_streaming_pipeline.py, action: create, reason: "runner determinístico do novo corpus"}
  - {path: fixtures/streaming_pipeline/pipeline_complete/input/facts.json, action: create, reason: "evidência positiva"}
  - {path: fixtures/streaming_pipeline/pipeline_complete/input/pipeline.json, action: create, reason: "contrato declarativo positivo"}
  - {path: fixtures/streaming_pipeline/pipeline_complete/meta.yaml, action: create, reason: "metadados do golden positivo"}
  - {path: fixtures/streaming_pipeline/pipeline_complete/expected/facts.json, action: create, reason: "facts compostos positivos"}
  - {path: fixtures/streaming_pipeline/pipeline_complete/expected/findings.json, action: create, reason: "nenhum finding no pipeline completo"}
  - {path: fixtures/streaming_pipeline/pipeline_missing/input/facts.json, action: create, reason: "blind spot de selector ausente"}
  - {path: fixtures/streaming_pipeline/pipeline_missing/input/pipeline.json, action: create, reason: "contrato declarativo incompleto"}
  - {path: fixtures/streaming_pipeline/pipeline_missing/meta.yaml, action: create, reason: "metadados do golden unresolved"}
  - {path: fixtures/streaming_pipeline/pipeline_missing/expected/facts.json, action: create, reason: "facts compostos com unresolved"}
  - {path: fixtures/streaming_pipeline/pipeline_missing/expected/findings.json, action: create, reason: "finding de blind spot"}
  - {path: fixtures/streaming_pipeline/pipeline_ambiguous/input/facts.json, action: create, reason: "dois matches para selector"}
  - {path: fixtures/streaming_pipeline/pipeline_ambiguous/input/pipeline.json, action: create, reason: "contrato com identidade ambígua"}
  - {path: fixtures/streaming_pipeline/pipeline_ambiguous/meta.yaml, action: create, reason: "metadados do golden ambíguo"}
  - {path: fixtures/streaming_pipeline/pipeline_ambiguous/expected/facts.json, action: create, reason: "facts compostos ambíguos"}
  - {path: fixtures/streaming_pipeline/pipeline_ambiguous/expected/findings.json, action: create, reason: "finding de ambiguidade"}
  - {path: fixtures/streaming_pipeline/pipeline_invalid/input/facts.json, action: create, reason: "contrato com shape inválido"}
  - {path: fixtures/streaming_pipeline/pipeline_invalid/input/pipeline.json, action: create, reason: "entrada inválida fail-closed"}
  - {path: fixtures/streaming_pipeline/pipeline_invalid/meta.yaml, action: create, reason: "metadados do golden inválido"}
  - {path: fixtures/streaming_pipeline/pipeline_invalid/expected/facts.json, action: create, reason: "unresolved de contrato"}
  - {path: fixtures/streaming_pipeline/pipeline_invalid/expected/findings.json, action: create, reason: "finding de contrato inválido"}
  - {path: knowledge/streaming-pipeline-diagnostics.md, action: create, reason: "contrato, formato e limites operacionais"}
  - {path: knowledge/INDEX.md, action: modify, reason: "indexar novo knowledge"}
  - {path: skills/review-streaming-operations/SKILL.md, action: modify, reason: "rotear revisão para composição pipeline"}
  - {path: agents/streaming-realtime-architect.md, action: modify, reason: "orientar correlação declarativa end-to-end"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "registrar capacidade e limites"}
  - {path: docs/DELIVERY-LEDGER.md, action: modify, reason: "registrar wave/commit"}
  - {path: docs/EVOLUTION-CURRENT.md, action: modify, reason: "atualizar estado corrente"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "atualizar números e fechamento"}
  - {path: README.md, action: modify, reason: "atualizar contagens se movidas"}
  - {path: manifest.json, action: modify, reason: "atualizar contagens de facts/rules/fixtures"}
decisions:
  - id: D1
    choice: "Adicionar mode=pipeline ao compositor existente com pipeline_path opcional e selectors exatos."
    rejected: ["Criar nova tool/analyzer independente, duplicando surface e envelope.", "Inferir edges pela ordem dos arquivos ou por nomes parciais."]
    rollback: "git revert do commit da feature; remover modo, regra, corpus e documentação gerada sem tocar os modos existentes."
  - id: D2
    choice: "Selector aceita kind obrigatório e attrs escalares exact-match; match único é verificado, zero/múltiplo é unresolved."
    rejected: ["Regex/substring, que seria mais permissivo e menos auditável.", "Selector por subject.symbol apenas, que não cobre attrs de transporte e CDC."]
    rollback: "Reverter somente o módulo streaming_pipeline.py e manter o compositor anterior."
  - id: D3
    choice: "Rule SF-STREAM-015 julga apenas unresolved de pipeline com razão de blind spot."
    rejected: ["Criar finding positivo de saúde do pipeline sem métricas temporais.", "Usar finding para edge verified, duplicando fato de composição."]
    rollback: "Remover SF-STREAM-015 e seus goldens; facts verified/unresolved permanecem disponíveis para operadores."
covers:
  - {part: "pipeline contract and selectors", acceptance: [AC1, AC2]}
  - {part: "rule and golden corpus", acceptance: [AC3, AC5]}
  - {part: "CLI/MCP and documentation", acceptance: [AC4, AC6]}
---

# STREAMING_END_TO_END_PIPELINE — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| contrato/selectors | `sparkforge/facts/streaming_pipeline.py`, `sparkforge/facts/streaming_composition.py`, `tests/test_streaming_pipeline.py` | AC1, AC2 |
| regra/goldens | `rules/catalog/streaming.yaml`, `fixtures/streaming_pipeline/`, `tests/test_fixtures_golden_streaming_pipeline.py` | AC3, AC5 |
| superfície/documentação | adapters, knowledge, skill, agent, guias/locks/status | AC4, AC6 |

## Conhecimento consultado

O contrato existente foi lido por código e `sparkforge sdd status`; a regra de
composição foi comparada com `STREAMING_INTEGRATIONS_AND_CHECKPOINTS` e
`STREAMING_ARCHITECTURE_DECISION`. A documentação oficial do pipeline deve ser
tratada como formato de integração declarado, não como prova de capacidade: o
compositor não atribui semântica a uma aresta além dos facts que o selector
encontra.
