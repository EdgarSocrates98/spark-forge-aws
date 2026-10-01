---
sdd: 1
feature: SDD_EVAL
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Um agente que recebe o repositorio responde perguntas sobre o estado de specs usando sdd_check e sdd_status, e nao lendo o YAML no olho."
  prediction: "Numa suite de seis perguntas sobre fixtures sinteticas, o baseline registra k/N de acerto e de uso das tools exigidas; a comparacao com superpowers e AgentSpec sai recusada por nome."
  experiment: "Suite evals/agentic/sdd com gabarito recomputado pelo gate, runner com a suite como constante, e um baseline Haiku gravado."
acceptance:
  - id: AC1
    statement: "Cada resposta do gabarito da suite sdd e recomputada rodando o gate sobre a fixture citada, e o teste falha se divergir."
    verified_by: {kind: test, ref: "tests/test_sdd_eval_suite.py::test_gabarito_recomputado_pelo_gate"}
  - id: AC2
    statement: "A suite carrega pelo leitor de sparkforge.evals e exige sdd_check ou sdd_status em toda pergunta."
    verified_by: {kind: test, ref: "tests/test_sdd_eval_suite.py::test_suite_carrega_e_exige_as_tools"}
  - id: AC3
    statement: "As fixtures sdd ficam fora da conversao de quebra de linha do git, para o hash do upstream nao mudar no checkout Windows."
    verified_by: {kind: test, ref: "tests/test_sdd_eval_suite.py::test_fixtures_sem_conversao_de_quebra"}
  - id: AC4
    statement: "O runner de avaliacao aceita a suite sdd como constante nova, sem caminho vindo do argv."
    verified_by: {kind: test, ref: "tests/test_sdd_eval_suite.py::test_runner_conhece_a_suite_sdd"}
  - id: AC5
    statement: "Um baseline da suite sdd e gravado com k/N e as transicoes, sem afirmar ganho sobre os plugins."
    verified_by: {kind: command, ref: "python scripts/run_agentic_eval.py --suite sdd --model haiku --runs 1"}
success:
  - id: SC1
    metric: "Acerto k/N e uso das tools exigidas no baseline Haiku da suite sdd"
    source: "scorecard.json do baseline em evals/agentic/sdd/baselines/"
out_of_scope:
  - "Comparar o SDD proprio com superpowers ou AgentSpec: exige o mesmo caso bem posto rodando nos dois bracos, e os plugins nao produzem artefato que o gate leia (regra 30)."
  - "Medir custo em dolar sem cost_basis (regra 25)."
unknowns:
  - id: U1
    blocks: [AC5]
    unlock: "claude CLI autenticado na maquina do operador; sem ele o baseline fica pendente e o README da suite diz isso."
change_kinds: [fixture_corpus]
---

# SDD_EVAL — medir o uso, recusar a comparacao

## O que se mede

Se o agente, diante de perguntas sobre specs ("qual recusa esta feature
tem?", "em que fase esta a feature X?"), chama `sdd_check`/`sdd_status` e
responde o valor exato. O gabarito nao e escrito a mao: o teste o recomputa
rodando o gate sobre a fixture.

## O que se recusa

"O SDD proprio e melhor que superpowers e AgentSpec" nao e medivel aqui: os
plugins nao geram artefato que o gate leia, e um braco sem gate nao e o mesmo
caso. A recusa vai escrita no README da suite, com o que a destravaria.
