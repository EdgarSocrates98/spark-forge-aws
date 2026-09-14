<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_lakeformation`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Coleta a PERMISSAO de UMA tabela no Lake Formation: `list_permissions` (quem tem o que), `describe_resource` (a localizacao S3 esta registrada, e com qual role) e `get_data_lake_settings` (se a conta permite query engine de terceiro sem validacao de session tag -- o passo de CONTA que precede qualquer grant sob Full Table Access). E o artefato que fecha DOIS dos tres itens que `lakeformation.unresolved` nomeia; o terceiro, a policy do runtime role, e outro coletor. As TRES chamadas falham por motivos independentes e cada bloco carrega o SEU status -- um status unico faria 'nao consegui' virar indistinguivel de 'nao ha'. O recurso e OBRIGATORIO: `list_permissions` sem recurso devolve o inventario inteiro do data lake, que e dado de governanca de terceiros e nao tem por que entrar num `facts.json` committado. NAO le policy de IAM. Mesma politica offline-first dos demais coletores.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `database` | string | sim | Banco da tabela no catalogo. |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `table` | string | sim | Nome da tabela. |
| `catalog_id` | string | não | Id da conta dona do catalogo. Obrigatorio em cross-account: a MESMA `db.tabela` existe em contas diferentes, e sem ele as duas coletas se sobrescreveriam no manifesto. |
| `resource_arn` | string | não | Localizacao S3 a conferir em `describe_resource`. Sem ela o bloco sai `nao_coletado` em vez de sumir -- bloco ausente e indistinguivel de bloco vazio. |

## Na CLI

[`sparkforge collect athena-workgroup`](../cli/collect.md), [`sparkforge collect cloudwatch`](../cli/collect.md), [`sparkforge collect cloudwatch-logs`](../cli/collect.md), [`sparkforge collect emr-cluster`](../cli/collect.md), [`sparkforge collect emr-eks`](../cli/collect.md), [`sparkforge collect emr-serverless`](../cli/collect.md), [`sparkforge collect event-log`](../cli/collect.md), [`sparkforge collect glue-job`](../cli/collect.md), [`sparkforge collect glue-job-runs`](../cli/collect.md), [`sparkforge collect glue-resource-link`](../cli/collect.md), [`sparkforge collect iam-access`](../cli/collect.md), [`sparkforge collect iceberg-metadata`](../cli/collect.md), [`sparkforge collect lakeformation`](../cli/collect.md), [`sparkforge collect parquet-footer`](../cli/collect.md), [`sparkforge collect verify`](../cli/collect.md)

## Capacidade

collect real AWS artifacts and verify the manifest

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
