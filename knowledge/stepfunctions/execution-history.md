# Histórico de execução do Step Functions: o que ele prova, e o que ele não prova

> **Lido em 2026-09-19.** A página de referência da API `GetExecutionHistory`, mais as
> três páginas do guia já citadas em
> [`glue-integration.md`](glue-integration.md). **Relido em 2026-09-20**, com a página do
> tipo `HistoryEvent` acrescentada: dela vêm o `id` sequencial (§1) e a descrição do
> `previousEventId` que a lacuna 8 nomeia (§5). Quem consome: o extrator
> `sparkforge/facts/sfn_history.py` e as três regras de
> `rules/catalog/sfn-history.yaml`. Frase entre aspas é citação literal; o resto é
> leitura nossa, e diz de qual frase veio.

## 1. O que a API entrega, e o que ela recusa

- "Returns the history of the specified execution as a list of events." A resposta é
  uma **lista de eventos**, não um resumo: quem quiser tentativa, duração ou desfecho
  tem que derivá-los dos eventos.
- "This API action is not supported by `EXPRESS` state machines." O histórico de uma
  EXPRESS vai para o CloudWatch Logs, e o extrator daqui não o lê. Por isso a área
  `SF-SFNX` não tem nenhuma regra de EXPRESS: o artefato não existe.
- `includeExecutionData`: "You can select whether execution data (input or output of a
  history event) is returned. The default is `true`." **Sem ele não há `output`**, e
  sem `output` não há `JobRunId` para ler. O extrator emite
  `sfn.unresolved: execution_data_absent` e nenhum `sfn.job_run` — nunca um id
  inventado.
- Paginação: "If `nextToken` is returned, there are more results available". `maxResults`
  tem default 100 e máximo 1000. Uma saída salva **com** `nextToken` é uma página, não o
  histórico: sai `sfn.unresolved: truncated`.
- **A ordem do arquivo não importa, e por isso `--reverse-order` funciona.** "By default,
  the results are returned in ascending order of the `timeStamp` of the events. Use the
  `reverseOrder` parameter to get the latest events first", e o parâmetro é descrito como
  "Lists events in descending order of their `timeStamp`". O extrator não depende da
  ordem do arquivo: ele ordena pelo `id` (`sparkforge/facts/sfn_history.py:535`,
  `sorted(eventos, key=lambda e: int(e["id"]))`), e a página do `HistoryEvent` sustenta
  que isso é a ordem dos eventos — "The id of the event. Events are numbered
  sequentially, starting at one." Uma página gravada em ordem decrescente lê igual a uma
  crescente. **A consequência é a do item seguinte**: com `--reverse-order` a primeira
  página é o FIM do histórico, e é ali que `truncated: true` e um `status` resolvido
  aparecem juntos.
- **Truncamento e `status` são independentes, e a leitura nossa aqui é do código, não da
  página.** O `status` da execução sai `unresolved` quando o evento terminal dela
  (`ExecutionSucceeded`, `ExecutionFailed`, `ExecutionAborted`, `ExecutionTimedOut`) não
  está na página salva — nunca um desfecho adivinhado —, e isso é outra condição:
  `sparkforge/facts/sfn_history.py:536` deriva o `status` dos eventos lidos
  (`_desfecho_da_execucao`), e as linhas 538 e 542 emitem `truncated` e
  `execution_terminal_absent` em dois `if` separados. Uma página truncada que **contém**
  o evento terminal sai `truncated: true` **e** `status: succeeded` ao mesmo tempo. O
  contrário também existe: página inteira, sem `nextToken`, de uma execução ainda em voo
  sai `truncated: false` e `status: unresolved`.

## 2. A forma de cada evento, e o que ela sustenta

Todo evento tem `id`, `previousEventId`, `timestamp` e `type`.

| evento | campos que importam | o que sustenta |
|---|---|---|
| `ExecutionStarted` | — | o instante inicial da execução |
| `TaskStateEntered` | `stateEnteredEventDetails.name` | **o nome do estado** — a fonte que o extrator usa, e a única que ANTECEDE a tentativa |
| `TaskScheduled` | `taskScheduledEventDetails` com `resource`, `resourceType`, `parameters`, `region`, `timeoutInSeconds` | **uma tentativa** começou; o serviço, o padrão de integração e o prazo declarado |
| `TaskStarted` | `taskStartedEventDetails` | a chamada saiu |
| `TaskSubmitted` | `taskSubmittedEventDetails.output` | o `JobRunId` do Glue (§3) |
| `TaskSucceeded`, `TaskFailed`, `TaskTimedOut`, `TaskStartFailed`, `TaskSubmitFailed` | `error` e `cause` nos que os têm | **a tentativa terminou**, e como |
| `TaskStateExited` | `stateExitedEventDetails.name` | o estado saiu — publica o **mesmo nome**, e o extrator **não** o lê |
| `ExecutionSucceeded`, `ExecutionFailed`, `ExecutionAborted`, `ExecutionTimedOut` | `error` e `cause` | **o desfecho da execução** |

**Dois eventos publicam o nome do estado, e o extrator lê um só.** O
`TaskStateExited` traz `stateExitedEventDetails.name`, o mesmo nome; o extrator não o
lê em lugar nenhum — `stateEnteredEventDetails` é o único que ele acessa
(`sparkforge/facts/sfn_history.py:570`). A razão é de ordem, não de conteúdo: o nome
tem que ser resolvido para o `TaskScheduled`, que é onde a tentativa começa, e só o
`TaskStateEntered` vem **antes** dele na cadeia. O `TaskStateExited` sai depois da
última tentativa do estado, e num estado com retry ele aparece uma vez para várias
tentativas — nomear por ele seria nomear tarde demais e com granularidade errada.

