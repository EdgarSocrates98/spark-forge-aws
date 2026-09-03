---
name: aws-storage
description: Use quando precisar escolher, comparar ou operar servicos de armazenamento AWS — S3 (General Purpose, Express One Zone, Tables, Vectors, Files), EFS, FSx (Lustre, ONTAP, OpenZFS, Windows), EBS, DataSync, Transfer Family, Storage Gateway, AWS Backup. Cobre selecao de servico por workload, custo, performance, configuracao, seguranca, troubleshooting e migracao de dados. Aplica quando alguem pergunta onde armazenar ou arquivar dados, qual servico de storage escolher, como comparar dois, como migrar de on-premises ou entre servicos AWS, como proteger/replicar/recuperar dados, como otimizar custo de storage, onde deployar NFS/SMB/POSIX compartilhado, onde guardar vector embeddings ou dados tabulares, ou como um servico de storage AWS funciona. NAO use para motores de consulta SQL (Athena, Spark, Redshift, EMR), ETL (Glue), streaming (Kafka, MSK, Kinesis) ou bancos gerenciados (RDS, Aurora, DynamoDB).
---

# AWS Storage

Dominio de especialidade para escolher entre servicos de armazenamento AWS, selecionar
storage classes, otimizar custo e rotear para recursos de operacao. Cobre armazenamento
de objeto (S3 General Purpose e suas storage classes, S3 Express One Zone em directory
buckets, S3 Tables, S3 Vectors), armazenamento de arquivo (EFS, S3 Files, FSx for Lustre,
FSx for NetApp ONTAP, FSx for OpenZFS, FSx for Windows File Server) e armazenamento em
bloco (EBS e EC2 instance store), mais os servicos de movimentacao e protecao de dados
(DataSync, Storage Gateway, Transfer Family, AWS Backup). Nao aconselha sobre bancos de
dados nem motores de consulta analitica. Funciona com ou sem o AWS MCP server; quando
disponivel, o AWS MCP server e recomendado para verificar especificacoes e precos
correntes, e toda a orientacao tambem funciona com o AWS CLI padrao.

## Como tratar a consulta do usuario

Quando esta skill e acionada, classifique o pedido e siga o caminho apropriado.

### Regras globais

Aplicam-se a toda resposta independentemente do caminho:

1. **Verifique numeros correntes.** Quando o AWS MCP server estiver disponivel, use
   `search_documentation` e `read_documentation` para checar antes de citar valores
   especificos. Ao citar custos, inclua link para a pagina de precos relevante. Ao citar
   metricas de performance, inclua link para a pagina do produto. Caso contrario,
   verifique contra paginas de documentacao AWS linkadas ou use o AWS CLI para confirmar
   valores correntes. Onde um arquivo de referencia direciona a documentacao para um
   valor corrente, voce DEVE recuperar aquele valor da pagina linkada antes de responder.
   Nao substitua por numero lembrado nem ofereca aproximacao. Se a recuperacao nao for
   possivel no ambiente atual, nomeie o valor que nao pôde verificar em vez de citar de
   memoria.

2. **Recupere o arquivo de referencia relevante** antes de responder perguntas sobre um
   servico. Especificacoes, limites e capacidades dos servicos de storage AWS mudam
   frequentemente. NAO responda de memoria. Recupere a orientacao de troubleshooting e
   "gotchas" dos arquivos de referencia e inclua na resposta. Justifique recomendacoes
   por aderencia ao workload, nao mencionando que um arquivo "explicitamente" cita um
   workload para um servico.

3. **Inclua implicacoes de custo** ao recomendar servicos ou abordagens. Nao espere o
   usuario perguntar. Nao compare servicos apenas por custos de armazenamento; taxas por
   objeto como cobrancas de metadado podem mudar materialmente o TCO. Para analise de
   custo profunda, monitoramento ou otimizacao alem de selecao de storage, roteie para a
   skill `aws-billing-and-cost-management`.

4. **Tenha clareza sobre a necessidade do usuario** ao recomendar. Caso a consulta
   determine a categoria de storage e os servicos relevantes, recupere informacao e
   recomende diretamente. Caso a consulta nao esteja totalmente especificada, mencione as
   suposicoes e limitacoes da recomendacao e inclua perguntas adicionais que confirmariam
   ou mudariam a resposta. Faca perguntas de escopo apenas quando a consulta nao permite
   determinar a categoria de storage.

---

### Passo 1: Classificar a intencao

Determine o que o usuario precisa:

| Intencao | Exemplos | Significado |
| --- | --- | --- |
| SELECT | "O que devo usar?", "Qual servico?", "Comparar A vs B", "Quero migrar X para AWS" | Usuario precisa de ajuda para escolher |
| INVESTIGATE | "Como configuro X?", "Por que Y falha?", "Quais os limites de Z?" | Usuario sabe o servico e precisa de ajuda operacional |

