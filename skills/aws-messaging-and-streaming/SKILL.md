---
name: aws-messaging-and-streaming
description: Use quando for raciocinar sobre padrões de mensageria e streaming na AWS — escolher entre SQS, SNS, EventBridge, Amazon MQ, Kinesis Data Streams, Data Firehose, Managed Service for Apache Flink e MSK, ou decidir qual padrão (mensageria vs. streaming) cabe a um workload. Use também para identificar qual serviço AWS possui cada canal de comunicação com cliente (e-mail via SES; WhatsApp, SMS, MMS, RCS, voice e mobile push via AWS End User Messaging) e rotear à skill especializada. NÃO use para perguntas detalhadas de MSK ou Managed Service for Apache Flink — prefira skills específicas. Não configura canais de comunicação com cliente; adia às skills especializadas.
---

# Serviços AWS de Mensageria & Streaming

Ao responder perguntas de mensageria e streaming AWS, verifique números
específicos, versões, limites e detalhes comportamentais em skills específicas
de serviço ou na documentação oficial da AWS. Em caso de dúvida, busque skills
ou docs em vez de adivinhar. Opções de configuração fabricadas ou números de
versão incorretos são piores do que admitir incerteza.

Quando uma pergunta envolver configurações recomendadas (alarmes CloudWatch,
thresholds, tratamento de dados ausentes), busque skills específicas de serviço
ou documentação em vez de depender de boas práticas gerais.

## Visão geral

Domínio para escolher e usar serviços AWS que movem dados entre produtores e
consumidores. Esta skill cobre dois padrões fundamentais — **mensageria** e
**streaming** — e os serviços AWS que implementam cada um. Também marca a
fronteira com **comunicação com cliente** — mensagens entregues a pessoas em vez
de a componentes de aplicação — e roteia essas perguntas à skill ou
documentação AWS que possui cada canal (ver Comunicação com cliente
(Application-to-Person) abaixo). Use esta skill para decidir qual padrão cabe a
um workload, selecionar o serviço certo e entender como os serviços se integram.

Para orientação específica de serviços AWS individuais, veja arquivos de
referência ou skills específicas de serviço.

## Streaming e Mensageria

### O que é Mensageria?

Mensageria habilita **comunicação desacoplada e assíncrona** entre componentes.
Um produtor envia uma mensagem; um ou mais consumidores a recebem e processam.
Uma vez processada, a mensagem é tipicamente deletada. Serviços de mensageria
tratam garantias de entrega, retries e roteamento de dead-letter.

**Características-chave:**

- Mensagens são consumidas uma vez (ponto-a-ponto) ou fan-out (pub/sub), depois
  removidas
- Sem replay — uma vez reconhecida, a mensagem some
- Projetadas para workloads de comando/requisição, distribuição de tarefas e
  notificação de eventos

### O que é Streaming?

Streaming habilita **fluxo de dados contínuo, ordenado, durável e de alto
throughput**. Produtores anexam registros a um log; consumidores leem de
posições nesse log. Registros persistem por um período de retenção configurável
independentemente do consumo.

**Características-chave:**

- Registros são retidos e replayáveis dentro da janela de retenção
- Ordenação estrita dentro de uma partição/shard
- Múltiplos consumidores independentes podem ler os mesmos dados em posições
  diferentes
- Projetados para event sourcing, analytics em tempo real, change data capture e
  processamento contínuo

### Diferenças-chave

| Dimensão | Mensageria | Streaming |
|---|---|---|
| **Ciclo de vida do dado** | Deletado após consumo | Retido para replay (horas a indefinidamente) |
| **Ordenação** | Best-effort (Standard) ou por-grupo (FIFO) | Estrita por-partição/shard |
| **Modelo de consumidor** | Consumidores competidores (distribuição de trabalho) | Leitores independentes (fan-out por posição) |
| **Padrão de throughput** | Bursty, variável | Sustentado, alto volume |
| **Replay** | Não suportado (exceto redrive de DLQ) | Nativo — seek para qualquer posição na retenção |
| **Latência típica** | Milissegundos (push ou short-poll) | Milissegundos a poucos segundos |
| **Unidade de escala** | Concorrência (consumidores/pollers) | Partições ou shards |

### Casos de uso de Mensageria

- Desacoplar microsserviços com padrões request/response ou comando
- Distribuir trabalho entre um pool de consumidores competidores (filas de
  tarefas)
