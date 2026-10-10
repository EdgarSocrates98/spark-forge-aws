<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_graph_status`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Estado do indice que alimenta `graph view` — existe, frescor, contagens. Responde SOBRE o indice, nao COM ele; a unica leitura que explica por que `graph_view` recusaria.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `root` | string | não | Raiz do repo analisado (default: cwd). |

## Na CLI

[`sparkforge-aws graph status`](../cli/graph.md), [`sparkforge-aws graph view`](../cli/graph.md)

## Capacidade

emit ForgeGraphView/v1 projection and index state (Graph Studio producer)

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
