<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_code_export`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Exporta o grafo de codigo no formato de EXTRACAO que a fonte do Graphify publica -- `id`/`label`/`source_file`/`source_location` nos nos, `source`/`target`/`relation`/`confidence` nas arestas. MEDIDO em 2026-09-02: o formato do `graph.json` FINAL do Graphify NAO e publicado (o README nao o especifica e o ARCHITECTURE.md diz que o schema que mostra e o da extracao, anterior a `build()`), entao esta tool exporta o que a fonte de fato publica e declara no proprio artefato o que nao faz. NAO ha importacao e NAO ha dependencia de `graphifyy`: a compatibilidade e de FORMATO, nunca de codigo. Tudo o que este motor sabe e a fonte nao nomeia vive no bloco `sparkforge`, separado, para que ninguem assuma que veio de la.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio analisado. Nada e lido fora dela. |
| `communities` | boolean | não | Inclui a comunidade de cada no. `false` deixa `communities.algorithm` como `null`, que diz 'nao calculei' -- diferente de chave ausente. |
| `db` | string | não | Arquivo do indice. Omitido, o default e `.sparkforge/local/codeintel/graph.sqlite3` sob `repo`. |
| `detail_level` | string: `summary`, `normal`, `full` | não | `summary` para as contagens e a declaracao de compatibilidade; `normal` e `full` trazem nos e arestas. |

## Na CLI

[`sparkforge code export`](../cli/code.md)

## Capacidade

exportar o grafo no formato de extracao do Graphify

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
