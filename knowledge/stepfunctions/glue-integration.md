# Step Functions disparando job Glue: integração, retry e tipo de workflow

> **Lido em 2026-09-19.** Nove páginas oficiais da AWS: cinco do guia do AWS Step
> Functions, duas da API do AWS Step Functions e duas da API do AWS Glue. Quem consome: o extrator
> `sparkforge/facts/stepfunctions.py` (os dois defaults publicados moram lá, com a URL
> ao lado) e as quatro regras de `rules/catalog/stepfunctions.yaml`. Frase entre aspas é
> citação literal; o resto é leitura nossa, e diz de qual frase veio.

## 1. O recurso e os padrões de integração

O Glue tem o padrão *Run a Job* (`.sync`), com o recurso
`arn:aws:states:::glue:startJobRun.sync` (connect-glue). A mesma página publica a
política IAM gerada para o `.sync` — `glue:StartJobRun`, `glue:GetJobRun`,
`glue:GetJobRuns` e `glue:BatchStopJobRun` — e, para Request Response e callback, só
`glue:StartJobRun`. A única API otimizada listada é `StartJobRun`: `getJobRun` só
entra pela integração AWS SDK (`arn:aws:states:::aws-sdk:glue:getJobRun`).

| padrão | `Resource` | o que a documentação diz |
|---|---|---|
| Request Response | `arn:aws:states:::glue:startJobRun` | "Step Functions will not wait for a job to complete." |
| Run a Job (`.sync`) | `arn:aws:states:::glue:startJobRun.sync` | "If a task using this (`.sync`) service integration pattern is aborted, and Step Functions is unable to cancel the task, you might incur additional charges from the integrated service." |
| callback (`.waitForTaskToken`) | — | o extrator registra o padrão; nenhuma regra o julga para o Glue |

Sobre o tipo de workflow, a mesma página (connect-to-resource): "Express Workflows only
support Request Response integrations." E choosing-workflow-type: "Express Workflows do
not support Job-run (`.sync`) or Callback (`.waitForTaskToken`) service integration
patterns." A cobrança também difere (choosing-workflow-type): STANDARD "billed according
to the number of state transitions processed", EXPRESS "billed by number of executions,
total duration of execution, and memory consumed during execution".

Leitura nossa, e não frase: a espera montada à mão — `startJobRun` sem `.sync`, `Wait`,
`aws-sdk:glue:getJobRun`, `Choice` — é espera deliberada. Por isso a SF-SFN-001 não
dispara quando a mesma definição tem um Task `glue:getJobRun`
(`polled_by_get_job_run`). O `End` de um ramo de `Parallel` ou `Map` encerra o ramo, e o
`Next` do contêiner roda depois dele: o extrator propaga esse `Next`
(`enclosing_has_next`, `effective_has_next`).

## 2. Retry, erros reservados e os defaults

- `MaxAttempts` "(`3` by default)" — concepts-error-handling. O extrator grava o efetivo
  (`max_attempts`) e a marca de omitido (`max_attempts_defaulted`).
- `States.TaskFailed` "matches any known error name except for `States.Timeout`", e
  `States.ALL` não pega `States.Runtime` — concepts-error-handling.
- `TimeoutSeconds`: "The default value is 99,999,999", e `TimeoutSeconds` e
  `TimeoutSecondsPath` não coexistem no mesmo estado — state-task.

Leitura nossa, a partir das duas primeiras: a falha de um JobRun sob `.sync` chega ao
estado como erro, e o primeiro retrier, na ordem declarada, cujo `ErrorEquals` contém
`States.TaskFailed` ou `States.ALL` a casa. Cada tentativa desse retrier chama
`StartJobRun` de novo — um JobRun novo, não uma retomada.

## 3. O lado do Glue

- `MaxRetries`: "The maximum number of times to retry this job after a JobRun fails."
  (aws-glue-api-jobs-job).
- `Timeout`: "defaulted to 2,880 minutes for Glue version 4.0 and earlier, or 480
  minutes for Glue version 5.0 and later" (aws-glue-api-jobs-job).
- Os parâmetros de `StartJobRun` não incluem `MaxRetries` (aws-glue-api-jobs-runs).
  Leitura nossa, a partir disso: o Step Functions não o sobrescreve.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-SFN-001 | Request Response com estado seguinte efetivo e sem `getJobRun` na definição: o estado seguinte roda com o job em execução | que o job vai falhar |
| SF-SFN-002 | retrier efetivo sobre a falha do job `.sync`: o Task é agendado até 1 + `MaxAttempts` vezes, cada vez um `StartJobRun` novo; P1 quando o número é o default | que retry é errado |
| SF-SFN-003 | `.sync` sob `type: EXPRESS` declarado | nada quando o tipo é `undeclared`; nem se a API recusaria publicar (lacuna 4) |
| SF-SFN-004 | as duas camadas de retry existem sobre o mesmo job `.sync` | quantas vezes o job roda numa falha (lacuna 1) |

