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
  claim: "Um resumo por execução gravado em JSON basta para o coordenador do case."
  prediction: "O coordenador lê o resumo sem abrir o relatório inteiro, e o teste do resumo passa; se ele precisar abrir o relatório, a afirmação está errada."
  experiment: "Gravar o resumo, ler com o coordenador num case sintético e rodar o teste."
acceptance:
  - id: AC1
    statement: "O resumo é gravado com os campos declarados."
    verified_by: {kind: test, ref: "tests/test_exemplo.py::test_exemplo"}
success:
  - id: SC1
    metric: "Bytes do resumo contra bytes do relatório"
    source: "wc -c sobre os dois arquivos da mesma execução"
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

> Template da skill `sdd-define`. Troque `feature: EXEMPLO` pelo nome da
> feature e ponha `status: draft` ao copiar. `upstream` só existe quando a
> feature tem `explore.md`; sem explore, apague o bloco inteiro. Rode
> `sparkforge sdd stamp` para preencher o `sha256`, nunca o calcule à mão.
> `status: ready` só com zero recusa e depois da leitura do operador.

## Problema

O coordenador do case abre o relatório inteiro para ler três campos.

## Critérios

- `acceptance` tem um `verified_by` por critério: `test` (node id do pytest),
  `command`, `funcval` ou `fact` (`arquivo#id` ou `arquivo#kind:<kind>`). O
  teste pode ainda não existir; o `check` devolve `test_not_written` até o
  build escrevê-lo.
- A previsão da hipótese é mensurável no ship, parte por parte.
- `success` sempre com `source`: de onde vem o número.
- `change_kinds` sai da lista fechada de `sparkforge/sdd/change_kinds.yaml`; é
  dela que o ship deriva os registros.
- `case_id` só no perfil `operator`, copiado do case aberto.
