---
sdd: 1
feature: SDD_OPERATOR
phase: define
profile: dev
status: ready
hypothesis:
  claim: "Com os coordenadores apontando para as skills sdd-* e o gate conferindo o artefato do funcval, quem usa os agents do SparkForge consegue especificar e mudar o proprio job com o SDD sem escrever na propria arvore."
  prediction: "Um fluxo operator sintetico (case open, change sandbox, funcval compare) produz uma feature que passa no sdd check, e o gate recusa o mesmo fluxo quando o sandbox ou a comparacao faltam."
  experiment: "Teste ponta a ponta que chama as tools reais case_open e change_sandbox num repositorio sintetico e roda sdd check sobre a feature operator."
acceptance:
  - id: AC1
    statement: "Uma feature operator montada a partir de case_open e change_sandbox reais passa no sdd check."
    verified_by: {kind: test, ref: "tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta"}
  - id: AC2
    statement: "verified_by kind funcval que aponta para arquivo sem nenhum funcval.check_delta e recusado como funcval_not_comparison."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_funcval_not_comparison"}
  - id: AC3
    statement: "Comparacao com funcval.unresolved sai em unresolved como funcval_blind_spot, nomeando os checks."
    verified_by: {kind: test, ref: "tests/test_sdd.py::test_funcval_blind_spot"}
  - id: AC4
    statement: "Os coordenadores que recomendam mudanca de job declaram as skills sdd-define e sdd-build e dizem quando abrir a spec."
    verified_by: {kind: test, ref: "tests/test_sdd_operator.py::test_coordenadores_apontam_o_sdd"}
success:
  - id: SC1
    metric: "Codigos de recusa e lacuna que o fluxo operator exercita no teste ponta a ponta"
    source: "tests/test_sdd_operator.py"
out_of_scope:
  - "Julgar se a divergencia do funcval passa do limiar: isso e das regras SF-FVAL no judge (regra 11), nao do gate de spec."
  - "Aplicar a mudanca na arvore do operador: o build operator termina em change propose."
unknowns: []
change_kinds: [agent_or_skill]
---

# SDD_OPERATOR — o SDD para quem muda o proprio job

## Problema

O nucleo ja recusa feature operator sem case e sem sandbox, mas so confere que
os diretorios existem. Duas lacunas:

1. `verified_by.kind: funcval` so confere que o arquivo existe; um JSON qualquer
   passa.
2. Nenhum coordenador leva o operador ate o SDD: quem pede "mude meu job" cai
   direto em `tune` ou `change plan`, sem spec.

## O que muda

- O gate le o arquivo do funcval e exige ao menos um `funcval.check_delta`;
  `funcval.unresolved` vira lacuna com nome. O veredito da divergencia continua
  com `judge` (SF-FVAL-*).
- Os coordenadores `spark-performance-architect`,
  `glue-incremental-performance-architect`, `glue-infra-reviewer` e
  `pyspark-code-reviewer` declaram `sdd-define` e `sdd-build` e dizem quando a
  mudanca pede spec.
- Um teste ponta a ponta prova o fluxo com as tools reais.