**O encadeamento é por ramo, e é ele que pareia.** `previousEventId` aponta para o
evento anterior *daquele ramo*: dentro de `Parallel` e de `Map`, eventos de ramos
diferentes se intercalam na ordem de `id`, mas cada cadeia continua correta. Por isso o
extrator sobe a cadeia a partir do próprio evento — de um `TaskScheduled` até o
`TaskStateEntered`, de um terminal até o `TaskScheduled` — em vez de usar "o último
visto". Cadeia quebrada, raiz alcançada sem achar, ou ciclo: `sfn.unresolved` nomeado,
nunca um chute.

## 3. O `JobRunId` do Glue, e por que ele é uma lacuna

A página da API **não** descreve a forma do `output` do `TaskSubmitted` de uma
integração com o Glue. A página de integração diz que o `JobName` é inserido na
resposta, e nada mais. O extrator então lê defensivamente: `output` como objeto **ou**
como string com JSON dentro, e três chaves na ordem — `JobRunId`, `Id`, e `JobRun.Id`.
O que não casa sai em `sfn.unresolved: job_run_id_unrecognized` **com as chaves de topo
que ele viu**, que é exatamente o dado de que um histórico real precisa para fechar a
lacuna 1 abaixo.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-SFNX-001 | os agendamentos do Task no histórico passam do teto `1 + MaxAttempts` que o ASL declara | qual dos dois está errado; quantos JobRuns a falha produziu (lacuna 1 de `glue-integration.md`); custo |
| SF-SFNX-002 | a tentativa `.sync` terminou em `TaskTimedOut`, e o desfecho do JobRun **não foi observado** | que o job continuou rodando, nem que ele parou (lacuna 2); custo do run órfão (regra 13) |
| SF-SFNX-003 | a execução parou (`Aborted`/`TimedOut`) com o Task `.sync` agendado e sem terminal próprio | o que a AWS faz com o JobRun nesse caso (lacuna 2); custo |

**Nenhuma das três atribui custo, e a recusa é de desenho.** Dizer "você pagou por um
JobRun órfão" exige o `dpu_seconds` de um run que ninguém leu, e é o que a regra 13 do
`CLAUDE.md` proíbe; dizer o valor em dólar exige `cost_basis` (regra 25). O que o
histórico entrega é o `JobRunId` — e é por ele que `sparkforge finops` responde custo
com `dpu_seconds` medido.

## 5. Lacunas nomeadas

1. **A forma do `output` do `TaskSubmitted` do Glue.** Não publicada (§3). O extrator lê
   três formas e nomeia o resto. O que destrava: **um histórico real** com
   `includeExecutionData` ligado, lido na conversa e nunca commitado — o
   `job_run_id_unrecognized` que ele produzir traz as chaves de topo, e elas fecham a
   lacuna numa linha.
2. **O JobRun quando o Task expira ou a execução é abortada.** A descrição do abort do
   `.sync` não cobre o timeout do Task, e nada diz o que acontece com o JobRun quando a
   execução termina em `ExecutionAborted`. Por isso `SF-SFNX-002` e `SF-SFNX-003`
   afirmam **não observação**, e o conserto que elas propõem é declarar a limpeza em vez
   de confiar no default. O que destrava: frase oficial, ou um par
   (histórico, `get-job-run`) real.
3. **A composição dos retries continua aberta.** Esta feature mede quantas vezes o
   **Task** foi agendado; ela não mede quantos **JobRuns** uma falha produziu, porque o
   `MaxRetries` do próprio job é outra camada. Ver a lacuna 1 de
   [`glue-integration.md`](glue-integration.md). O que destrava: o par entre um
   histórico real com falha e os JobRuns do mesmo intervalo
   (`sparkforge collect glue-job-runs`) — e o `sfn.job_run` desta feature é metade dele.
4. **Histórico real não observado.** O corpus `fixtures/sfn_history/` é sintético,
   montado a partir da forma de evento publicada. Ele prova o **mecanismo**, não a
   resposta (U2 de `docs/sdd/SFN_HISTORY/define.md`).
5. **EXPRESS fora de alcance.** A API não o suporta (§1), e o CloudWatch Logs tem outro
   formato. Nada aqui vale para EXPRESS.
6. **Map distribuído (`mapRunArn`) não é lido.** Os eventos `MapRun*` entram na lista de
   tipos conhecidos e não produzem fact: o extrator não segue as execuções filhas de um
   Distributed Map, e o que roda dentro delas fica fora do histórico da mãe.
7. **`sfn.*` do histórico sai com `line: 0`.** O extrator lê JSON sem posição de linha, e
   o `subject.symbol` é `<estado>#<ordem>`. `sparkforge report github` não ancora esses
   achados numa linha do arquivo.

## Fontes

- Referência da API do AWS Step Functions — `GetExecutionHistory`: a lista de eventos, o veto a EXPRESS, `includeExecutionData`, `nextToken`/`maxResults`, `reverseOrder` e a forma de cada `*EventDetails`. https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html (retrieved 2026-09-20)
- Referência da API do AWS Step Functions — `HistoryEvent`: o `id` sequencial, o `previousEventId` e a lista de `Valid Values` do `type`. https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html (retrieved 2026-09-20)
- Guia do AWS Step Functions — padrões de integração com serviços: Request Response, `.sync`, o abort. https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — tratamento de erro: `MaxAttempts`, `States.TaskFailed`, `States.ALL`. https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — integração com o AWS Glue: o recurso `arn:aws:states:::glue:startJobRun.sync` e a política gerada. https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html (retrieved 2026-09-19)
