---
sdd: 1
feature: TOKEN_ESTIMATE_UNICO
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/TOKEN_ESTIMATE_UNICO/define.md
  sha256: "dae8f8025321cf1eff07f0368eafd020c12b4cb0ea4f7a777172a678049ca6f9"
files:
  - {path: tests/test_token_estimate_unico.py, action: create, reason: "os tres testes de AC1 a AC3; o de identidade falha antes, porque os tres sitios tem formula propria"}
  - {path: sparkforge/agents/budget.py, action: modify, reason: "dono unico da estimativa; a docstring passa a dizer que e a unica e por que o teto"}
  - {path: sparkforge/tools/cost.py, action: modify, reason: "estimate_tokens deixa de ter corpo proprio e passa a ser o de agents/budget, mantendo o nome publico que o __init__ reexporta e o console script sparkforge-tools usa"}
  - {path: sparkforge/context/funnel.py, action: modify, reason: "a conta em linha (piso) vira chamada a estimate_tokens (teto)"}
  - {path: sparkforge/providers/mock.py, action: modify, reason: "as duas contas em linha (piso, podendo dar 0) viram chamada a estimate_tokens"}
  - {path: sparkforge/codeintel/budget.py, action: modify, reason: "a docstring dizia a consolidacao devida; passa a dizer que foi feita, e mantem a razao de este modulo ficar fora"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "a linha auditada que diz 'existe quatro vezes, e essas divergem' passa a descrever o que existe"}
  - {path: docs/claims.lock.json, action: modify, reason: "as alegacoes que o gate de lastro listar, remediadas por id"}
decisions:
  - id: D1
    choice: "O dono e sparkforge/agents/budget.py::estimate_tokens: teto de len/4, minimo 1, nao-string vira JSON ordenado. E o mais completo dos quatro, e o que ja decide o corte das memorias de agente."
    rejected: ["Criar um modulo novo so para a funcao: mais um arquivo em sparkforge/ para mover as alegacoes de corpus, sem ganho sobre o dono que ja existe."]
    rollback: "git revert; as quatro formulas voltam."
  - id: D2
    choice: "tools/cost.py mantem o nome estimate_tokens como alias do dono (`from sparkforge.agents.budget import estimate_tokens`), porque o pacote sparkforge.tools o reexporta como API publica e o console script sparkforge-tools o chama. A identidade (is) prova que e a mesma funcao."
    rejected: ["Apagar tools.cost.estimate_tokens e mudar quem importa: quebraria a API publica do pacote e o console script."]
    rollback: "o mesmo revert de D1."
  - id: D3
    choice: "codeintel/budget.py fica de fora: mede utf8_bytes / 3, e a docstring dele explica que a unidade e o papel sao outros."
    rejected: ["Consolidar os cinco: mudaria select_context para toda memoria de agente, que a propria docstring recusa."]
    rollback: "nenhum: e ausencia de mudanca."
  - id: D4
    choice: "A propriedade do AC2 e testada, nao argumentada: para entradas sinteticas, a escolha do funnel com o estimador unico e prefixo da escolha com a formula antiga, reproduzida no proprio teste."
    rejected: ["Confiar no argumento 'teto e sempre maior ou igual ao piso': verdade para a estimativa por chunk, mas o que importa e o conjunto escolhido, e isso se mede."]
    rollback: "git revert do teste."
covers:
  - {part: "o dono e os tres sitios", acceptance: [AC1, AC3]}
  - {part: "a propriedade do funnel", acceptance: [AC2]}
  - {part: "goldens", acceptance: [AC4]}
  - {part: "a alegacao auditada", acceptance: [AC5]}
---

# TOKEN_ESTIMATE_UNICO — desenho

`agents/budget.py` é o dono. `tools/cost.py` vira alias (a API pública e o console script
continuam funcionando, e a identidade prova que é a mesma função). `funnel` e `mock` trocam
a conta em linha pela chamada. `codeintel` fica fora, com a razão dele.

O vermelho é natural: o teste de identidade falha enquanto três sítios têm fórmula própria,
e o do mock falha porque texto curto dá 0.
