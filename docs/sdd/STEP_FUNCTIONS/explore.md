---
sdd: 1
feature: STEP_FUNCTIONS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Extrator novo de ASL (sparkforge/facts/stepfunctions.py) que le o .asl.json do repositorio ou a saida de describe-state-machine e emite um fact por Task (servico, API, padrao de integracao request-response/.sync/.waitForTaskToken, JobName literal ou dinamico, Retry efetivo com os defaults da documentacao, Catch, TimeoutSeconds) e sfn.unresolved nomeado para o que nao le; verbo sparkforge analyze step-functions e tool MCP; area SF-SFN com regras que julgam so o ASL; coordenador existente (glue-infra-reviewer) declara a area e ganha rota por findings_area."
    tradeoffs:
      - "passa pelas tres portas do criterio de dominio: extrator, regra que julga, coordenador com rota real"
      - "regras so com o ASL: Glue sem .sync seguido de estado dependente; retry implicito (MaxAttempts default 3) sobre job batch inteiro; .sync sob workflow EXPRESS quando o tipo e conhecido"
      - "nao cruza com a definicao do job Glue (MaxRetries, Timeout): o retry multiplicado fica para o incremento seguinte"
  - id: B
    summary: "A mais uma regra que cruza o ASL com a definicao do job Glue (tf.attribute de aws_glue_job ou o collect glue-job) pelo JobName literal: Retry do Step Functions multiplicado pelo MaxRetries do Glue."
    tradeoffs:
      - "a regra de maior custo evitado: tentativas = (1 + MaxAttempts) x (1 + MaxRetries)"
      - "JobName dinamico (JobName.$, JSONata) nao casa e vira unresolved; o join por nome precisa de fixture pareada"
      - "o dobro do tamanho de A num incremento so"
  - id: C
    summary: "So o documento de conhecimento (knowledge/stepfunctions/glue-integration.md, com as frases citadas) e o extrator, sem area de regra."
    tradeoffs:
      - "o mais barato"
      - "facts sem regra nao julgam nada; o operador ganha leitura, nao achado"
chosen: B
---

# STEP_FUNCTIONS — exploração

## Origem

Primeiro domínio novo depois do critério de domínio (#89): entra por artefato coletável.
Escolhas do operador em 2026-09-19: domínio Step Functions; artefato do primeiro
incremento, a definição ASL.

## Perfil

`dev`.

## O que o repositório tem hoje

Nada de Step Functions em `sparkforge/`: as cinco ocorrências de `StartJobRun` são do EMR
Serverless. O precedente de forma é o Control-M: `sparkforge/facts/controlm_jobs.py` lê o
`Jobs-as-Code`, JSON versionado, como código-fonte.

## Fontes lidas (2026-09-19)

- `https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html`: Glue tem o
  padrão *Run a Job (.sync)*; o recurso é `arn:aws:states:::glue:startJobRun.sync`; a
  política gerada para `.sync` inclui `glue:BatchStopJobRun`.
- `https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html`:
  - Request Response: "Step Functions will not wait for a job to complete."
  - `.sync`: "If a task using this (`.sync`) service integration pattern is aborted,
    and Step Functions is unable to cancel the task, you might incur additional charges
    from the integrated service."
  - "Express Workflows only support Request Response integrations."
- `https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html`:
  - `MaxAttempts` "(`3` by default)";
  - `States.TaskFailed` "matches any known error name except for `States.Timeout`";
  - `States.ALL` não pega `States.Runtime`.
- `https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html`:
  - `TimeoutSeconds` "The default value is 99,999,999";
  - `TimeoutSeconds` e `TimeoutSecondsPath` não coexistem.

## Perguntas feitas

1. Qual domínio? Step Functions.
2. Qual artefato? A definição ASL.
3. Qual abordagem? Resposta (2026-09-19): B, ASL mais o cruzamento com o job Glue.

## Abordagens

A (recomendada) fecha o domínio pelas três portas com regras que só o ASL sustenta. B
acrescenta o cruzamento com o job Glue, que é a regra de maior valor, e dobra o
tamanho. C não julga nada.

## Fontes do lado do Glue (2026-09-19)

- `https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html`:
  - `MaxRetries`: "The maximum number of times to retry this job after a JobRun fails.";
  - `Timeout`: "defaulted to 2,880 minutes for Glue version 4.0 and earlier, or 480 minutes
    for Glue version 5.0 and later".
- `https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html`: os parâmetros
  de `StartJobRun` não incluem `MaxRetries`. O Step Functions não o sobrescreve.
- Nenhuma das duas documentações descreve como o retry do Step Functions se compõe com o
  `MaxRetries` do Glue. O `.sync` acompanha o `JobRunId` que o `StartJobRun` devolveu, e o
  retry do Glue é outro `JobRun`. A composição é lacuna nomeada, não suposição.
- O lado do Glue já vira fact: `tf.attribute` com `key: max_retries`, lido pela
  `SF-GLUE-004`. O cruzamento pelo `JobName` é predicado entre dois artefatos, e pela
  regra 33 vira fact derivado, no molde de `sparkforge/facts/bridge.py`.

## Escolha

B, escolhida pelo operador: a regra de maior valor do domínio é a das duas camadas de
retry sobre o mesmo job, e ela só existe cruzando os dois artefatos.
