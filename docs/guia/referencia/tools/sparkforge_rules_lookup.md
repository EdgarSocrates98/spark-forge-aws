<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_rules_lookup`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Consulta o catalogo de regras determinístico por id ou categoria, devolvendo threshold, runtime_scope e fontes completas. Este e o nucleo da independencia de modelo: o LLM nao precisa saber de cor o limiar ou a severidade de uma regra -- ele consulta o catalogo versionado e recebe sempre a mesma resposta, qualquer que seja o modelo por tras da chamada.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `as_of` | string | não | Dia de referencia do estado das fontes (AAAA-MM-DD). Default: hoje, UTC. |
| `category` | string | não |  |
| `cursor` | string | não |  |
| `id` | array de string | não |  |
| `limit` | integer | não |  |
| `source_freshness` | boolean | não | Acrescenta `source_freshness` (estado de cada fonte citada: fixed, unverified, stale, aging, fresh ou unresolved, com o motivo e as datas) e `freshness_policy` (limiar declarado, `as_of` e contagem por estado). Calculado sobre knowledge/sources.lock.json: depende do lock e do dia. stale = a fonte mudou depois da data em que a regra a validou. |

## Na CLI

[`sparkforge rules lookup`](../cli/rules.md)

## Capacidade

look up a rule with threshold, version guard and source

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
