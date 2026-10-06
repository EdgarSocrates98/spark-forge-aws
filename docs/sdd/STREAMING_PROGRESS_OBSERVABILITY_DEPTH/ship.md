---
sdd: 1
feature: STREAMING_PROGRESS_OBSERVABILITY_DEPTH
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_PROGRESS_OBSERVABILITY_DEPTH/build_report.md
  sha256: "cf1e0db32819d6daaee039e032745f203af724c8824824d3a8ebf1eb699bd489"
hypothesis_outcome: confirmed
registries:
  - rules_catalog_gates
  - manifest_rule_count
  - reachability_lists
  - snippet_measure
  - runtime_scope_gates
  - fixture_kind_coverage
  - fixture_corpus_gates
  - offline_manifest
  - sources_lock
  - surface_lock
  - generated_reference
  - sync_skills
  - agents_parity
  - status_numbers_gate
deviations:
  - "streaming.progress.series foi ampliado; não foi criado segundo extrator nem tool nova."
  - "Watermark parado e memória crescente são sintomas observados, sem threshold, causa, freshness, exactly-once ou claim de performance."
  - "Timestamps e watermarks inválidos permanecem unresolved nomeados; a ordem do arquivo não preenche a evidência."
  - "A suíte completa não foi executada nesta frente, conforme escopo solicitado."
---

# STREAMING_PROGRESS_OBSERVABILITY_DEPTH — ship

## Resultado

Ship concluído. `streaming.progress.series` agora preserva, em envelope compacto,
span temporal observado, duração do batch, memória total observada por operador
de state e progressão de watermark quando a série é completa. As regras
`SF-STREAM-013` e `SF-STREAM-014` transformam apenas os sintomas observados de
watermark parado e memória crescente em findings evidence-first, exigindo duas
observações e `env.runtime_signal`.

## Aceitação

- **AC1–AC2:** medidas temporais, duração, state memory, watermark e unresolved
  nomeado estão cobertos nos testes direcionados do extrator.
- **AC3/AC5:** as duas regras têm evidence/runtime gates, ação, rollback,
  fontes e goldens positivos; ausência de runtime ou de série suficiente não
  produz finding.
- **AC4:** fixtures existentes foram regeneradas e
  `progress_watermark_stalled` cobre fatos e findings determinísticos.
- **AC6:** knowledge, skill canônica, mirrors, prompt coverage, referência
  gerada, surface lock, offline manifest, status numbers e catálogo foram
  reconciliados.

## Gates executados

- Facts direcionados: 2 passed; regras direcionadas: 1 passed; cobertura docs: 1
  passed; regressão de facts/regras: 11 passed.
- Golden streaming: 35 passed; corpus/fixture/offline gates: 116 passed;
  runtime-scope gates: 781 passed.
- Catálogo/docs/knowledge: 1214 passed.
- `gen_reference_docs --check`, `sync_skills --check`, surface lock, status
  numbers, refresh knowledge offline e bundle offline: verdes.
- `sparkforge-aws sdd check --repo . --feature STREAMING_PROGRESS_OBSERVABILITY_DEPTH`:
  verde, sem recusas ou unresolved.

## Limites e próximos desbloqueios

Não há medição de performance, custo, throughput, latência, capacidade cloud,
freshness, exatamente-once, replay, causalidade ou endpoint live. Para fechar
esses eixos ainda são necessários progress real em runtime, collector/endpoint,
artefatos temporais pareados ou execução funcional conforme o caso.

O ship não altera a ativação do Decision Plane e não cria claims de produção.
