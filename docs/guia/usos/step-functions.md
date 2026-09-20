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
# 1. Salvar o historico (o operador roda isto na conta; o SparkForge nao chama a API).
#    SEM limitar a paginacao: a CLI junta as paginas sozinha, e a saida sai inteira.
aws stepfunctions get-execution-history \
  --execution-arn <arn> --include-execution-data \
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

### O que fazer quando o histórico passa de uma página

**O jeito mais barato é não deixar ele virar página.** A CLI já junta as páginas
sozinha: o `help` de `aws stepfunctions get-execution-history` (medido na aws-cli
2.36.38) diz que a operação "is a paginated operation. Multiple API calls may be issued
in order to retrieve the entire data set of results. You can disable pagination by
providing the `--no-paginate` argument." Deixada em paz, ela emite quantas chamadas
forem precisas e a saída salva traz o histórico inteiro, sem `nextToken`. Quem **limita**
a coleta é o operador — `--max-items`, `--no-paginate`, ou um salvamento que não veio da
CLI (SDK, console). É daí que sai uma página, e é por isso que o `truncated` existe.

Já tendo as páginas separadas, **junte-as num arquivo só**. O SparkForge lê **um arquivo
como uma execução**, e salvar cada página como um `.json` no mesmo diretório **não** é o
mesmo: o `analyze` daria um `sfn.execution` por página e, no `fuse`, as tentativas de uma
mesma execução cairiam em grupos diferentes (o agrupamento é por arquivo), o que
subestima o retry observado.

```bash
# Juntar as paginas num arquivo so, SEM nextToken -- e esse que o analyze le
python - /tmp/sf/pag-*.json <<'PY' > /tmp/sf/execucao.json
import json, sys
eventos = [e for p in sys.argv[1:] for e in json.load(open(p))["events"]]
json.dump({"events": eventos}, sys.stdout)
PY
```

A ordem em que as páginas entram não importa: o extrator ordena pelo `id` do evento, que
a API numera sequencialmente. E se a colagem repetir um evento, ele não passa calado —
sai `sfn.unresolved` com `event_id_duplicated`, a primeira ocorrência vence, e a contagem
de tentativas continua a que o arquivo sustenta.

Enquanto o arquivo for uma página só, o `truncated` fica lá e é assim que deve ser: ele é
a diferença entre "o histórico é este" e "esta é a parte que eu salvei".

| kind | um por | o que diz |
|---|---|---|
| `sfn.execution` | arquivo | `status` pelo evento terminal (`unresolved` quando ele não está no arquivo), duração, contagem dos eventos **lidos** (`read_event_count` — o que não é objeto, o de tipo desconhecido e o de `id` repetido ficam de fora, cada um com a sua recusa), `truncated` |
| `sfn.attempt` | tentativa de Task (`<estado>#<ordem>`) | nome do estado, ordem, padrão de integração, resultado, duração, `error`, `cause`, e o prazo declarado do Task |
| `sfn.job_run` | `JobRunId` lido do `output` do `TaskSubmitted` | o id, o `JobName` quando vem junto, e de qual chave ele foi lido |
| `sfn.retry_observado` | **execução e estado** (o par arquivo + nome), só em `fuse` com o ASL | tentativas observadas contra o teto declarado |
| `sfn.unresolved` | o que não deu para ler ou parear | `truncated`, `execution_terminal_absent`, cadeia quebrada, `event_type_unknown`, `event_id_duplicated`, `event_not_an_object`, `state_unresolved`, `attempt_unanchored`, `execution_data_absent`, `execution_redriven`, `job_run_id_unrecognized`; e na derivação, `asl_absent`, `state_name_absent_in_asl`, `state_name_ambiguous`, `declared_ceiling_unreadable`, `redrive_in_execution` e `glue_attempt_absent` |
| `sfn.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

**O `sfn.retry_observado` é por execução E por estado, e isso importa com mais de um
histórico no case.** Retry é orçamento de **uma** execução: somar as tentativas de dois
runs do mesmo estado acusaria de estourar o teto dois runs que cabem nele. O lado medido
é agrupado pelo par (arquivo do histórico, nome do estado); o lado declarado, o
`sfn.task` do ASL, continua pareado só pelo nome, porque o ASL é outro artefato e nada
nele diz de que execução ele é — e um mesmo `sfn.task` pareia legitimamente com várias
execuções.

**Duas recusas que você pode ver e que não são erro seu.** `event_id_duplicated` sai
quando o arquivo repete o `id` de um evento — página colada duas vezes, ou histórico
montado à mão: a primeira ocorrência vence, a repetição é descartada e a ordem das
tentativas continua sendo a que o arquivo sustenta. `glue_attempt_absent` sai quando um
arquivo tem tentativa medida e **nenhuma** delas é `glue:startJobRun` — a integração
`aws-sdk`, por exemplo, publica `resourceType: aws-sdk:glue`, e o confronto de retry não
a alcança. A recusa é por arquivo e lista o `<serviço>:<api>` de cada tentativa dele, que
é por onde o próximo passo aparece. Ela não sai para o arquivo que **tem**
`glue:startJobRun`: esse tem confronto.

**Redrive: a contagem para de ser comparável, e a recusa diz isso.** Quando o histórico
traz `ExecutionRedriven`, a execução foi **retomada**: o Task é reagendado dentro da
MESMA execução, e nada no arquivo separa as tentativas de antes das de depois. As
tentativas continuam medidas e publicadas; o que sai é o **confronto** — por execução e
por estado sai `sfn.unresolved: redrive_in_execution` no lugar do `sfn.retry_observado`,
e a `SF-SFNX-001` fica sem âncora naquele arquivo. A recusa é por **arquivo**: uma
execução sem redrive, salva ao lado no mesmo case, continua tendo confronto. Medir o
redrive em vez de recusá-lo exigiria saber quantas tentativas caíram antes e quantas
depois, e a forma do evento não foi lida (lacuna 9 de
`knowledge/stepfunctions/execution-history.md`).

### As três regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-SFNX-001` | os agendamentos do Task passam do teto `1 + MaxAttempts` que o ASL declara (exige os dois artefatos no `fuse`) | P2 |
| `SF-SFNX-002` | a tentativa `.sync` terminou em `TaskTimedOut` **depois de ter sido submetida** (`submitted: true`): o desfecho do JobRun que ela acompanhava não foi observado | P1 |
| `SF-SFNX-003` | a execução terminou em `Aborted` ou `TimedOut` com o Task `.sync` agendado e sem evento terminal próprio | P1 |

A `SF-SFNX-002` **só fala quando a submissão aconteceu**, e a condição não é
decorativa: um `.sync` que expira ANTES do `TaskSubmitted` — prazo que não cobriu nem o
`StartJobRun` — não deixou `JobRunId` nenhum, e ali não há job órfão a investigar, há um
prazo curto demais. Sem a condição, o achado mandaria você rodar
`aws glue get-job-run` sobre um identificador que o histórico não registra.

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
