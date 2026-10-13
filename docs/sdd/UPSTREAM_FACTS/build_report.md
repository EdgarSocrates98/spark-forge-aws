---
sdd: 1
feature: UPSTREAM_FACTS
phase: build_report
profile: dev
status: ready
upstream:
  path: docs/sdd/UPSTREAM_FACTS/plan.md
  sha256: "16a0371b2931825a6d48b5035c20bc4b528f358d796724c22aa74b06f0ffd173"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_upstream_intake.py -x -q", exit: 2}
    green: {command: "python -m pytest tests/test_upstream_intake.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_upstream_intake.py -x -q", exit: 2}
    green: {command: "python -m pytest tests/test_upstream_intake.py -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_fixtures_golden_mcp_parity.py -q", exit: 1}
    green: {command: "python -m pytest tests/test_fixtures_golden_mcp_parity.py -q", exit: 0}
claims:
  - text: "Documento sparkforge/upstream-facts/v1 válido entra em items, conta em by_kind e nomeia o arquivo em filters_applied.upstream."
    evidence_ref: "tests/test_upstream_intake.py::TestAnalyzePysparkMerge::test_upstream_facts_merge_into_items"
  - text: "Fact sem id `upstream:`, kind `upstream.`, extractor estrangeiro ou provenance attrs.upstream completa é recusado, nunca admitido parcialmente."
    evidence_ref: "tests/test_upstream_intake.py::TestForeignIdentity::test_native_or_missing_extractor_is_laundering"
  - text: "Chave imperativa em qualquer profundidade recusa o documento; `upstream`, `comment` e `plan_run` (provenance) passam."
    evidence_ref: "tests/test_upstream_intake.py::TestInstructionDenylist::test_plan_run_is_provenance_not_instruction"
  - text: "Bounds de 128 facts e 256 KiB são enforcement duro com exit 2."
    evidence_ref: "tests/test_upstream_intake.py::TestDocumentValidation::test_fact_count_bound"
  - text: "CLI `--upstream` e tool `sparkforge_analyze_pyspark(upstream=...)` consomem o mesmo intake; recusa sai exit 2 / error-envelope."
    evidence_ref: "tests/test_upstream_intake.py::TestToolSurface::test_tool_refusal_is_an_error_envelope"
  - text: "Golden MCP continua byte a byte com as duas diferenças aditivas declaradas e datadas."
    evidence_ref: "tests/test_fixtures_golden_mcp_parity.py"
change_id: null
---

# UPSTREAM_FACTS — relatório do build

## Desvios do plano

- A neutralização do golden assumia `rules` em toda saída alterada; a saída de
  `analyze` não tem `rules`. A correção tornou `_neutro` condicional e manteve
  as exceções declaradas — sem relaxar o byte a byte.
- O `_h_analyze_pyspark` passou a repassar `args.get("upstream")`; a alteração
  no inputSchema (+1 propriedade) e em `filters_applied` (+1 chave nula) mudou
  o diff medido de 47 para 48 por transporte — declarado no teste, datado.

## Revisão

Revisão de spec: cada task cobre só os ACs declarados; o intake não toca em
`judge`, `unresolved` ou regras nativas. Revisão de qualidade: bounds antes do
parse custoso; denylist iterativa sem recursão; nenhum fact estrangeiro tem id
rederivado (D2).

## Evidência

- `python -m pytest tests/test_upstream_intake.py -q` → 41 passed
- `python -m pytest tests/test_fixtures_golden_mcp_parity.py -q` → 13 passed
- Suíte focada (adapters/tools/schemas/surface) → 355 passed
