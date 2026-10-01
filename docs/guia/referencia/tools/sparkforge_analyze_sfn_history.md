<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_sfn_history`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts do HISTORICO de execucao de uma state machine do AWS Step Functions: a saida salva de `aws stepfunctions get-execution-history` (o objeto de resposta com `events`, ou a lista crua de eventos). Emite `sfn.execution` (status pelo evento terminal -- `unresolved` quando ele nao esta no arquivo, NUNCA sucesso por suposicao --, duracao e contagem dos eventos LIDOS), um `sfn.attempt` por TENTATIVA de Task (nome do estado pela cadeia de `previousEventId`, ordem, padrao de integracao, resultado, duracao, erro e cause), `sfn.job_run` com o JobRunId do Glue lido do `output` do TaskSubmitted, `sfn.unresolved` com a razao do que nao deu para ler ou parear (historico truncado, cadeia quebrada, evento de tipo desconhecido, `includeExecutionData` desligado, output de forma nao reconhecida), e a sentinela `sfn.analyzed`. NAO chama a API e NAO le a definicao: para a definicao ASL, use `sparkforge_analyze_step_functions`. A API nao suporta state machine EXPRESS. Nao atribui custo a tentativa nenhuma.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .json salvo de get-execution-history, ou diretorio com eles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze sfn-history`](../cli/analyze.md)

## Capacidade

extract facts from an AWS Step Functions execution history

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
