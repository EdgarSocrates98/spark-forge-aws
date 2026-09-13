<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_glue_resource_link`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Le o objeto que o job consulta na conta CONSUMIDORA via `glue:GetTable` (ou `glue:GetDatabase` sem `table`) e, por default, o recurso de ORIGEM que o link declara. Duas chamadas com STATUS SEPARADOS, porque falham por motivos diferentes: o link pode existir e a origem nao ser visivel, e a origem pode existir sem link nenhum. `catalog_id` e o catalogo CONSUMIDOR, onde o link mora -- o de origem sai MEDIDO do proprio link e nunca e passado a mao, senao a conferencia seria contra o catalogo que o operador SUPOE. NAO le o estado do AWS RAM: link que resolve nao prova share aceito, e share aceito nao cria link. NAO decide se o nome bate -- isso e derivacao, e mora no extrator. Mesma politica offline-first dos demais coletores.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `database` | string | sim | Banco do link na conta consumidora. |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `catalog_id` | string | não | Id da conta CONSUMIDORA, onde o link mora. |
| `table` | string | não | Nome do link de TABELA. Sem ele o alvo e um BANCO, e a comparacao de nome muda com isso. |
| `verify_target` | boolean | não | Le tambem o recurso de origem. Default ligado: link que aponta para lugar nenhum e o defeito que este coletor existe para achar. |

## Na CLI

[`sparkforge collect athena-workgroup`](../cli/collect.md), [`sparkforge collect cloudwatch`](../cli/collect.md), [`sparkforge collect cloudwatch-logs`](../cli/collect.md), [`sparkforge collect emr-cluster`](../cli/collect.md), [`sparkforge collect emr-eks`](../cli/collect.md), [`sparkforge collect emr-serverless`](../cli/collect.md), [`sparkforge collect event-log`](../cli/collect.md), [`sparkforge collect glue-job`](../cli/collect.md), [`sparkforge collect glue-job-runs`](../cli/collect.md), [`sparkforge collect glue-resource-link`](../cli/collect.md), [`sparkforge collect iam-access`](../cli/collect.md), [`sparkforge collect iceberg-metadata`](../cli/collect.md), [`sparkforge collect lakeformation`](../cli/collect.md), [`sparkforge collect verify`](../cli/collect.md)

## Capacidade

collect real AWS artifacts and verify the manifest

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `true` |
| `readOnlyHint` | `false` |
