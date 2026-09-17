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
  - {path: tests/test_exemplo.py, action: create, reason: "teste de AC1, escrito antes do código"}
  - {path: exemplo/resumo.py, action: create, reason: "resumir(), os três campos que o coordenador lê"}
decisions:
  - id: D1
    choice: "Resumo em JSON com os três campos que o coordenador consome."
    rejected: ["verbo novo de CLI, que moveria a superfície sem segundo consumidor"]
    rollback: "git revert do commit do resumo; o coordenador volta a ler o relatório."
covers:
  - {part: "resumo", acceptance: [AC1]}
---

# EXEMPLO — desenho

> Template da skill `sdd-design`. Troque `feature: EXEMPLO` pelo nome da
> feature e ponha `status: draft` ao copiar. Todo caminho com
> `action: modify` ou `delete` precisa existir hoje (confira com
> `sparkforge code symbol` ou abrindo o arquivo); caminho novo é `create`. Toda
> decisão tem `rejected` e `rollback`. Todo `AC` do define aparece em algum
> `covers`.

## Partes

| parte | arquivos | critério |
|---|---|---|
| resumo | `tests/test_exemplo.py`, `exemplo/resumo.py` | AC1 |

## Conhecimento consultado

Cite o que foi lido e por qual verbo (`sparkforge rules lookup`,
`sparkforge knowledge path`), com a versão, nunca a memória do agente.
