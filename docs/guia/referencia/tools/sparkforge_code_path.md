<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_path`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

O caminho MAIS CURTO de chamadas de um simbolo ate outro, descendo pelas chamadas. Responde o que `sparkforge_code_symbol` nao responde: aquela diz O QUE um simbolo alcanca (o raio), esta diz COMO ele chega num alvo -- e e por onde o caminho passa que se decide onde intervir. Quando nao ha caminho, `reason` separa TRES casos que nao querem dizer o mesmo: `node_not_indexed`, `depth_exhausted` (recusa por teto -- subir `depth` pode mudar a resposta) e `no_resolved_path` (o grafo esgotou antes do teto). O caminho percorre somente aresta RESOLVIDA, e `graph.resolution_rate` diz o tamanho do ponto cego. CORPO DE FONTE NUNCA SAI DAQUI -- para o codigo use `sparkforge_code_read`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `destino` | string | sim | Id de onde o caminho termina. Para o sentido inverso, troque os dois: nao ha parametro de direcao. |
| `origem` | string | sim | Id de onde o caminho comeca, de `sparkforge_code_search`. |
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `depth` | integer | não | Teto de saltos. Satura no maximo, nao recusa; atingi-lo sai como `reason: depth_exhausted`. |
| `detail_level` | string: `summary`, `normal`, `full` | não | `summary` para o veredito e as contagens do grafo; `normal` e `full` acrescentam os nos do caminho. |

## Na CLI

[`sparkforge code path`](../cli/code.md)

## Capacidade

tracar o caminho de chamadas entre dois simbolos

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
