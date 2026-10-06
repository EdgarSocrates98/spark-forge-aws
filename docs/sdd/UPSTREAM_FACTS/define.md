---
sdd: 1
feature: UPSTREAM_FACTS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/UPSTREAM_FACTS/explore.md
  sha256: "ee51d559a8c240b9b1d6dc6123cc5d297e0430101a3c4f9eae978ae2d377a35f"
hypothesis:
  claim: "`analyze pyspark` consegue admitir evidência de outro motor via documento `sparkforge/upstream-facts/v1`, preservando identidade estrangeira (id/kind/extractor em namespaces `upstream`), sem que nenhum fact estrangeiro dispare regra nativa, conte em `unresolved` ou transporte instrução."
  prediction: "Com documento válido, `items` termina com os facts do documento na ordem declarada, `by_kind` conta os kinds `upstream.*` e `filters_applied.upstream` nomeia o arquivo; documento malformado, não marcado, imperativo ou acima dos bounds sai com exit 2. Se um fact estrangeiro disparar regra nativa, for contado em `unresolved` ou uma chave `prompt` passar, a afirmação está errada."
  experiment: "tests/test_upstream_intake.py: documentos válidos e cada classe de recusa, pelo _core, pelo CLI e pela tool MCP."
acceptance:
  - id: AC1
    statement: "Documento válido entra em `items` no fim (ordem preservada), com `by_kind` contando os kinds `upstream.*` e `filters_applied.upstream` nomeando o arquivo consumido."
    verified_by: {kind: test, ref: "tests/test_upstream_intake.py::TestAnalyzePysparkMerge::test_upstream_facts_merge_into_items"}
  - id: AC2
    statement: "Identidade estrangeira é obrigatória: `id` sem prefixo `upstream:`, `kind` sem `upstream.`, `provenance.extractor` nativo ou `attrs.upstream` sem provider/run_id/node/item recusam o documento."
    verified_by: {kind: test, ref: "tests/test_upstream_intake.py::TestForeignIdentity::test_id_must_carry_upstream_prefix"}
  - id: AC3
    statement: "Chave imperativa em qualquer profundidade de subject/measures/attrs/provenance recusa o documento inteiro; o intake transporta evidência, nunca instrução."
    verified_by: {kind: test, ref: "tests/test_upstream_intake.py::TestInstructionDenylist::test_imperative_key_refused"}
  - id: AC4
    statement: "Bounds são enforcement duro: >128 facts ou >256 KiB recusam; na admissão, provenance.artifact/artifact_sha256 são gravados com o arquivo consumido."
    verified_by: {kind: test, ref: "tests/test_upstream_intake.py::TestDocumentValidation::test_file_size_bound"}
  - id: AC5
    statement: "As duas superfícies aceitam o intake: `--upstream` no CLI e `upstream` no inputSchema de `sparkforge_analyze_pyspark`, ambos opcionais; recusa sai como exit 2 / {error, exit_code: 2}."
    verified_by: {kind: test, ref: "tests/test_upstream_intake.py::TestCliSurface::test_cli_upstream_merges_facts"}
  - id: AC6
    statement: "O golden de paridade MCP continua byte a byte: as diferenças novas (inputSchema.upstream e filters_applied.upstream nulo) entram declaradas nos mecanismos de exceção datados."
    verified_by: {kind: command, ref: "python -m pytest tests/test_fixtures_golden_mcp_parity.py -q"}
success:
  - id: SC1
    metric: "Facts upstream por documento admitido, com limite"
    source: "128 facts / 256 KiB em sparkforge/adapters/upstream.py"
  - id: SC2
    metric: "Bytes que a tool `sparkforge_analyze_pyspark` cresceu no surface lock"
    source: "git diff docs/surface.lock.json (tools.total_bytes)"
out_of_scope:
  - "Intake `--upstream` em outros verbos analyze (graph, sql, data-quality): o The Forge consome só `pyspark` hoje; cada novo verbo entra por feature própria."
  - "O lado tradutor (theforge_sparkforge/handoff.py): mora no adapter do The Forge, repositório vizinho."
unknowns: []
case_id: null
change_kinds: [tool_or_verb, disk_read]
---

# UPSTREAM_FACTS — requisitos

## Problema

O The Forge encadeia especialistas por handoff (`theforge/Handoff/v1`). O lado
da API já recebe evidência estrangeira por `apiforge/upstream-facts/v1`; o lado
de dados não tem intake nenhum — o diagnóstico do Forge Doctor Data chegaria ao
Spark Forge como texto livre (instrução disfarçada) ou não chegaria.

## Critérios

Cada `verified_by` aponta o teste que prova o critério; AC6 é comando porque a
prova é o gate inteiro ficar verde com as exceções declaradas.

## Limites

- Facts admitidos nunca viram alvo de regra nativa: kinds `upstream.*` não
  casam com `where`/`expr` de nenhuma regra do catálogo, por construção do
  namespace.
- `unresolved` continua medindo ponto cego do extrator local: facts vindos de
  fora não entram no contador.
