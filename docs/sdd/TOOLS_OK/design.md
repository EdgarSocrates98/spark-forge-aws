---
sdd: 1
feature: TOOLS_OK
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/TOOLS_OK/define.md
  sha256: "8a9f29794c6b31464f0168600c94252b5dd8bd76034f8cd1ad966835ecbfdee3"
files:
  - {path: tests/test_tools_ok_rule.py, action: create, reason: "testes de AC1, AC2 e AC3, escritos antes do texto"}
  - {path: CLAUDE.md, action: modify, reason: "bloco curto logo abaixo do titulo, antes da lista numerada: pergunta sobre artefato vai primeiro ao verbo, com tabela de tipo de pergunta para verbo"}
  - {path: AGENTS.md, action: modify, reason: "o mesmo bloco, em ingles como o resto do arquivo, com o mesmo conjunto de verbos"}
  - {path: evals/agentic/fase0/baselines, action: modify, reason: "baseline novo 2026-09-XX-haiku-4-5-tools-ok com r1..r3, gravado pela rodada do AC5"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo move alegacoes do gate de lastro"}
decisions:
  - id: D1
    choice: "O bloco fica logo abaixo do titulo do CLAUDE.md, antes de 'Ao trabalhar em codigo PySpark', sem numero: nao renumera as regras 1 a 33 que tests/test_bootstrap_budget.py trava, e e a primeira coisa que o agente le."
    rejected: ["regra numerada nova (34): cairia no fim do arquivo, depois de 23 KB de texto", "secao nova no meio: o canal injetado e lido de cima para baixo, e a medida mostra o agente pulando o que fica longe"]
    rollback: "git revert do commit da regra"
  - id: D2
    choice: "A tabela liga tipo de pergunta ao verbo pelo nome da tool MCP (sparkforge_<verbo>): codigo PySpark -> analyze_pyspark e judge; plano fisico -> analyze_plan e judge; event log -> analyze_event_log e judge; regra do catalogo -> rules_lookup; versao e runtime -> runtime_detect ou release_describe; custo -> finops; comparar runs -> benchmark. Uma linha diz que a resposta cita o fact_id ou o rule_id que a sustenta."
    rejected: ["listar as 106 tools: estoura o teto e dilui a regra", "citar a CLI em vez da tool MCP: na eval o agente chama tools MCP, e o grader confere por nome de tool"]
    rollback: "git revert do commit da regra"
  - id: D3
    choice: "AC3 prova que todo verbo citado existe em sparkforge.adapters.tools.TOOLS e que o conjunto cobre todas as required_tools da suite fase0, lendo a propria suite."
    rejected: ["conferir contra lista escrita no teste: envelhece sem acusar"]
    rollback: "git revert do commit do teste"
  - id: D4
    choice: "A medida roda --runs 3 com o modelo e a suite do baseline de 2026-09-16, e o baseline novo e gravado ao lado dele; a comparacao entra no ship com k/N, sem afirmar causa alem do experimento."
    rejected: ["--runs 1: a variancia entre repeticoes do baseline (3, 3, 1) nao cabe numa amostra so"]
    rollback: "git rm do diretorio do baseline novo"
covers:
  - {part: "regra no CLAUDE.md", acceptance: [AC1, AC4]}
  - {part: "regra no AGENTS.md", acceptance: [AC2, AC4]}
  - {part: "trava dos verbos", acceptance: [AC3]}
  - {part: "medida", acceptance: [AC5]}
---

# TOOLS_OK — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| regra no CLAUDE.md | `CLAUDE.md` | AC1, AC4 |
| regra no AGENTS.md | `AGENTS.md` | AC2, AC4 |
| trava dos verbos | `tests/test_tools_ok_rule.py` | AC3 |
| medida | baseline novo em `evals/agentic/fase0/baselines/` | AC5 |

## Medidas que sustentam o desenho

- `CLAUDE.md` 23 533 bytes e `AGENTS.md` 22 145, teto 26 000: o bloco cabe se ficar
  em torno de 1,2 KB.
- `tests/test_bootstrap_budget.py::test_regras_do_claude_md_mantem_a_numeracao` trava
  a numeração 1–33: o bloco não é numerado.
- As `required_tools` da suíte fase0: `analyze_pyspark`, `judge`, `rules_lookup`,
  `runtime_detect` ou `release_describe`, `finops`, `benchmark` ou
  `analyze_event_log`, `analyze_plan`.
