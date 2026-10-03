---
sdd: 1
feature: STREAMING_REALTIME_DATA_PLATFORM
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_REALTIME_DATA_PLATFORM/explore.md
  sha256: "621b8fb163f6f6ba284313dacbe32e621d1b318f4b4219cbad0f9cc3f8b8278a"
hypothesis:
  claim: "Um backbone determinístico para Structured Streaming, baseado em artefatos de código e séries de StreamingQueryProgress, permite diagnosticar sintomas somente quando a evidência e o runtime sustentam a conclusão, sem degradar os fluxos batch existentes."
  prediction: "As fixtures de código e progresso produzirão facts determinísticos para source, sink, checkpoint, trigger, watermark, state e métricas por batch; séries insuficientes produzirão unresolved e nenhum finding de tendência; a suíte batch existente continuará passando fora das limitações ambientais já registradas."
  experiment: "Implementar os extractors, rules, fixtures e superfícies CLI/MCP da primeira onda; executar pytest focado, checks SDD, validação de catálogo/surface lock e a comparação de saída CLI/MCP sobre os mesmos artefatos."
acceptance:
  - id: AC1
    statement: "O extrator de código Structured Streaming identifica source, sink, checkpoint, trigger, output mode, watermark, stateful operations, joins, deduplication e foreachBatch com âncoras de arquivo e linha."
    verified_by: {kind: test, ref: "tests/test_facts_streaming.py::test_extract_structured_streaming_source_emits_anchored_facts"}
  - id: AC2
    statement: "O extrator de StreamingQueryProgress emite fatos por batch, source, sink, event-time e state operator, preservando unidades e a ordem observada."
    verified_by: {kind: test, ref: "tests/test_facts_streaming.py::test_extract_streaming_progress_emits_batch_source_sink_and_state_facts"}
  - id: AC3
    statement: "Uma série de progresso insuficiente para concluir tendência emite unresolved nomeado e não dispara finding de backlog, watermark ou crescimento de state."
    verified_by: {kind: test, ref: "tests/test_facts_streaming.py::test_insufficient_progress_is_unresolved_not_a_trend"}
  - id: AC4
    statement: "Rules Structured Streaming exigem runtime e evidência de série antes de julgar backlog, duração de trigger, watermark, state e checkpoint."
    verified_by: {kind: test, ref: "tests/test_streaming_rules.py::test_streaming_rules_require_runtime_and_sufficient_evidence"}
  - id: AC5
    statement: "O corpus possui casos positivos, negativos, unresolved e runtime divergente para a primeira onda, com facts e findings esperados."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_streaming.py::test_all_required_fixtures_exist"}
  - id: AC6
    statement: "A superfície CLI e MCP expõe o mesmo contrato para analisar código Structured Streaming e StreamingQueryProgress."
    verified_by: {kind: test, ref: "tests/test_analyze_streaming.py::test_cli_and_core_emit_identical_streaming_envelope"}
  - id: AC7
    statement: "A extração é determinística e não altera o comportamento dos extractors batch existentes."
    verified_by: {kind: test, ref: "tests/test_facts_streaming.py::test_streaming_extraction_is_deterministic_and_batch_safe"}
  - id: AC8
    statement: "O catálogo, routing, referências geradas, mirrors aplicáveis e surface lock reconhecem a primeira onda sem tool órfã ou rule inalcançável."
    verified_by: {kind: command, ref: "python scripts/check_surface_lock.py; python scripts/sync_skills.py --check; sparkforge sdd check --repo . --feature STREAMING_REALTIME_DATA_PLATFORM"}
success:
  - id: SC1
    metric: "Casos de streaming da primeira onda com extração, julgamento, routing e validação verdes"
    source: "pytest focado em tests/test_facts_streaming.py, tests/test_streaming_rules.py, tests/test_fixtures_golden_streaming.py e tests/test_analyze_streaming.py"
  - id: SC2
    metric: "Diferença entre a superfície declarada e a superfície gerada"
    source: "python scripts/check_surface_lock.py"
  - id: SC3
    metric: "Estado SDD da feature e lacunas nomeadas"
    source: "sparkforge sdd check --repo . --feature STREAMING_REALTIME_DATA_PLATFORM"
out_of_scope:
  - "Collectors que chamam Kafka, MSK, Kinesis, Flink, DMS, Debezium ou AWS live; a primeira onda aceita artifacts locais e mantém o core offline-first."
  - "Inferir throughput, latência, custo, capacidade, exactly-once, retenção ou número ideal de partições sem measurement e runtime confirmado."
  - "Parser de checkpoint interno sem contrato de versão; essa decisão fica para uma feature própria."
  - "Implementar Kafka/MSK, Kinesis, Flink, Managed Flink, CDC, Schema Registry e arquitetura de decisão completos; ficam nas ondas registradas no explore."
  - "Criar novos coordinators ou agents como substituto de evidence; a superfície agentic entra depois de facts e rules estáveis."
unknowns:
  - id: U1
    blocks: [AC4]
    unlock: "Consultar fontes oficiais e matrizes de runtime para separar Structured Streaming upstream de Glue Streaming/RTM antes de fixar guards."
  - id: U2
    blocks: [AC2, AC3]
    unlock: "Definir e validar o envelope local aceito para StreamingQueryProgress e a quantidade mínima de observações exigida por cada regra."
  - id: U3
    blocks: [AC8]
    unlock: "Confirmar o gerador de referências, surface lock, manifest de facts e os gates reais após o design."
  - id: U4
    blocks: []
    unlock: "Obter amostras oficiais de checkpoint metadata por versão; sem isso, manter a capacidade como unresolved e fora da primeira onda."
case_id: null
change_kinds: [extractor, rule, rule_runtime_scope, rule_area, fixture_corpus, knowledge_doc, tool_or_verb, routing, agent_or_skill]
---

# STREAMING_REALTIME_DATA_PLATFORM — requisitos

## Problema

O repositório conhece streaming apenas em documentação curta e em dois
especialistas Python que aplicam thresholds sem artefato, `fact_id`, `rule_id` ou
guarda de versão. Isso não permite distinguir padrão reconhecido de diagnóstico
comprovado. A primeira onda cria o backbone observável sobre o qual Kafka, Kinesis,
Flink, CDC, contratos e lakehouse poderão ser adicionados sem duplicar semântica.

## Critérios

Cada critério acima tem verificador executável. Findings só podem sair de facts
ancorados; ausência de série ou runtime vira `unresolved`, nunca zero implícito.
Qualquer regra nova terá fonte, `runtime_scope`, action e fixture positiva/negativa.

## Limites

Esta fase não promete ganhos de performance nem cobertura total do prompt. Ela
entrega a fundação determinística e deixa as integrações externas, parser de
checkpoint e especialistas de transportes como features posteriores explícitas.
