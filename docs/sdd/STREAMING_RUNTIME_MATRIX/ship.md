---
sdd: 1
feature: STREAMING_RUNTIME_MATRIX
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/STREAMING_RUNTIME_MATRIX/build_report.md
  sha256: "7d86adaa735d774dac6b87c337d58583e1c85c5594e2966b7e1426a7dd0e239e"
hypothesis_outcome: confirmed
registries: [offline_manifest, sources_lock]
deviations: ["MSK e Managed Flink permanecem UNRESOLVED sem snapshot managed/regional local; nenhuma regra recebeu runtime_scope novo."]
---

# STREAMING_RUNTIME_MATRIX — entrega

Matriz streaming adicionada ao knowledge index, source lock e bundle offline.
Estados upstream/managed/observed ficam separados; ausência de evidência live
permanece explícita.

## Gates rodados

- `python -m pytest tests/test_streaming_runtime_matrix.py -q --basetemp .sparkforge/local/pytest-streaming-runtime-matrix` — `3 passed`, exit 0.
- `python -m pytest tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q --basetemp .sparkforge/local/pytest-streaming-runtime-knowledge` — `43 passed`, exit 0.
- `python scripts/refresh_knowledge.py --check --offline` — exit 0.
- `python scripts/verify_offline_bundle.py --check` — `69 checked`, `failed: []`, exit 0.
- `python scripts/check_status_numbers.py --strict` — exit 0.
- `sparkforge-aws sdd check --repo . --feature STREAMING_RUNTIME_MATRIX` — `ok: true`.

## Lições

- Runtime upstream, serviço gerenciado e runtime observado são evidências
  diferentes; uma release upstream não autoriza compatibilidade gerenciada.
- Sem snapshot regional ou artefato live, MSK e Managed Flink permanecem
  `UNRESOLVED`; a lacuna é preservada em vez de preenchida por inferência.