---

### Passo 2a: Caminho SELECT

O usuario precisa de ajuda para escolher. Use os fatores de decisao abaixo, perguntando
para preencher lacunas que mudariam a escolha.

**Fatores de decisao:**

| # | Fator | Entender |
| --- | --- | --- |
| 1 | Contexto do workload | Novo workload ou migracao? Se migrando, sistema origem (NetApp, ZFS, Windows, Lustre, GPFS)? Que aplicacao acessa? Como acessa (API, protocolo de arquivo, bloco)? Qual OS? Qual modelo de dado (estruturado, vetores, objetos, filesystem)? |
| 2 | Capacidade e padroes de acesso | Quanto dado, quantos arquivos/objetos, tamanhos tipicos? Sequencial ou aleatorio? Read-heavy, write-heavy ou misto? |
| 3 | Requisitos de performance | Latencia, throughput ou IOPS especificos? Concorrencia esperada? |
| 4 | Durabilidade e protecao | RTO? RPO? Retencao por compliance? Resiliencia cross-region? Imutabilidade? |
| 5 | Disponibilidade | Multi-AZ ou Single-AZ aceitavel? Colocado com compute especifico? |

Use a tabela de Opcoes de Storage para identificar servicos candidatos. Recupere os
arquivos de referencia para cada candidato. Recomende servico(s) especifico(s) com:

1. Justificativa clara vinculada aos requisitos declarados.
2. Alternativas quando a escolha e proxima ou depende de informacao nao especificada,
   explicando o tradeoff.

---

### Passo 2b: Caminho INVESTIGATE

O usuario ja sabe o servico e precisa de ajuda operacional.

1. Classifique o dominio da pergunta:

| Dominio | Exemplos | Esclarecer |
| --- | --- | --- |
| Migracao e transferencia | "Mover dados para AWS", "Configurar DataSync" | Sistema origem, destino, volume, caminho de rede |
| Protecao e resiliencia | "Configurar backup", "Replicacao cross-region", "DR" | Cenario de falha, RTO/RPO, escopo de replicacao |
| Custo e lifecycle | "Reduzir conta de storage", "Right-size volumes" | Servico/config corrente, frequencia de acesso, crescimento |
| Performance | "Reads lentos", "Gargalo de throughput", "Preciso de IOPS" | Observado vs requerido, padrao de acesso, suspeito |
| Seguranca e compliance | "Encriptar em repouso", "Restringir acesso ao bucket", "HIPAA" | Objetivo, framework de compliance |
| Configuracao | "Montar EFS no EKS", "Configurar replicacao" | Ambiente cliente, operacao alvo |
| Troubleshooting | "AccessDenied", "Mount travando", "Pico de latencia" | Erro/sintoma, o que mudou, tentativas |

2. Faca perguntas de escopo para informacao ausente que mudaria a orientacao. Onde o
   detalhe faltante nao mudaria a orientacao, responda sob suposicao declarada.
3. Recupere os arquivos de referencia para todos os servicos candidatos.
4. Forneca orientacao especifica e acionavel, com gotchas e links de documentacao.
5. Ao responder Configuracao ou Seguranca, recomende habilitar access logging, CloudTrail
   data events e CloudWatch metrics para observabilidade.

## Opcoes de armazenamento

### Armazenamento de objeto

| Servico | Caracteristicas | Workloads comuns |
| --- | --- | --- |
| S3 General Purpose | Escala virtualmente ilimitada, multiplas storage classes (frequent-access a archive), lifecycle rules. Disponibilidade regional. API REST/HTTP. | Data lakes, backup/arquivo, ML, midia, logs, websites, arquivos de compliance |
| S3 Express One Zone | Directory buckets single-AZ, latencia single-digit ms. | ML em escala, Spark/EMR shuffle, checkpoints, ETL intermediario, analytics hot, Kafka tiered storage |
| S3 Tables | Tabelas Apache Iceberg gerenciadas em S3 com compacao automatica. Disponibilidade regional. | Tabelas de data lake, dados analiticos estruturados, saida de ETL, streaming para SQL |
| S3 Vectors | Armazenamento e busca de similaridade de vetores em S3. | RAG, busca semantica, recomendacao, deduplicacao de vetores, deteccao de anomalia/fraude, memoria de agentes |
| S3 Metadata | Metadado de objeto consultavel em tabelas Iceberg read-only. | Analytics de negocio, catalogacao, governanca, otimizacao de storage |

### Armazenamento de arquivo

Ao nomear um servico, sempre especifique o nome completo (FSx for Lustre, FSx for Windows
File Server, FSx for NetApp ONTAP, FSx for OpenZFS). EFS e S3 Files podem ser montados por
Lambda e Fargate. FSx for NetApp ONTAP e FSx for OpenZFS sao acessiveis via S3 Access
Points for FSx (expoe dados de arquivo pela API S3 sem copiar).

