<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_graph_view`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Projecao ForgeGraphView/v1 do indice de codigo persistido — a mesma saida de `sparkforge-aws graph view`, produtora do Graph Studio. Somente leitura sobre `.sparkforge_aws/local/codeintel/graph.sqlite3`; sem indice recusa SF-GRAPH-NO-INDEX com o unlock `code index`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `limit` | integer | não | Teto de nos da projecao (default 5000). |
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
