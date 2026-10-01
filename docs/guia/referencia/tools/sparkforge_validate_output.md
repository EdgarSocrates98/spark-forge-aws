<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_validate_output`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Valida um finding proposto contra o JSON Schema e contra a regra de ganho sem benchmark_ref antes de aceita-lo. Este e o outro pilar da independencia de modelo: um LLM diferente pode redigir o finding de outra forma, mas so passa se for logicamente consistente com o catalogo -- a validacao decide o que e aceitavel, nao o modelo que escreveu. `benchmark_ref` cita o `fact_id` de um `bench.run_delta` (`sparkforge_benchmark`), nao texto livre; informando `facts_path` o id citado passa a precisar existir naquele conjunto.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `finding` | object | sim |  |
| `facts_path` | string | não | Opcional. Caminho de um arquivo de facts. Sem ele, `benchmark_ref` so e cobrado na FORMA (`f_` + 6 hex); com ele, o `fact_id` citado precisa estar no conjunto. |

## Na CLI

[`sparkforge validate`](../cli/validate.md)

## Capacidade

validate a recommendation written by the model

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
