<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_symbol`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Tudo que o indice sabe sobre UM simbolo: metadado, assinatura normalizada, quem o chama, quem ele chama, e o raio de impacto ate `depth` saltos acima. CORPO DE FONTE NUNCA SAI DAQUI, em nenhum `detail_level` -- para o codigo use `sparkforge_code_read`, que aplica os tetos duros e devolve o trecho com rotulo de confianca. `callees` traz somente chamadas RESOLVIDAS: chamada com receptor de tipo desconhecido vive em `unresolved_refs` e nao aparece, entao lista vazia nao quer dizer folha.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `node_id` | string | sim | Id devolvido por `sparkforge_code_search`. |
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `depth` | integer | não | Saltos do raio de impacto. Satura no teto, nao recusa. |
| `detail_level` | string: `summary`, `normal`, `full` | não | `summary` para no metadado; `normal` acrescenta vizinhanca direta; `full` acrescenta o raio de impacto e os testes nele. |

## Na CLI

[`sparkforge code read`](../cli/code.md), [`sparkforge code symbol`](../cli/code.md)

## Capacidade

inspecionar simbolo, vizinhanca e raio de impacto

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
