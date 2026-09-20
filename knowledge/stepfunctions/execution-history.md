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
  ordem do arquivo: `extract_sfn_history` ordena pelo `id`
  (`sorted(eventos, key=lambda e: int(e["id"]))`), e a página do `HistoryEvent` sustenta
  que isso é a ordem dos eventos — "The id of the event. Events are numbered
  sequentially, starting at one." Uma página gravada em ordem decrescente lê igual a uma
  crescente. **A consequência é a do item seguinte**: com `--reverse-order` a primeira
  página é o FIM do histórico, e é ali que `truncated: true` e um `status` resolvido
  aparecem juntos.
- **Truncamento e `status` são independentes, e a leitura nossa aqui é do código, não da
  página.** O `status` da execução sai `unresolved` quando o evento terminal dela
  (`ExecutionSucceeded`, `ExecutionFailed`, `ExecutionAborted`, `ExecutionTimedOut`) não
  está na página salva — nunca um desfecho adivinhado —, e isso é outra condição: em
  `sparkforge/facts/sfn_history.py`, `_desfecho_da_execucao` deriva o `status` dos
  eventos **lidos** (percorrendo-os de trás para frente atrás de um dos quatro), e
  `extract_sfn_history` emite `truncated` e `execution_terminal_absent` em dois `if`
  separados, nenhum dos quais lê o outro. Uma página truncada que **contém**
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

**Dois eventos publicam o nome do estado, e o extrator lê um só.** O `TaskStateExited`
traz `stateExitedEventDetails.name`, o mesmo nome; o extrator não o lê em lugar nenhum.
`stateEnteredEventDetails` é o único bloco de nome que ele acessa — no laço de
`extract_sfn_history` que resolve o estado de cada `TaskScheduled` —, e
`stateExitedEventDetails` não aparece no módulo. A razão é de ordem, não de conteúdo: o
nome tem que ser resolvido para o `TaskScheduled`, que é onde a tentativa começa, e só o
`TaskStateEntered` vem **antes** dele na cadeia. O `TaskStateExited` sai depois da
última tentativa do estado, e num estado com retry ele aparece uma vez para várias
tentativas — nomear por ele seria nomear tarde demais e com granularidade errada.

**O encadeamento é o que pareia, e a premissa dele é NOSSA — ver a lacuna 8.** A única
frase citada sobre o campo é a da página do `HistoryEvent`: "The id of the previous
event." Ela diz que existe um anterior; **não** diz que o anterior é o do mesmo ramo.
Que dentro de `Parallel` e de `Map` os eventos de ramos diferentes se intercalem na
ordem de `id` e mesmo assim cada cadeia continue correta é **leitura nossa, não
publicada**, e é a premissa de todo o pareamento de tentativas desta feature. Por isso o
extrator sobe a cadeia a partir do próprio evento — de um `TaskScheduled` até o
`TaskStateEntered`, de um terminal até o `TaskScheduled` — em vez de usar "o último
visto": se a premissa vale, subir a cadeia é o único jeito certo; se ela não vale, "o
último visto" estaria errado do mesmo jeito. Cadeia quebrada, raiz alcançada sem achar,
ou ciclo: `sfn.unresolved` nomeado (`chain_broken`, `chain_root`, `chain_cycle`), nunca
um chute — e é por essas três recusas que a premissa errada apareceria, em vez de virar
uma tentativa atribuída ao estado errado em silêncio.

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

