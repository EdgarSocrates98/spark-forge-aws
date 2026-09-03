---
name: aws-billing-and-cost-management
description: Use quando for analisar custos AWS, encontrar economias, gerenciar budgets, avaliar Savings Plans e Reserved Instances, right-size EC2/Lambda/RDS/EBS com Compute Optimizer, consultar pricing de serviço, query CUR com Athena, detectar anomalias de custo, escopar custos a billing views, ou monitorar Free Tier. Gatilhos: conta AWS, análise de custo, reduzir spend, savings plan, reserved instance, right-size, budget alert, cost optimization, pricing, free tier, cost anomaly, CUR, cost audit, billing view.
---

# Billing and Cost Management

Analise, otimize e gerencie custos AWS. Esta skill codifica expertise de domínio
dos produtos de cost management da AWS — gotchas, padrões corretos de uso de API
e workflows de otimização que modelos frequentemente erram.

Esta skill é **procedimento operacional que pode mutar infraestrutura AWS ao
vivo** (criar budgets, comprar Savings Plans, alterar enrollment do Compute
Optimizer). Não é gatilho do motor SparkForge — o motor é offline e
determinístico. Por isso a fronteira `## Não faz` é estrita e o despacho é
recusado.

## Uso

Use esta skill quando:

- Analisar spending AWS, trends de custo ou breakdowns de custo
- Configurar ou gerenciar budget alerts
- Avaliar compras de Savings Plans ou Reserved Instances
- Right-size EC2, Lambda, RDS ou EBS
- Consultar pricing de serviço AWS
- Rodar cost audits ou investigar cost spikes
- Query dados CUR com Athena
- Escopar análise de custo a um billing view específico
- Checar uso de Free Tier

## Conceitos core

- **Cost Explorer** — query de dados de custo/uso por serviço, conta, tag ou range
  de tempo
- **Budgets** — thresholds de spending com alerts; suporta scoping por billing view
- **Billing Views** — escopam dados de custo a um subconjunto do billing (custom
  view, billing group ou primary)
- **Compute Optimizer** — recomendações de right-sizing para EC2, Lambda, EBS, RDS
- **Cost Optimization Hub** — recomendações de economia agregadas across serviços
- **Savings Plans / Reserved Instances** — descontos por compromisso
- **CUR 2.0** — dados de billing detalhados por line-item, queryable via Athena

**Setup recomendado:** use o AWS MCP server para execução sandboxed, audit
logging e controles enterprise. Sem AWS MCP, todos os comandos usam AWS CLI
padrão.

## Regra crítica: sempre confira a data atual

**Antes de QUALQUER chamada de Cost Explorer, Budgets ou Savings Plans, você
DEVE determinar a data atual.** Use uma ferramenta para obter data e hora atuais
— NÃO assuma nem adivinhe o ano. LLMs frequentemente defaultam para datas dos
dados de treinamento em vez da data real, produzindo análises de dados stale que
parecem corretas mas estão completamente erradas.

## Regra crítica: cálculos determinísticos

**Você NUNCA deve realizar cálculos numéricos (somas, médias, percentagens,
comparações, contagens, min/max) raciocinando na resposta.** Aritmética de LLM é
não-confiável e produz respostas erradas em dados de custo.

**Você SEMPRE deve usar um script ou calculator tool** para qualquer matemática
sobre dados retornados de APIs. Escreva um script Python que realize o cálculo e
imprima o resultado. Se a tool `run_script` do AWS MCP server estiver disponível,
use-a. Senão, rode o script localmente.

Leia `references/deterministic-calculations.md` para padrões e exemplos.

## Guia de decisão

