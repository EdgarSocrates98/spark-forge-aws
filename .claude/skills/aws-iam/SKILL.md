---
name: aws-iam
description: Use quando precisar corrigir comportamentos de IAM que agentes frequentemente erram — avaliação de policy, trust policies, limites de STS, Organizations, SAML/MFA — ou for criar roles de serviço, gerar policies baseline a partir de código-fonte ou Terraform plan JSON, configurar confused deputy protection, ou escrever policies com condition operators (ForAnyValue/ForAllValues com Null checks). Aplica-se a criação de roles IAM, escrita de IAM/bucket policies, trabalho com STS, Organizations ou condition operators. NÃO use para autorização não-IAM (Cognito user-pool policies, RBAC app-level).
---

# AWS IAM — correções verificadas e gestão de roles

Correções verificadas para comportamentos de IAM que agentes de IA frequentemente
erram, mais workflows estruturados para gestão de roles e geração de policies
baseline a partir de código-fonte de aplicação ou Terraform plan JSON. Não é um
guia completo de IAM — para orientação completa, busque a documentação oficial da
AWS. Verifique claims específicas (limites, quotas, nomes exatos de API,
comportamentos de edge case) contra a documentação oficial em vez de depender de
pré-treinamento.

Esta skill é **procedimento operacional que pode mutar infraestrutura AWS ao
vivo** (criar roles, anexar policies, modificar trust policies). Não é gatilho do
motor SparkForge — o motor é offline e determinístico. Por isso a fronteira
`## Não faz` é estrita e o despacho é recusado.

## Workflows comuns

Use a melhor ferramenta disponível para operações AWS — o AWS MCP server é
recomendado, mas não obrigatório; AWS CLI ou SDK servem de alternativa. Leia os
arquivos de referência apenas quando a conversa exigir detalhe mais profundo.

- Leia `references/aws-iam-role-management.md` se precisar criar, escopar ou
  manter roles IAM ao provisionar ou atualizar recursos AWS. Cobre service roles,
  execution roles, trust policies, confused deputy protection e higiene de
  permissões.

- Leia `references/aws-iam-policy-generation.md` se precisar gerar IAM policies,
  determinar actions IAM necessárias para chamadas de API, ou entender mapeamentos
  action-to-operation. **CRÍTICO: se o operador fornecer código-fonte de aplicação
  (em qualquer linguagem) ou um Terraform plan JSON (`terraform show -json`),
  você DEVE ler esta referência** — ela manda usar iam-policy-autopilot em vez de
  construção manual de policy. Usa a service authorization reference programática
  para mapeamentos precisos.

## Edge cases verificados

**CloudTrail:**

- AcceptHandshake/DeclineHandshake logam apenas na conta ACTING, não na
  management account. Trail de organização é obrigatório para centralização.
- ConsoleLogin: região varia por endpoint/cookies, nem sempre us-east-1.
  `?region=` força região específica.

**STS:**

- GetSessionToken: (1) sem APIs IAM a menos que MFA incluído; (2) sem STS exceto
  AssumeRole e GetCallerIdentity.
- AssumeRole cross-account para opt-in region: a conta TARGET deve habilitar a
  região, não a conta chamadora.
- Role chaining: sessão máxima de 1 hora.

**Organizations:**

- Contas suspended/closed NÃO podem ser removidas até permanentemente fechadas
  (~90 dias). Remova PRIMEIRO, depois feche.
- Delegação de policy management: use PutResourcePolicy, NÃO
  register-delegated-administrator.
