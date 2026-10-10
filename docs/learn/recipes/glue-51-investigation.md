# Receita — investigar um job no Glue 5.1

**O quê:** `runtime detect --glue 5.1` + `analyze terraform`/`analyze
glue-job-runs` + `judge --glue 5.1` — inventário da infraestrutura declarada,
facts dos artefatos e julgamento contra as regras `SF-GLUE*`/`SF-ENV*` do
runtime 5.1.
**Por que:** no Glue, versão decide limiar — o que é aceitável no 4.0 pode ser
finding no 5.1, e a fonte da versão (flag, Terraform, dump) muda a confiança
da resposta.
**Quando:** avaliar definição de job Glue, Terraform de jobs, ou runs
observados, no runtime 5.1.
**Quando não:** migração 5.1 → 6.0 (receita de migração:
[usos/migracao-de-versao](../../guia/usos/migracao-de-versao.md)); prova de
comportamento em produção — `collect` na AWS é outro caminho e pede credencial.

## Problema

"Este job Glue 5.1 está bem definido? O Terraform dele tem contradição? O que
as regras do runtime 5.1 dizem?"

## Pré-requisitos

`sparkforge-aws` instalado; `.tf` de jobs Glue, definição do job ou dump de
runs; saber que o runtime alvo é 5.1 (ou deixar `runtime detect` inferir do
`glue_version` do Terraform / do fact observado).

## Passo a passo

```bash
# confirmar o runtime — declaração ou facts observados vencem a flag
sparkforge-aws runtime detect --glue 5.1 \
  --facts .sparkforge_aws/facts.json

# extrair a definição de infraestrutura (Terraform dos jobs)
sparkforge-aws analyze terraform --path infra/ \
  --out .sparkforge_aws/facts-tf.json

# julgar contra o catálogo versionado do 5.1
sparkforge-aws judge --facts .sparkforge_aws/facts-tf.json --glue 5.1 \
  --out .sparkforge_aws/findings.json
```

## Saída esperada / interpretação

Findings `SF-GLUE-*` (worker_type vs max_capacity, bookmarks com
max_concurrent_runs, retries sobre escrita não idempotente, observabilidade
ausente, segredo em argumento) e `SF-ENV-*` (runtime/versão), cada um com
`rule_id`, limiar, fonte e `fact_id` da evidência. Divergência entre fontes
de versão sai reportada — nunca trocada em silêncio.

## Verificação

`rules lookup --runtime glue --index` mostra as regras escopadas ao Glue;
`rules lookup --id SF-GLUE-XXX` traz limiar e fonte com data de qualquer
finding.

## Limitações

Facts vêm do artefato fornecido — sem `.tf`, definição ou dump, a resposta é
`unresolved` honesto. O catálogo muda depressa que o código: rejulgar facts
antigos com catálogo novo não reprocessa a fonte.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| versão divergente reportada | `--glue` vs `glue_version` do Terraform | a declaração **perde** para o observado — é comportamento, não erro |
| findings vazios com .tf presente | blocos sem `aws_glue_job` | `analyze terraform` cobre o recurso declarado; confira o path |
| regra `skipped` | guarda de versão não casou | `--show-skipped` no `judge` mostra o motivo por regra |

## Uso por agentes

Skill `review-glue-terraform` (revisão de IaC de jobs Glue) e coordenador
`glue-infra-reviewer` — definição do job, disparo por Step Functions/Airflow
e observabilidade, no runtime declarado.