| Pergunta | Tool | Referência |
|---|---|---|
| O que estou gastando? Onde custos sobem? | Cost Explorer | `references/cost-explorer.md` |
| Quanto custa um serviço? | Price List API | `references/pricing-lookup.md` |
| Onde posso economizar? (comece aqui) | Cost Optimization Hub | `references/cost-optimization-hub.md` |
| Devo comprar Savings Plans? | CE SP Recommendations | `references/savings-plans.md` |
| Devo comprar Reserved Instances? | CE RI Recommendations | `references/reserved-instances.md` |
| Deep-dive em rec específico de EC2/Lambda/EBS/RDS? | Compute Optimizer | `references/ec2-rightsizing.md`, `references/lambda-optimization.md`, `references/rds-optimization.md`, `references/ebs-optimization.md` |
| Como configuro budget alerts? | Budgets | `references/budgets.md` |
| O que causa um cost spike? | Cost Anomaly Detection | `references/cost-explorer.md` |
| Estou dentro do Free Tier? | Free Tier API | `references/free-tier.md` |
| Como reduzo minha conta? | Cost Audit workflow | `references/cost-audit.md` |
| Como query dados detalhados de billing? | CUR 2.0 + Athena | `references/cur-athena.md` |
| Como otimizo serviços específicos? | Per-service patterns | `references/service-optimization.md` |
| Como escopo custos a um billing view? | Billing Views | Veja [Billing Views](#billing-views) abaixo |

## Tarefas comuns

### Analisar custos por serviço
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```
Default para `UnblendedCost`. Exclua Credits/Refunds com `--filter '{"Not":{"Dimensions":{"Key":"RECORD_TYPE","Values":["Credit","Refund"]}}}'`. End date é exclusive.

### Rodar cost audit
Leia `references/cost-audit.md` para o workflow completo de 7 passos: top cost
drivers → comparação month-over-month → recomendações de otimização → idle
resources → commitment coverage → quick wins por serviço → report.

### Obter recomendações de right-sizing
Compute Optimizer exige opt-in primeiro: `aws compute-optimizer
update-enrollment-status --status Active`. Depois leia
`references/ec2-rightsizing.md` para EC2 ou a referência específica do recurso.

### Consultar pricing de serviço
Leia `references/pricing-lookup.md` para service codes e attribute filters. Trap
comum: service codes do Price List API diferem dos nomes de serviço do Cost
Explorer.

## Billing Views

Um billing view escopa dados de custo e uso a uma fatia específica do billing de
uma conta (ex.: billing group, custom view ou default primary view). Quando o
operador quiser analisar custos por um billing view particular, adicione
`--billing-view-arn` às chamadas de API suportadas.

### Descobrir billing views disponíveis
```bash
aws billing list-billing-views \
  --billing-view-types PRIMARY CUSTOM BILLING_GROUP
```
Requer permissão `billing:ListBillingViews`.

### Usar billing view com Cost Explorer
```bash
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-04-01 \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --billing-view-arn arn:aws:billing::ACCOUNT_ID:billingview/BILLING_VIEW_ID
```

### Criar budget escopado a billing view
No JSON `--budget`, inclua o campo `BillingViewArn`:
```bash
aws budgets create-budget --account-id ACCOUNT_ID \
  --budget '{
    "BudgetName": "TeamX-Monthly",
    "BudgetLimit": {"Amount": "1000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "BillingViewArn": "arn:aws:billing::ACCOUNT_ID:billingview/BILLING_VIEW_ID"
  }'
```

### Suporte de API para `--billing-view-arn`

| Suporta `--billing-view-arn` | NÃO suporta |
|---|---|
| `ce get-cost-and-usage` | `ce get-reservation-coverage` |
| `ce get-cost-and-usage-with-resources` | `ce get-reservation-utilization` |
| `ce get-cost-forecast` | `ce get-savings-plans-coverage` |
| `ce get-usage-forecast` | `ce get-savings-plans-utilization` |
| `ce get-dimension-values` | |
| `ce get-tags` | |
| `ce get-cost-comparison-drivers` | |
| `budgets create-budget` (no budget JSON) | |

## Troubleshooting

| Erro | Causa | Fix |
|---|---|---|
| `ValidationException` no Cost Explorer | Dimension key errado (ex. `CHARGE_TYPE` em vez de `RECORD_TYPE`) | Use `RECORD_TYPE` para filtro de charge type |
| Resultados vazios com filter | Valor do filter não casa exatamente | Chame `GetDimensionValues` antes para obter valores válidos |
| `AccessDeniedException` em dados hourly | Granularidade hourly não habilitada | Habilite em Cost Explorer preferences |
| `Account not registered` no Compute Optimizer | Não fez opt-in | Rode `update-enrollment-status --status Active` |
| Budgets API falha fora us-east-1 | Budgets exige us-east-1 | Set `--region us-east-1` |
| Cost Explorer `Total` vazio com GroupBy | By design — totais excluídos ao agrupar | Faça chamada separada sem GroupBy, ou some resultados agrupados com script |
| `AccessDeniedException` em `list-billing-views` | Permissão faltando | Usuário precisa `billing:ListBillingViews` |
| `ValidationException` com `--billing-view-arn` | API não suporta billing views, ou ARN malformado | Confira a tabela de suporte acima; formato do ARN é `arn:aws:billing::ACCOUNT_ID:billingview/VIEW_ID` |
| Budget mostra `UNHEALTHY` health status | Acesso ao billing view revogado ou view deletado | Cheque `HealthStatus.StatusReason` no `describe-budget`; garanta `billing:GetBillingViewData` |

## Referência rápida

| Necessidade | Referência | Comando-chave |
|---|---|---|
| O que estou gastando | `references/cost-explorer.md` | `ce get-cost-and-usage` (UnblendedCost, End exclusive) |
| Onde economizar | `references/cost-optimization-hub.md` | Cost Optimization Hub (comece aqui) |
| Savings Plans | `references/savings-plans.md` | `ce get-savings-plans-purchase-recommendations` |
| Reserved Instances | `references/reserved-instances.md` | `ce get-reservation-purchase-recommendations` |
| Right-size EC2 | `references/ec2-rightsizing.md` | `compute-optimizer get-ec2-recommendations` (opt-in antes) |
| Right-size Lambda | `references/lambda-optimization.md` | `compute-optimizer get-lambda-function-recommendations` |
| Budget alerts | `references/budgets.md` | `budgets create-budget` (us-east-1) |
| Cost spike | `references/cost-explorer.md` | Cost Anomaly Detection |
| Free Tier | `references/free-tier.md` | Free Tier API |
| Cost audit | `references/cost-audit.md` | workflow de 7 passos |
| CUR com Athena | `references/cur-athena.md` | Athena query sobre CUR 2.0 |
| Pricing lookup | `references/pricing-lookup.md` | Price List API (service codes ≠ CE names) |
| Cálculos | `references/deterministic-calculations.md` | script Python — nunca aritmética de LLM |

## Quando NÃO usar

- **Custo de execução de job Glue/EMR em DPU-seconds**: use `benchmark-pyspark-job`
  (compara dois runs por tempo e resultado) ou `sparkforge finops` (custo por run
  e onde está o alavanca, a partir de `glue.job_run`/`glue.run_cost` facts). O
  Cost Explorer agrega por serviço e conta; o custo de DPU-seconds de um run
  específico é fact determinístico extraído do event log e do `GetJobRuns`, não
  dado de billing.
- **Right-sizing de cluster EMR/Glue por gargalo de performance**: o Compute
  Optimizer recomenda por utilização de recurso; gargalo dominante de job PySpark
  é diagnóstico do motor SparkForge (shuffle, spill, skew), não recomendação de
  billing.
- **FinOps de commit**: Savings Plans e RIs aqui são avaliação de compra; a
  decisão de commit multi-conta com CUR + Athena é `references/cur-athena.md`,
  não o motor.

## Red flags

- Fazer qualquer chamada de Cost Explorer/Budgets/Savings Plans sem confirmar a
  data atual primeiro — LLMs defaultam para datas de treinamento e produzem
  análise stale que parece correta.
- Realizar cálculos numéricos (somas, médias, percentagens) raciocinando na
  resposta — aritmética de LLM é não-confiável em dados de custo. Use script.
- Usar `CHARGE_TYPE` em vez de `RECORD_TYPE` como dimension key de filtro —
  `ValidationException`.
- Esquecer que End date é exclusive no `--time-period` — mês errado silenciosamente.
- Rodar Budgets API fora de us-east-1 — falha sem mensagem útil.
- Assumir que service codes do Price List API casam com nomes de serviço do Cost
  Explorer — não casam.
- Criar budget com `--billing-view-arn` em API que não suporta —
  `ValidationException`. Confira a tabela de suporte.
- Tratar `Total` vazio com GroupBy como bug — é by design; faça chamada sem
  GroupBy ou some com script.

## Não faz

Esta skill é procedimento operacional que pode mutar infraestrutura AWS ao vivo. Não executa comandos de escrita sem confirmação explícita do operador. Não despacha como subagente.

Comandos de escrita — `budgets create-budget`, `compute-optimizer
update-enrollment-status`, compra de Savings Plans/Reserved Instances, `billing
create-billing-view` — você **não executa** sem confirmação explícita do
operador para cada comando. Compra de commit (Savings Plans, RIs) é irreversível
e binda a conta por 1–3 anos: você **recomenda** com a análise, exibe o que o
commit faz, e **sobe a decisão** a quem pode ser perguntado — o operador na
sessão, ou o agente pai que despachou. Dentro de um subagente, obter essa
confirmação é **impossível** (`ask_user_question` é sempre negado a subagente), e
por isso esta skill **não despacha**.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill
`aws-billing-and-cost-management`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa do guia de decisão, dos workflows e dos `references/` (cost-explorer,
pricing-lookup, cost-optimization-hub, savings-plans, reserved-instances,
ec2-rightsizing, lambda-optimization, rds-optimization, ebs-optimization,
budgets, free-tier, cost-audit, cur-athena, service-optimization,
deterministic-calculations) — esta é uma adaptação ao contrato SparkForge (PT-BR,
fronteira de manutenção, não-despachável), e **pode desatualizar** quando a AWS
atualizar o procedimento. Antes de reproduzir comando de escrita, confira o
upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a data
atual antes de qualquer chamada de Cost Explorer/Budgets; nenhum número sem
`fact_id` (aqui, fact vem do artefato de `get-cost-and-usage` / `get-dimension-
values`, não de inspeção); cálculos numéricos sempre por script, nunca por
raciocínio; `validate_output` antes de apresentar; compra de commit você **não
executa** — recomende, e a confirmação de escopo e retenção **sobe a quem pode
ser perguntado**: o operador na sessão, ou o agente pai que despachou.
