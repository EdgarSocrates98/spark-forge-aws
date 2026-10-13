---
sdd: 1
feature: UPSTREAM_FACTS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/UPSTREAM_FACTS/design.md
  sha256: "034d479d24f015c571bbc0703b12b0d04726f5c2b9c0f4ec800f817a8baeb70f"
tasks:
  - id: T1
    files: [sparkforge/adapters/upstream.py, tests/test_upstream_intake.py]
    covers: [AC2, AC3, AC4]
    test: {path: tests/test_upstream_intake.py, name: 'TestDocumentValidation::test_file_size_bound'}
  - id: T2
    files: [sparkforge/adapters/_core.py, sparkforge/adapters/tools.py, sparkforge/adapters/cli.py, tests/test_upstream_intake.py]
    covers: [AC1, AC5]
    test: {path: tests/test_upstream_intake.py, name: 'TestAnalyzePysparkMerge::test_upstream_facts_merge_into_items'}
  - id: T3
    files: [tests/test_fixtures_golden_mcp_parity.py, docs/surface.lock.json, docs/reference/cli.md, docs/guia/08-rigor-e-handoff.md]
    covers: [AC6]
    test: {path: tests/test_fixtures_golden_mcp_parity.py, name: 'TestHandshakeLegado::test_toda_chamada_bate_byte_a_byte'}
---

# UPSTREAM_FACTS — plano

## T1 — módulo de intake e sua recusa

Teste primeiro, em `tests/test_upstream_intake.py` — `TestDocumentValidation`,
`TestForeignIdentity`, `TestInstructionDenylist`, `TestProvenanceStamp`:
documento válido vira dicts de Fact com artefato carimbado; cada classe de
recusa sai com `AdapterError` exit 2 e mensagem declarando o motivo.

```bash
python -m pytest tests/test_upstream_intake.py -x -q
```

Vermelho esperado: `ImportError: cannot import name 'upstream' from
'sparkforge.adapters'` (exit 2, collection) — o módulo é a unidade sob teste.

Código mínimo, em `sparkforge/adapters/upstream.py`: `UPSTREAM_DOC_SCHEMA =
"sparkforge/upstream-facts/v1"`, `UPSTREAM_MAX_FACTS = 128`,
`UPSTREAM_MAX_BYTES = 256 * 1024`, `_FORBIDDEN` espelhando o api-forge,
`_check_identity` (id `upstream:`, kind `upstream.`, extractor estrangeiro,
`attrs.upstream` com provider/run_id/node/item), `_scan_forbidden` iterativo,
`load_upstream_document(path) -> list[dict]` que carimba
`provenance.artifact`/`artifact_sha256` com o arquivo consumido.

## T2 — merge no `_core` e nas duas superfícies

Mesmo arquivo de teste — `TestAnalyzePysparkMerge`, `TestCliSurface`,
`TestToolSurface`: merge no fim de `items`, `kind` filtra os upstream,
`filters_applied.upstream` nomeia o arquivo, recusa vira exit 2 no CLI e
`{error, exit_code: 2}` na tool; inputSchema declara `upstream`.

```bash
python -m pytest tests/test_upstream_intake.py -q
```

Código: `_core.analyze_pyspark` ganha `upstream: str | Path | None` —
valida primeiro, extrai depois, concatena no fim de `items`; `tools.py` adiciona
`upstream` ao inputSchema e repassa `args.get("upstream")`; `cli.py` adiciona
`--upstream` e repassa.

## T3 — superfície declarada e docs

Golden de paridade MCP: declarar as duas diferenças aditivas datadas
(`inputSchema.upstream` e `filters_applied.upstream`), corrigir a
neutralização condicional para saída de analyze sem `rules`. Regen:

```bash
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py --update
python -m pytest tests/test_fixtures_golden_mcp_parity.py -q
```

E o contrato no guia `docs/guia/08-rigor-e-handoff.md` (seção do intake, shape
do documento, identidade obrigatória, denylist, bounds, política de recusa).
