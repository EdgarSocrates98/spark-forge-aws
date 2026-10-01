<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_collect_emr_eks`

**Efeito:** Acessa a AWS (lê a conta) e grava o artefato em disco local.

## O que faz

Baixa `describe-virtual-cluster` e `describe-job-run` de uma execucao Amazon EMR on EKS e grava as DUAS respostas num unico arquivo autocontido, sob as chaves de topo `virtualCluster` e `jobRun`, no mesmo shape camelCase que `aws emr-containers ...` devolve -- coleta manual e automatica produzem o mesmo arquivo, que e o que `sparkforge_analyze_emr_eks` le. DUAS chamadas, nem uma nem seis: diferente do EMR Serverless, onde `GetApplication` devolve tudo num objeto so, aqui identidade do cluster virtual e execucao sao APIS SEPARADAS do servico `emr-containers`, e nenhuma contem a outra. OS DOIS IDS SAO OBRIGATORIOS, e nao ha resolucao por nome: `DescribeJobRun` exige `virtual_cluster_id` junto do `job_run_id` -- a propria API nao aceita um job run sem o cluster virtual que o contem. Nome NAO serve: escolher uma entre homonimas em silencio gravaria o artefato errado com aparencia de certo. Ficam FORA por decisao, nao por limitacao da API: `list-job-runs` (listagem, nao coleta de uma execucao identificada), o pod template apontado pela configuracao (outra chamada, `GetObject`) e todo o lado EKS. Mesma politica offline-first de `sparkforge_collect_event_log`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `job_run_id` | string | sim | Id da execucao. Obrigatorio junto do cluster virtual, porque a API exige os dois. |
| `now` | string | sim | Timestamp ISO 8601. |
| `repo` | string | sim |  |
| `virtual_cluster_id` | string | sim | Id do cluster virtual. Nome NAO serve -- `DescribeJobRun` exige o id. |

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
