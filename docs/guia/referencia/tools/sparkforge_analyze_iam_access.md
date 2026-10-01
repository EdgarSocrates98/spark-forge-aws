<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_iam_access`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Extrai a DECISAO de IAM ja simulada por `collect iam-access`, com a CAMADA que decidiu. `EvalDecision` tem QUATRO respostas e as tres de negacao exigem consertos DIFERENTES: `implicitDeny` se conserta acrescentando permissao; `explicitDeny` nao, porque `Deny` vence todo `Allow`; e quando a negacao vem de service control policy ou de permissions boundary, mexer na policy do role nao muda nada. `attrs.denied_by` nomeia a camada, e colapsar as quatro num booleano faria 'adicione a permissao' virar o conselho unico -- errado em tres dos quatro casos. Ele NAO afirma que a operacao real vai passar (a AWS avalia policies, nao tenta a chamada) e NAO cobre policy de RECURSO: bucket policy, key policy do KMS e Glue resource policy sao avaliacao separada, e esse limite sai em `iam.access.unresolved` em TODO artefato. `allowed` sem recurso simulado NAO e `allowed` naquele recurso, e `scoped_to_resource` diz qual das duas perguntas foi feita.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Artefato gravado por `sparkforge collect iam-access`, ou o diretorio deles. |
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
