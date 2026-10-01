<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_glue_resource_link`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai a TOPOLOGIA do catalogo ja coletada por `collect glue-resource-link`: o objeto na conta consumidora e resource link ou tabela comum, para onde ele aponta, e se o nome bate com o do recurso de origem. A UNICA derivacao e `name_matches_source`, e ela existe porque a AWS declara suportado apenas o link com o MESMO nome do recurso de origem -- afirmacao que ate esta tool nao tinha fact nenhum para conferi-la. A comparacao NAO e a mesma nos dois tipos: link de tabela compara contra `TargetTable.Name`, link de banco contra `TargetDatabase.DatabaseName`, que nao tem campo `Name` -- colapsar as duas daria nome divergente em todo link de banco correto. Ele NAO afirma que o link esta pendurado quando o alvo nao resolve: sob Lake Formation `EntityNotFoundException` e a mesma resposta para recurso inexistente e para recurso NAO AUTORIZADO, e `target_absence_is_ambiguous` sai `True` em vez de a ambiguidade ser resolvida por chute. NAO le grant e NAO le o estado do AWS RAM -- as duas sao outras pernas do grafo de acesso.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Artefato gravado por `sparkforge collect glue-resource-link`, ou o diretorio deles. |
| `cursor` | string | não |  |
| `detail_level` | string: `summary`, `normal`, `full` | não | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e `schema_version` UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a `id`, `kind`, `measures`, `at` (arquivo:linha) e `symbol`. Nada e apagado em silencio: o que sai do item aparece no envelope. NAO existe verbo que busque um fato por id -- para ter o fato inteiro de volta, reexecute o mesmo verbo em `full` e pague o payload inteiro outra vez. O `id` e estavel entre execucoes, entao serve para casar a linha do resumo com o mesmo fato numa execucao `full`. |
| `kind` | array de string | não |  |
| `limit` | integer | não |  |

## Na CLI

[`sparkforge analyze glue-resource-link`](../cli/analyze.md), [`sparkforge analyze iam-access`](../cli/analyze.md), [`sparkforge analyze lakeformation-grants`](../cli/analyze.md)

## Capacidade

read who holds which Lake Formation permission on a table

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
