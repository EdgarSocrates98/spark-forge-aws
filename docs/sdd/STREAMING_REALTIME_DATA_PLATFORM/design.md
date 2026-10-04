---
sdd: 1
feature: STREAMING_REALTIME_DATA_PLATFORM
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_REALTIME_DATA_PLATFORM/define.md
  sha256: "1aa247b5fee9475f008a37b0ebcbcacc6abb7b883566d563188ea2c169c891da"
files:
  - {path: sparkforge/facts/pyspark_ast.py, action: modify, reason: "Emite facts estruturais adicionais para APIs Structured Streaming sem remover facts batch."}
  - {path: sparkforge/facts/streaming.py, action: create, reason: "Extrai StreamingQueryProgress local em JSON/JSONL, inclusive séries e unresolved nomeados."}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "Mantém contrato único de análise streaming e paginação compartilhada entre CLI e MCP."}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "Expõe sparkforge analyze streaming com tipo de artefato explícito."}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "Expõe sparkforge_analyze_streaming com schema e handler idênticos ao core."}
  - {path: rules/catalog/streaming.yaml, action: create, reason: "Julga somente facts streaming ancorados, com runtime_scope e actions reversíveis."}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "Roteia SF-STREAM para spark-performance-architect por findings_area."}
  - {path: agents/spark-performance-architect.md, action: modify, reason: "Declara SF-STREAM como área coordenada após existir extrator e catálogo."}
  - {path: .agents/agents/spark-performance-architect.md, action: modify, reason: "Espelho gerado do coordinator para Devin; será regenerado por sync_skills."}
  - {path: .claude/agents/spark-performance-architect.md, action: modify, reason: "Espelho gerado do coordinator para Claude; será regenerado por sync_skills."}
  - {path: knowledge/streaming-reliability.md, action: modify, reason: "Registra envelope aceito, limites de evidência e fontes oficiais da primeira onda."}
  - {path: knowledge/INDEX.md, action: modify, reason: "Indexa conhecimento Structured Streaming como domínio separado de procedimentos."}
  - {path: manifest.json, action: modify, reason: "Atualiza contagens declaradas de rules/tools e foco streaming."}
  - {path: tests/test_facts_streaming.py, action: create, reason: "Cobre extraction source/progress, unresolved, determinismo e não-regressão batch."}
  - {path: tests/test_streaming_rules.py, action: create, reason: "Cobre guardas de runtime/evidência e findings SF-STREAM."}
  - {path: tests/test_fixtures_golden_streaming.py, action: create, reason: "Runner golden do corpus streaming com facts, findings, positivos, negativos e runtime divergente."}
  - {path: tests/test_streaming_surface.py, action: create, reason: "Confere equivalência do contrato CLI/MCP e ausência de tool órfã."}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "Registra facts streaming no inventário manual de extratores e corpus."}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "Registra streaming.py no inventário de extratores alcançáveis."}
  - {path: fixtures/streaming/streaming_source.py, action: create, reason: "Código positivo com source/sink/checkpoint/trigger/watermark/state/join/dedup/foreachBatch."}
  - {path: fixtures/streaming/batch_only.py, action: create, reason: "Código negativo batch para provar que a extensão não cria streaming facts falsos."}
  - {path: fixtures/streaming/progress_positive.jsonl, action: create, reason: "Série observada com batches, source, sink, event-time e state operator."}
  - {path: fixtures/streaming/progress_single.jsonl, action: create, reason: "Uma observação: deve resultar em unresolved, sem tendência."}
  - {path: fixtures/streaming/progress_malformed.jsonl, action: create, reason: "Envelope inválido/linha truncada para blind spot nomeado."}
  - {path: fixtures/streaming/meta.yaml, action: create, reason: "Runtime e expectativas do golden corpus, incluindo caso divergente."}
  - {path: docs/surface.lock.json, action: modify, reason: "Gerado após registrar nova tool MCP; impede drift de superfície."}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "Referência gerada do novo subcomando analyze streaming."}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_streaming.md, action: create, reason: "Referência gerada da nova tool MCP."}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "Índice gerado de tools."}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "Hash do documento de conhecimento atualizado."}
  - {path: knowledge/sources.lock.json, action: modify, reason: "Watchlist e hashes/refs das fontes oficiais novas."}
