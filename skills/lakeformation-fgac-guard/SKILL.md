---
name: lakeformation-fgac-guard
description: Use quando um job Glue declara `--enable-lakeformation-fine-grained-access` ou configuração de Full Table Access e alguém pergunta "posso passar um JAR extra?", "por que meu conector parou de funcionar sob FGAC?", "por que a leitura funciona e a escrita não?", "troquei `writeTo` por `INSERT INTO` e continua dando erro de Lake Formation", "dá para usar UDF Java / HiveUDF / data source customizado com controle de acesso fino?" ou quando é preciso decidir entre FGAC e Full Table Access, ou entre manter FGAC e manter uma dependência. Use antes de recomendar `--extra-jars` em qualquer job com FGAC ligado, e antes de trocar a API de escrita de um job que falha sob Lake Formation. Se você está prestes a ler o Terraform no olho procurando os argumentos, rode `sparkforge migrate glue <dir> --from 5.1 --to 6.0` — a área `SF-LF` correlaciona o que precisa ser correlacionado, e é isso que separa a regra de um gerador de acusação falsa.
---

# Lake Formation FGAC Guard

Sob controle de acesso fino do Lake Formation, a AWS **bloqueia** o fornecimento de JAR adicional para extensão do Spark, conector ou metastore. O bloqueio não é lacuna de roadmap: ele existe para preservar o isolamento completo do system driver — o mesmo motivo que bloqueia UDT, HiveUDF, função com classe customizada, data source customizado e `ANALYZE TABLE`.

Não existe meio-termo. A AWS não oferece um modo de FGAC que aceite JAR adicional, e nenhum ajuste de argumento reconcilia os dois.

## Antes de tudo: qual modelo de acesso, e em qual versão

**FGAC e Full Table Access são dois modelos, e a AWS proíbe os dois no mesmo job.** A diferença que decide não é granularidade — é **quem vende a credencial**:

| | quem lê e escreve o S3 |
|---|---|
| **FGAC** | leitura passa pelo Lake Formation; **escrita usa IAM do runtime role** |
| **FTA** | credencial do Lake Formation para tabela **registrada**; runtime role para o resto |

A versão muda o significado, não só o número:

| | Glue 4.0 | Glue 5.0 | Glue 5.1 |
|---|---|---|---|
| Filesystem S3 default | EMRFS | EMRFS | **S3A** |
| FGAC via `GlueContext`/DynamicFrame | suportado | **removido** | removido |
| FGAC escrita de dado | não existe | **não suportado** | **suportado** |

**Três consequências que mudam o diagnóstico:**

- um job de 4.0 que lia com `create_dynamic_frame.from_catalog` **não tem tradução direta** para FGAC no 5.x;
- afirmar "FGAC não escreve" para um Glue 5.1 é erro de versão, e o contrário também;
- **FTA num Glue 5.1 de configuração default não funciona**: FTA exige EMRFS, e o 5.1 trocou o default para S3A. Pior — `fs.s3.credentialsResolverClass` é chave de EMRFS e sob S3A é **ignorada sem erro**.

O eixo completo, com as citações e o **conflito declarado** entre quatro frases da documentação da AWS sobre escrita em tabela registrada, está em [`knowledge/glue/lakeformation-fgac.md`](../../knowledge/glue/lakeformation-fgac.md) §0, §5 e §6.

## A API de escrita não é o caminho de autorização

Quando `writeTo`, `insertInto` e `spark.sql INSERT INTO` **falham todas juntas**, a API não é a variável. Trocar entre elas muda a interface de alto nível e não muda catálogo, filesystem, credencial nem permissão. Suba de camada em vez de trocar de API — as regras abaixo são exatamente esse degrau.

## Procedimento

1. Aponte a análise para o diretório que contém os `.tf` do job. Sem Terraform, o eixo `lakeformation` nasce `BLOCKED`: a topologia de FGAC é declarada nos `default_arguments` do job, nunca no código Python.

2. `sparkforge migrate glue <dir> --from 5.1 --to 6.0`

3. Leia `gates["lakeformation"]`. Um `SF-LF-001` em P0 fecha esse eixo — e **só** esse. Um achado move um eixo, nunca dois.

## Por que a regra não acusa em falso

