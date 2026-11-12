# TestExecutionReceipt — a prova atrás do red e do green

Referência da skill `sdd-build`. O schema do `build_report.md` registra hoje
`red: {command, exit}` e `green: {command, exit}` por tarefa; os campos
restantes do recibo moram no corpo da seção da tarefa até o schema
formalizá-los (campo novo no frontmatter sai `schema_invalid`).

## Os campos

| campo | o que prova | regra |
|---|---|---|
| `baseline_sha` | o vermelho/verde é **deste** commit, não de uma árvore anterior | sha curto do HEAD no momento do comando |
| `argv` | o comando como foi invocado, argumento a argumento | não a paráfrase nem o comando "de costume" |
| `exit_code` | o que apareceu | o número que a saída mostrou — não o esperado |
| `executor` | quem rodou | subagente/modelo/sessão; responde "quem pode confirmar?" |
| `per_test` | resultado por teste citado | quando a saída os distingue (`nodeid: PASSED/FAILED`) |
| `artifact_sha256` | o log ou artefato gravado é este, byte a byte | quando houver artefato; `receipt verify` confere |

O `command`/`exit` do schema continua sendo o que o gate lê; o recibo é o
que o revisor lê. Sem recibo, `red` é alegação.

## As quatro regras

1. **Nunca inventar.** `red.exit` sem ter visto a saída, `green` copiado
   do plano, "deve ter falhado" — fraude, não atalho. O recibo inteiro da
   tarefa morre e a tarefa recomeça do teste.
2. **Ambiente não é TDD.** `SyntaxError` no próprio teste, venv quebrado,
   credencial ausente, coleta que falhou por import — isso é falha de
   ambiente. O vermelho de TDD exige que o que falta seja a unidade sob
   teste. Conserte o ambiente e rode de novo, ou registre `blocked` com o
   motivo.
3. **Mudou, revalida.** Qualquer edição no código depois do `green`
   invalida o recibo: `baseline_sha` novo, comando rodado de novo. "Passou
   antes da última edição" é evidência de outra árvore.
4. **Frescor.** Recibo cita o sha em que rodou; apresentado como prova do
   código de hoje quando o HEAD já andou, é evidência velha — relé.

## Checkpoint, retry e recovery

- O **checkpoint** é o commit da tarefa: interrupção retoma dele. Sessão
  nova lê o `build_report` e o log para achar a próxima tarefa.
- A **reexecução é idempotente**: a tarefa retomada lê o estado (o teste
  existe? o diff está aplicado?) antes de escrever. Tarefa que não pode
  ser idempotente (registro de uma vez, migração) declara o porquê e o
  ponto de no-return.
- **Retry seguro**: o mesmo comando falhando duas vezes pelo mesmo motivo
  não se repete uma terceira sem diagnóstico e mudança declarada.
- **Recovery**: `blocked` sai com motivo e com a saída combinada com o
  operador. Passo destrutivo (reset, sandbox limpo, checkout sobre mudança
  não commitada, arquivo removido) **só com aprovação explícita e nomeada
  do operador para aquele passo**.
- **Conflict detection** antes de despachar: arquivo do manifesto sumiu,
  teste renomeado, diff de outra tarefa no mesmo caminho — sobe ao
  operador, não se resolve no jeito.
- **Concurrency**: um writer por árvore por vez. `parallel_safe` do plano
  governa quais tarefas podem ir juntas; nunca autoriza dois writers na
  mesma working copy.

## O que o recibo não substitui

- Não substitui o `red`/`green` do schema — o gate continua lendo-os.
- Não substitui as duas revisões nem a revisão final do diff.
- Não substitui `evidence_ref` da claim no `sdd-ship` — o recibo prova que
  o comando rodou; a claim precisa da medida que ele produziu.