| Servico | Caracteristicas | Workloads comuns |
| --- | --- | --- |
| EFS | NFS elastico serverless, EFS Standard/IA/Archive, Lifecycle Management. Multi-AZ por default. Montavel por Lambda, Fargate, EC2, ECS, EKS. | Containers, apps Linux cloud-native, serverless persistente, analytics/ML, processamento de midia, home dirs compartilhados |
| FSx for Lustre | Filesystem paralelo, altissimo throughput agregado. Classes SSD e Intelligent-Tiering. | ML/GPU em escala, HPC, genoma, modelagem financeira, renderizacao, EDA back-end |
| FSx for OpenZFS | ZFS data management (clones instantaneos, snapshots, compressao, replicacao). Baixa latencia, alto IOPS. Single-AZ e Multi-AZ. Acesso S3-API. | Bancos em EC2, dev/test com clones rapidos, migracao ZFS/NFS, EDA front-end, modelagem financeira, midia |
| FSx for NetApp ONTAP | ONTAP completo (SnapMirror, FlexClone, dedup, compressao, SnapLock WORM, QoS). Multi-protocolo: NFS, SMB, iSCSI, NVMe-over-TCP, S3-API. Single-AZ e Multi-AZ. | NAS enterprise, multi-protocolo, bancos em EC2 (SAP HANA, Oracle, SQL Server), VMware, EDA front-end, hibrido/DR |
| FSx for Windows File Server | SMB gerenciado em Windows Server com AD (Kerberos, NTFS ACLs), DFS, shadow copies, FSRM. Acessivel de Linux/macOS. Single-AZ e Multi-AZ. | File shares Windows, .NET, Microsoft SQL Server, migracao de Windows Server |

### Armazenamento em bloco

| Servico | Caracteristicas | Workloads comuns |
| --- | --- | --- |
| EBS | Disco virtual de alta performance anexado a EC2. Duravel, redimensionavel, SSD ou HDD. Snapshots para backup. AZ-scoped. Provisao performance independente de capacidade em gp3. | Bancos, aplicacoes transacionais, boot volumes, dev/test, batch sequencial, scans de data warehouse |
| EC2 Instance Store | SSD fisico local no host, latencia mais baixa e throughput mais alto. Efemero: dado perdido se a instancia parar. | Scratch temporario, caches, buffers descartaveis |

---

## Sobreposicao entre servicos

| Recurso | O que habilita | O que e | Fontes |
| --- | --- | --- | --- |
| S3 Files | Dados S3 acessiveis a apps baseadas em arquivo | NFS gerenciado sobre bucket S3, infraestrutura EFS. Dado fica em S3. | `references/s3-files-knowledge.md`, `references/efs-knowledge.md` |
| S3 Access Points for FSx | Dados FSx acessiveis a apps S3 | Expoe FSx ONTAP/OpenZFS pela API S3 sem copiar. | `references/fsx-ontap-knowledge.md`, `references/fsx-openzfs-knowledge.md` |

---

## Seguranca

Seguranca na AWS e responsabilidade compartilhada. Voce DEVE incluir orientacao de
seguranca ao recomendar ou configurar recursos de storage. Sempre recomende encriptacao
em repouso e em transito. Onde encriptacao em repouso e opcional ou nao default, avise
explicitamente para habilitar na criacao — frequentemente imutavel depois. Recomende IAM
policies com least-privilege. Recomende condition keys (`aws:SourceArn`, `aws:SourceAccount`,
`aws:SourceVpc`) em resource policies para prevenir confused deputy. Recomende encriptar
destinos de log (KMS para CloudTrail e CloudWatch Logs, SSE para buckets de access log,
KMS para topicos SNS). Restrinja inbound de security group ao minimo aplicavel. Controles
de seguranca especificos por servico estao na linha Security da tabela Service Information
de cada referencia — leia antes de aconselhar sobre aquele servico.

## Referência rápida

| Topico | Referencia |
| --- | --- |
| S3 (General Purpose) | `references/s3-general-purpose-knowledge.md` |
| S3 Metadata | `references/s3-general-purpose-knowledge.md` |
| S3 Tables | `references/s3-tables-knowledge.md` |
| S3 Vectors | `references/s3-vectors-knowledge.md` |
| S3 Express One Zone | `references/s3-express-knowledge.md` |
| S3 Files | `references/s3-files-knowledge.md` |
| Amazon EFS | `references/efs-knowledge.md` |
| FSx for Lustre | `references/fsx-lustre-knowledge.md` |
| FSx for NetApp ONTAP | `references/fsx-ontap-knowledge.md` |
| FSx for OpenZFS | `references/fsx-openzfs-knowledge.md` |
| FSx for Windows File Server | `references/fsx-windows-knowledge.md` |
| Amazon EBS | `references/ebs-knowledge.md` |
| Data Movement e Protection (DataSync, Transfer Family, Storage Gateway, AWS Backup) | `references/data-movement-and-protection-knowledge.md` |

