# Step Functions: como a state machine dispara o job Glue

O **AWS Step Functions** orquestra jobs Glue por uma *state machine*, escrita em Amazon
States Language (ASL). Este manual mostra como o SparkForge lê essa definição e confere
três coisas sobre o job Glue que ela dispara: se o fluxo **espera** o job terminar, se
um **retry** reagenda o Task (até 1 + `MaxAttempts` vezes, cada vez um `StartJobRun`
novo), e se o **tipo** do workflow suporta o padrão que a definição pede. Com o Terraform do job ao lado, ele mostra também quando o
retry existe nas **duas camadas** — na state machine e no próprio job.

O SparkForge **não** chama a API do Step Functions e não lê histórico de execução. Ele
lê a definição. Todos os exemplos usam arquivos sintéticos de `fixtures/stepfunctions/`.

## Receita rápida

```bash
mkdir -p /tmp/sf

# 1. Extrair os facts da definicao (.asl.json, saida de describe-state-machine, ou diretorio)
sparkforge analyze step-functions \
  --path fixtures/stepfunctions/glue_sem_sync/input --out /tmp/sf/facts_sfn.json

# 2. Julgar: SF-SFN-001 a 003 leem so o ASL
sparkforge judge --facts /tmp/sf/facts_sfn.json

# 3. Com o Terraform do job: extrair os dois lados, fundir e julgar
sparkforge analyze step-functions \
  --path fixtures/stepfunctions/retry_duas_camadas/input --out /tmp/sf/sfn.json
sparkforge analyze terraform \
  --path fixtures/stepfunctions/retry_duas_camadas/input --out /tmp/sf/tf.json
sparkforge fuse --facts /tmp/sf/sfn.json --facts /tmp/sf/tf.json --out /tmp/sf/fundidos.json
sparkforge judge --facts /tmp/sf/fundidos.json
```

A definição vem do repositório (o `.asl.json` que o IaC publica) ou da conta: a saída de
`aws stepfunctions describe-state-machine --state-machine-arn <arn>`, salva em arquivo,
é lida do mesmo jeito — e é a única das duas que traz o `type` (STANDARD ou EXPRESS).

## O que sai

| kind | um por | o que diz |
|---|---|---|
| `sfn.state_machine` | definição | `type` (`STANDARD`, `EXPRESS` ou `undeclared`), linguagem de consulta, origem |
| `sfn.task` | estado `Task`, inclusive em `Parallel` e `Map` | serviço, API, padrão (`request_response`, `sync`, `callback`), `JobName` literal ou dinâmico, retriers com o `MaxAttempts` efetivo, `Catch`, `TimeoutSeconds` |
| `sfn.glue_job_link` | Task ligado a um `aws_glue_job` (só em `fuse`) | o retry efetivo do Step Functions e o `max_retries` do job |
| `sfn.unresolved` | o que não deu para ler ou ligar | a razão: JSON inválido ou fundo demais, arquivo acima do teto, tipo desconhecido, `MaxAttempts` ilegível, recurso dinâmico, `JobName` dinâmico ou ausente, job ausente do Terraform |
| `sfn.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

Um `.asl.json` não traz o tipo do workflow: sem a saída de `describe-state-machine`, ele
sai `undeclared`, nunca `STANDARD` por suposição.

## As quatro regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-SFN-001` | `glue:startJobRun` sem `.sync` com estado seguinte — o `Next` do estado, ou o do `Parallel`/`Map` quando o Task é `End` de ramo — e sem `glue:getJobRun` na mesma definição: o próximo estado roda com o job em execução | P2 |
| `SF-SFN-002` | Task `.sync` com retrier em `States.ALL` ou `States.TaskFailed` e `MaxAttempts` efetivo maior que zero: o Task é agendado até 1 + `MaxAttempts` vezes, cada vez um `StartJobRun` novo | P1 com `MaxAttempts` omitido (3 por default), P2 declarado |
| `SF-SFN-003` | `.sync` numa state machine com `type: EXPRESS` declarado | P1 |
| `SF-SFN-004` | o Task `.sync` ligado ao job tem retry efetivo e o job tem `max_retries` maior que zero | P2 |

A `SF-SFN-004` afirma só que as duas camadas existem. **Quantas vezes o job roda numa
falha não é documentado** — o retry do Glue é outro JobRun, e o `.sync` acompanha o
primeiro. Medir exige um histórico de execução real com falha e os JobRuns do mesmo
intervalo (`sparkforge collect glue-job-runs`).

## O que ele não faz

- Não lê histórico de execução (`get-execution-history`) nem coleta da conta: o
  operador salva a saída do `describe-state-machine` em arquivo.
- Não lê a definição dentro de `aws_sfn_state_machine` do Terraform (`templatefile`,
  `jsonencode`): só o ASL em arquivo ou a saída do `describe-state-machine`.
- Não julga outros serviços (Lambda, Batch, EMR): o extrator os registra, e nenhuma regra
  os julga.
- Não compara o `TimeoutSeconds` do Task com o `Timeout` do job: o que acontece com o
  JobRun quando o estado expira não é documentado.

## Referência

- As frases citadas e as lacunas: [`knowledge/stepfunctions/glue-integration.md`](../../../knowledge/stepfunctions/glue-integration.md).
- As regras: [`rules/catalog/stepfunctions.yaml`](../../../rules/catalog/stepfunctions.yaml).
- O corpus: [`fixtures/stepfunctions/`](../../../fixtures/stepfunctions/).