O vínculo da SF-SFN-004 é por `JobName` literal igual ao `name` do `aws_glue_job`, feito
em `fuse`, e só para Task `.sync`: em Request Response o retrier cobre a chamada
`StartJobRun`, não a falha do job. `JobName.$` e expressão JSONata
(`job_name_dynamic`), `JobName` ausente ou não-texto (`job_name_absent`) e job ausente do
Terraform saem em `sfn.unresolved` com a razão, nunca como vínculo.

## 5. Lacunas nomeadas

1. **Composição dos retries.** Nenhuma das duas documentações descreve como o retry do
   Step Functions compõe com o `MaxRetries` do Glue. O `.sync` acompanha o `JobRunId`
   que o `StartJobRun` devolveu, e o retry do Glue é outro JobRun. O que destrava
   afirmar a contagem de tentativas: um histórico de execução real com falha
   (`get-execution-history`) junto dos JobRuns do mesmo intervalo, ou documentação
   oficial que a descreva.
2. **JobRun quando o Task expira.** A leitura registrada em
   `docs/sdd/STEP_FUNCTIONS/define.md` não achou o que acontece com o JobRun quando o
   estado expira por `States.Timeout`: a descrição do abort do `.sync` não inclui
   timeout. Por isso não há regra de `TimeoutSeconds` contra o `Timeout` do job.
3. **ASL real não observado.** O corpus `fixtures/stepfunctions/` é sintético, montado a
   partir dos exemplos oficiais. Um `.asl.json` ou `describe-state-machine` real do
   operador, lido na conversa e nunca commitado, é o que o testaria contra produção.
4. **A API recusa EXPRESS com `.sync`?** Procurado em 2026-09-19 em
   `CreateStateMachine` (o erro `InvalidDefinition` é só "The provided Amazon States
   Language definition is not valid."), em `ValidateStateMachineDefinition` (que recebe
   `type`, mas não lista diagnóstico para o padrão de integração) e em
   choosing-workflow-type. Nenhuma frase diz se criar ou atualizar uma EXPRESS com
   `.sync` é recusado. Se for, a combinação que a SF-SFN-003 julga só aparece em
   definição não publicada (um `.asl.json` revisado antes do deploy, com o tipo sabido
   por outro meio). O que destrava: `aws stepfunctions validate-state-machine-definition
   --type EXPRESS` sobre uma definição com `.sync`, ou frase oficial.
5. **Distributed Map com `ProcessorConfig.ExecutionType: EXPRESS` não é lido.** O
   extrator só copia o `type` da state machine para o Task, e não lê o
   `ExecutionType` das execuções filhas de um Map distribuído (leitura nossa, sem frase
   citada aqui: com `EXPRESS`, as filhas são EXPRESS mesmo numa mãe STANDARD). Um
   `.sync` dentro desse Map sai com o `state_machine_type` da mãe, e a SF-SFN-003 não o
   vê.
6. **`sfn.*` sai com `line: 0`.** O extrator lê JSON sem posição de linha, e o
   `subject.symbol` é o caminho do estado. `sparkforge report github` não ancora esses
   achados numa linha do arquivo.

## Fontes

- Guia do AWS Step Functions — integração com o AWS Glue: o padrão `.sync`, o recurso `arn:aws:states:::glue:startJobRun.sync` e a política gerada. https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — padrões de integração com serviços: Request Response, `.sync`, o abort, e o limite dos Express Workflows. https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — tratamento de erro: `MaxAttempts`, `States.TaskFailed`, `States.ALL`. https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — escolha do tipo de workflow: Express sem `.sync`, e os modelos de cobrança. https://docs.aws.amazon.com/step-functions/latest/dg/choosing-workflow-type.html (retrieved 2026-09-19)
- API do AWS Step Functions — CreateStateMachine: o parâmetro `type` e o erro `InvalidDefinition`. https://docs.aws.amazon.com/step-functions/latest/apireference/API_CreateStateMachine.html (retrieved 2026-09-19)
- API do AWS Step Functions — ValidateStateMachineDefinition: validação com `type`, sem diagnóstico de padrão de integração. https://docs.aws.amazon.com/step-functions/latest/apireference/API_ValidateStateMachineDefinition.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — estado Task: `TimeoutSeconds` e `TimeoutSecondsPath`. https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html (retrieved 2026-09-19)
- API do AWS Glue — Jobs: `MaxRetries` e `Timeout`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html (retrieved 2026-09-19)
- API do AWS Glue — Job runs: os parâmetros de `StartJobRun`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html (retrieved 2026-09-19)
