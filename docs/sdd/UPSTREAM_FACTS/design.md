---
sdd: 1
feature: UPSTREAM_FACTS
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/UPSTREAM_FACTS/define.md
  sha256: "bd8dcedcb27c9fafa3a41805ed026d22886fa9dfc33a360f4b1238c92e1dae16"
covers:
  - {part: "intake (upstream.py)", acceptance: [AC2, AC3, AC4]}
  - {part: "merge + superfícies", acceptance: [AC1, AC5]}
  - {part: "paridade MCP declarada", acceptance: [AC6]}
files:
  - {path: tests/test_upstream_intake.py, action: create, reason: "41 testes de AC1-AC5, escritos antes do código"}
  - {path: sparkforge/adapters/upstream.py, action: create, reason: "validação do documento: shape, identidade estrangeira, denylist, bounds"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "parâmetro upstream em analyze_pyspark; merge no fim de items"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "inputSchema de sparkforge_analyze_pyspark ganha upstream; handler repassa"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "flag --upstream em analyze pyspark"}
  - {path: tests/test_fixtures_golden_mcp_parity.py, action: modify, reason: "declarar as duas diferenças aditivas datadas; neutralização condicional"}
  - {path: docs/surface.lock.json, action: modify, reason: "regenerado por check_surface_lock.py --update"}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "regenerado por gen_reference_docs.py (--upstream)"}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_pyspark.md, action: modify, reason: "regenerado por gen_reference_docs.py (inputSchema.upstream)"}
  - {path: docs/guia/08-rigor-e-handoff.md, action: modify, reason: "contrato sparkforge/upstream-facts/v1 documentado"}
decisions:
  - id: D1
    choice: "Intake primeiro, fatos locais depois: `load_upstream_document` valida antes do walk do FS; recusa sai antes de tocar no disco do projeto."
    rejected: ["merge inline depois da varredura — documento malformado custaria uma varredura inteira"]
    rollback: "git revert do commit; `--upstream` volta a não existir."
  - id: D2
    choice: "Merge no fim de `items`, sem rederivação de id: `Fact.from_dict` confia no id recebido (`upstream:*`)."
    rejected: ["rederivar com Fact.compute_id — lavaria a origem, quebrando a endereçabilidade do emissor"]
    rollback: "mesma reversão; os facts upstream somem com o parâmetro."
  - id: D3
    choice: "Denylist iterativa com pilha explícita varrendo subject/measures/attrs/provenance (mais larga que a do api-forge, que cobre só attrs/measures); vocabulário idêntico ao `_FORBIDDEN_KEYS` de lá."
    rejected: ["recursão — limite de pilha em adversário; vocabulário divergente do api-forge — dois dialetos de recusa no mesmo fluxo de handoff"]
    rollback: "mesma reversão."
  - id: D4
    choice: "Shape checado com `dataclasses.fields(Fact)`; campos desconhecidos tolerados."
    rejected: ["validar semântica nativa além do shape — recusaria campos de especialistas de outros domínios"]
    rollback: "mesma reversão."
  - id: D5
    choice: "Identidade imperfeita recusa o documento inteiro, nunca skip parcial."
    rejected: ["skip com aviso — fact sem marcação é indistinguível de lavagem (AF-UPSTREAM-UNMARKED)"]
    rollback: "mesma reversão."
---

# UPSTREAM_FACTS — desenho

## Fluxo

```
CLI: analyze pyspark --upstream <doc>          MCP tool: {path, upstream: <doc>}
        |                                              |
        +---------------- _core.analyze_pyspark ------+
                                   |
            upstream is not None -> _load_upstream_document
                                   |   (bounds → dict/list/shape → identidade → denylist)
                                   v
                              list[Fact] estrangeiros
                                   |
            walk *.py -> extratores -> facts locais
                                   |
                      items = locais + estrangeiros
```

`filters_applied.upstream` registra o arquivo consumido (string) ou `null`; os
facts estrangeiros entram em `items`, `by_kind` e `total_count`, nunca em
`unresolved`, e não disparam regra nativa porque nenhum `where` casa
`upstream.*`.

## Identidade obrigatória

`id` prefixo `upstream:` (endereço por conteúdo do emissor); `kind` prefixo
`upstream.`; `provenance.extractor` fora do catálogo local e sem prefixo
`sparkforge`; `attrs.upstream` com `provider`, `run_id`, `node`, `item` todos
não vazios. Qualquer falta = recusa total (D5).

## Denylist

`_FORBIDDEN` espelha `_FORBIDDEN_KEYS` do api-forge: action, agent, command,
context, directive, execute, goal, instruction, message, objective, plan,
prompt, request, role, route, routing, system, task, tool_call, workflow.
Varredura iterativa, comparação `casefold`, sem wildcard nem substring —
`upstream` e `comment` passam.

## Bounds

128 facts e 256 KiB por chamada, gravados em
`provenance.artifact`/`artifact_sha256` de cada fact admitido (a fonte real do
fact: o documento, não o transporte).
