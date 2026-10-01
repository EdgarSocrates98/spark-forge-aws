<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_capacity`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Escolhe, entre as capacidades que o job JA RODOU, a mais BARATA que cumpre o SLA -- nunca a mais rapida. `sparkforge_workload` DESCREVE o job por eixo; esta tool ESCOLHE a capacidade, e a escolha e SEMPRE `safety: "REVIEW"` -- nada aqui aplica a mudanca. Verbo de topo, nao um `analyze`: nao extrai nada de artefato, decide sobre o que outros verbos ja extrairam -- mesma razao de `benchmark`, `fuse` e `workload`. TRES RECUSAS SUSTENTAM O RESULTADO: (1) so capacidade OBSERVADA entra -- extrapolar para uma nunca rodada exigiria uma lei de escala que fonte nenhuma publica; (2) so run COMPARAVEL conta -- fora da tolerancia de volume do run corrente, o historico cai em `discarded_runs`/`refused`, nunca some em silencio; (3) a RESOLUCAO e declarada -- com `n` runs comparaveis a estimativa nao distingue nada mais fino que `1/n`, e alvo mais fino que isso e recusa (`resolution_too_coarse`), nao aprovacao.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string | sim | Arquivo de facts (JSON) do run CORRENTE -- precisa conter `workload.declared` (o SLA) e os `spark.sql.scan` que dao o volume de hoje, tipicamente `sparkforge_analyze_sql_metrics --out`. |
| `job_name` | string | sim |  |
| `job_run_id` | string | sim | Id do run que este plano descreve. |
| `history_path` | string | não | Diretorio com um arquivo de facts por run ANTERIOR (`sparkforge_analyze_glue_job_runs --out`, um por run), a fonte das capacidades observadas. Sem ele, `candidates` sai vazio -- nenhuma capacidade foi observada. |

## Na CLI

[`sparkforge capacity`](../cli/capacity.md), [`sparkforge finops`](../cli/finops.md)

## Capacidade

choose the cheapest observed capacity that meets the SLA

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
