<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_change_sandbox`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Autonomia L2 (§15, sandbox execute): aplica um diff unificado (`diff_path`, do `sparkforge change plan --out` ou de `git diff`) numa COPIA do repositorio em `.sparkforge/sandbox/<id>/` -- `before/` pristina e `after/` com o diff --, roda o scan nas duas e compara os achados pela chave estavel: `new`, `resolved`, `kept_count` e `moved_candidates`, com as obrigacoes de prova (validation e rollback) das regras tocadas e os proximos passos. O aplicador e estrito, tudo ou nada: diff_vazio, diff_grande_demais, diff_nao_suportado (criacao, remocao, renome, binario), diff_malformado, diff_nao_aplica, caminho_fora_da_raiz, arquivo_fora_da_copia. `clean` apaga `.sparkforge/sandbox/`. O QUE ELA NAO FAZ: nao toca a arvore principal (`main_tree_touched: false`), nao executa comando do repositorio (testes sao do operador), nao usa git e nao afirma ganho: a diferenca de achados nao e desempenho.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do repositorio. |
| `clean` | boolean | não | Apaga .sparkforge/sandbox/ em vez de aplicar. |
| `diff_path` | string | não | Arquivo de diff unificado a aplicar na copia. |

## Na CLI

[`sparkforge change plan`](../cli/change.md), [`sparkforge change propose`](../cli/change.md), [`sparkforge change sandbox`](../cli/change.md)

## Capacidade

produce a configuration change and try any diff in a sandbox copy

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
