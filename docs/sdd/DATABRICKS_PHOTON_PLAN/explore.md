---
sdd: 1
feature: DATABRICKS_PHOTON_PLAN
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "O extrator de plano reconhece os operadores Photon* e a secao == Photon Explanation == e emite um fact proprio; a recusa das regras de plano passa a disparar por esse fact, alem da declaracao --photon on; o udf_type do ArrowEvalPython deixa de afirmar pandas."
    tradeoffs:
      - "fecha o silencio medido com evidencia do proprio artefato, sem depender de o operador declarar Photon"
      - "nao arrisca julgar operador que o SparkForge nao entende"
      - "regra de plano continua sem julgar plano Photon: recusa com nome, nao achado"
  - id: B
    summary: "A mais o mapeamento dos operadores Photon para os equivalentes do Spark, para as regras de plano julgarem planos Photon."
    tradeoffs:
      - "mais valor: as regras de plano voltariam a dizer algo sobre job Photon"
      - "um plano observado so, e ele ja mostra que o broadcast Photon passa por PhotonShuffleExchangeSink SinglePartition e PhotonShuffleMapStage EXECUTOR_BROADCAST, nao por BroadcastExchange: mapeamento ingenuo criaria achado errado"
      - "exige tabela de equivalencia com fonte, ou varios planos observados"
  - id: C
    summary: "So o generico: todo operador desconhecido vira plan.unresolved nomeado, mais a correcao do udf_type."
    tradeoffs:
      - "o mais barato, e cobre qualquer engine desconhecida"
      - "a recusa de Photon continua dependendo da declaracao do operador"
chosen: A
---

# DATABRICKS_PHOTON_PLAN — exploração

## Origem

Incremento seguinte a DATABRICKS_SPARK (PR #83), empilhado na branch dela. Em
2026-09-18 o operador rodou, numa conta Databricks Free Edition (serverless, Spark
4.2.0), `explain(mode="formatted")` de um groupBy com join e de uma UDF Python comum,
sobre dados sintéticos (`spark.range`). A observação está em
`knowledge/databricks/runtime-matrix.md` §4.

## Perfil

`dev`: a mudança é no próprio SparkForge.

## Medidas lidas antes de propor

- `sparkforge/facts/spark_plan.py` reconhece operador por nome exato
  (`_JOIN_OPERATORS`, `_EXCHANGE_OPERATORS`, `_PYTHON_UDF_OPERATORS`...) e ignora raiz
  fora de `_KNOWN_OPERATOR_ROOTS`.
- `sparkforge analyze plan` sobre o plano Photon observado, rodado fora do
  repositório: emite só `plan.analyzed` e `plan.aqe` — nenhum `plan.join`,
  `plan.exchange` nem `plan.unresolved`.
- Sobre o plano da UDF: `plan.python_udf` com `operator: ArrowEvalPython` e
  `udf_type: "pandas"`, para um `@F.udf` comum. `ArrowEvalPython` está mapeado para
  `pandas` em `_PYTHON_UDF_OPERATORS` já no Spark open source.
- No plano observado, o lado pequeno do broadcast passou por
  `PhotonShuffleExchangeSink` (`SinglePartition`) e `PhotonShuffleMapStage`
  (`EXECUTOR_BROADCAST`), não por um nó de `BroadcastExchange`.

## Perguntas feitas, uma por vez

1. Qual abordagem? Resposta: A.

## Escolha

A. Fecha o silêncio que DATABRICKS_SPARK mediu, com evidência do próprio plano, e
não arrisca achado errado sobre operador que o SparkForge ainda não entende. B fica
registrada para quando houver tabela de equivalência com fonte ou planos observados
em número suficiente; C foi superada por A, que cobre o caso Photon sem abrir
`plan.unresolved` para toda engine.

## Em aberto para o define

- Forma do fact novo (nome do kind, medidas: contagem de operadores Photon, presença
  da seção de explicação, frase da explicação) e onde a recusa o lê: o engine só
  recebe o runtime, então a recusa por fact precisa de um caminho — um fact que
  `_runtime_e_facts` traduz para `photon: on`, ou o engine olhando os facts.
- O que o `udf_type` do `ArrowEvalPython` passa a dizer, e quais regras o leem
  (`sparkforge rules lookup` pelas que exigem `plan.python_udf`).
- Se o plano que vem no event log (`SparkListenerSQLExecutionStart`) também traz
  operadores Photon: não observado (serverless não entrega event log); fica fora ou
  vira lacuna nomeada.
