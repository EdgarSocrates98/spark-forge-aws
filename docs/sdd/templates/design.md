---
sdd: 1
feature: EXEMPLO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/EXEMPLO/define.md
  sha256: ""
files:
  - {path: tests/test_exemplo.py, action: create, reason: "teste de AC1, escrito antes do codigo"}
  - {path: exemplo/resumo.py, action: create, reason: "resumir(), os tres campos que o coordenador le"}
decisions:
  - id: D1
    choice: "Resumo em JSON com os tres campos que o coordenador consome."
    rejected: ["verbo novo de CLI, que moveria a superficie sem segundo consumidor"]
    rollback: "git revert do commit do resumo; o coordenador volta a ler o relatorio."
covers:
  - {part: "resumo", acceptance: [AC1]}
---

# EXEMPLO — desenho

> Template da skill `sdd-design`. Todo caminho com `action: modify` ou `delete`
> precisa existir hoje (confira com `sparkforge code symbol` ou abrindo o
> arquivo); caminho novo e `create`. Toda decisao tem `rejected` e `rollback`.
> Todo `AC` do define aparece em algum `covers`.

## Partes

| parte | arquivos | criterio |
|---|---|---|
| resumo | `tests/test_exemplo.py`, `exemplo/resumo.py` | AC1 |

## Conhecimento consultado

Cite o que foi lido e por qual verbo (`sparkforge rules lookup`,
`sparkforge knowledge path`), nunca a memoria do agente.
