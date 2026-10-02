---
sdd: 1
feature: STREAMING_SLO_EVALUATION
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_SLO_EVALUATION/define.md
  sha256: "3faac0ac3fa085041023d89d4117105888f492656c024a9556642b21df160ab3"
files:
  - {path: sparkforge/facts/streaming_slo.py, action: create, reason: "compor status SLO sobre declarations e batches observados"}
  - {path: sparkforge/facts/streaming_composition.py, action: modify, reason: "despachar mode=slo e preservar envelope analisado"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "passar slo_name ao compositor comum"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "expor mode=slo e --slo-name"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "manter paridade de schema CLI/MCP"}
  - {path: rules/catalog/streaming-operations.yaml, action: modify, reason: "julgar violação observada e avaliação unresolved"}
  - {path: tests/test_facts_streaming_slo.py, action: create, reason: "provar comparação, janela e unresolved antes do código"}
  - {path: tests/test_streaming_rules.py, action: modify, reason: "provar regras SLO evidence-first"}
  - {path: tests/test_analyze_streaming_composition.py, action: modify, reason: "provar envelope CLI/MCP do modo SLO"}
  - {path: fixtures/streaming_composition, action: modify, reason: "goldens met, violated e unresolved"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "registrar kinds derivados de streaming_slo"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "registrar compositor SLO para alcance das regras"}
  - {path: skills/analyze-streaming-composition/SKILL.md, action: modify, reason: "documentar avaliação declarada contra observação"}
  - {path: knowledge/streaming-operations.md, action: modify, reason: "explicar janela, comparadores, unidade e limites"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "marcar SLO operacional como diagnosable"}
  - {path: docs/surface.lock.json, action: modify, reason: "declarar novo mode e argumento"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "atualizar hash do conhecimento"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "registrar números correntes da entrega"}
decisions:
  - id: D1
    choice: "Reutilizar analyze streaming-composition com mode=slo e slo_name opcional, exigindo query_name quando a identidade não for única."
    rejected: ["criar ferramenta MCP separada", "avaliar dentro de streaming_ops"]
    rollback: "Remover mode=slo, slo_name e compositor derivado; declarations streaming.slo e modos legados permanecem intactos."
  - id: D2
    choice: "Aceitar somente métricas canônicas presentes em streaming.progress.batch, com unidade declarada equivalente e source spark_progress/structured_streaming."
    rejected: ["converter unidades", "calcular p95/freshness a partir de taxa", "tratar qualquer campo arbitrário como SLO"]
    rollback: "Remover mapa de métricas e manter todos os casos não suportados como unresolved."
  - id: D3
    choice: "Exigir duas ou mais observações timestampadas e span observado maior ou igual à janela declarada antes de emitir met/violated."
    rejected: ["considerar uma amostra suficiente", "assumir que o nome da janela prova cobertura", "preencher timestamps ausentes"]
    rollback: "Retirar status resolvido e conservar streaming.slo.unresolved para cobertura incompleta."
  - id: D4
    choice: "Emitir um fact agregado com valores mínimo/máximo, contagem, span, comparator e source_fact_ids; SF-STREAM-010 julga somente status violated."
    rejected: ["finding para status met", "finding por batch", "atribuir causa ou custo à violação"]
    rollback: "Remover regra nova e manter o fact observado para reauditoria."
covers:
  - {part: "SLO compositor", acceptance: [AC1, AC2, AC3]}
  - {part: "rule", acceptance: [AC4]}
  - {part: "adapters", acceptance: [AC5]}
  - {part: "goldens", acceptance: [AC6]}
  - {part: "docs and registries", acceptance: [AC7]}
---

# STREAMING_SLO_EVALUATION — desenho

O fluxo continua `facts → composição → judge`. `streaming_ops` declara o
target; `streaming` fornece batches. O novo compositor não lê arquivos, não
consulta serviço e não altera nenhum dado.

## Algoritmo determinístico

1. Selecionar uma declaração `streaming.slo` pelo `slo_name` ou por unicidade.
2. Selecionar batches do `query_name` no mesmo artefato; ambiguidade vira
   `streaming.slo.unresolved`.
3. Normalizar somente `lt`, `lte`, `gt`, `gte`, `eq`, janela simples `s/m/h/d` e
   aliases explícitos de unidade; rejeitar conversão implícita.
4. Extrair valores da allowlist de measures (`input_rows_per_second`,
   `processed_rows_per_second`, `batch_duration_ms`, `num_input_rows`) e
   timestamps ISO-8601 dos batches.
5. Exigir pelo menos duas observações, `observed_span_seconds >= window_seconds`
   e source compatível. Com cobertura, todos os valores devem passar para `met`;
   qualquer falha produz `violated`.

O fact resolvido preserva target, extremos, contagem, janela, operador, query,
ids de origem e `causal_inference: false`. O unresolved nomeia a primeira
barreira determinística sem inventar zero, sucesso ou causa.

## Conhecimento consultado

- `sparkforge rules lookup --category streaming_slo`: `SF-STREAM-004`, que
  confirma que declaração sem target não prova atendimento.
- `sparkforge analyze streaming-ops --path ...`: o contrato atual emite
  `streaming.slo` com target, metric, operator, unit, window e source.
- `knowledge/streaming-operations.md`: separação entre declaração SLO e série
  observada; sem comparação de unidade/janela não há veredito.
- `sparkforge/facts/streaming.py` e `sparkforge/facts/streaming_composition.py`:
  batches já carregam timestamp, query_name e measures de taxa/duração.
