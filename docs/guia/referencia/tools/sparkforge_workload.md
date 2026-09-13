<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_workload`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Perfil de workload por eixos independentes -- scan, shuffle, memoria, skew, arquivos, join, SLA e classe de entrada -- a partir de facts JA extraidos. Cada eixo carrega o valor, a BASE que o produziu e a CONFIANCA: `measured` sai de artefato, `declared` sai do inventario versionado e nunca e promovido, e `unknown` carrega o fact que falta e, quando existe, o comando que fecha a lacuna. Verbo de topo, nao um `analyze`: nao extrai nada de artefato, classifica o que outros verbos ja extrairam -- mesma razao pela qual `benchmark` e `fuse` sao verbos proprios. A escala vem do HISTORICO DO PROPRIO JOB, nunca de limiar universal: sem `history_path`, os eixos de volume (`scan_intensity`, `shuffle_intensity`) saem `unknown` de proposito, em vez de comparar contra um limiar inventado que valeria para um job e mentiria para outro.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string | sim | Arquivo de facts (JSON) gerado por `analyze`, tipicamente `sparkforge_analyze_sql_metrics --out`. |
| `job_name` | string | sim |  |
| `job_run_id` | string | sim | Id do run que este perfil descreve. |
| `history_path` | string | não | Diretorio com um arquivo de facts por run ANTERIOR (`sparkforge_analyze_glue_job_runs --out`), um arquivo por run. A separacao por arquivo e o que identifica cada run: `execution_id` e por aplicacao, e dois event logs diferentes colidem nele. Sem este parametro, os eixos que precisam de escala saem `unknown`. |

## Na CLI

[`sparkforge workload`](../cli/workload.md)

## Capacidade

profile a workload by independent axis from already-extracted facts

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
