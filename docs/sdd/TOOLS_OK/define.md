---
sdd: 1
feature: TOOLS_OK
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/TOOLS_OK/explore.md
  sha256: "77296e9ec2324b3c6622c7b4a15a9b903473a59511995e1350b4ee5a14050154"
hypothesis:
  claim: "Uma regra curta no que o host injeta (CLAUDE.md e AGENTS.md), mandando a pergunta sobre artefato primeiro ao verbo do SparkForge, faz o agente usar as tools exigidas sem perder acerto. O answer_protocol da suite ja pede isso no texto da pergunta, e o agente ignora; a hipotese e que o canal injetado muda o comportamento onde a pergunta nao mudou."
  prediction: "Numa rodada Haiku 4.5 da suite fase0 com 3 repeticoes, com o CLAUDE.md e o AGENTS.md novos, a mediana de tools_ok por repeticao sobe de 3 (baseline 2026-09-16: 3, 3 e 1) para 7 ou mais, e nenhuma repeticao tem acerto abaixo de 9 (o minimo do baseline). Se a mediana de tools_ok ficar em 3 ou menos, ou se o acerto cair abaixo de 9 em qualquer repeticao, a afirmacao esta errada."
  experiment: "Gravar a regra, rodar python scripts/run_agentic_eval.py --suite fase0 --model haiku --runs 3, e comparar o scorecard com evals/agentic/fase0/baselines/2026-09-16-haiku-4-5-lookup-busca."
acceptance:
  - id: AC1
    statement: "O CLAUDE.md abre, antes da primeira secao de regras numeradas, com uma regra curta: pergunta sobre artefato vai primeiro ao verbo do SparkForge, com uma tabela de tipo de pergunta para verbo."
    verified_by: {kind: test, ref: "tests/test_tools_ok_rule.py::test_claude_md_abre_com_a_regra_de_prova"}
  - id: AC2
    statement: "O AGENTS.md carrega a mesma regra, com o mesmo conjunto de verbos."
    verified_by: {kind: test, ref: "tests/test_tools_ok_rule.py::test_agents_md_carrega_a_mesma_regra"}
  - id: AC3
    statement: "Todo verbo que a regra cita existe como tool MCP do SparkForge, e cobre as tools que a suite fase0 exige."
    verified_by: {kind: test, ref: "tests/test_tools_ok_rule.py::test_verbos_da_regra_existem_e_cobrem_a_suite"}
  - id: AC4
    statement: "O CLAUDE.md e o AGENTS.md continuam dentro do teto de tamanho."
    verified_by: {kind: command, ref: "python -m pytest tests/test_bootstrap_budget.py -q"}
  - id: AC5
    statement: "Uma rodada Haiku 4.5 da suite fase0 com 3 repeticoes e gravada como baseline novo, com tools_ok e acerto por repeticao e a comparacao com o baseline de 2026-09-16, sem afirmar ganho alem do medido."
    verified_by: {kind: command, ref: "python scripts/run_agentic_eval.py --suite fase0 --model haiku --runs 3"}
success:
  - id: SC1
    metric: "Mediana de tools_ok por repeticao, antes (3) e depois"
    source: "scorecard r1..r3 do baseline novo em evals/agentic/fase0/baselines/, contra 2026-09-16-haiku-4-5-lookup-busca"
  - id: SC2
    metric: "Acerto por repeticao, antes (9, 9, 10) e depois"
    source: "os mesmos scorecards"
  - id: SC3
    metric: "Bytes de resultado de Read e de tools MCP do SparkForge por repeticao"
    source: "tool_result_bytes_by_tool dos mesmos scorecards"
out_of_scope:
  - "Hook PreToolUse que recusa Read (abordagem C do explore): feature seguinte se tools_ok nao subir."
  - "Descricoes de tools e skills (abordagem B)."
  - "Grader conferir se a resposta cita fact_id ou rule_id: o grader atual confere tools; medir a citacao e mudanca propria em sparkforge/evals."
  - "Mudar a suite fase0 ou o answer_protocol: a medida so vale com a suite constante."
  - "Outros modelos alem do Haiku 4.5."
unknowns:
  - id: U1
    blocks: [AC5]
    unlock: "claude CLI autenticado na maquina do operador e o custo da rodada (medido antes em cerca de US$ 6 por 3 repeticoes da fase0) aprovado pelo operador; sem isso o baseline fica pendente e o ship fecha a hipotese como abandoned."
  - id: U2
    blocks: [AC5]
    unlock: "A maquina ficou sem memoria em execucoes longas nesta sessao; a rodada precisa terminar sem ser interrompida. Destrava: rodar com a maquina livre, uma repeticao por vez se preciso (--runs 1 tres vezes)."
change_kinds: [claims]
---

# TOOLS_OK — requisitos

## Problema

No baseline de 2026-09-16 (Haiku 4.5, fase0, 3 repetições), o agente acerta 9 ou 10
de 13 perguntas lendo os arquivos, e usa as tools exigidas em 3, 3 e 1 delas. O
`answer_protocol` da suíte já diz "Responda usando as tools ou a CLI do SparkForge";
o agente não segue. O `Read` responde por 380 039 bytes de resultado na primeira
repetição; as tools MCP do SparkForge juntas, cerca de 18 000.

## Fontes citadas

- `evals/agentic/fase0/baselines/2026-09-16-haiku-4-5-lookup-busca/r1..r3.json`:
  `totals.correct` 9, 9, 10; `totals.tools_ok` 3, 3, 1.
- `scripts/run_agentic_eval.py`: `WORKSPACE_FILES` copia `CLAUDE.md`, `AGENTS.md` e
  `AGENT_PROTOCOL.md` para o workspace da eval.
- `tests/test_bootstrap_budget.py`: teto de 26 000 bytes para cada um; hoje o
  `CLAUDE.md` tem 23 533 e o `AGENTS.md` 22 145.

## Critérios

- AC1 a AC4 são a regra e a trava dela; AC5 é a medida.
- `change_kinds: [claims]` porque o teste novo é `.py` e move alegações do gate de
  lastro; `CLAUDE.md` e `AGENTS.md` não têm chave própria em `change_kinds.yaml`, e o
  gate deles é o `test_bootstrap_budget` do AC4.
