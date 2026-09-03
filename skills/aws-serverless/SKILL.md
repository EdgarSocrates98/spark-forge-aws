---
name: aws-serverless
description: Use quando precisar construir, deployar, gerenciar, debugar, configurar ou otimizar aplicacoes serverless na AWS com Lambda, API Gateway, Step Functions, EventBridge e SAM/CDK. Cobre cold starts, CORS, event source mappings, troubleshooting, concorrencia, SnapStart, Powertools, Function URLs, EventBridge Scheduler, Lambda layers e production readiness. Aplica quando alguem menciona Lambda, API Gateway, Step Functions, SAM templates, CDK serverless stacks, triggers de DynamoDB Stream, SQS event sources, cold starts, timeouts, erros 502/504, throttling, concorrencia, CORS, Powertools ou qualquer arquitetura event-driven na AWS, mesmo sem a palavra "serverless". NAO use para EC2, containers ECS/Fargate ou Amplify hosting.
---

# AWS Serverless

Dominio de especialidade para construir aplicacoes serverless na AWS: Lambda, API Gateway,
Step Functions, EventBridge, event source mappings, concorrencia, cold starts, deployment
e troubleshooting.

Funciona melhor com o AWS MCP server — execute comandos CLI, consulte CloudWatch, valide
configs diretamente. Toda orientacao tambem funciona com AWS CLI padrao.

## Skills especializadas — verifique primeiro

Estas cobrem capacidades e procedimentos que as referencias gerais abaixo nao cobrem.
Roteie para a skill correspondente antes de recorrer as referencias.

### Orquestracao de workflow

Roteie aqui quando o usuario quer coordenar multiplos passos, servicos ou funcoes.
Gatilhos incluem "orquestracao", "workflow", "state machine", "coordenacao multi-step",
"coordenar Lambda functions", "durable execution", "pipeline com retries", ou intencao de
construir saga/compensacao, human-in-the-loop, fan-out ou coordenacao async longa.

Ao iniciar nova orquestracao, voce DEVE apresentar a escolha entre AWS Step Functions e
AWS Lambda Durable Functions antes de implementar — nao escolha silenciosamente.

| Use esta skill | Quando o workload envolve |
|---|---|
| `design-step-functions-orchestration` | Orquestracao cujo trabalho principal e chamar servicos AWS diretamente; coordenar compute nao-Lambda (ECS/Fargate, Glue, SageMaker, Batch) via integracoes nativas; workflow visual e auditavel para compliance; ASL como especificacao entre times |
| `aws-lambda-durable-functions` | Orquestracao code-first in-process quando ja construindo em Lambda; muitos passos finos por execucao onde custo cumulativo de Step Functions Standard pode ser significativo; logica de orquestracao no mesmo codebase da aplicacao |

**Tradeoff (use quando ambos servem):** Durable Functions mantem a orquestracao no codebase
da Lambda; Step Functions externaliza em state machine gerenciada e visual com integracoes
de servico nativas.

**Seguranca:** Ambos persistem estado e payloads de workflow — Step Functions registra
input/output completo no historico de execucao. Como baseline, habilite execution logging
(CloudTrail) e CloudWatch alarms em falhas, e use roles de execucao least-privilege por
workflow. Nao passe secrets, tokens ou PII pelo estado do workflow; referencie por
Secrets Manager/ARN, e aplique KMS key gerenciada pelo cliente para encriptar estado
quando o dado for sensivel.

### Procedimentos de tarefa passo-a-passo (SOPs de CLI testados)

| Use esta skill | Para a tarefa |
|---|---|
| `connecting-lambda-to-api-gateway` | Conectar Lambda a API REST/HTTP: integracao proxy, permissoes, CORS, throttling, access logging, deployment |
| `connecting-lambda-to-dynamodb` | Conectar Lambda ao DynamoDB: IAM role, permissoes read/write, stream event source mapping |
| `creating-api-gateway-stage` | Criar stage de API Gateway com CloudWatch logging, X-Ray, throttling, WAF, autorizacao |
| `deploying-custom-domain-rest-api` | Deployar REST API com dominio customizado: cert ACM, Lambda backend, authorizer, base path mapping, Route 53 |
| `debugging-lambda-timeouts` | Diagnosticar Lambda com timeout: config, CloudWatch logs/metrics, VPC, cold starts, memoria, downstream calls |
| `processing-s3-uploads-with-step-functions` | Workflow event-driven: S3 upload -> EventBridge -> Step Functions -> Lambda (arquivos pequenos) ou Fargate (grandes) |

## Roteamento (referencias gerais nesta skill)

| Necessidade do usuario | Leia |
|-----------|------|
| Construir nova app serverless — selecao de padrao | `references/architecture.md` |
| Config Lambda, cold starts, SnapStart, memoria, VPC, layers, Function URLs | `references/lambda.md` |
| Concorrencia (reserved, provisioned, ESM controls) | `references/concurrency.md` |
| Event sources (SQS, DynamoDB Streams, SNS, Kinesis), filtragem, batch failures | `references/event-sources.md` |
| Step Functions, EventBridge rules/pipes/scheduler | `references/orchestration.md` |
| API Gateway quotas, authorizers, WebSocket | `references/api-gateway.md` |
| SAM/CDK resource types e iteracao rapida | `references/deployment.md` |
| Production readiness, observabilidade, anti-patterns | `references/production.md` |
| Debugar erro (string exata -> causa -> fix) | `references/troubleshooting.md` |

