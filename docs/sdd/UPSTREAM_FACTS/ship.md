---
sdd: 1
feature: UPSTREAM_FACTS
phase: ship
profile: dev
status: ready
upstream:
  path: docs/sdd/UPSTREAM_FACTS/build_report.md
  sha256: "192cfd62daf77cff747b0666b613821099958c2dbe79c284c098da22f4be1b92"
hypothesis_outcome: confirmed
registries: [surface_lock, generated_reference, verify_wheel]
deviations:
  - "Neutralização do golden MCP tornada condicional: saída de analyze não tem `rules`; as duas diferenças aditivas (inputSchema.upstream, filters_applied.upstream) ficaram declaradas e datadas."
---

# UPSTREAM_FACTS — entrega

## Hipótese

Confirmada: `analyze pyspark` admite `sparkforge/upstream-facts/v1` em ambas as
superfícies, com identidade estrangeira obrigatória, denylist imperativa e
bounds duros; nenhum fact estrangeiro dispara regra nativa (namespace
`upstream.*`) nem conta em `unresolved`. O oráculo é `items` no fim com
`filters_applied.upstream` nomeando o arquivo — medido em 41 testes.

## Gates rodados

- `python -m pytest tests/test_upstream_intake.py -q` (41 passed)
- `python -m pytest tests/test_fixtures_golden_mcp_parity.py -q` (13 passed)
- `python scripts/gen_reference_docs.py` + `tests/test_reference_docs.py`
- `python scripts/check_surface_lock.py --update` (lock regerado, +208 bytes)
- `python scripts/verify_wheel.py` (disk_read)
- Suíte focada adapters/tools/schemas → 355 passed

## Lições

- O intake vive em `_core.analyze_pyspark`: um ponto de merge só serve CLI e
  tool sem divergência de política — o mesmo desenho que o api-forge usa.
- Identidade estrangeira no próprio documento (`upstream:`/`upstream.`/
  extractor fora do catálogo) dispensa regra de heurística: a recusa é
  estrutural, não probabilística.
- O golden byte-a-byte do MCP precisa de neutralização por formato de saída;
  assumir `rules` em todo payload quebrava no novo campo.