- Fan-out de notificações onde cada assinante age independentemente
- Workloads bursty que se beneficiam de buffer de fila
- Migrar aplicações JMS/AMQP existentes (Amazon MQ)

### Casos de uso de Streaming

- Ingestão contínua de alto throughput (logs, métricas, clickstreams, telemetria
  IoT)
- Event sourcing onde consumidores precisam replayar de qualquer ponto no tempo
- Múltiplos consumidores independentes processando os mesmos dados de forma
  diferente
- Analytics em tempo real, agregações em janela ou complex event processing
- Pipelines de change data capture (CDC)

### Serviços de Mensageria

Esses serviços são geralmente usados para workloads de mensageria. Às vezes
serviços de streaming (Kinesis Data Streams, MSK) também são usados para
mensageria, dependendo do caso de uso e requisitos.

| Serviço | Melhor para | Diferenciador-chave |
|---|---|---|
| **Amazon SQS** | Filas de tarefas, desacoplamento, buffering | Totalmente gerenciado, throughput ilimitado (Standard), exactly-once (FIFO), fair queues para workloads multi-tenant |
| **Amazon SNS** | Fan-out, notificações pub/sub | Push para múltiplos assinantes (SQS, Lambda, HTTP; endpoints de e-mail/SMS servem a alertas operacionais — para e-mail ou SMS de cliente veja Comunicação com cliente) |
| **Amazon EventBridge** | Roteamento de eventos, integração cross-account/SaaS | Filtragem baseada em conteúdo, schema registry, 200+ integrações de fonte AWS |
| **Amazon MQ** | Lift-and-shift de apps JMS/AMQP/MQTT existentes | Compatibilidade de protocolo (ActiveMQ, RabbitMQ) para migração legada |

### Serviços de Streaming

Esses serviços são geralmente usados para workloads de streaming.

| Serviço | Melhor para | Diferenciador-chave |
|---|---|---|
| **Amazon Kinesis Data Streams** | Ingestão em tempo real com consumidores AWS-nativos | Modo on-demand Advantage (scaling instantâneo, sem gestão de shard), retenção 1–365 dias |
| **Amazon Data Firehose** | Entrega zero-admin para storage/analytics | Auto-escala, faz buffer, batch e entrega a destinos |
| **Amazon Managed Service for Apache Flink** | Processamento de stream complexo (joins, windows, state) | Runtime Apache Flink completo — SQL, Java, Python APIs para computação stateful |
| **Amazon MSK** | Workloads Kafka-nativos, compatibilidade de ecossistema | API Apache Kafka, Express brokers (3x throughput, 20x scaling mais rápido vs. Standard brokers), amplo ecossistema de conectores |

## Comunicação com cliente (Application-to-Person)

Os serviços acima movem dados aplicação-para-aplicação, entre componentes da
mesma aplicação. Um grupo separado de serviços AWS é aplicação-para-pessoa
(A2P): entrega mensagens a — ou recebe de — destinatários fora da aplicação,
como clientes e assinantes. Os dois grupos não são intercambiáveis.

| Canal | Serviço | Skill |
|---|---|---|
| E-mail | **Amazon SES** | `amazon-ses` |
| WhatsApp | **AWS End User Messaging Social** | `aws-social-messaging` |
| SMS, MMS, RCS, voice | **AWS End User Messaging SMS** | Nenhuma |
| Mobile push | **AWS End User Messaging Push** | Nenhuma |

Responda dois tipos de pergunta diretamente desta seção: a qual grupo um
workload pertence, e qual serviço possui um canal. Para qualquer outra pergunta
de comunicação com cliente — configurar um canal, enviar por ele ou
troubleshoot de entrega — não responda desta skill: carregue a skill nomeada na
tabela e responda a partir dela.

Para carregá-la, use `aws___retrieve_skill(skill_name="<skill>")` com o nome
exato da tabela quando o AWS MCP server estiver disponível, ou leia o documento
da skill do Agent Toolkit em `skills/<skill>/SKILL.md`. Onde a tabela diz
Nenhuma, ou a skill nomeada não puder ser carregada, diga isso, então responda
usando as ferramentas de documentação (`aws___search_documentation`,
`aws___read_documentation`) se disponíveis, ou a documentação AWS do serviço
nomeado caso contrário.

## Armadilhas comuns de integração