**A `SF-SFNX-001` não fala sobre execução retomada.** Com `ExecutionRedriven` no
histórico, `build_sfn_retry_observado` emite `sfn.unresolved: redrive_in_execution` no
lugar do fact que a regra ancora, e ela sai em `skipped` — "não perguntei", nunca "está
tudo bem". A razão está na lacuna 9.

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
8. **O `previousEventId` por RAMO não está publicado, e é a premissa de todo o
   pareamento — inclusive da recusa nova.** Nas duas páginas da API relidas em
   2026-09-20, o campo tem uma descrição e só uma: "The id of the previous event." Nada
   ali diz que, dentro de um `Parallel` ou de um `Map`, o anterior é o do **mesmo ramo**.
   **O que mudou em 2026-09-20** (feature `docs/sdd/SFN_TENTATIVA/`): o extrator deixou
   de numerar estados de mesmo nome em ramos concorrentes. Para um nome, ele junta os
   `TaskStateEntered` distintos a que os `TaskScheduled` daquele nome se encadeiam; se
   dois deles forem mutuamente **não-ancestrais** — nenhum alcança o outro subindo
   `previousEventId` —, nenhum `sfn.attempt` daquele nome é emitido, nenhum `sfn.job_run`
   dele é ligado, e sai `sfn.unresolved: state_name_in_concurrent_branches`. Antes disso,
   o contador era chaveado só pelo nome, e a primeira tentativa do segundo ramo saía com
   `attempt_index: 2` — um índice que o arquivo não sustenta, e que é o `subject.symbol`
   por onde `SF-SFNX-002` e `SF-SFNX-003` apontam o achado. Reentrada **sequencial** —
   um retry, ou um `Choice` que volta — não cai ali: a entrada anterior está na cadeia da
   seguinte, as duas se alcançam, e a numeração 1..n continua valendo. **O critério
   depende da premissa, e errar nela continua sendo recusa a mais, nunca afirmação a
   menos**: se o encadeamento não fosse por ramo, duas entradas sequenciais poderiam
   parecer não-ancestrais, e o efeito seria recusar um estado que o arquivo sustenta. O
   que destrava: **um histórico real de execução com `Parallel` ou `Map`** — conferir se
   a cadeia de um ramo pula os `id` do outro é uma leitura de dois minutos —, ou uma
   frase oficial. O corpus sintético (`parallel_estado_homonimo` e `retry_em_ramo_unico`)
   exercita o **mecanismo**, não a premissa.
9. **A lista de tipos conhecidos do extrator já é a publicada, e o redrive virou recusa
   em vez de medida.** Medido na releitura de 2026-09-20: os `Valid Values` do campo
   `type` do `HistoryEvent` trazem 62 tipos, e `_TIPOS_CONHECIDOS` tinha 59. **Em
   2026-09-20** (feature `docs/sdd/SFN_TENTATIVA/`) os três que faltavam entraram, e não
   entraram iguais: `EvaluationFailed` e `MapRunRedriven` são tipo conhecido que não
   produz fact nem recusa, como os demais `MapRun*`; `ExecutionRedriven` entra com razão
   própria. **`ExecutionRedriven` é a execução RETOMADA**, e ele muda o que "quantas
   vezes o Task foi agendado" significa: um redrive reagenda o Task dentro da MESMA
   execução, e nada no arquivo separa as tentativas de antes das de depois. O extrator
   emite `sfn.unresolved: execution_redriven` por evento, e `build_sfn_retry_observado`
   emite `sfn.unresolved: redrive_in_execution` **no lugar** do `sfn.retry_observado`
   para o artefato que tem uma delas — as tentativas continuam medidas e publicadas, e o
   que se recusa é a **comparação** com o teto declarado no ASL. **O que continua aberto
   é MEDIR o redrive em vez de recusá-lo.** A forma do evento `ExecutionRedriven` não foi
   lida: se ele traz um contador de redrive, ou o `id` do evento em que a retomada
   começou, não está em nenhuma das páginas citadas aqui (U3 de
   `docs/sdd/SFN_TENTATIVA/define.md`). Com esse campo, as tentativas de antes e as de
   depois se separariam e o confronto voltaria a existir, uma contagem por rodada. O que
   destrava: **a página do `HistoryEvent` lida com esse foco**, ou um histórico real com
   redrive.

## Fontes

- Referência da API do AWS Step Functions — `GetExecutionHistory`: a lista de eventos, o veto a EXPRESS, `includeExecutionData`, `nextToken`/`maxResults`, `reverseOrder` e a forma de cada `*EventDetails`. https://docs.aws.amazon.com/step-functions/latest/apireference/API_GetExecutionHistory.html (retrieved 2026-09-20)
- Referência da API do AWS Step Functions — `HistoryEvent`: o `id` sequencial, o `previousEventId` e a lista de `Valid Values` do `type`. https://docs.aws.amazon.com/step-functions/latest/apireference/API_HistoryEvent.html (retrieved 2026-09-20)
- Guia do AWS Step Functions — padrões de integração com serviços: Request Response, `.sync`, o abort. https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — tratamento de erro: `MaxAttempts`, `States.TaskFailed`, `States.ALL`. https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html (retrieved 2026-09-19)
- Guia do AWS Step Functions — integração com o AWS Glue: o recurso `arn:aws:states:::glue:startJobRun.sync` e a política gerada. https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html (retrieved 2026-09-19)
