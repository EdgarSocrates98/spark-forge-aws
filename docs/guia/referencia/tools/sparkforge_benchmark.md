<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_benchmark`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Compara DUAS execucoes a partir dos facts de event log de cada uma (`sparkforge_analyze_event_log` gravado em disco), e emite `bench.run_delta`, `bench.stage_delta`, `bench.unmatched`, `bench.analyzed`, `bench.runtime_pair` e `bench.unresolved`. Verbo de topo, nao um `analyze`: nao extrai nada de artefato, compara dois conjuntos ja extraidos. O QUE ELE RECUSA AFIRMAR, e isso importa mais que o que ele afirma: (1) `total_task_ms` e TEMPO DE TASK SOMADO (`mean_ms * task_count` sobre os stages) -- e trabalho, NAO tempo de relogio; o event log nao carrega duracao wall-clock, e um job pode terminar antes no relogio somando MAIS tempo de task ao paralelizar melhor, entao uma alta aqui pede confirmacao no relogio antes de reverter qualquer coisa. (2) Esta ferramenta NAO EXECUTA NADA: nao roda Spark, nao chama AWS, nao mede; ela le dois conjuntos de facts que alguem ja coletou. (3) O casamento de stage e por `symbol` IDENTICO -- `stage_id` nao e estavel entre execucoes --, e o que nao casa nao e silenciado: vira `bench.unmatched` e entra em `unmatched_stage_count`. (4) Uma chave `*_delta_pct` AUSENTE significa "nao sei", nunca "zero": ela e omitida quando o lado antes e zero, quando a medida falta ou esta incompleta de um lado, ou quando a populacao de stages mudou -- casos em que o percentual seria inventado. Os totais observados ficam; o que cai e a razao entre eles.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `after_path` | string | sim | Arquivo de facts da execucao DEPOIS, gerado por `sparkforge_analyze_event_log`. |
| `before_path` | string | sim | Arquivo de facts da execucao ANTES, gerado por `sparkforge_analyze_event_log`. |
| `after_runtime` | string | não | Versao de runtime em que a execucao DEPOIS rodou. |
| `before_runtime` | string | não | Versao de runtime em que a execucao ANTES rodou. Opcional: comparar duas execucoes no MESMO runtime continua valendo, e e o caso de medir mudanca de codigo. Rotular OS DOIS lados com valores diferentes emite `bench.runtime_pair`, que e o unico fato que sustenta uma afirmacao sobre MIGRACAO; rotular um lado so emite `missing_runtime_label`, e rotular os dois com o mesmo valor emite `same_runtime_label`. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge benchmark`](../cli/benchmark.md)

## Capacidade

compare two Spark runs from their event log facts

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
