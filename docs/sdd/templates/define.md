---
sdd: 1
feature: EXEMPLO
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/EXEMPLO/explore.md
  sha256: ""
hypothesis:
  claim: "Um resumo por execucao gravado em JSON basta para o coordenador do case."
  prediction: "O coordenador le o resumo sem abrir o relatorio inteiro, e o teste do resumo passa."
  experiment: "Gravar o resumo, ler com o coordenador num case sintetico e rodar o teste."
acceptance:
  - id: AC1
    statement: "O resumo e gravado com os campos declarados."
    verified_by: {kind: test, ref: "tests/test_exemplo.py::test_exemplo"}
success:
  - id: SC1
    metric: "Bytes do resumo contra bytes do relatorio"
    source: "wc -c sobre os dois arquivos da mesma execucao"
out_of_scope:
  - "Verbo novo de CLI (abordagem B do explore)."
unknowns:
  - id: U1
    blocks: [AC1]
    unlock: "Ler o coordenador com sparkforge code symbol para saber que campo ele consome."
case_id: null
change_kinds: [agent_or_skill]
---

# EXEMPLO — requisitos

> Template da skill `sdd-define`. `upstream` so existe quando a feature tem
> `explore.md`; sem explore, apague o bloco inteiro. Rode `sparkforge sdd stamp`
> para preencher o `sha256`, nunca o calcule a mao. `status: draft` enquanto
> houver pergunta aberta.

## Problema

O coordenador do case abre o relatorio inteiro para ler tres campos.

## Criterios

- `acceptance` tem um `verified_by` por criterio: `test` (node id do pytest),
  `command`, `funcval` ou `fact`. O teste pode ainda nao existir; o `check`
  devolve `test_not_written` ate o build escreve-lo.
- `success` sempre com `source`: de onde vem o numero.
- `change_kinds` sai da lista fechada de `sparkforge/sdd/change_kinds.yaml`; e
  dela que o ship deriva os registros.
- `case_id` so no perfil `operator`, copiado do case aberto.
