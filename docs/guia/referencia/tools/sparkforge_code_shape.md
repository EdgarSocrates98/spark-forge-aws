<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_shape`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

A FORMA do grafo de codigo: comunidades (grupos que se chamam mais entre si) e os nos de maior grau. NAO e um julgamento -- comunidade nao e modulo nem sugestao de refatoracao, e grau alto nao e defeito: um simbolo chamado de trinta lugares pode ser um utilitario bem fatorado. `communities.algorithm` sai no corpo porque a particao e REPRODUZIVEL e nao UNICA: propagacao de rotulo nao tem resposta canonica. As duas medidas contam aresta RESOLVIDA, e `graph.resolution_rate` diz o tamanho do ponto cego. CORPO DE FONTE NUNCA SAI DAQUI.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `detail_level` | string: `summary`, `normal`, `full` | não | `summary` para as contagens e o metodo; `normal` e `full` acrescentam os membros e a lista por grau. |
| `top` | integer | não | Quantas comunidades e quantos nos por grau devolver. Satura no teto, nao recusa. |

## Na CLI

[`sparkforge code shape`](../cli/code.md)

## Capacidade

medir a forma do grafo de codigo -- comunidades e grau

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
