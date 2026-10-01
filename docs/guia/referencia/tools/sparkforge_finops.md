<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_finops`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta -- capacidade ou codigo. Verbo de topo, nao um `analyze`: nao extrai nada de artefato, consome facts JA extraidos -- mesma razao de `benchmark`, `fuse`, `sparkforge_workload` e `sparkforge_capacity`. Os achados vem do `judge` sobre os MESMOS facts -- esta tool nao escreve regra nenhuma, so agrupa o que o motor ja produz sob o eixo financeiro, separando achado que aponta para CODIGO (`levers.code`) de achado que aponta para CAPACIDADE (`levers.capacity`, que aponta para `sparkforge_capacity`) -- a conta sozinha nao diz qual alavanca e a certa. O QUE ESTE RELATORIO RECUSA: (1) atribuir custo a causa -- 'voce desperdicou X com spill' exigiria o custo do run que NAO aconteceu; (2) interpolar entre capacidades observadas -- a curva seria bonita e mentiria exatamente entre os pontos; (3) ordenar achado por economia estimada -- cada numero desses e um contrafactual disfarcado de prioridade; (4) limiar de 'caro' -- fonte nenhuma diz que um preco por run e muito. `region` e `runtime_version` valem `UNQUALIFIED` quando a fonte de preco foi lida e nao qualificou o eixo -- distinto de vazio, que diria que nenhum custo resolveu.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_path` | string | sim | Arquivo de facts (JSON) com `glue.job_run` do job e, quando houver, `workload.declared` (o SLA) -- tipicamente `sparkforge_analyze_glue_job_runs --out`. |
| `job_name` | string | sim |  |

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