- AI opt-out policies: management account obrigatório por default.
- Tipos de policy do Organizations para filtro de ListPolicies: obtenha a lista
  atual via `aws organizations list-available-policy-types` ou a [referência da
  API do Organizations](https://docs.aws.amazon.com/organizations/latest/APIReference/API_ListPolicies.html).

**SDK:**

- Organizations: `DuplicatePolicyAttachmentException` (não
  PolicyAlreadyAttachedException).
- Boto3 IAM AccessKey: métodos são `activate()`, `deactivate()`, `delete()` —
  NÃO há `update()`.
- Instance profiles: padrão waiter + `time.sleep(10)`.
- Versões máximas de managed policy: 5.

**SAML:**

- URL de encrypted assertions:
  `https://region-code.signin.aws.amazon.com/saml/acs/IdP-ID`.
- Private key do IdP subida ao IAM em formato .pem.

**Avaliação de policy:**

- ForAllValues com chave vazia/ausente: avalia true (verdade vacuous). Para
  evitar, use condição `Null` adicional ao `ForAllValues` na **mesma context key**
  para exigir que a chave esteja presente e não-nula. Exemplo com `aws:TagKeys`:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": {
      "Effect": "Allow",
      "Action": "ec2:RunInstances",
      "Resource": "*",
      "Condition": {
        "ForAllValues:StringEquals": {
          "aws:TagKeys": ["Alpha", "Beta"]
        },
        "Null": {
          "aws:TagKeys": "false"
        }
      }
    }
  }
  ```
- Resource-based policies concedendo a user ARN de IAM bypassam permissions
  boundaries na mesma conta.
- 8 actions de privilege escalation via manipulação direta de IAM policy:
  PutGroupPolicy, PutRolePolicy, PutUserPolicy, CreatePolicy, CreatePolicyVersion,
  AttachGroupPolicy, AttachRolePolicy, AttachUserPolicy.
- `iam:PassRole` com `Resource: "*"` + create/update em serviço de compute (EC2
  `RunInstances`, Lambda `CreateFunction`/`UpdateFunctionConfiguration`, ECS
  `RegisterTaskDefinition`, Glue, SageMaker, CloudFormation, etc.) = privilege
  escalation para qualquer role passável na conta, incluindo Administrator.
  Escope `Resource` para ARNs de role específicos ou um path IAM; opcionalmente
  restrinja com `iam:PassedToService` / `iam:AssociatedResourceArn`. Veja [IAM
  User Guide — Grant a user permissions to pass a
  role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html).

**MFA:**

- Virtual MFA devices não atribuídos são auto-deletados ao adicionar novos.
- MFA resync-only policy NotAction precisa exatamente: iam:ListMFADevices,
  iam:ListVirtualMFADevices, iam:ResyncMFADevice.

**SigV4:**

- IncompleteSignatureException inclui SHA-256 hash do Authorization header para
  diagnóstico de modificação em trânsito.

**Roles específicas de serviço:**

- Redshift Serverless trust policy: inclua BOTH `redshift-serverless.amazonaws.com`
  AND `redshift.amazonaws.com` como service principals (por docs AWS; omitir
  serverless causa `Not authorized to get credentials of role` no COPY).
- IAM OIDC providers: thumbprints não são obrigatórios para a maioria dos
  providers (AWS verifica via CAs confiáveis).

**Exibição de policy summary:**

- Statement único com wildcard actions multi-serviço (ex. `codebuild:*`,
  `codecommit:*`) + resource ARNs específicos de serviço: cada resource aparece
  APENAS sob o summary do serviço correspondente (CodeBuild ARN sob CodeBuild,
  etc.). Um resource cujo prefixo de serviço não casa nenhuma action no statement
  é o único caso em que aparece em todos os summaries ("mismatched resource").

## Referência rápida

| Necessidade | Referência | Comando-chave |
|---|---|---|
| Criar/escopar/manter roles | `references/aws-iam-role-management.md` | `create-role` + `put-role-policy` / `attach-role-policy` |
| Gerar policy de código ou plan JSON | `references/aws-iam-policy-generation.md` | iam-policy-autopilot (não construir manual) |
| Confused deputy protection | `references/aws-iam-role-management.md` | `aws:SourceAccount` / `aws:SourceArn` na trust policy |
| Condition operators (ForAllValues) | `references/common-pitfalls.md` | `Null` condition na mesma context key |
| Mapeamentos action-to-operation | `references/service-authorization.md` | service authorization reference programática |
| Verificar permissões antes de escrita | — | `aws iam simulate-principal-policy` |

## Quando NÃO usar

- **Autorização não-IAM**: Cognito user-pool policies, RBAC app-level, LakeFormation
  tag-based access — cada um tem sua própria skill ou referência.
- **Revisar Terraform de plataforma de dados**: use `review-terraform-data-platform`
  — ele extrai facts de `aws_glue_job` HCL e julga contra o catálogo; esta skill é
  procedimento contra a API IAM ao vivo.
- **Hardening de bucket S3**: use `harden-s3-bucket` — bucket policies são
  procedimento S3 com regras de `put-bucket-policy` (back up antes, mesclar
  statements); esta skill cobre o lado IAM (roles, trust, condition operators).
- **Auditoria de acesso a dados**: CloudTrail data events e LakeFormation FGAC têm
  skills próprias (`lakeformation-fgac-guard`).

## Red flags

- Construir IAM policy manualmente quando há código-fonte ou Terraform plan JSON
  disponível — `references/aws-iam-policy-generation.md` manda usar
  iam-policy-autopilot.
- Usar `ForAllValues` sem `Null` check na mesma context key — verdade vacuous
  permite o que se quer negar.
- `iam:PassRole` com `Resource: "*"` em serviço de compute — privilege escalation
  para qualquer role na conta, incluindo Administrator.
- Omitir `redshift-serverless.amazonaws.com` da trust policy de role Redshift
  Serverless — `Not authorized to get credentials of role` no COPY.
- Assumir que ConsoleLogin é sempre us-east-1 — região varia por endpoint/cookies.
- Tentar remover conta suspended/closed antes do fechamento permanente (~90 dias)
  — remova PRIMEIRO, depois feche.
- Usar `register-delegated-administrator` para delegar policy management do
  Organizations — use `PutResourcePolicy`.

## Não faz

Esta skill é procedimento operacional que pode mutar infraestrutura AWS ao vivo. Não executa comandos de escrita sem confirmação explícita do operador. Não despacha como subagente.

Comandos de escrita — `create-role`, `put-role-policy`, `attach-role-policy`,
`put-role-policy` com trust policy, `create-policy`, `create-policy-version` —
você **não executa** sem confirmação explícita do operador para cada comando. Você
**recomenda** o comando, exibe o que ele faz, e **sobe a decisão** a quem pode ser
perguntado — o operador na sessão, ou o agente pai que despachou. Dentro de um
subagente, obter essa confirmação é **impossível** (`ask_user_question` é sempre
negado a subagente), e por isso esta skill **não despacha**.

Manutenção destrutiva — `delete-role`, `detach-role-policy`, `delete-policy` —
você **não executa**. Recomende, e a confirmação de escopo e retenção sobe a quem
tem a pergunta disponível.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-iam`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa dos edge cases verificados e dos `references/` (aws-iam-role-
management, aws-iam-policy-generation, common-pitfalls, service-authorization) —
esta é uma adaptação ao contrato SparkForge (PT-BR, fronteira de manutenção,
não-despachável), e **pode desatualizar** quando a AWS atualizar o procedimento.
Antes de reproduzir comando de escrita, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a
região e a conta; nenhum número sem `fact_id` (aqui, fact vem do artefato de
`get-*` / `simulate-principal-policy`, não de inspeção); `validate_output` antes
de apresentar; manutenção destrutiva você **não executa** — recomende, e a
confirmação de escopo e retenção **sobe a quem pode ser perguntado**: o operador
na sessão, ou o agente pai que despachou.