decisions:
  - id: D1
    choice: "Um verbo analyze streaming recebe --artifact source|progress e chama extratores locais; CLI e MCP projetam o mesmo envelope de facts."
    rejected: ["Dois verbos independentes por superfície, que duplicariam contrato", "Collector live nesta onda, que violaria offline-first e tornaria o diagnóstico dependente de rede"]
    rollback: "git revert do commit da superfície; remover parser/handler/tool e manter os extratores apenas até a próxima reversão do backbone."
  - id: D2
    choice: "Adicionar detecção Structured Streaming de modo aditivo em pyspark_ast.py e filtrar os kinds no verbo dedicado."
    rejected: ["Parser AST paralelo, que duplicaria âncoras e quebraria a equivalência analyze pyspark", "Inferência por nome de arquivo, que confundiria batch e streaming"]
    rollback: "git revert do commit do extrator; facts batch existentes permanecem no estado anterior."
  - id: D3
    choice: "Aceitar apenas objetos StreamingQueryProgress documentados como JSON ou linhas JSONL; envelopes desconhecidos e linhas inválidas viram streaming.progress.unresolved."
    rejected: ["Ler checkpoint interno sem contrato de versão, que transformaria formato privado em falsa evidência", "Descartar linha inválida silenciosamente, que faria ausência parecer série limpa"]
    rollback: "git revert do commit de streaming.py; nenhum artefato live é alterado."
  - id: D4
    choice: "Regras iniciais usam relações observadas e quantidade mínima de observações declarada no fato; não usam thresholds de lag/throughput copiados dos especialistas legados."
    rejected: ["Hard-code 50000/20000/0.85 dos módulos streaming existentes, sem medição nem fonte runtime", "Prometer latency/backlog/throughput universal a partir de uma foto"]
    rollback: "git revert do commit do catálogo; remover a entrada SF-STREAM da routing e do coordinator se a área deixar de existir."
  - id: D5
    choice: "runtime_scope permanece agnóstico ({}) nesta primeira onda; regras exigem runtime confirmado no julgamento e distinguem Spark upstream de Glue por facts futuros."
    rejected: ["Fixar Glue >=5.0 por associação de produto, sem fronteira oficial para cada claim", "Tratar Spark 4.2 como runtime universal porque a documentação latest o publica"]
    rollback: "git revert do commit do catálogo e do conhecimento; nenhum runtime detectado é alterado."
  - id: D6
    choice: "Reusar spark-performance-architect como coordinator de SF-STREAM até haver evidência de que transportes/CDC/Flink exigem eixo separado."
    rejected: ["Criar agent dedicado antes de haver artefatos de transporte, que seria nome sem domínio observável", "Usar specialist Python legado como prova, que não tem Fact/Finding/rule_id"]
    rollback: "git revert do commit de agent/routing e regenerar os espelhos com scripts/sync_skills.py."
  - id: D7
    choice: "Conhecimento cita versões e URLs oficiais consultadas, mas não transforma documentação em garantia de performance ou exatamente-once."
    rejected: ["Consolidar defaults AWS e Spark numa tabela sem runtime efetivo", "Citar blogs ou memória como autoridade para uma regra executável"]
    rollback: "git revert do commit de knowledge; reexecutar refresh_knowledge.py --update --offline para alinhar locks."
covers:
  - {part: "source-extractor", acceptance: [AC1, AC7]}
  - {part: "progress-extractor", acceptance: [AC2, AC3, AC7]}
  - {part: "catalog-and-runtime-guards", acceptance: [AC4, AC5]}
  - {part: "fixture-corpus", acceptance: [AC3, AC5, AC7]}
  - {part: "cli-mcp-contract", acceptance: [AC6]}
  - {part: "catalog-routing-and-generated-surfaces", acceptance: [AC8]}
  - {part: "knowledge-boundary", acceptance: [AC4, AC8]}
---

# STREAMING_REALTIME_DATA_PLATFORM — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| source-extractor | `sparkforge/facts/pyspark_ast.py` | AC1, AC7 |
| progress-extractor | `sparkforge/facts/streaming.py`, `sparkforge/adapters/_core.py` | AC2, AC3, AC7 |
| catalog-and-runtime-guards | `rules/catalog/streaming.yaml`, `rules/catalog/routing.yaml` | AC4, AC5 |
| fixture-corpus | `fixtures/streaming/`, `tests/test_fixtures_golden_streaming.py` | AC3, AC5, AC7 |
| cli-mcp-contract | `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py`, `tests/test_streaming_surface.py` | AC6 |
| catalog-routing-and-generated-surfaces | agents, mirrors, references, `docs/surface.lock.json`, manifests | AC8 |
| knowledge-boundary | `knowledge/streaming-reliability.md`, `knowledge/INDEX.md` | AC4, AC8 |

## Contrato de fatos

Source code emits only anchored observations: `streaming.source`, `streaming.sink`,
`streaming.checkpoint`, `streaming.trigger`, `streaming.output_mode`,
`streaming.watermark`, `streaming.stateful_operation`, `streaming.join`,
`streaming.dedup`, `streaming.foreach_batch`, and a per-file sentinel. The existing
PySpark kinds remain unchanged and the dedicated verb filters to streaming kinds.

Progress extraction accepts a `StreamingQueryProgress` object, a list of objects, or
JSONL records. It emits one fact for each batch/source/sink/state operator and event-time
field, plus an aggregated series fact only when its required observations and measurements
are present. Invalid JSON, missing required fields, and insufficient series never fabricate
zeroes; they emit `streaming.progress.unresolved` with reason and observed counts.

## Regras e evidência

Initial rules are structural/relational: checkpoint configured versus explicitly absent in
an analyzed query, and observed input/processed rate or state growth only when the progress
series has enough records. No rule gives a universal capacity, latency, cost, or exactly-once
claim. Every rule carries `runtime_scope: {}`, sources, action, validation, rollback and a
fixture path. Findings must cite the emitted fact IDs.

## Conhecimento consultado

- Apache Spark Structured Streaming Programming Guide, Spark 4.2.0 latest documentation,
  consulted through the official Spark pages returned by web search on 2026-10-01; records
  checkpoints, triggers, watermarks, state and output modes as runtime-dependent semantics.
- PySpark 4.2.0 API `StreamingQuery.lastProgress` and streaming listener source, official
  Spark pages consulted on 2026-10-01; records the progress envelope and version notes.
- AWS Glue Developer Guide, “Streaming ETL jobs” and “Using a streaming data source”,
  consulted on 2026-10-01; records Kinesis/Kafka/MSK inputs, checkpoints versus job
  bookmarks, Glue window behavior, and the boundary between Glue and upstream Spark.
- Existing local knowledge via `sparkforge knowledge path --file knowledge/streaming-reliability.md`
  and runtime/rule lookup verbs; local prose remains a pointer, not a substitute for the
  runtime artifact.

## Rollback e validação

Each implementation slice is independently revertible. Before ship, run focused tests,
catalog reachability/golden gates, `python scripts/sync_skills.py --check`, reference and
surface generation checks, offline knowledge locks, and `sparkforge sdd check`. Full-suite
baseline already has an environmental temp-file failure documented in the case; it is not
used as evidence of streaming correctness.
