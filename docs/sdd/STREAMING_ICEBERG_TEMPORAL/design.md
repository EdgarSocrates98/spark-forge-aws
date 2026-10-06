---
sdd: 1
feature: STREAMING_ICEBERG_TEMPORAL
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_ICEBERG_TEMPORAL/define.md
  sha256: "32e10987c906b783fad9baee9110d682ea294b8ba064513e325a844c0c0f76b8"
files:
  - {path: sparkforge_aws/facts/iceberg_metadata.py, action: modify, reason: "emitir iceberg.snapshot sem remover snapshots_summary legado"}
  - {path: sparkforge_aws/facts/streaming_composition.py, action: modify, reason: "despachar mode=iceberg_temporal"}
  - {path: sparkforge_aws/facts/streaming_iceberg_temporal.py, action: create, reason: "pareamento puro de batches e snapshots observados"}
  - {path: sparkforge_aws/adapters/_core.py, action: modify, reason: "passar tabela/query/tolerância ao novo modo comum"}
  - {path: sparkforge_aws/adapters/cli.py, action: modify, reason: "expor enum e ajuda do modo temporal Iceberg"}
  - {path: sparkforge_aws/adapters/tools.py, action: modify, reason: "manter paridade CLI/MCP read-only"}
  - {path: tests/test_facts_iceberg_metadata.py, action: modify, reason: "provar facts por snapshot e ausência de timestamp"}
  - {path: tests/test_facts_streaming_composition.py, action: modify, reason: "provar pareamento e unresolved temporal Iceberg"}
  - {path: tests/test_streaming_rules.py, action: modify, reason: "provar regra evidence-first"}
  - {path: tests/test_analyze_streaming_composition.py, action: modify, reason: "provar envelope CLI/MCP"}
  - {path: fixtures/streaming_composition, action: modify, reason: "goldens append, non-append e unresolved com snapshot facts"}
  - {path: rules/catalog/streaming_iceberg.yaml, action: modify, reason: "adicionar SF-STREAMICE-002"}
  - {path: skills/analyze-streaming-composition/SKILL.md, action: modify, reason: "documentar janela progresso→Iceberg e resumo"}
  - {path: knowledge/streaming-lakehouse-observability.md, action: modify, reason: "registrar limites de snapshot temporal e non-append"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "atualizar Wave G e lacunas reais"}
  - {path: docs/guia/referencia, action: modify, reason: "regenerar referências de CLI/MCP/skill"}
  - {path: docs/surface.lock.json, action: modify, reason: "declarar novo modo/schema"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "atualizar hash de knowledge"}
decisions:
  - id: D1
    choice: "Emitir iceberg.snapshot por entrada válida e manter snapshots_summary para compatibilidade."
    rejected: ["substituir resumo legado", "embutir lista potencialmente grande no fact agregado"]
    rollback: "Remover o fact singular e o modo temporal; snapshots_summary e mode=iceberg continuam intactos."
  - id: D2
    choice: "Parear por committed_at observado e timestamp de progress dentro de max_skew_seconds declarado."
    rejected: ["usar ordem de lista", "usar relógio local", "escolher tolerância fixa"]
    rollback: "Remover normalização temporal e preservar unresolved para snapshots sem timestamp."
  - id: D3
    choice: "Emitir um diagnóstico agregado com source_fact_ids de todos os pares, operações e causal_inference=false."
    rejected: ["um finding por snapshot", "copiar payload inteiro de cada snapshot"]
    rollback: "Retirar apenas o diagnóstico derivado e manter facts individuais reauditable."
  - id: D4
    choice: "SF-STREAMICE-002 exige dois pares completos, janela completa e non_append_observed."
    rejected: ["disparar com snapshot único", "atribuir causalidade ao atraso", "usar custo como limiar"]
    rollback: "Manter fato temporal e remover somente a regra nova."
covers:
  - {part: "snapshot facts", acceptance: [AC1]}
  - {part: "temporal composition", acceptance: [AC2, AC3]}
  - {part: "rule", acceptance: [AC4]}
  - {part: "adapters and goldens", acceptance: [AC5, AC6]}
  - {part: "docs and gates", acceptance: [AC7]}
---

# STREAMING_ICEBERG_TEMPORAL — desenho

O desenho conserva a separação facts→composição→judge. Snapshot facts são
observações atômicas; o compositor agrega somente pares compatíveis e guarda
ids para reextração. Nenhuma operação escreve no Iceberg ou no ambiente.

## Conhecimento consultado

- `sparkforge-aws rules lookup --category streaming_iceberg`: `SF-STREAMICE-001`
  existente exige vínculo factual e trata non-append como necessidade de replay,
  não como causa.
- `knowledge/streaming-lakehouse-observability.md`: contrato offline de
  snapshots, progresso, unresolved e limites de causalidade.
- `sparkforge-aws code symbol` sobre `_snapshots_summary_fact` e
  `analyze_streaming_composition`: a mudança reutiliza o extractor e o core
  existentes, sem criar ferramenta paralela.
