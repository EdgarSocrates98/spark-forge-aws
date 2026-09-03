---
name: harden-s3-bucket
description: Use quando for proteger um bucket S3 — criar bucket novo já hardenado, auditar bucket existente contra controles de segurança, remediar finding de security hub/guardduty, configurar encriptação (SSE-S3 com Bucket Keys, SSE-KMS com chave gerenciada pelo cliente), ou habilitar logging/monitoramento (server access logging, CloudTrail data events, GuardDuty, Config rules). Use também quando a pergunta for "esse bucket está seguro", "por que o finding de bucket público", "qual a diferença entre SSE-S3 e SSE-KMS aqui" ou "como bloqueio SSE-C", mesmo sem citar "harden". NÃO use para operações de dado S3 (upload/download/list), setup de S3 Tables (use `provision-s3-tables-table`), descoberta de assets existentes, ou hardening de serviços que não S3. Se você está prestes a rodar `put-bucket-policy` sem back up da policy atual, pare — `put-bucket-policy` substitui a policy inteira e descarta statements existentes em silêncio.
---

# Hardening de bucket S3

Camadas de controle de segurança S3 em cinco workflows: proteger bucket novo,
auditar bucket existente, remediar finding, configurar encriptação, habilitar
monitoramento. Segue as boas práticas do AWS Well-Architected Security Pillar.

Esta skill é **procedimento operacional que muta infraestrutura AWS ao vivo**
(`put-bucket-policy`, `put-bucket-encryption`, `create-detector`). Não é gatilho
do motor SparkForge — o motor é offline e determinístico. Por isso a fronteira
`## Não faz` é estrita e o despacho é recusado.

## Regra de segurança do put-bucket-policy

Aplica-se a **todo** workflow que chame `put-bucket-policy`:

- Recupere a policy existente **antes**: `aws s3api get-bucket-policy --bucket <nome>`.
- Se existir, faça back up: `aws s3api get-bucket-policy --bucket <nome> --output text > backup-policy-$(date +%s).json`.
- Se `NoSuchBucketPolicy`, prossiga com policy nova — sem backup.
- **Mescle** os statements novos no array `Statement` existente. Não substitua.
- Valide o JSON mesclado antes de aplicar: `echo '<policy>' | python3 -m json.tool`.
- Exiba o comando `put-bucket-policy` completo e aguarde confirmação.

## Procedimento

### 0. Verifique dependências

- Confirme credenciais: `aws sts get-caller-identity`.
- Confirme nome do bucket e região **antes** de qualquer escrita.
- Para validar permissões antes de escrita: `aws iam simulate-principal-policy`.

### 1. Classifique o pedido

| Intenção | Workflow |
|---|---|
| Proteger bucket novo | A |
| Auditar bucket existente | B |
| Corrigir finding específico | C |
| Configurar encriptação | D |
| Habilitar logging/monitoramento | E |

### 2. Workflow A — Proteger bucket novo

Passos em ordem, não pule:

1. Crie com `--bucket-namespace account-regional` (obrigatório, não opcional):
   ```
   aws s3api create-bucket --bucket <nome> --bucket-namespace account-regional --region <regiao>
   ```
2. Habilite versioning.
3. Habilite encriptação (SSE-S3 + Bucket Keys + bloquear SSE-C).
4. Habilite logging (pergunte qual opção — condicional).
5. Aplique bucket policy com `DenyInsecureTransport` (negar `s3:*` quando
   `aws:SecureTransport` é `false`) — obrigatório, não opcional.
6. Habilite ABAC.

**Não** altere Block Public Access — S3 já liga por default em bucket novo.
**Não** altere ACL ownership controls — S3 já desabilita ACLs
(`BucketOwnerEnforced`) por default.

### 3. Workflow B — Auditar bucket existente

Rode **todos** os comandos de leitura antes de reportar. **Não** execute
escrita durante auditoria. Reporte cada controle como PASS / FAIL / NOT
CONFIGURED com severidade. Para logging: PASS se **ou** server access logging
**ou** CloudTrail data events estiver ligado; NOT CONFIGURED só se nenhum.

### 4. Workflow C — Remediar finding

Identifique o tipo de issue antes de aplicar fix. Siga a regra de
`put-bucket-policy` se tocar policy. Após o fix, **re-rode** o check de
auditoria correspondente para confirmar a resolução.

### 5. Workflow D — Configurar encriptação

- Default: SSE-S3 com S3 Bucket Keys e SSE-C bloqueado, **a menos que** o
  operador peça KMS explicitamente.
- SSE-KMS: use **chave gerenciada pelo cliente**, **nunca** a AWS managed
  `aws/s3`. Especifique a chave por **ARN completo**, não por alias.
