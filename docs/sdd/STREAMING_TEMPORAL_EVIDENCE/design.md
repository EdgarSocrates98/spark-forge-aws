---
sdd: 1
feature: STREAMING_TEMPORAL_EVIDENCE
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_TEMPORAL_EVIDENCE/define.md
  sha256: "005fc7b3c6439dea3a3d73058ec4c9814c69d5f8a8aad3909ace6824b8848897"
files:
  - {path: sparkforge/facts/streaming_temporal.py, action: create, reason: "compositor puro de pares temporais sobre facts já extraídos"}
  - {path: sparkforge/facts/streaming_composition.py, action: modify, reason: "despachar o modo temporal sem duplicar envelope"}
  - {path: sparkforge/facts/transport.py, action: modify, reason: "preservar timestamp/observed_at já presente em offsets e shards"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "expor max_skew_seconds à composição comum"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "aceitar modo temporal e tolerância declarada"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "manter paridade CLI/MCP e declarar schema read-only"}
  - {path: tests/test_facts_streaming_temporal.py, action: create, reason: "provar pareamento, procedência e unresolved"}
  - {path: tests/test_facts_transport.py, action: modify, reason: "provar preservação de timestamp observado"}
  - {path: tests/test_streaming_rules.py, action: modify, reason: "provar finding temporal somente com dois pares"}
  - {path: tests/test_analyze_streaming_composition.py, action: modify, reason: "provar envelope CLI/MCP do modo temporal"}
  - {path: fixtures/streaming_temporal, action: create, reason: "goldens Kafka/Kinesis positivos e incompletos"}
  - {path: tests/test_fixtures_golden_streaming_temporal.py, action: create, reason: "cobrir corpus temporal e contrato de kinds"}
  - {path: rules/catalog/streaming_observability.yaml, action: modify, reason: "regra evidence-driven para janela temporal observada"}
  - {path: skills/analyze-streaming-composition/SKILL.md, action: modify, reason: "documentar modo temporal e uso token-efficient"}
  - {path: knowledge/streaming-lakehouse-observability.md, action: modify, reason: "documentar contrato temporal e limites de relógio"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "mover correlação temporal curta de lacuna total para contrato offline parcial"}
  - {path: docs/guia/referencia, action: modify, reason: "regenerar referência CLI/MCP/skill após alteração de superfície"}
  - {path: docs/surface.lock.json, action: modify, reason: "declarar crescimento medido do schema MCP"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "atualizar hash do conhecimento alterado"}
decisions:
  - id: D1
    choice: "Reusar `analyze streaming-composition` com `mode: temporal`, em vez de criar tool MCP nova."
    rejected: ["duplicar tool e envelope para o mesmo conjunto de facts", "CLI-only sem paridade MCP"]
    rollback: "Remover o modo temporal, restaurar enum/schema anterior e reverter o compositor novo; os analyzers de origem continuam intactos."
  - id: D2
    choice: "Aceitar somente timestamps observados ISO/numericamente normalizáveis e exigir max_skew_seconds do chamador."
    rejected: ["inferir tempo pela ordem dos arquivos", "escolher tolerância fixa sem declaração", "usar relógio local"]
    rollback: "Reverter normalização e preservar unresolved dos artefatos sem timestamp."
  - id: D3
    choice: "Agrupar múltiplas partições/shards pelo timestamp, carregar ids de todos os facts e emitir só resumo compacto."
    rejected: ["emitir uma finding por partição", "copiar cada par completo para o payload padrão"]
    rollback: "Retornar ao vínculo pontual de observabilidade e manter ids de origem para expansão reextraída."
  - id: D4
    choice: "Regra exige dois pares e coexistência observada de processamento abaixo da entrada com backlog/idade; não há limiar de lag, custo ou throughput."
    rejected: ["disparar por um snapshot", "classificar root cause", "prometer ganho esperado"]
    rollback: "Manter o fact temporal factual e retirar apenas o finding derivado."
covers:
  - {part: "extração e composição temporal", acceptance: [AC1, AC2, AC3]}
  - {part: "regra e evidência", acceptance: [AC4]}
  - {part: "fixtures e adapter parity", acceptance: [AC5, AC6]}
  - {part: "skill, knowledge, coverage e gates", acceptance: [AC7]}
---

# STREAMING_TEMPORAL_EVIDENCE — desenho

O compositor transforma uma relação temporal em evidência compacta, não em
causa. A janela é parte da entrada, o skew observado é parte da saída e os
facts individuais continuam disponíveis para reauditoria. `summary` e `normal`
reduzem bytes sem remover os ids necessários para buscar a evidência de origem.
