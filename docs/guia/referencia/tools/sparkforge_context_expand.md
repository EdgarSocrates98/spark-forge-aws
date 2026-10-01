<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_context_expand`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Resolve uma ref ctx://v1 no cache local, valida integridade SHA-256 e escopo autorizado antes de devolver o payload sob max_bytes.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `ref` | string | sim |  |
| `max_bytes` | integer | não |  |
| `repo` | string | não |  |

## Na CLI

[`sparkforge context expand`](../cli/context.md), [`sparkforge context start`](../cli/context.md)

## Capacidade

discover and expand selective context under a hard byte budget

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