- **Atributos de sistema vs. usuário em SQS:** Atributos como `AWSTraceHeader`
  (setado por X-Ray / EventBridge / Pipes ao enviar para uma DLQ SQS) e
  `SenderId`, `SentTimestamp` são atributos de *sistema* SQS, NÃO atributos de
  mensagem do usuário. Eles nunca são retornados por default de
  `ReceiveMessage` — solicite-os explicitamente via `AttributeNames=[...]` (ou
  `MessageSystemAttributeNames`), separado de `MessageAttributeNames` que busca
  atributos do usuário. Isso importa para DLQs, onde o trace header viaja no
  atributo de sistema e o slot de atributos-do-usuário carrega os metadados de
  falha do serviço (ex. `RULE_ARN`, `ERROR_CODE` do EventBridge).

- **SNS → Firehose → S3 separador de registro:** Para assinaturas SNS usando o
  protocolo `firehose` que aterrissam em S3, registros já são newline-delimited
  por default (NDJSON). NÃO ligue o `AppendDelimiterToRecord` do Firehose — o
  SNS emite o newline ele mesmo, e habilitar o processador produz double
  newlines.

- **DLQ de alvo de regra EventBridge + DLQ de assinatura SNS ambos precisam de
  política de fila DLQ.** Anexar a DLQ sozinho não basta — a DLQ descarta
  mensagens em silêncio até sua política de fila permitir o service principal.
  EventBridge: `PutTargets` com `DeadLetterConfig.Arn=<DLQ>`, mais política SQS
  `Allow sqs:SendMessage` para `Service: events.amazonaws.com` com
  `aws:SourceArn` = o ARN da regra. SNS: `SetSubscriptionAttributes`
  `RedrivePolicy={"deadLetterTargetArn":"<DLQ>"}`, mais política SQS permitindo
  `Service: sns.amazonaws.com` escopada pelo ARN do tópico.

- **Defaults de produção SQS: long polling + encriptação gerenciada pelo
  cliente.** Filas novas default para short-poll
  (`ReceiveMessageWaitTimeSeconds=0`) e SSE-SQS (chave AWS-owned). Para
  produção, `SetQueueAttributes` com `ReceiveMessageWaitTimeSeconds=20` (long
  polling) e `KmsMasterKeyId=<id/ARN de chave gerenciada pelo cliente>` em vez
  de deixar `alias/aws/sqs`.

- **Credenciais de broker e Kafka pertencem ao Secrets Manager, não a strings
  de conexão.** Não hardcode usernames, senhas ou credenciais SASL/SCRAM em
  config de aplicação, env vars, arquivos JAAS ou IaC. Para Amazon MQ
  (ActiveMQ/RabbitMQ) armazene usuários de broker como secrets e busque no
  startup; event source mappings Lambda para Amazon MQ exigem que as
  credenciais do broker sejam fornecidas como ARN de secret do Secrets Manager
  (`BASIC_AUTH`), não inline. Para MSK SASL/SCRAM o secret não é opcional: deve
  ser nomeado com o prefixo `AmazonMSK_` e encriptado com uma chave KMS
  **gerenciada pelo cliente** (secrets criados com a chave default
  `aws/secretsmanager` não podem ser associados a um cluster), então anexados via
  `BatchAssociateScramSecret`. Event source mappings Lambda para MSK
  (SASL/SCRAM ou mTLS) e Kafka self-managed também referenciam um ARN de secret
  do Secrets Manager em vez de credenciais inline. Habilite rotação e escope o
  read access IAM (`secretsmanager:GetSecretValue`) apenas à role consumidora.
  Veja AWS Well-Architected [SEC02-BP03 Store and use secrets
  securely](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_identities_secrets.html).

- **Políticas de recurso de service-principal precisam de condições
  `aws:SourceArn` / `aws:SourceAccount`.** Quando uma política de fila ou
  tópico concede a um service principal como `events.amazonaws.com`,
  `sns.amazonaws.com` ou `s3.amazonaws.com` permissão para `sqs:SendMessage` ou
  `sns:Publish`, omitir condições de source abre um buraco de confused-deputy —
  qualquer regra, tópico ou bucket em qualquer conta AWS pode dirigir escritas.
  Escope cada statement com `aws:SourceArn` (o ARN específico de
  regra/tópico/bucket/pipe; use `ArnLike` com `*` quando o ARN não for totalmente
  conhecido) e `aws:SourceAccount` (seu ID de conta). Para notificações de
  evento S3 ambas as chaves são necessárias porque ARNs de bucket S3 não carregam
  o ID da conta, então `aws:SourceArn` sozinho não restringe a conta. O mesmo
  padrão se aplica a políticas de trust de roles IAM usadas por regras
  EventBridge e EventBridge Pipes (principal `events.amazonaws.com` /
  `pipes.amazonaws.com`, `aws:SourceArn` = o ARN da regra ou pipe) — não apenas
  o caso de DLQ chamado acima. Veja o IAM User Guide sobre [The confused deputy
  problem](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html).

