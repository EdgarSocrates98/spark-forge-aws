---
sdd: 1
feature: SFN_HISTORY
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Extrator do JSON salvo de aws stepfunctions get-execution-history: sfn.execution (arn, status derivado dos eventos terminais, duracao), sfn.attempt (um por par TaskScheduled/terminal do mesmo estado, com ordem da tentativa, resultado, duracao e erro), sfn.job_run (JobRunId lido do output do TaskSubmitted do Glue) e sfn.unresolved nomeado; verbo sparkforge analyze sfn-history e tool MCP; area SF-SFNX com regras que confrontam o DECLARADO (sfn.task do ASL) com o MEDIDO (sfn.attempt), derivacao em fuse no molde de bridge.py."
    tradeoffs:
      - "e o unico caminho que destrava a lacuna U1 das duas features anteriores: quantos JobRun distintos uma falha produziu"
      - "confronto declarado x medido e o que o bridge.py ja faz entre codigo e execucao; o molde existe"
      - "exige artefato de execucao real do operador para valer em producao; fixture sintetica so prova o mecanismo"
  - id: B
    summary: "So o historico, sem cruzar com o ASL."
    tradeoffs:
      - "menor"
      - "deixa a lacuna U1 aberta, que e a razao de a feature existir"
  - id: C
    summary: "A mais um verbo collect que chama a API com credencial."
    tradeoffs:
      - "poupa o operador de salvar o JSON"
      - "sai do padrao das duas features anteriores, que leem artefato salvo, e exige credencial no caminho"
chosen: A
---

# SFN_HISTORY — exploração

## Origem

As features STEP_FUNCTIONS (#90) e AIRFLOW_DAG (#91) deixaram a mesma lacuna aberta, U1:
como o retry do orquestrador se compõe com o `MaxRetries` do job Glue. Nenhuma das duas
documentações descreve. O que decide é observação. Pedido do operador em 2026-09-19.

## Perfil

`dev`.

## Fontes lidas (2026-09-19)

`https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html`:

- "Returns the history of the specified execution as a list of events."
- "This API action is not supported by `EXPRESS` state machines."
- `includeExecutionData`: "You can select whether execution data (input or output of a
  history event) is returned. The default is `true`." Sem ele, não há `output` para ler o
  `JobRunId`.
- Paginação: "If `nextToken` is returned, there are more results available"; `maxResults`
  default 100, máximo 1000.
- Os eventos de Task carregam `resource` e `resourceType`:
  `taskScheduledEventDetails` (com `parameters`, `region`, `timeoutInSeconds`),
  `taskStartedEventDetails`, `taskSubmittedEventDetails` (com `output`),
  `taskSucceededEventDetails`, `taskFailedEventDetails` (com `error` e `cause`),
  `taskTimedOutEventDetails`, `taskStartFailedEventDetails` e
  `taskSubmitFailedEventDetails`.
- Estado: `stateEnteredEventDetails` e `stateExitedEventDetails` trazem `name`.
- `executionAbortedEventDetails`, `executionFailedEventDetails`,
  `executionTimedOutEventDetails` e `executionSucceededEventDetails` fecham a execução.
- Cada evento tem `id`, `previousEventId`, `timestamp` e `type`.

## O que o repositório já tem

- `sparkforge/facts/stepfunctions.py` lê o ASL e emite `sfn.task` com o retry **declarado**.
- `sparkforge/facts/bridge.py` é o molde do confronto entre o que o código declara e o que
  a execução mediu, com a regra 13 do `CLAUDE.md` ao lado: nomear o sintoma, nunca atribuir
  custo.
- `sparkforge/facts/event_log.py` é o precedente de ler artefato de execução salvo.

## Perguntas feitas

1. Qual escopo? Resposta (2026-09-19): A, histórico mais o confronto com o ASL.

## Abordagens

A (recomendada) é a única que destrava U1. B deixa a lacuna. C acrescenta credencial ao
caminho, contra o padrão das duas features anteriores.

## Escolha

A, escolhida pelo operador.