- Inclua `BucketKeyEnabled: true` e `BlockedEncryptionTypes: [SSE-C]` em toda
  configuração.
- A API S3 aceita `aws/s3` e alias sem erro — são **constraints do agente**, e
  você deve verificá-las com `get-bucket-encryption` depois de aplicar.

### 6. Workflow E — Habilitar monitoramento

- Verifique se detector GuardDuty já existe antes de criar
  (`aws guardduty list-detectors`).
- Para CloudTrail, use a **home region do trail**, não a região do bucket.
  Encontre com `aws cloudtrail describe-trails --query 'trailList[*].[Name,HomeRegion]'`.
- Habilite os quatro Config rules core recomendados.

## Referência rápida

| Workflow | Intenção | Comando-chave |
|---|---|---|
| A | Proteger bucket novo | `create-bucket --bucket-namespace account-regional` + `put-bucket-policy` (DenyInsecureTransport) |
| B | Auditar bucket existente | `get-bucket-*` (só leitura, reportar PASS/FAIL/NOT CONFIGURED) |
| C | Remediar finding | `put-bucket-policy` / `put-bucket-encryption` (após back up) |
| D | Configurar encriptação | `put-bucket-encryption` (SSE-S3+Bucket Keys ou SSE-KMS com CMK por ARN) |
| E | Habilitar monitoramento | `create-detector` (GuardDuty), CloudTrail data events, Config rules |

Regra de segurança do `put-bucket-policy`: `get` antes, back up se existir, mesclar statements, validar JSON, exibir e aguardar confirmação.

## Quando NÃO usar

- **Operações de dado S3** (upload, download, list, copy): não é hardening.
- **S3 Tables**: use `provision-s3-tables-table` — o produto é `s3tables:*`, não
  `s3:*`, e o procedimento é outro.
- **Descoberta de assets existentes**: a skill AWS `finding-data-lake-assets`
  cobre isso; aqui você já sabe qual bucket.
- **Hardening de serviços que não S3**: IAM, KMS, VPC endpoints têm suas
  próprias referências.
- **Revisar Terraform de plataforma de dados**: `review-terraform-data-platform`
  cobre IaC; esta skill é procedimento contra a API ao vivo.

## Red flags

- Rodar `put-bucket-policy` sem `get-bucket-policy` antes — substitui a policy
  inteira e descarta statements existentes em silêncio.
- Usar a AWS managed key `aws/s3` para SSE-KMS — a API aceita, mas é o default
  menos controlado. Use chave gerenciada pelo cliente por ARN completo.
- Especificar KMS por alias em vez de ARN — a API aceita, mas o agente não deve.
- Rodar comandos de escrita durante uma auditoria (Workflow B) — auditoria é
  só leitura.
- Criar detector GuardDuty sem `list-detectors` antes — `BadRequestException:
  detector already exists` é o sintoma.
- Usar a região do bucket para comandos CloudTrail em vez da home region do
  trail — a mudança não toma efeito e nada acusa.
- Tratar `ObjectLockConfigurationNotFoundError` como falha — é NOT CONFIGURED,
  não erro.

## Não faz

Esta skill **não executa** `put-bucket-policy`, `put-bucket-encryption`,
`create-detector` ou qualquer comando de escrita sem confirmação explícita do
operador para cada comando. Ela **recomenda** o comando, exibe o que ele faz,
faz back up da policy existente, e **sobe a decisão** a quem pode ser
perguntado — o operador na sessão, ou o agente pai que despachou. Dentro de um
subagente, obter essa confirmação é **impossível** (`ask_user_question` é
sempre negado a subagente), e por isso esta skill **não despacha**.

Manutenção destrutiva — `delete-bucket`, `delete-bucket-policy`, remoção de
versioning — você **não executa**. Recomende, e a confirmação de escopo e
retenção sobe a quem tem a pergunta disponível.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill
`specialized-skills/storage-skills/securing-s3-buckets`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa dos cinco workflows e dos `references/` (iam-permissions,
audit-checklist, encryption, remediation, workflows) — esta é uma adaptação ao
contrato SparkForge (PT-BR, fronteira de manutenção, não-despachável), e **pode
desatualizar** quando a AWS atualizar o procedimento. Antes de reproduzir
comando de escrita, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme o
runtime e a região; nenhum número sem `fact_id` (aqui, fact vem do artefato de
`get-bucket-*`, não de inspeção); `validate_output` antes de apresentar;
manutenção destrutiva você **não executa** — recomende, e a confirmação de
escopo e retenção **sobe a quem pode ser perguntado**: o operador na sessão,
ou o agente pai que despachou.
