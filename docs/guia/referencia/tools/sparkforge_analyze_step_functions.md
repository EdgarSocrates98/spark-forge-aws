<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_step_functions`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai facts da definicao de uma state machine do AWS Step Functions em Amazon States Language (ASL): o `.asl.json` versionado no repositorio, ou a saida salva de `aws stepfunctions describe-state-machine` (objeto com `definition` como string JSON e `type`). Emite `sfn.state_machine` (tipo STANDARD, EXPRESS ou `undeclared` -- um `.asl.json` nao carrega o tipo, e ele NUNCA e suposto STANDARD), um `sfn.task` por estado Task, inclusive dentro de Parallel e Map (servico, API, padrao `request_response`/`sync`/`callback`, JobName literal ou a marca de dinamico, retriers com o `MaxAttempts` EFETIVO -- 3 quando omitido, com a marca de omitido --, `Catch` e `TimeoutSeconds`), `sfn.unresolved` com a razao do que nao deu para ler, e a sentinela `sfn.analyzed`. NAO chama a API do Step Functions e NAO le historico de execucao: le a DEFINICAO.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo .json (ASL ou describe-state-machine) ou diretorio com eles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze step-functions`](../cli/analyze.md)

## Capacidade

extract facts from an AWS Step Functions state machine definition

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
