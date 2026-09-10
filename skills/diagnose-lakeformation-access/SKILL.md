---
name: diagnose-lakeformation-access
description: Use quando um job Glue lê tabela governada e falha ao escrever, ou quando alguém pergunta "por que a leitura passa e a escrita não?", "tomo AccessDenied e já dei SELECT", "troquei writeTo/insertInto/INSERT INTO e continua igual", "migrei de Glue 4.0 e nada funciona", ou quando é preciso descobrir QUAL permissão falta em vez de em qual plano a operação parou. É o procedimento que ORDENA os quatro coletores de governança de acesso; para a pergunta "esta configuração é suportada?" isolada, use `lakeformation-fgac-guard`.
---

# Diagnosticar acesso sob Lake Formation

Vinte e uma regras julgam esta área — 10 em `SF-LF`, 3 em `SF-IAM`, 8 em `SF-ERR`
— e quatro coletores a alimentam. **Este documento existe porque ter as peças não
é ter o caminho.**

## A regra que decide tudo: a API de escrita não é o caminho de autorização

Quando `writeTo`, `insertInto` e `spark.sql INSERT INTO` **falham todas juntas**,
a API não é a variável. As três atravessam o mesmo catálogo, o mesmo filesystem,
a mesma credencial e a mesma permissão. Trocar entre elas muda a interface de
alto nível e não muda nenhuma das quatro.

**Se você está prestes a sugerir outra API, pare e rode o passo 1.**

## Ordem, e por que ela é essa

Cada passo responde uma metade que o anterior deixou aberta. Rodar fora de ordem
produz achados verdadeiros sobre a pergunta errada.

### Passo 1 — o que o JOB declara (sem AWS, sem credencial)

```bash
sparkforge analyze terraform --path infra/ --out .sparkforge/facts_tf.json
sparkforge judge --facts .sparkforge/facts_tf.json
```

Sai daqui, antes de qualquer chamada à AWS:

| Achado | O que ele diz |
|---|---|
| `SF-LF-003` | catálogo Iceberg de nome arbitrário sob FGAC — só `spark_catalog` é suportado |
| `SF-LF-004` | resolver de credencial sem EMRFS no Glue 5.1 — **configuração inerte, sem erro** |
| `SF-LF-005` | FGAC e Full Table Access declarados juntos — a AWS proíbe |
| `SF-LF-006` | FGAC com menos de 4 workers |
| `SF-LF-001` / `SF-LF-002` | JAR extra ou streaming sob FGAC |

**Um achado aqui costuma encerrar a investigação**, e ele custa zero chamada de
API. `SF-LF-003` e `SF-LF-004` são os dois que mais aparecem em job migrado de
Glue 4.0.

### Passo 2 — o que a TABELA e a CONTA respondem

```bash
sparkforge collect lakeformation --repo . --database <db> --table <t> \
    --catalog-id <conta-dona-do-catalogo> \
    --resource-arn <localizacao-s3-da-tabela> --now <ISO8601>
sparkforge analyze lakeformation-grants --path .sparkforge/artifacts/lakeformation/ \
    --out .sparkforge/facts_lf.json
```

| Achado | O que ele diz |
|---|---|
| `SF-LF-007` | o job pede Full Table Access e a **conta** recusa — o passo de conta precede qualquer concessão |
| `SF-LF-008` | `IAM_ALLOWED_PRINCIPALS` com `ALL` — a tabela está registrada e o Lake Formation **não a governa** |
| `SF-LF-009` | escrita sob FGAC em localização **registrada** — a documentação da AWS **não fecha** |
| `SF-LF-010` | registrada, e o job não declara modelo de acesso nenhum |

**`--catalog-id` é obrigatório em cross-account.** A mesma `db.tabela` existe em
contas diferentes, e sem ele as duas coletas se sobrescrevem no manifesto.

### Passo 3 — o que o IAM decide, **simulado**

```bash
sparkforge collect iam-access --repo . --role-arn <runtime-role> \
    --resource-arn <arn-do-alvo> \
    --action s3:PutObject --action kms:GenerateDataKey --now <ISO8601>
sparkforge analyze iam-access --path .sparkforge/artifacts/iam_access/ \
    --out .sparkforge/facts_iam.json
```

