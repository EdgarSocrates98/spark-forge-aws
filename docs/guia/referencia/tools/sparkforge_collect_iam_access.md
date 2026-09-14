<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_iam_access`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Simula acoes contra um role via `iam:SimulatePrincipalPolicy` e grava a DECISAO da AWS. SIMULAR e nao PARSEAR e a decisao de desenho: permission boundary recorta o que a policy concede sem aparecer nela, service control policy nega acima do role, `Deny` explicito em qualquer policy anexada vence todo `Allow`, e `Condition` depende de contexto que um parser nao tem -- um leitor de documento erra exatamente nesses quatro casos. A lista default de acoes vem da documentacao de Lake Formation e Glue e e SUBSTITUIVEL: quem sabe qual operacao falhou passa as acoes dela. Sem `resource_arns` a simulacao responde sobre `*`, o que NAO e a mesma pergunta -- o fact carrega `scoped_to_resource` para que as duas nao se confundam. NAO cobre policy de recurso. Mesma politica offline-first dos demais coletores.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `role_arn` | string | sim | ARN do role a simular -- tipicamente o runtime role do job. |
| `actions` | array de string | não | Acoes a simular. Sem ela, a lista default de Lake Formation e Glue. Passar a lista inteira quando a pergunta e sobre UMA escrita produz decisoes que nao dizem nada sobre o caso. |
| `resource_arns` | array de string | não | Recursos contra os quais simular. Sem eles a resposta e sobre `*`. |

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