**Nota:** Arquivos de referencia contem versoes de runtime, quotas e matrizes de feature
especificas que mudam. Quando precisao importar (producao, escolha de runtime, quotas),
confirme contra documentacao AWS corrente. As referencias focam em valores e gotchas faceis
de errar — nao em basicos.

## Referência rápida

| Topico | Referencia |
| --- | --- |
| Arquitetura e selecao de padrao | `references/architecture.md` |
| Lambda (config, cold starts, SnapStart, memoria, VPC, layers) | `references/lambda.md` |
| Concorrencia (reserved, provisioned, ESM) | `references/concurrency.md` |
| Event sources (SQS, DynamoDB Streams, SNS, Kinesis) | `references/event-sources.md` |
| Orquestracao (Step Functions, EventBridge) | `references/orchestration.md` |
| API Gateway (quotas, authorizers, WebSocket) | `references/api-gateway.md` |
| Deployment (SAM/CDK) | `references/deployment.md` |
| Production readiness e observabilidade | `references/production.md` |
| Troubleshooting (erro -> causa -> fix) | `references/troubleshooting.md` |

### Skills SparkForge relacionadas

| Topico | Skill |
| --- | --- |
| Desenhar aplicacao Lambda serverless | `design-lambda-serverless` |
| Desenhar orquestracao com Step Functions | `design-step-functions-orchestration` |

## Quando NÃO usar

- **EC2**: nao e serverless — instancias persistentes com provisioning.
- **Containers ECS/Fargate**: embora Fargate seja serverless no nivel de infra, a skill
  cobre Lambda/Step Functions/EventBridge; para ECS/Fargate use documentacao AWS ou skills
  de container.
- **Amplify hosting**: nao coberto — produto distinto de hosting de frontend.
- **Desenho de arquitetura Lambda**: use `design-lambda-serverless` para decisoes de
  estrutura de funcao, packaging e estrategias de deploy.
- **Desenho de orquestracao Step Functions**: use `design-step-functions-orchestration`
  para decisoes de ASL, estados, integracoes e padroes de workflow.
- **Glue/Spark jobs**: nao sao serverless Lambda — use as skills de performance Glue.
- **Bancos de dados**: roteie para `aws-database` (DynamoDB, Aurora, etc).

## Red flags

- Escolher Step Functions vs Durable Functions silenciosamente sem apresentar o tradeoff
  ao usuario — a skill exige que a escolha seja explicita.
- Passar secrets, tokens ou PII pelo estado do workflow em vez de referenciar por
  Secrets Manager/ARN — expoe dado sensivel no historico de execucao.
- Configurar Lambda sem checar cold starts e impacto de VPC — VPC adiciona latencia de
  cold start; SnapStart mitiga em Java mas nao em outras runtimes.
- Nao confirmar quotas de runtime e feature contra documentacao corrente antes de
  recomendacao de producao — referencias podem estar desatualizadas.
- Ignorar concorrencia (reserved vs provisioned) ao diagnosticar throttling —
  `references/concurrency.md` tem os detalhes que resolvem o sintoma.
- Tratar erro 502/504 como problema de Lambda sem checar API Gateway — o sintoma e
  identico e a causa e diferente; `references/troubleshooting.md` mapeia string de erro
  a causa.
- Deployar sem access logging e X-Ray em API Gateway — observabilidade de producao
  nao é opcional.

## Não faz

Esta skill e procedimento operacional que pode mutar infraestrutura AWS ao vivo. Nao
executa comandos de escrita sem confirmacao explicita do operador. Nao despacha como
subagente.

Comandos de escrita — `aws lambda create-function`, `aws lambda update-function-code`,
`aws apigateway create-rest-api`, `aws stepfunctions create-state-machine`,
`aws events put-rule` — voce **nao executa**. Recomende o comando, exiba o que ele faz,
e **suba a decisao** a quem pode ser perguntado — o operador na sessao, ou o agente pai
que despachou. Dentro de um subagente, obter essa confirmacao e **impossivel**
(`ask_user_question` e sempre negado a subagente), e por isso esta skill **nao despacha**.

Manutencao destrutiva — `delete-function`, `delete-rest-api`, `delete-state-machine`,
remocao de event source mapping — voce **nao executa**. Recomende, e a confirmacao de
escopo e retencao sobe a quem tem a pergunta disponivel.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-serverless`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream e a fonte autoritativa
dos arquivos de referencia (`references/lambda.md`, `references/concurrency.md`,
`references/event-sources.md`, `references/orchestration.md`, `references/api-gateway.md`,
`references/deployment.md`, `references/production.md`, `references/troubleshooting.md`,
`references/architecture.md`) e do template Powertools (`assets/powertools-handler.py`,
nao copiado localmente). Esta e uma adaptacao ao contrato SparkForge (PT-BR, fronteira de
manutencao, nao-despachavel) e **pode desatualizar** quando a AWS atualizar runtimes,
quotas ou procedimentos. Antes de reproduzir comando de escrita, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme regiao, runtime
e servico; nenhum numero sem verificacao contra documentacao corrente ou referencia;
manutencao destrutiva voce **nao executa** — recomende, e a confirmacao de escopo e
retencao **sobe a quem pode ser perguntado**: o operador na sessao, ou o agente pai que
despachou.