**Simular e não parsear**, e a diferença é o passo inteiro. `SimulatePrincipalPolicy`
devolve a resposta da AWS com boundary, service control policy, `Deny` explícito e
`Condition` já resolvidos. Nenhum dos quatro aparece no documento da policy do role.

| Achado | O conserto |
|---|---|
| `SF-IAM-001` | boundary — **editar a policy do role não muda nada** |
| `SF-IAM-002` | service control policy — a decisão é da organização |
| `SF-IAM-003` | `Deny` explícito — acrescentar `Allow` **não vence** |

**Passe as ações da operação que falhou**, não a lista inteira. E
`--resource-arn` muda a pergunta: sem ele a AWS responde sobre `*`, e `allowed`
sobre `*` não é `allowed` naquele recurso.

### Passo 4 — a mensagem exata

```bash
sparkforge collect cloudwatch-logs --repo . --job-name <job> --job-run <run> \
    --log-group /aws-glue/jobs/error --start <ISO8601> --end <ISO8601> --now <ISO8601>
sparkforge analyze cloudwatch-logs --path .sparkforge/artifacts/cloudwatch_logs/
```

| Assinatura | Regra |
|---|---|
| `Insufficient Lake Formation permission(s) on` | `SF-ERR-006` |
| `GetTemporaryGlueTableCredentials` | `SF-ERR-014` |
| `lakeformation:GetDataAccess` | `SF-ERR-015` |
| `glue:GetTable` | `SF-ERR-016` |
| `Security validation exception` | `SF-ERR-017` |

**Por que este passo é o último e não o primeiro:** o log confirma *qual* plano
recusou; os passos 1 a 3 dizem *por quê*. Começar pelo log dá o nome da falha e
nenhuma das causas.

## O que nenhum dos quatro alcança

**Policy de recurso.** Bucket policy do S3, key policy do KMS e Glue resource
policy são avaliação **separada** — um `allowed` no passo 3 com bucket policy
negando ainda falha. `iam.access.unresolved` publica esse limite em todo
artefato, sempre, inclusive quando tudo respondeu `ok`.

**A execução.** A AWS avalia policies; ela não tenta a chamada.
`missing_context_values` lista as chaves de condição que o simulador não tinha.

## Red flags

- **"Já dei SELECT."** São dois planos de autorização. Ter `SELECT` no Lake
  Formation não salva uma operação sem a permissão de IAM sobre a API do Glue —
  `SF-ERR-016` separa os dois.
- **"Existe `ALL` sobre a tabela."** Confira o **principal**. `ALL` para
  `IAM_ALLOWED_PRINCIPALS` não autoriza principal nenhum em particular, e é
  `SF-LF-008`.
- **"Vou alargar a policy S3 do role."** Para localização **registrada** o
  caminho de dado não é o do role — `SF-LF-010`. A permissão a mais não é usada, e
  fica.
- **"Vou trocar para Full Table Access."** No Glue 5.1 isso quebra calado sem
  EMRFS restaurado (`SF-LF-004`), exige `ALL` e não `SELECT`, mais
  `lakeformation:GetDataAccess`, mais o passo de conta (`SF-LF-007`).
- **"O gate saiu `PASS`."** Confirme que havia artefato. Sem `tf.attribute` o
  eixo sai `BLOCKED`, e `BLOCKED` não é `PASS`.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; `next_step`
antes de escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de
memória; `validate_output` antes de apresentar; reporte `unresolved`.

**Nenhuma recomendação desta área é executada por você.** Conceder permissão,
desregistrar localização, alterar boundary ou service control policy são
mudanças de postura de segurança, e três delas têm raio maior que o do job. A
decisão **sobe a quem pode ser perguntado** — o agente pai, ou o operador na
sessão.

## Quando NÃO usar

- A pergunta é **"esta configuração é suportada?"** isolada, sem falha em curso:
  use `lakeformation-fgac-guard`.
- A pergunta é sobre **desempenho** do job governado: FGAC muda a alocação de
  workers, e isso é `tune-glue-job`.
- A pergunta é sobre **qual coluna mascarar**: isto aqui é sobre acesso negado,
  não sobre modelar a política.