`SF-LF-001` usa `same_subject: true`. Um `.tf` com dois jobs — um com FGAC e sem JAR, outro com JAR e sem FGAC — satisfaz as duas condições **no arquivo**, e os dois jobs estão corretos. Sem esse campo, o motor cruzaria os dois e acusaria em P0 uma configuração que a AWS suporta.

A âncora é `tf.attribute` e não `tf.resource` porque as duas condições são atributos, e o subject de todo `tf.attribute` de um job já é o job.

`--extra-jars = ""` é HCL válido e produz um atributo declarado que não fornece JAR nenhum. A regra filtra isso com uma desigualdade explícita, porque acusar um job que não pede nada é a mesma classe de falso positivo, do outro lado.

## A decisão, e ela é de quem responde pela governança

**Manter FGAC** — reescrever em Spark SQL nativo ou API de DataFrame o que o JAR fazia, e remover `--extra-jars`. Vale quando o JAR é um conector para formato que o runtime já lê nativamente, ou uma biblioteca de utilidade pequena.

**Manter a dependência** — remover `--enable-lakeformation-fine-grained-access` e mover o controle de acesso para o mecanismo que sobra: permissão IAM sobre o caminho S3 do runtime role. É controle mais grosso, e a diferença precisa ser **registrada** com quem responde pela governança, não absorvida em silêncio.

Confira o classpath inteiro na mesma passada, não só o JAR que motivou o achado: `--extra-jars` costuma carregar mais de um artefato, e cada um é uma decisão separada.

## VARIANT e FGAC não convivem

A AWS declara que FGAC **não** é suportado com coluna VARIANT no Glue 6.0. Se o plano inclui adotar VARIANT (feature da spec v3) num dado governado por FGAC, as duas coisas não cabem juntas — e essa é uma restrição de feature, separada do bloqueio de JAR acima.

## Referência rápida

**Estrutural — lida do Terraform e do código, antes de qualquer execução:**

| Regra | O que correlaciona | Escopo |
|---|---|---|
| `SF-LF-001` | FGAC **e** `--extra-jars` não vazio, no mesmo job | `glue >=5.0` |
| `SF-LF-002` | FGAC **e** `command { name = "gluestreaming" }` | `glue >=5.0` |
| `SF-LF-003` | FGAC **e** catálogo Iceberg de nome arbitrário (não `spark_catalog`) | `glue >=5.0` |
| `SF-LF-004` | resolver de credencial do Lake Formation **sem** EMRFS restaurado | `glue >=5.1` |
| `SF-LF-005` | FGAC **e** Full Table Access declarados no mesmo job | `glue >=5.0` |
| `SF-LF-006` | FGAC com `number_of_workers` abaixo de 4 | `glue >=5.0` |

**Da exceção — exigem a linha de log casada MAIS o companheiro derivado:**

| Regra | Assinatura | Companheiro |
|---|---|---|
| `SF-ERR-006` | `Insufficient Lake Formation permission(s) on` | `tf.spark_conf` |
| `SF-ERR-014` | `GetTemporaryGlueTableCredentials` | `lakeformation.access_model` |
| `SF-ERR-015` | `lakeformation:GetDataAccess` | `lakeformation.filesystem` |
| `SF-ERR-016` | `glue:GetTable` | `lakeformation.access_model` |
| `SF-ERR-017` | `Security validation exception` | `lakeformation.access_model` |

**Procedência, e ela é declarada:** a página de troubleshooting do AWS Glue **não publica string de erro literal** — publica título de sintoma. Das quatro assinaturas de `SF-ERR-014` a `SF-ERR-017`, só `Security validation exception` é frase que a AWS escreve; as outras três casam por **nome de ação IAM ou de API**, que é a parte publicada. Casar por nome de ação é o mais forte que a fonte sustenta, e é por isso que nenhuma das quatro dispara sem o companheiro.

Severidade, escopo de versão e o texto completo: `sparkforge rules lookup --id SF-LF-003` (e assim por diante).

## Os facts que o motor deriva, e o que eles não afirmam

`sparkforge/facts/lakeformation.py` deriva quatro kinds sobre a união dos facts, sem ler artefato:

