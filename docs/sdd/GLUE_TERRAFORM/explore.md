---
sdd: 1
feature: GLUE_TERRAFORM
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Modulo auxiliar proprio, sparkforge/facts/glue_terraform.py, SEM EMITTED_KINDS, com as duas funcoes que hoje estao duplicadas entre stepfunctions.py e airflow_dag.py: o indice de nome literal de job Glue vindo de tf.attribute, e a leitura de max_retries com as tres origens (literal, absent, not_literal). Os dois extratores passam a importar."
    tradeoffs:
      - "e o que os docstrings das DUAS copias ja pedem por escrito: o de airflow_dag.py diz 'o lugar certo da funcao e um modulo proprio'"
      - "a contagem de extratores nao se move: scripts/check_status_numbers.py::_extratores conta so modulo de facts/ que tem EMITTED_KINDS, e a docstring dele nomeia o precedente (runtime_matrix, pricing)"
      - "impede a divergencia em vez de detecta-la: passa a existir UMA definicao"
      - "custo: um arquivo a mais em facts/, e o design precisa conferir uma a uma as listas manuais de teste que varrem aquele diretorio"
  - id: B
    summary: "Deixar as duas copias e acrescentar um teste que trava a igualdade dos corpos."
    tradeoffs:
      - "risco zero de mudar comportamento"
      - "DETECTA divergencia em vez de impedi-la, e so depois de ela existir"
      - "fragil: os docstrings das duas copias ja diferem hoje, entao o teste teria de comparar so o corpo -- e um teste que normaliza texto de codigo envelhece mal"
  - id: C
    summary: "Mover as duas para terraform.py, onde o fact tf.attribute nasce."
    tradeoffs:
      - "nenhum arquivo novo, e tematicamente o leitor fica ao lado do produtor"
      - "poe um leitor de FACTS dentro de um extrator de ARTEFATO, que e outra responsabilidade"
      - "terraform.py ja e grande, e cresceria sem que a mudanca pedisse"
chosen: A
---

# GLUE_TERRAFORM — exploração

## Origem

A feature AIRFLOW_DAG (#91) duplicou de propósito duas funções que já existiam em
`stepfunctions.py`, e registrou a dívida no próprio código e no `ship.md`. As revisões
finais de #91, #92 e #93 conferiram, uma a uma, que as cópias não divergiram. O operador
pediu a consolidação em 2026-09-20 e escolheu decompor em duas features; esta é a segunda,
depois da `SFN_TENTATIVA`.

## Perfil

`dev`. A mudança é no próprio SparkForge.

## O que foi medido nesta árvore (2026-09-20, `main` em `e4141869`)

- `sparkforge/facts/stepfunctions.py`, linhas 551 e 569: `_glue_jobs_por_nome` e
  `_max_retries`.
- `sparkforge/facts/airflow_dag.py`, linhas 931 e 955: as mesmas duas.
- **Os corpos são idênticos; só os docstrings diferem.** O de `airflow_dag.py` diz:
  *"GEMEA de `stepfunctions._glue_jobs_por_nome`, e duplicada de proposito NESTE
  incremento: um leitor de DAG nao deveria importar um leitor de ASL para saber ler
  Terraform. O lugar certo da funcao e um modulo proprio (...) e ele nao esta no manifesto
  deste desenho."*
- Chamadores: `stepfunctions.py` nas linhas 619 e 661, `airflow_dag.py` nas 1000 e 1040 —
  dois cada, dentro das derivações `build_sfn_glue_link` e `build_af_glue_link`.
- Não há terceira cópia: `aws_glue_job.` aparece em `sparkforge/` só nesses dois módulos
  (mais uma menção em `adapters/tools.py`, que é texto de descrição de tool).
- **A contagem de extratores não se move.**
  `scripts/check_status_numbers.py::_extratores` devolve
  `[m for m in _modulos_de_fact() if getattr(m, "EMITTED_KINDS", None)]`, e a docstring
  dele diz: *"Modulo de `facts/` que EMITE kind. Os que so carregam conhecimento
  (`runtime_matrix`, `pricing`, ...) nao sao extrator"*.

## Perguntas feitas

1. Qual abordagem? Resposta (2026-09-20): A.

## Abordagens

A é a recomendada porque é a única que **impede** a divergência em vez de detectá-la, e
porque o precedente de módulo auxiliar dentro de `facts/` já existe e está escrito na
docstring do gate que poderia reclamar. B deixa duas definições vivas e aposta num teste
que compara texto de código. C resolve a duplicação e cria outra confusão, pondo um
consumidor de facts dentro de um extrator de artefato.

## Escolha

A, escolhida pelo operador.