### Skills SparkForge relacionadas

| Topico | Skill |
| --- | --- |
| Desenhar data lake em S3 | `design-s3-data-lake` |
| Provisionar tabela S3 Tables | `provision-s3-tables-table` |
| Hardening de bucket S3 | `harden-s3-bucket` |
| Otimizar layout Parquet | `optimize-parquet-layout` |

## Quando NÃO usar

- **Motores de consulta SQL** (Athena, Spark, Redshift, EMR): nao sao armazenamento —
  sao compute sobre dados. Para otimizar Athena, use `optimize-athena-queries`.
- **ETL** (Glue): use as skills de performance Glue (`glue-incremental-performance-architect`,
  `tune-glue-job`).
- **Streaming** (Kafka, MSK, Kinesis): roteie para `aws-messaging-and-streaming`.
- **Bancos gerenciados** (RDS, Aurora, DynamoDB): roteie para `aws-database`.
- **Hardening de bucket S3 especifico**: use `harden-s3-bucket` — ele tem workflows
  dedicados de auditoria, remediation e encriptacao.
- **Provisionar S3 Tables**: use `provision-s3-tables-table` — o produto e `s3tables:*`,
  nao `s3:*`, e o procedimento e outro.
- **Desenho de data lake**: use `design-s3-data-lake` para arquitetura de data lake em S3.
- **Otimizar layout Parquet**: use `optimize-parquet-layout` para decisao de row group,
  partitioning e compressao.

## Red flags

- Citar custo ou metrica de performance de memoria sem verificar contra documentacao
  corrente — especificacoes de storage AWS mudam frequentemente.
- Recomendar S3 General Purpose quando o workload precisa de latencia single-digit ms
  sem checar S3 Express One Zone.
- Comparar servicos apenas por custo de armazenamento, ignorando taxas por objeto
  (metadado, requests, lifecycle transitions) que mudam o TCO.
- Configurar encriptacao em repouso depois da criacao do recurso — frequentemente
  imutavel; habilite na criacao.
- Nao mencionar S3 Access Points for FSx quando o usuario precisa ler dados FSx de
  consumers S3-native ou servicos serverless.
- Tratar `ObjectLockConfigurationNotFoundError` como erro — e NOT CONFIGURED, nao falha.
- Recomendar FSx sem especificar o nome completo do servico (Lustre vs ONTAP vs OpenZFS
  vs Windows) — sao produtos diferentes com capacidades distintas.
- Nao recuperar o arquivo de referencia do servico antes de responder — gotchas e
  limites especificos ficam invisiveis.

## Não faz

Esta skill e procedimento operacional que pode mutar infraestrutura AWS ao vivo. Nao
executa comandos de escrita sem confirmacao explicita do operador. Nao despacha como
subagente.

Comandos de escrita — `put-bucket-policy`, `put-bucket-encryption`, `put-bucket-lifecycle`,
`create-file-system`, `create-volume`, `create-backup-plan` — voce **nao executa**.
Recomende o comando, exiba o que ele faz, faca back up da configuracao existente, e **suba
a decisao** a quem pode ser perguntado — o operador na sessao, ou o agente pai que
despachou. Dentro de um subagente, obter essa confirmacao e **impossivel**
(`ask_user_question` e sempre negado a subagente), e por isso esta skill **nao despacha**.

Manutencao destrutiva — `delete-bucket`, `delete-file-system`, `delete-volume`, remocao
de versioning — voce **nao executa**. Recomende, e a confirmacao de escopo e retencao
sobe a quem tem a pergunta disponivel.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-storage`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream e a fonte autoritativa
dos arquivos de referencia (`references/s3-general-purpose-knowledge.md`,
`references/efs-knowledge.md`, `references/fsx-*.md`, `references/ebs-knowledge.md`,
`references/data-movement-and-protection-knowledge.md`, etc.) e do procedimento de
classificacao SELECT/INVESTIGATE. Esta e uma adaptacao ao contrato SparkForge (PT-BR,
fronteira de manutencao, nao-despachavel) e **pode desatualizar** quando a AWS atualizar
especificacoes ou procedimentos. Antes de reproduzir comando de escrita, confira o
upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a regiao e o
servico; nenhum numero sem verificacao contra documentacao corrente ou arquivo de
referencia; manutencao destrutiva voce **nao executa** — recomende, e a confirmacao de
escopo e retencao **sobe a quem pode ser perguntado**: o operador na sessao, ou o agente
pai que despachou.
