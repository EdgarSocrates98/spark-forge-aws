---
sdd: 1
feature: STREAMING_REALTIME_DATA_PLATFORM
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_REALTIME_DATA_PLATFORM/build_report.md
  sha256: "9f2f0fce0830669683a926a9d6809cd95ab738b73a04a048b8b5cfb9266b7320"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, runtime_scope_gates, routing_yaml, coordinator_rule_areas, fixture_corpus_gates, offline_manifest, sources_lock, surface_lock, generated_reference, router_gates, sync_skills, agents_parity]
deviations:
  - "A primeira onda entrega o backbone offline de Structured Streaming; Kafka/MSK, Kinesis, Flink, CDC, contratos e manutenção de lakehouse permanecem como ondas nomeadas no explore, não como capacidade alegada nesta entrega."
  - "A integração pós-build atualizou parity.yaml, allowlists de MCP/fixtures, kinds canônicos, contagens de superfície e cinco goldens derivados de assessment; nenhuma regra existente foi reinterpretada."
  - "A suíte final teve uma falha de caminho Windows somente quando executada sob basetemp longo; tests/test_integrate.py passou completo com basetemp curto."
  - "O gate histórico check_vnext_claims.py permanece fora dos registries desta feature e recusa referências a commits ausentes no clone; nenhum manifesto de claims foi alterado."
---

# STREAMING_REALTIME_DATA_PLATFORM — entrega

## Hipótese

**Confirmada para a primeira onda.** O repositório agora extrai evidência
determinística de fonte Structured Streaming e de `StreamingQueryProgress`,
preserva blind spots como `unresolved`, julga somente com runtime/evidência
suficientes, roteia findings para o coordenador existente e publica o mesmo
contrato por CLI e MCP. O corpus golden cobre positivo, negativo, série curta,
JSON inválido e divergência de runtime. A previsão não inclui as ondas de
transporte, CDC, Flink ou lakehouse listadas no explore.

## O que a entrega acrescenta

- facts estáticos para `readStream`/`writeStream`, checkpoint, trigger,
  watermark, output mode, operações stateful, joins, dedup e `foreachBatch`;
- parser offline JSON/JSONL de `StreamingQueryProgress` com ordem observada,
  batch/source/sink/event-time/state e série somente quando há observações
  suficientes;
- regras `SF-STREAM-001` a `SF-STREAM-003`, runtime guard e rota `AGENT-090`;
- `sparkforge analyze streaming` e `sparkforge_analyze_streaming`, com envelope
  compartilhado;
- fixtures, goldens, conhecimento oficial offline, locks e referências geradas;
- capability/parity para os cinco caminhos de execução documentados.

## Gates rodados

| gate | comando/resumo | resultado |
|---|---|---|
| regras, catálogo e escopo | suítes de catálogo/reachability, engine, result axis, cobertura de agentes, routing, fixtures e refresh | pass; 1045 pass no gate catalogado |
| extrator e corpus | suítes de facts, golden streaming, kinds e wheel | pass; 780 no gate de extrator e 101 no wheel |
| runtime e routing | gates de runtime scope e routing | pass; 679 e 169 pass |
| agentes e superfície | paridade de agentes, autorização, capability/parity MCP e contratos de superfície | pass; 203 pass no gate de agentes |
| conhecimento offline | `python scripts/verify_offline_bundle.py --check` e testes de knowledge | exit 0; bundle sem divergência |
| referências | `python scripts/gen_reference_docs.py` e `python scripts/check_surface_lock.py` | 0 páginas pendentes; exit 0 |
| números | `python scripts/check_status_numbers.py --strict` | exit 0 |
| suíte sequencial | nove lotes oficiais | 5509 pass, 6 skipped; `test_integrate.py` completo: 115 pass, 1 skipped com basetemp curto |
| SDD | `sparkforge sdd check --repo . --feature STREAMING_REALTIME_DATA_PLATFORM` | esperado exit 0 após stamp |

## Rollback

Reverter commits da branch `codex/streaming-realtime-platform` na ordem
inversa, preservando os artefatos SDD e o case até a revisão do operador. A
remoção da capacidade deve retirar juntos extrator, regras, fixtures, locks,
referências e parity para não deixar superfície órfã.

## Pendências para próximas ondas

- `STREAMING_TRANSPORT_DIAGNOSTICS`: Kafka/MSK, Kinesis e Glue Streaming;
- `STREAMING_PROCESSING_RUNTIMES`: Flink, Glue 4/5/6, Spark RT e compatibilidade;
- `STREAMING_CDC_CONTRACTS`: CDC, schema evolution, DLQ e contratos de evento;
- `STREAMING_LAKEHOUSE_OBSERVABILITY`: Iceberg, checkpoints, state store,
  latência, atraso e FinOps sem inventar custo;
- `STREAMING_ARCHITECTURE_DECISIONS`: ADRs e trade-offs comparáveis;
- `STREAMING_AGENTIC_SURFACE`: especialistas, skills, playbooks e ferramentas
  específicos quando houver artefatos/gates que sustentem cada domínio.

## Lições

- Uma nova tool exige atualizar simultaneamente capability/parity, kinds
  canônicos, allowlists, contagens, referências e goldens derivados.
- `StreamingQueryProgress` permite evidência operacional offline, mas não prova
  exatamente-once, semântica de negócio ou custo sem artefatos adicionais.
- Basetemp longo em Windows pode transformar um teste funcional em erro de
  caminho; gates de suíte devem usar isolamento curto e explícito.
