# Step Functions: como a state machine dispara o job Glue

O **AWS Step Functions** orquestra jobs Glue por uma *state machine*, escrita em Amazon
States Language (ASL). Este manual mostra como o SparkForge lê essa definição e confere
três coisas sobre o job Glue que ela dispara: se o fluxo **espera** o job terminar, se
um **retry** reagenda o Task (até 1 + `MaxAttempts` vezes, cada vez um `StartJobRun`
novo), e se o **tipo** do workflow suporta o padrão que a definição pede. Com o Terraform do job ao lado, ele mostra também quando o
retry existe nas **duas camadas** — na state machine e no próprio job.

O SparkForge **não** chama a API do Step Functions: ele lê **artefato salvo**. São dois,
e a diferença entre eles é a razão desta página ter duas metades — a **definição** diz o
que devia acontecer, e o **histórico de execução** diz o que aconteceu. Todos os exemplos
usam arquivos sintéticos de `fixtures/stepfunctions/` e `fixtures/sfn_history/`.

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

## A outra metade: o histórico de execução

A definição diz quantas vezes o Task **pode** ser reagendado. Só o histórico diz quantas
vezes ele **foi** — e é ele que separa retry declarado de retry observado.

```bash
# 1. Salvar o historico (o operador roda isto na conta; o SparkForge nao chama a API)
aws stepfunctions get-execution-history \
  --execution-arn <arn> --include-execution-data --max-results 1000 \
  > /tmp/sf/execucao.json

# 2. Extrair os facts do historico
sparkforge analyze sfn-history \
  --path fixtures/sfn_history/task_timed_out_sync/input/historico \
  --out /tmp/sf/facts_hist.json

# 3. Julgar: SF-SFNX-002 e 003 leem so o historico
sparkforge judge --facts /tmp/sf/facts_hist.json

# 4. Com a definicao do MESMO state machine: fundir, e o confronto aparece
sparkforge analyze sfn-history \
  --path fixtures/sfn_history/retry_acima_do_declarado/input/historico \
  --out /tmp/sf/hist.json
sparkforge analyze step-functions \
  --path fixtures/sfn_history/retry_acima_do_declarado/input/definicao \
  --out /tmp/sf/asl.json
sparkforge fuse --facts /tmp/sf/hist.json --facts /tmp/sf/asl.json --out /tmp/sf/juntos.json
sparkforge judge --facts /tmp/sf/juntos.json
```

**`--include-execution-data` não é opcional na prática**: sem ele não há `output` no
`TaskSubmitted`, e sem `output` não há `JobRunId`. O SparkForge não inventa um: sai
`sfn.unresolved` com `execution_data_absent`.

**Se a saída tiver `nextToken`, ela é uma página, não o histórico.** O SparkForge lê o
que está lá e marca `truncated`.

**`truncated` e `status` são duas perguntas diferentes.** O `status` da execução sai
`unresolved` quando o evento terminal dela não está **na página salva** — nunca sucesso
por suposição. Truncada com o terminal dentro (a primeira página de um
`--reverse-order`, por exemplo) sai `truncated: true` e `status: failed` ao mesmo tempo;
inteira, de uma execução ainda em voo, sai `truncated: false` e `status: unresolved`.

| kind | um por | o que diz |
|---|---|---|
| `sfn.execution` | arquivo | `status` pelo evento terminal (`unresolved` quando ele não está no arquivo), duração, contagem dos eventos **lidos** (`read_event_count` — o que não é objeto, o de tipo desconhecido e o de `id` repetido ficam de fora, cada um com a sua recusa), `truncated` |
| `sfn.attempt` | tentativa de Task (`<estado>#<ordem>`) | nome do estado, ordem, padrão de integração, resultado, duração, `error`, `cause`, e o prazo declarado do Task |
| `sfn.job_run` | `JobRunId` lido do `output` do `TaskSubmitted` | o id, o `JobName` quando vem junto, e de qual chave ele foi lido |
| `sfn.retry_observado` | estado, só em `fuse` com o ASL | tentativas observadas contra o teto declarado |
| `sfn.unresolved` | o que não deu para ler ou parear | truncamento, cadeia quebrada, tipo de evento desconhecido, `execution_data_absent`, `job_run_id_unrecognized`, ASL ausente ou ambíguo |
| `sfn.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

### As três regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-SFNX-001` | os agendamentos do Task passam do teto `1 + MaxAttempts` que o ASL declara (exige os dois artefatos no `fuse`) | P2 |
| `SF-SFNX-002` | a tentativa `.sync` terminou em `TaskTimedOut`: o desfecho do JobRun que ela acompanhava não foi observado | P1 |
| `SF-SFNX-003` | a execução terminou em `Aborted` ou `TimedOut` com o Task `.sync` agendado e sem evento terminal próprio | P1 |

**Nenhuma delas fala em custo.** Atribuir custo a uma tentativa exigiria o `dpu_seconds`
de um run que ninguém leu. O que o histórico entrega é o `JobRunId` — e é com ele que
`sparkforge finops` responde custo com medida de verdade.

**EXPRESS não passa por aqui**: a API não suporta `get-execution-history` para ela, e o
histórico dela vai para o CloudWatch Logs.

## O que ele não faz

- Não coleta da conta: o operador salva a saída do `describe-state-machine` e a do
  `get-execution-history` em arquivo, e aponta cada verbo para o seu.
- Não lê histórico de state machine EXPRESS: a API não o suporta.
- Não segue as execuções filhas de um Distributed Map (`mapRunArn`).
- Não lê a definição dentro de `aws_sfn_state_machine` do Terraform (`templatefile`,
  `jsonencode`): só o ASL em arquivo ou a saída do `describe-state-machine`.
- Não julga outros serviços (Lambda, Batch, EMR): o extrator os registra, e nenhuma regra
  os julga.
- Não compara o `TimeoutSeconds` do Task com o `Timeout` do job: o que acontece com o
  JobRun quando o estado expira não é documentado.

## Referência

- As frases citadas e as lacunas da definição: [`knowledge/stepfunctions/glue-integration.md`](../../../knowledge/stepfunctions/glue-integration.md).
- As frases citadas e as lacunas do histórico: [`knowledge/stepfunctions/execution-history.md`](../../../knowledge/stepfunctions/execution-history.md).
- As regras: [`rules/catalog/stepfunctions.yaml`](../../../rules/catalog/stepfunctions.yaml).
- As regras do histórico: [`rules/catalog/sfn-history.yaml`](../../../rules/catalog/sfn-history.yaml).
- O corpus: [`fixtures/stepfunctions/`](../../../fixtures/stepfunctions/).
- O corpus do histórico: [`fixtures/sfn_history/`](../../../fixtures/sfn_history/).
