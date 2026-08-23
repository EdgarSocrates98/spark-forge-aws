---
name: lakeformation-fgac-guard
description: Use quando um job Glue declara `--enable-lakeformation-fine-grained-access` e alguém pergunta "posso passar um JAR extra?", "por que meu conector parou de funcionar sob FGAC?", "dá para usar UDF Java / HiveUDF / data source customizado com controle de acesso fino?" ou quando é preciso decidir entre manter FGAC e manter uma dependência. Use antes de recomendar `--extra-jars` em qualquer job com FGAC ligado. Se você está prestes a ler o Terraform no olho procurando os dois argumentos juntos, rode `sparkforge migrate glue <dir> --from 5.1 --to 6.0` — a área `SF-LF` correlaciona os dois **dentro do mesmo job**, e é isso que separa a regra de um gerador de acusação falsa.
subagent: true
agent: sf-lake-formation-specialist
---

# Lake Formation FGAC Guard

Sob controle de acesso fino do Lake Formation, a AWS **bloqueia** o fornecimento de JAR adicional para extensão do Spark, conector ou metastore. O bloqueio não é lacuna de roadmap: ele existe para preservar o isolamento completo do system driver — o mesmo motivo que bloqueia UDT, HiveUDF, função com classe customizada, data source customizado e `ANALYZE TABLE`.

Não existe meio-termo. A AWS não oferece um modo de FGAC que aceite JAR adicional, e nenhum ajuste de argumento reconcilia os dois.

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

| Regra | O que correlaciona |
|---|---|
| `SF-LF-001` | `--enable-lakeformation-fine-grained-access = true` **e** `--extra-jars` não vazio, no mesmo job |

Severidade, escopo de versão e o texto completo: `sparkforge rules lookup --id SF-LF-001`.

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
