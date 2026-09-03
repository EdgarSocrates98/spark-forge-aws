---
name: aws-security
description: Use quando a pergunta envolver serviços AWS de segurança — Security Hub V2 (OCSF) findings, conectores, agregadores, automation rules e resumo de postura; Security Hub CSPM (V1/ASFF) controles e padrões de compliance; GuardDuty threat findings; Inspector vulnerability findings; Macie sensitive data findings; Detective investigation; e Security Lake. Use para postura de segurança, Exposure findings, controles CSPM falhados, threat findings, vulnerability findings, sensitive data findings, automation rules ou configuração cross-service de segurança em ambientes AWS. Procedimentos usam sintaxe AWS CLI padrão e funcionam com ou sem o AWS MCP server.
---

# AWS Security

**PARE — Não responda a partir de conhecimento geral.** Antes de responder a
qualquer pergunta de serviço de segurança, casar o pedido do usuário com o
registro de sub-skills abaixo e seguir seu procedimento. Se o procedimento diz
para carregar um arquivo de referência, você DEVE lê-lo antes de fornecer
orientação operacional. Nunca pule o passo de roteamento.

Serviços AWS de Security fornecem detecção de ameaças (GuardDuty), gestão de
vulnerabilidades (Inspector), dashboard de segurança unificado e análise de
exposição (Security Hub), gestão de postura de compliance (Security Hub CSPM),
descoberta de dados sensíveis (Macie), investigação (Detective) e armazenamento
centralizado de logs (Security Lake). Cada serviço tem procedimentos de
referência dedicados para revisão de configuração e sumarização de
findings/investigação.

Esta skill funciona com ou sem o AWS MCP server. Quando disponível, o AWS MCP
server é recomendado para execução sandboxed e audit logging. Procedimentos
usam sintaxe AWS CLI padrão (`aws <service> <command>`).

Veja `references/services-overview.md` para relacionamentos entre serviços,
formatos de dados e padrões de integração cross-service.

## Regras globais

1. **Apenas APIs de leitura.** Esta skill e todas suas referências usam
   exclusivamente APIs não-mutantes. NUNCA referencie, recomende ou invoque
   qualquer API que crie, modifique, delete, habilite, desabilite ou de outra
   forma mute estado de recurso ou configuração — nem mesmo em recomendações em
   prosa. Veja arquivos de referência de serviço para a lista completa de APIs
   permitidas.

