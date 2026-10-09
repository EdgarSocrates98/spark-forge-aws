<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_dq_ai_assess`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Compoe facts de governanca Glue DQ ADVANCED, valida DQDL externo por sintaxe, julga SF-DQ-AI e retorna tres views no relatorio. Nao gera regras, nao envia rows a provider e nao estima custo.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `facts_paths` | array de string | sim |  |
| `cost_facts_path` | string | não |  |
| `dqdl_path` | string | não |  |
| `glue` | string | não |  |
| `python` | string | não |  |
| `review_path` | string | não |  |
| `spark` | string | não |  |
| `view` | string: `all`, `maintainer`, `operator`, `security_compliance` | não |  |

## Na CLI

[`sparkforge-aws analyze dq-ai`](../cli/analyze.md), [`sparkforge-aws dq-ai assess`](../cli/dq-ai.md)

## Capacidade

compose deterministic data-quality AI assessment

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
