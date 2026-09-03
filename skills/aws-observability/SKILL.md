---
name: aws-observability
description: Use quando for configurar, depurar ou otimizar observabilidade AWS com CloudWatch (Log Insights, Metrics, Alarms, Dashboards, EMF), X-Ray, CloudTrail e ADOT (AWS Distro for OpenTelemetry), ou habilitar/onboardar um serviço em Application Signals via ADOT auto-instrumentation SDKs. Aplica-se a alarms (métrico, composto, anomalia), dashboards, custom metrics/EMF, tracing e sampling, config de ADOT collector, CloudTrail auditing, synthetics/canaries e Dynamic Instrumentation. NÃO use para logging de aplicação ou detecção de ameaças de segurança.
---

# AWS Observability

Expertise de domínio para observabilidade AWS across métricas, logs e traces,
cobrindo o ciclo completo: **habilitar/onboardar** um serviço em Application
Signals usando ADOT (AWS Distro for OpenTelemetry) auto-instrumentation SDKs e
ServiceEvents — fazer o serviço aparecer no Application Signals — em EC2, ECS, EKS
e Lambda, em Python, Node.js, Java e .NET.

**Funciona melhor com** o [AWS MCP server](https://docs.aws.amazon.com/aws-mcp/)
— permite rodar comandos CLI, query CloudWatch e validar configurações
diretamente. Toda orientação também funciona com AWS CLI padrão.

**Nota:** arquivos de referência contêm versões de runtime, valores de quota e
matrizes de feature que podem mudar. Quando precisão importar (deploy em
produção, escolha de runtime, checagem de quota), confirme valores contra a
documentação atual da AWS em vez de depender apenas dos valores nestes arquivos.

Esta skill é **procedimento operacional que pode mutar infraestrutura AWS ao
vivo** (criar alarms, dashboards, habilitar Application Signals, instrumentar
Dynamic Instrumentation em serviço rodando). Não é gatilho do motor SparkForge —
o motor é offline e determinístico. Por isso a fronteira `## Não faz` é estrita e
o despacho é recusado.

## Roteamento

| Necessidade | Ação |
|---|---|
| Habilitar/onboardar serviço em Application Signals (auto-instrumentation) | Leia `references/application-signals-onboarding.md` |
| Propagar metadata git/deployment do ServiceEvents via CI/CD | Leia `references/application-signals-cicd-metadata.md` |
| Passos por plataforma/linguagem | Leia o `references/appsignals-guides/<plataforma>-<linguagem>.md` correspondente (ex. `references/appsignals-guides/eks-python.md`) |
| Escrever queries de Log Insights | Leia `references/log-insights.md` |
| Configurar alarms (métrico, composto, anomalia) | Leia `references/alarms.md` |
| Publicar custom metrics ou usar EMF | Leia `references/metrics.md` |
| Configurar X-Ray tracing ou ADOT | Leia `references/tracing.md` |
| Construir dashboards | Leia `references/dashboards.md` |
| Depurar problemas de observabilidade | Leia `references/troubleshooting.md` — começa com os 5 fixes mais comuns |
| Depurar falhas de canary | Leia `references/synthetics.md` — veja tabela de Common failures |
| CloudTrail operational auditing | Leia `references/cloudtrail.md` |
| Criar synthetic canaries | Leia `references/synthetics.md` |
| Depurar serviço rodando com breakpoints/snapshots — Dynamic Instrumentation (**modifica serviços ao vivo e captura dados em tempo real**) | Leia `references/dynamic-instrumentation.md` na íntegra antes de agir. Confirme com o operador antes de qualquer create/delete, e narre antes de ações significativas: observação → hipótese → ação proposta → resultado esperado. Diagnóstico de root cause em serviço rodando a partir de inspeção de fonte/código. Inspeção de fonte identifica hipóteses, não root causes confirmados. Mantenha causas suspeitas tentativas até evidência de runtime confirmar. |
| Spans múltiplas áreas | Leia a referência mais específica primeiro, depois consulte as demais conforme necessário |

## Referência rápida

| Necessidade | Referência | Comando-chave |
|---|---|---|
| Application Signals onboarding | `references/application-signals-onboarding.md` | EKS add-on, CloudWatch Agent IAM, OTLP endpoints |
| ServiceEvents CI/CD metadata | `references/application-signals-cicd-metadata.md` | 5 vars `OTEL_AWS_SERVICE_EVENTS_*` |
| Guia por plataforma/linguagem | `references/appsignals-guides/<p>-<l>.md` | 16 guias (EC2/ECS/EKS/Lambda × Python/Node/Java/.NET) |
| Log Insights queries | `references/log-insights.md` | `logs start-query` / `get-query-results` |
| Alarms | `references/alarms.md` | `cloudwatch put-metric-alarm` / `put-composite-alarm` |
| Custom metrics / EMF | `references/metrics.md` | `logs put-log-events` com EMF structured log |
| X-Ray / ADOT tracing | `references/tracing.md` | sampling rules, collector config, annotations vs metadata |
| Dashboards | `references/dashboards.md` | `cloudwatch put-dashboard` |
| Troubleshooting | `references/troubleshooting.md` | erro → causa → fix por serviço |
| CloudTrail auditing | `references/cloudtrail.md` | `lookup-events`, S3+Athena queries |
| Synthetics/canaries | `references/synthetics.md` | `synthetics create-canary` |
| Dynamic Instrumentation | `references/dynamic-instrumentation.md` | breakpoints/probes em código ao vivo, snapshot capture |

## Quando NÃO usar

- **Logging de aplicação**: escolha de framework de log, níveis, formatação —
  não é observabilidade AWS.
- **Detecção de ameaças de segurança**: GuardDuty, Security Hub, Detective têm
  cobertura própria; CloudTrail aqui é operational auditing, não threat hunting.
- **Análise de Spark UI / event log de job Glue/EMR**: use `analyze-spark-ui`
  (leitura de abas do Spark UI) ou `analyze-analytics` (facts de event log,
  CloudWatch metrics de run) — estas skills SparkForge extraem facts
  determinísticos do artefato; a observabilidade AWS aqui é configuração e
  depuração da infraestrutura de monitoramento.
- **Revisar Terraform de plataforma de dados**: `review-terraform-data-platform`
  cobre IaC; esta skill é procedimento contra a API CloudWatch ao vivo.

## Red flags

- Habilitar Dynamic Instrumentation sem ler `references/dynamic-instrumentation.md`
  na íntegra — modifica serviço ao vivo e captura dados em tempo real.
- Criar alarm sem confirmar o namespace e metricName exatos — alarm inerte não
  acusa nada e nada alerta.
- Assumir versão de runtime ou quota dos arquivos de referência sem conferir
  documentação atual em deploy de produção.
- Configurar ADOT collector sem validar o endpoint OTLP — traces somem
  silenciosamente.
- Habilitar Application Signals sem o IAM do CloudWatch Agent configurado — o
  serviço não aparece e nenhum erro explícito acusa.
- Tratar inspeção de fonte como root cause confirmado em Dynamic Instrumentation
  — é hipótese até evidência de runtime confirmar.

## Não faz

Esta skill é procedimento operacional que pode mutar infraestrutura AWS ao vivo. Não executa comandos de escrita sem confirmação explícita do operador. Não despacha como subagente.

Comandos de escrita — `put-metric-alarm`, `put-dashboard`, `create-canary`,
habilitar Application Signals add-on, create/delete de Dynamic Instrumentation
breakpoints/snapshots — você **não executa** sem confirmação explícita do
operador para cada comando. Você **recomenda** o comando, exibe o que ele faz, e
**sobe a decisão** a quem pode ser perguntado — o operador na sessão, ou o agente
pai que despachou. Dentro de um subagente, obter essa confirmação é **impossível**
(`ask_user_question` é sempre negado a subagente), e por isso esta skill **não
despacha**.

Dynamic Instrumentation é o caso mais sensível: modifica serviço rodando e captura
dados em tempo real. Confirme escopo, retenção e handling de PII antes de qualquer
create/delete, e narre antes de agir: observação → hipótese → ação proposta →
resultado esperado.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-observability`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa do roteamento e dos `references/` (application-signals-onboarding,
application-signals-cicd-metadata, appsignals-guides, alarms, log-insights,
metrics, tracing, dashboards, troubleshooting, cloudtrail, synthetics,
dynamic-instrumentation) — esta é uma adaptação ao contrato SparkForge (PT-BR,
fronteira de manutenção, não-despachável), e **pode desatualizar** quando a AWS
atualizar o procedimento. Antes de reproduzir comando de escrita, confira o
upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a
região e o serviço; nenhum número sem `fact_id` (aqui, fact vem do artefato de
`get-*` / `start-query`, não de inspeção); `validate_output` antes de apresentar;
manutenção destrutiva — especialmente Dynamic Instrumentation — você **não
executa** — recomende, e a confirmação de escopo e retenção **sobe a quem pode
ser perguntado**: o operador na sessão, ou o agente pai que despachou.