2. **Sem julgamentos de severidade sobre estado de configuração.** Apresente o
   que está e não está configurado factualmente. Não atribua labels de
   severidade, avaliações de gap ou enquadramento editorial (ex. "gap
   crítico", "issue de segurança") a estado de configuração.

3. **Sem recomendações de supressão de falso-positivo.** Foque em ajudar
   clientes a entender findings. Não recomende filtros de supressão, regras de
   archival ou dismiss de finding.

4. **Priorize Attack Sequences no GuardDuty.** Findings com prefixo de tipo
   `AttackSequence:` representam ataques multi-step correlacionados. Sempre
   traga estes primeiro, antes do breakdown de severidade.

5. **Priorize Exposure findings no Security Hub.** Exposure findings (attack
   paths, exposição de recurso) representam a correlação cross-service única do
   Security Hub. Traga estes primeiro em qualquer sumário de findings.

6. **Operações caras exigem pedido explícito.** NÃO paginar por todas as contas
   membro por default. Enumeração por-conta só executa se o usuário pedir
   explicitamente informação detalhada em nível de conta. Use APIs de
   statistics/count quando disponíveis (ex. `get-coverage-statistics`).

7. **Casar o idioma do usuário.** Responda no mesmo idioma em que o usuário
   escreve.

8. **Verifique, não adivinhe.** Se você não pode confirmar um fato a partir de
   um arquivo de referência ou saída de API, diga isso.

9. **Divulgação de dados sensíveis.** Quando um procedimento produz saída que
   pode conter informação sensível (corpos completos de finding, endereços IP,
   identificadores de recurso, configurações de rede, detalhes de threat
   intelligence), apresente um sumário primeiro. Note quais dados sensíveis a
   saída completa contém. Exiba a resposta raw completa apenas quando o
   chamador pedir explicitamente.

## Como esta skill funciona

1. **Encontre a sub-skill** — Case o pedido do usuário com o registro de
   sub-skills abaixo. Case por significado, não por wording exato. Se ambíguo,
   pergunte: "Você está checando configuração, ou precisa de um sumário de
   findings?"

2. **Se uma sub-skill casar** — leia `references/{sub-skill-id}.md` e siga seu
   procedimento.

3. **Se nenhuma sub-skill casar** — responda a partir dos arquivos de referência
   de serviço listados abaixo. Carregue `references/services-overview.md` para
   contexto cross-service, ou o arquivo de referência de serviço relevante (ex.
   `references/guardduty.md`) para escopo de API e questões de severity
   scoring.

4. **Visão geral cross-service** — Quando o usuário pergunta sobre postura de
   segurança geral através de múltiplos serviços, comece com
   `references/services-overview.md`, então roteie às sub-skills relevantes.

## Registro de sub-skills

| ID | Nome | Frases-gatilho | Quando rotear aqui | Referência |
|----|------|-----------------|-------------------|-----------|
| `guardduty-configuration` | GuardDuty Config Review | "is GuardDuty configured", "check detector", "GuardDuty features enabled", "runtime monitoring setup" | Usuário quer verificar completude de deploy do GuardDuty | `references/guardduty-configuration.md` |
| `guardduty-findings` | GuardDuty Findings Summary | "summarize GuardDuty findings", "what threats", "GuardDuty severity breakdown", "attack sequences" | Usuário quer snapshot de postura de findings | `references/guardduty-findings.md` |
| `inspector-configuration` | Inspector Config Review | "is Inspector scanning", "Inspector enabled", "scan types", "coverage gaps" | Usuário quer verificar deploy do Inspector | `references/inspector-configuration.md` |
| `inspector-findings` | Inspector Findings Summary | "vulnerabilities found", "Inspector findings", "CVE summary", "vulnerability posture" | Usuário quer visão geral de vulnerabilidades | `references/inspector-findings.md` |
| `security-hub-configuration` | Security Hub Config Review | "Security Hub integrations", "aggregation configured", "connectors", "automation rules", "V2 automation rules", "OCSF automation rules" | Usuário quer verificar setup do Security Hub V2 (OCSF) | `references/security-hub-configuration.md` |
| `security-hub-findings` | Security Hub Findings Summary | "risk overview", "exposure findings", "attack paths", "OCSF findings", "security posture trends" | Usuário quer visão geral de findings do Security Hub V2 (OCSF) | `references/security-hub-findings.md` |
| `security-hub-cspm-configuration` | CSPM Config Review | "standards enabled", "controls", "FSBP", "CIS", "PCI-DSS", "NIST", "compliance setup", "AI security", "AI best practices", "CSPM automation rules", "ASFF automation rules" | Usuário quer verificar setup de padrões de compliance | `references/security-hub-cspm-configuration.md` |
| `security-hub-cspm-findings` | CSPM Compliance Summary | "compliance posture", "failed controls", "pass rate", "ASFF findings", "third-party findings" | Usuário quer visão geral de findings de compliance | `references/security-hub-cspm-findings.md` |
| `macie-configuration` | Macie Config Review | "Macie configured", "data discovery setup", "classification jobs", "Macie enabled" | Usuário quer verificar deploy do Macie | `references/macie-configuration.md` |
| `macie-findings` | Macie Findings Summary | "sensitive data found", "Macie findings", "data classification results", "PII detected" | Usuário quer visão geral de dados sensíveis | `references/macie-findings.md` |
| `detective-configuration` | Detective Config Review | "Detective configured", "behavior graph", "Detective members", "data sources" | Usuário quer verificar deploy do Detective | `references/detective-configuration.md` |
| `detective-investigations` | Detective Investigations Summary | "Detective investigations", "investigation status", "indicators", "finding groups" | Usuário quer visão geral do landscape de investigação | `references/detective-investigations.md` |
| `security-lake-configuration` | Security Lake Config Review | "Security Lake configured", "log sources enabled", "subscribers", "data lake setup" | Usuário quer verificar deploy do Security Lake | `references/security-lake-configuration.md` |
| `security-lake-sources` | Security Lake Sources Summary | "what's flowing into Security Lake", "ingestion status", "source health", "data lake exceptions" | Usuário quer visão geral de saúde do data lake | `references/security-lake-sources.md` |
| `organization-policies` | Organization Policies Review | "organization policies", "org policies", "SECURITYHUB_POLICY", "INSPECTOR_POLICY", "list-policies", "policy targets", "policy enforcement" | Usuário quer revisar ou descobrir políticas de serviço do AWS Organizations | `references/organization-policies.md` |

## Desambiguação

| Palavras-chave | Roteie para |
|----------|----------|
| "automation rules" (ambíguo) | Tanto Security Hub quanto Security Hub CSPM têm automation rules. Se cliente usa Security Hub V2 (OCSF), roteie para Security Hub config. Se cliente usa Security Hub CSPM (ASFF), roteie para CSPM config. Pergunte se unclear. |
| "standards", "controls", "compliance", "FSBP", "CIS", "PCI", "NIST", "ASFF" | Skills de Security Hub CSPM |
| "integrations", "risk score", "attack path", "OCSF", "exposure", "connectors" | Skills de Security Hub |
| "threat detection", "GuardDuty", "detector", "runtime monitoring", "attack sequence" | Skills de GuardDuty |
| "vulnerability", "CVE", "Inspector", "scanning", "code vulnerability" | Skills de Inspector |
| "sensitive data", "classification", "Macie", "PII", "data discovery" | Skills de Macie |
| "investigation", "behavior graph", "Detective", "indicators" | Skills de Detective |
| "data lake", "log sources", "Security Lake", "subscribers", "ingestion" | Skills de Security Lake |
| "organization policies", "org policies", "policy type", "list-policies --filter" | Organization Policies (cross-service) |

**Nota:** Se um cliente está usando Security Hub V2 (OCSF), ele deve usar
automation rules do Security Hub (`list-automation-rules-v2`) e NÃO deve usar
features do Security Hub CSPM para novas regras, embora CSPM permaneça
tecnicamente disponível.

## Referência de serviço

Carregue arquivos de referência de serviço sob demanda — apenas quando o turno
atual exige contexto sobre capacidades de serviço, escopo de API ou severity
scoring.

| Referência | Conteúdo | Quando carregar |
|-------|---------|-------------|
| `references/services-overview.md` | Relacionamentos cross-service, formatos de dados, modelos de membership, descoberta de admin, convenções de API | Questões cross-service, postura de segurança geral, "quais serviços devo habilitar" |
| `references/guardduty.md` | APIs do GuardDuty, severity scoring, notas de serviço | Questões específicas de GuardDuty sobre APIs ou severity |
| `references/inspector.md` | APIs do Inspector, severity scoring, notas de serviço | Questões específicas de Inspector sobre APIs ou severity |
| `references/security-hub.md` | APIs do Security Hub V2 (OCSF), severity scoring, notas de serviço | Questões específicas de Security Hub V2 sobre APIs ou severity |
| `references/security-hub-cspm.md` | APIs do Security Hub CSPM (V1/ASFF), severity scoring, notas de serviço | Questões específicas de CSPM sobre APIs ou severity |
| `references/macie.md` | APIs do Macie, severity scoring, notas de serviço | Questões específicas de Macie sobre APIs ou severity |
| `references/detective.md` | APIs do Detective, severity scoring, notas de serviço | Questões específicas de Detective sobre APIs ou severity |
| `references/security-lake.md` | APIs do Security Lake, notas de serviço | Questões específicas de Security Lake sobre APIs |
| `references/organization-policies.md` | Padrão de descoberta de organization policies, tipos de política, APIs do Organizations | Questões sobre enforcement de política em nível de org através de serviços de segurança |

## Referência rápida

| Serviço | Para quê | Comando-chave de leitura |
|---|---|---|
| GuardDuty | Threat findings, attack sequences | `list-detectors`, `get-detector`, `list-findings` |
| Inspector | Vulnerability findings, CVE | `list-findings` |
| Security Hub V2 (OCSF) | Exposure, attack paths, risk | `list-automation-rules-v2`, `list-findings-v2` |
| Security Hub CSPM | Compliance, controles, standards | `describe-hub`, `list-standards`, `get-enabled-products` |
| Macie | Dados sensíveis, PII | `get-classification-scope`, `list-classification-jobs` |
| Detective | Investigação, behavior graph | `list-graphs`, `list-investigations` |
| Security Lake | Data lake, log sources | `list-data-lake-exceptions`, `list-log-sources` |

Cross-referência SparkForge: findings de bucket S3 público ou de encriptação
devem cruzar com `harden-s3-bucket` (remediação) e `review-terraform-data-platform`
(IaC que declarou o recurso exposto).

## Quando NÃO usar

- **Operações de escrita em serviços de segurança:** esta skill é apenas
  leitura. Habilitar/desabilitar detectores, criar automation rules, suprimir
  findings — não faça daqui.
- **Hardening de bucket S3:** use `harden-s3-bucket` para remediação operacional
  de bucket.
- **Revisão de Terraform de plataforma de dados:** use
  `review-terraform-data-platform` para IaC; esta skill lê a API ao vivo.
- **Postura de compliance fora da AWS:** CSPM aqui cobre apenas padrões AWS
  (FSBP, CIS, PCI-DSS, NIST) no Security Hub.
- **Supressão de falso-positivo:** não recomendada; foque em ajudar o cliente a
  entender o finding.

## Red flags

- Paginar por todas as contas membro por default sem pedido explícito — operação
  cara; use statistics/count APIs.
- Recomendar supressão/archival de findings — foco é entender, não descartar.
- Atribuir labels de severidade a estado de configuração ("gap crítico") —
  apresente factualmente.
- Pular o passo de roteamento de sub-skill e responder de conhecimento geral.
- Não priorizar Attack Sequences (`AttackSequence:`) no GuardDuty ou Exposure
  findings no Security Hub antes do breakdown de severidade.
- Exibir corpo completo de finding com IPs/dados sensíveis sem antes apresentar
  sumário e pedir confirmação.
- Carregar arquivo de referência apenas quando conveniente em vez de quando o
  procedimento exige.

## Não faz

Esta skill é procedimento operacional que pode mutar infraestrutura AWS ao
vivo. Não executa comandos de escrita sem confirmação explícita do operador. Não
despacha como subagente.

## Proveniência

Adaptado de `aws/agent-toolkit-for-aws`, skill `aws-security`, commit
`10b28af8aa3417eeeac6f1ebb5dd4f470a0c3594` (2026-09-02). O upstream é a fonte
autoritativa do registro de sub-skills, das regras globais e dos
`references/` (guardduty, inspector, security-hub, security-hub-cspm, macie,
detective, security-lake, organization-policies, services-overview). Esta é uma
adaptação ao contrato SparkForge (PT-BR, fronteira de manutenção,
não-despachável) e **pode desatualizar** quando a AWS atualizar o serviço. Antes
de reproduzir comando de escrita, confira o upstream.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de executar; confirme a
região e a conta; nenhum número sem `fact_id` (aqui, fact vem do artefato de API
de leitura, não de inspeção); `validate_output` antes de apresentar; manutenção
destrutiva você **não executa** — recomende, e a confirmação de escopo **sobe a
quem pode ser perguntado**: o operador na sessão, ou o agente pai que despachou.