| kind | o que carrega |
|---|---|
| `lakeformation.access_model` | `model`, `fgac_enabled`, `declared_value` — e `"false"` declarado **não** é o mesmo que ausente |
| `lakeformation.iceberg_catalog` | `catalog_name`, `is_session_catalog`, `catalog_impl`, `lakeformation_enabled` |
| `lakeformation.filesystem` | `lf_credentials_resolver_declared`, `emrfs_restored`, `fs_s3_impl` |
| `lakeformation.unresolved` | a lacuna: grant do Lake Formation, policy do runtime role, registro da localização S3 |

**`is_session_catalog: false` é observação, nunca acusação.** A restrição de session catalog é de FGAC, e a AWS publica exemplo de FTA com catálogo de nome arbitrário. Quem cruza as duas coisas é a regra.

**`lakeformation.unresolved` é a metade honesta de todo achado desta área:** nenhuma concessão do Lake Formation e nenhuma policy de IAM entra em artefato que este motor colete. Um achado daqui diz em qual **plano** a operação parou; ele não diz qual permissão falta.

Aprofundamento sob demanda: [`knowledge/glue/lakeformation-fgac.md`](../../knowledge/glue/lakeformation-fgac.md) traz o que a documentação declara e o que ela não declara; [`docs/aws/glue/6.0/lakeformation.md`](../../docs/aws/glue/6.0/lakeformation.md) é a leitura pelo lado do runtime 6.0.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime.
Remover `--enable-lakeformation-fine-grained-access` afrouxa o controle de acesso, e
manutenção destrutiva você **não executa** — recomende, e a decisão **sobe a quem pode ser
perguntado**: o agente pai que despachou, ou o operador na sessão, que a leva a quem
responde pela governança do dado.

Das duas saídas possíveis, nenhuma é default. Escolher por conta própria entre perder a
dependência e perder o FGAC é decidir postura de segurança sem dono.

## Quando NÃO usar

- A pergunta é sobre **permissão negada entre contas**: isso é topologia de permissão, não FGAC contra classpath — o diagnóstico de cross-account é outro caminho.
- A pergunta é sobre a **migração inteira** do job: use `migrate-glue-6`, que traz este eixo junto com os outros.
- A pergunta é sobre **qual coluna mascarar**: isto aqui é sobre o que o FGAC impede o job de fazer, não sobre modelar a política.

## Red flags

- **"É só um JAR pequeno."** O bloqueio é sobre fornecer JAR, não sobre o tamanho dele.
- **"Vou usar `--user-jars-first` para contornar."** Não contorna: o argumento muda a ordem do classpath, não a restrição do FGAC — e sob Glue 6.0 ele tem um modo de falha próprio com AWS SDK v2 anterior a 2.44.6 (`ERR-GLUE-003`).
- **"O gate `lakeformation` saiu `PASS`."** Confirme que havia `.tf` na análise. Sem `tf.attribute` o eixo sai `BLOCKED`, e `BLOCKED` não é `PASS`.
- **"Removi o FGAC e o job voltou."** Voltou a rodar, com controle de acesso mais grosso. Isso é uma mudança de postura de segurança e precisa de dono declarado.
- **"Já tentei `writeTo`, `insertInto` e `INSERT INTO`."** Se as três falham juntas, a API não é a variável — elas atravessam o mesmo catálogo, o mesmo filesystem e a mesma credencial. Suba de camada: `SF-LF-003`, `SF-LF-004` e a família `SF-ERR-014..017`.
- **"Eu já dei SELECT no Lake Formation."** São dois planos de autorização. A AWS declara que ter `SELECT` não salva uma operação que não tem a permissão de IAM sobre a API do Glue — é o que `SF-ERR-016` separa.
- **"Vou trocar para Full Table Access."** Num Glue 5.1 isso quebra calado se o EMRFS não for restaurado, e exige `ALL` no Lake Formation para escrever (não `SELECT`), mais `lakeformation:GetDataAccess` no IAM, mais o passo de conta de *application integration*. FGAC e FTA não coexistem no mesmo job — se a leitura precisa de FGAC e a escrita precisa de credencial do Lake Formation, um job só não resolve.
- **"O alvo está registrado no Lake Formation e a escrita falha sob FGAC."** Isso cai num **conflito declarado** da documentação da AWS (§6 do documento de conhecimento): o caminho do role não é usado para localização registrada, e o grant do Lake Formation não autoriza escrita. Não escolha um lado — apresente as três saídas que a documentação sustenta.