## Referência rápida

| Padrão | Serviço típico | Quando |
|---|---|---|
| Mensageria comando/tarefa | SQS | Descouplar, buffer bursty, consumidores competidores |
| Mensageria pub/sub fan-out | SNS | Notificação a múltiplos assinantes |
| Roteamento de eventos cross-account/SaaS | EventBridge | Filtragem por conteúdo, schema registry |
| Migração legada JMS/AMQP | Amazon MQ | Compatibilidade de protocolo |
| Streaming ingestão AWS-nativo | Kinesis Data Streams | Retenção 1–365 dias, on-demand |
| Streaming entrega zero-admin | Data Firehose | Buffer/batch/entrega a destinos |
| Streaming processamento stateful | Managed Service for Apache Flink | Joins, windows, SQL/Java/Python |
| Streaming Kafka-nativo | MSK | Ecossistema Kafka, Express brokers |
| Comunicação com cliente (e-mail) | SES | Skill `amazon-ses` |

Fronteira com orquestração: pipelines de orquestração de workflows (Airflow,
Step Functions) são cobertos por `design-airflow-pipelines` e
`design-step-functions-orchestration`; esta skill trata o transporte de
mensagens/eventos entre produtores e consumidores, não o agendamento de tarefas.

## Quando NÃO usar

- **Perguntas detalhadas de MSK ou Managed Service for Apache Flink:** prefira
  skills específicas de serviço ou documentação AWS.
- **Comunicação com cliente (e-mail, SMS, WhatsApp, push):** esta skill apenas
  identifica o canal e roteia; não configura nem envia. Use a skill nomeada na
  tabela de Comunicação com cliente.
- **Orquestração de workflows e agendamento de tarefas:** use
  `design-airflow-pipelines` ou `design-step-functions-orchestration`.
- **Configurações recomendadas específicas (alarmes CloudWatch, thresholds):**
  busque skills específicas de serviço ou docs em vez de boas práticas gerais
  daqui.

## Red flags

- Habilitar `AppendDelimiterToRecord` no Firehose para assinatura SNS → Firehose
  → S3 — produz double newlines (o SNS já emite o newline).
- Anexar uma DLQ a alvo de regra EventBridge ou assinatura SNS sem a política de
  fila permitindo o service principal — mensagens descartadas em silêncio.
- Deixar fila SQS de produção em short-poll e SSE-SQS com chave AWS-owned em
  vez de long polling e chave gerenciada pelo cliente.
- Hardcode de credenciais de broker/Kafka em config, env vars ou IaC em vez de
  Secrets Manager.
- Omitir `aws:SourceArn`/`aws:SourceAccount` em políticas de recurso que
  concedem a service principals — buraco de confused-deputy.
- Tratar `AWSTraceHeader`, `SenderId`, `SentTimestamp` como atributos de
  mensagem do usuário — são atributos de sistema, solicitados via
  `AttributeNames`, não `MessageAttributeNames`.
- Adivinhar números de versão, limites ou detalhes comportamentais em vez de
  buscar skill ou doc específica.

## Não faz

Esta skill é procedimento operacional que pode mutar infraestrutura AWS ao
vivo. Não executa comandos de escrita sem confirmação explícita do operador. Não
despacha como subagente.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-messaging-and-streaming`,
commit `10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a
fonte autoritativa dos padrões de mensageria/streaming, da tabela de serviços e
das armadilhas de integração. Esta é uma adaptação ao contrato SparkForge
(PT-BR, fronteira de manutenção, não-despachável) e **pode desatualizar** quando
a AWS atualizar o serviço. Antes de reproduzir comando de escrita, confira o
upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a
região e o serviço; nenhum número sem `fact_id` (aqui, fact vem do artefato de
API ou doc, não de inspeção); `validate_output` antes de apresentar; manutenção
destrutiva você **não executa** — recomende, e a confirmação de escopo **sobe a
quem pode ser perguntado**: o operador na sessão, ou o agente pai que despachou.
