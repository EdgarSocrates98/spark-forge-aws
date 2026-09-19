# Step Functions disparando job Glue: integração, retry e tipo de workflow

> **Lido em 2026-09-19.** Seis páginas oficiais da AWS: quatro do guia do AWS Step
> Functions e duas da API do AWS Glue. Quem consome: o extrator
> `sparkforge/facts/stepfunctions.py` (os dois defaults publicados moram lá, com a URL
> ao lado) e as quatro regras de `rules/catalog/stepfunctions.yaml`. Frase entre aspas é
> citação literal; o resto é leitura nossa, e diz de qual frase veio.

## 1. O recurso e os padrões de integração

O Glue tem o padrão *Run a Job* (`.sync`), com o recurso
`arn:aws:states:::glue:startJobRun.sync` (connect-glue). A mesma página publica a
política IAM gerada para o `.sync`, e ela inclui `glue:BatchStopJobRun`.

| padrão | `Resource` | o que a documentação diz |
|---|---|---|
| Request Response | `arn:aws:states:::glue:startJobRun` | "Step Functions will not wait for a job to complete." |
| Run a Job (`.sync`) | `arn:aws:states:::glue:startJobRun.sync` | "If a task using this (`.sync`) service integration pattern is aborted, and Step Functions is unable to cancel the task, you might incur additional charges from the integrated service." |
| callback (`.waitForTaskToken`) | — | o extrator registra o padrão; nenhuma regra o julga para o Glue |

Sobre o tipo de workflow, a mesma página (connect-to-resource): "Express Workflows only
support Request Response integrations."

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
- Os parâmetros de `StartJobRun` não incluem `MaxRetries` (aws-glue-api-jobs-runs): o
  Step Functions não o sobrescreve.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-SFN-001 | Request Response com `Next`: o estado seguinte roda com o job em execução | que o job vai falhar |
| SF-SFN-002 | retrier efetivo sobre a falha do job `.sync`; P1 quando o número é o default | que retry é errado — só que cada tentativa é um JobRun inteiro |
| SF-SFN-003 | `.sync` sob `type: EXPRESS` declarado | nada quando o tipo é `undeclared` |
| SF-SFN-004 | as duas camadas de retry existem sobre o mesmo job | quantas vezes o job roda numa falha (lacuna 1) |

O vínculo da SF-SFN-004 é por `JobName` literal igual ao `name` do `aws_glue_job`, feito
em `fuse`. `JobName.$`, expressão JSONata e job ausente do Terraform saem em
`sfn.unresolved` com a razão, nunca como vínculo.

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

## Fontes

- Guia do AWS Step Functions — integração com o AWS Glue: o padrão `.sync`, o recurso `arn:aws:states:::glue:startJobRun.sync` e a política gerada. https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — padrões de integração com serviços: Request Response, `.sync`, o abort, e o limite dos Express Workflows. https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — tratamento de erro: `MaxAttempts`, `States.TaskFailed`, `States.ALL`. https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — estado Task: `TimeoutSeconds` e `TimeoutSecondsPath`. https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html (retrieved 2026-09-19)
- API do AWS Glue — Jobs: `MaxRetries` e `Timeout`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html (retrieved 2026-09-19)
- API do AWS Glue — Job runs: os parâmetros de `StartJobRun`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html (retrieved 2026-09-19)
