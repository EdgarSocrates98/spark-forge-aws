# Matriz de runtime Amazon EMR Serverless

Esta página existe para responder **uma** pergunta, registrada como D-5 no spec da Fase 5d: a matriz de release do EMR Serverless coincide com a do EMR on EC2, a ponto de `EMR_MATRIX` poder ser reaproveitada para derivar versão de Spark a partir do `releaseLabel` de um `get-application`?

**A resposta é não** — não porque as versões divirjam, mas porque **a documentação do Serverless não publica a matriz**. O que ela publica cobre um componente de quatro, e numa precisão menor. Esta página mede o que existe, e declara onde a fonte acaba.

**Esta página passou a ter espelho executável em 2026-08-31**, e a §6.1 registra exatamente o que mudou e o que não mudou. O espelho é [`runtime-matrix.yaml`](runtime-matrix.yaml), e ele carrega **só as colunas que as tabelas das §2 e §4 medem**: `spark` nas 24 releases numeradas, mais `iceberg` nas duas `emr-spark-8.0*`. Hadoop, Iceberg das numeradas e Python continuam fora — não por pendência, mas porque a fonte não os publica, que é a medição desta página inteira. A decisão da §6 sobre o **extrator** continua valendo palavra por palavra.

## 1. O que a fonte do Serverless publica, e o que ela não publica

Cada release do EMR Serverless tem uma página própria — não há página-resumo equivalente às duas *Application versions* do EMR on EC2. As 24 páginas numeradas foram lidas uma a uma em 2026-08-04, e **todas** trazem a mesma tabela de três linhas:

| Application | Version |
|---|---|
| Apache Spark | *(versão da comunidade)* |
| Apache Hive | 3.1.2 ou 3.1.3 |
| Apache Tez | 0.9.2 ou 0.10.2 |

Confronte com a página de EC2, que traz dezenas de linhas por release, incluindo Hadoop, Iceberg e Python. A diferença é estrutural:

| Componente | EMR on EC2 | EMR Serverless |
|---|---|---|
| Spark | `3.5.6-amzn-2` — comunidade **+ sufixo do fork** | `3.5.6` — só a versão da comunidade |
| Hadoop | publicado por release | **não publicado** |
| Iceberg | publicado por release | **não publicado** (ver §5) |
| Python | publicado como conjunto de interpretadores instalados | **não publicado** (ver §5) |

**As duas consequências que decidem o desenho desta fase:**

1. **O sufixo `-amzn-N` não existe na fonte do Serverless.** `EMR_MATRIX` guarda `"3.5.6-amzn-2"`, e esse é o valor que `RuntimeContext.spark` receberia. Afirmar que uma application `emr-7.13.0` roda `3.5.6-amzn-2` seria copiar um dado de EC2 para um artefato que não o declara. O que a fonte do Serverless sustenta é `3.5.6` — e só.
2. **Três dos quatro componentes da matriz simplesmente não têm valor de fonte.** Não é que divirjam: não foram publicados. Preencher por analogia com o EC2 seria inventar.

## 2. Spark, release a release, contra `EMR_MATRIX`

Coluna *EC2* copiada de [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md); coluna *Serverless* lida da página própria de cada release em 2026-08-04. *Comunidade bate* compara o EC2 **truncado no primeiro segmento com sufixo de vendor** — a mesma normalização que `sparkforge/rules/version_scope.py` aplica.

| Release | Spark no EC2 | Spark no Serverless | Comunidade bate |
|---|---|---|---|
| emr-7.13.0 | 3.5.6-amzn-2 | 3.5.6 | sim |
| emr-7.12.0 | 3.5.6-amzn-1 | 3.5.6 | sim |
| emr-7.11.0 | 3.5.6-amzn-0 | 3.5.6 | sim |
| emr-7.10.0 | 3.5.5-amzn-1 | 3.5.5 | sim |
| emr-7.9.0 | 3.5.5-amzn-0 | 3.5.5 | sim |
| emr-7.8.0 | 3.5.4-amzn-0 | 3.5.4 | sim |
| emr-7.7.0 | 3.5.3-amzn-1 | 3.5.3 | sim |
| emr-7.6.0 | 3.5.3-amzn-0 | 3.5.3 | sim |
| emr-7.5.0 | 3.5.2-amzn-1 | 3.5.2 | sim |
| emr-7.4.0 | 3.5.2-amzn-0 | 3.5.2 | sim |
| emr-7.3.0 | 3.5.1-amzn-1 | 3.5.1 | sim |
| emr-7.2.0 | 3.5.1-amzn-0 | 3.5.1 | sim |
| emr-7.1.0 | 3.5.0-amzn-1 | 3.5.0 | sim |
| emr-7.0.0 | 3.5.0-amzn-0 | 3.5.0 | sim |
| emr-6.15.0 | 3.4.1-amzn-2 | 3.4.1 | sim |
| emr-6.14.0 | 3.4.1-amzn-1 | 3.4.1 | sim |
| emr-6.13.0 | 3.4.1-amzn-0 | 3.4.1 | sim |
| emr-6.12.0 | 3.4.0-amzn-0 | 3.4.0 | sim |
| emr-6.11.1 | 3.3.2-amzn-0.1 | **não existe** | — |
| emr-6.11.0 | 3.3.2-amzn-0 | 3.3.2 | sim |
| emr-6.10.1 | 3.3.1-amzn-0.1 | **não existe** | — |
| emr-6.10.0 | 3.3.1-amzn-0 | 3.3.1 | sim |
| emr-6.9.1 | 3.3.0-amzn-1.1 | **não existe** | — |
| emr-6.9.0 | 3.3.0-amzn-1 | 3.3.0 | sim |
| emr-6.8.1 | 3.3.0-amzn-0.1 | **não existe** | — |
| emr-6.8.0 | 3.3.0-amzn-0 | 3.3.0 | sim |
| emr-6.7.0 | 3.2.1-amzn-0 | 3.2.1 | sim |
| emr-6.6.0 | 3.2.0-amzn-0 | 3.2.0 | sim |
| emr-6.5.0 | 3.1.2-amzn-1 | **não existe** | — |
| emr-6.4.0 | 3.1.2-amzn-0 | **não existe** | — |

**24 das 30 releases de `EMR_MATRIX` existem no Serverless, e nas 24 a versão de comunidade do Spark coincide.** Nenhuma divergiu.

Isso é menos do que parece, e é importante não ler a mais. A afirmação sustentada é: *"a versão de comunidade do Spark coincide"*. As afirmações **não** sustentadas são *"o binário é o mesmo"* (o fork não é declarado no Serverless) e *"os outros componentes coincidem"* (não há com o que comparar).

## 3. As seis releases que o EC2 tem e o Serverless não

Duas famílias, com razões diferentes:

- **`emr-6.4.0` e `emr-6.5.0`** — o EMR Serverless começa em 6.6.0. A própria página de releases declara: *"With Amazon EMR 6.6.0 and higher, deploy EMR Serverless. This deployment option isn't available with earlier Amazon EMR release versions."*
- **`emr-6.8.1`, `emr-6.9.1`, `emr-6.10.1`, `emr-6.11.1`** — as quatro releases de patch da série 6.x não aparecem na lista do Serverless. São exatamente as quatro que usam a forma de sufixo de dois níveis (`3.3.2-amzn-0.1`) que quebrou `version_scope.py` e foi corrigida na Fase 5b. **No Serverless elas não existem**, então aquele modo de falha não tem como reaparecer por esta porta.

Um `releaseLabel` de `emr-6.4.0` ou `emr-6.8.1` num `get-application` seria, portanto, um valor que a documentação não reconhece. O extrator não deve tratá-lo como release válida do Serverless só porque `EMR_MATRIX` tem a chave.

## 4. Os dois release labels que não são `emr-X.Y.Z`

A lista de releases do Serverless traz duas entradas cuja forma **não** é `emr-<major>.<minor>.<patch>`:

| Release label | Spark | Iceberg | Observação |
|---|---|---|---|
| `emr-spark-8.0.0` | 4.0.2-amzn-0 | 1.10.1-amzn-0 | GA. Também traz Delta `4.0.0-amzn-1-spark` e Hudi `1.1.0-amzn-0` |
| `emr-spark-8.0-preview` | 4.0.1 | 1.10.0-amzn-spark-0 | superseded por `emr-spark-8.0.0` |

Duas coisas aqui, e as duas mexem com código:

**A forma do label.** `emr-spark-8.0.0` é um valor legítimo de `--release-label` — a própria página traz o `create-application` que o usa. Um parser que assuma `emr-` seguido de três números produz lixo ou exceção nele. `emr-spark-8.0-preview` é pior: tem **dois** segmentos numéricos, não três. **`release_major`/`release_minor` precisam ser omitidos para essas duas formas**, no padrão "chave ausente é como este motor diz que não sabe", e não forçados a um número.

**A ironia da tabela.** É justamente nessas duas releases — as que `EMR_MATRIX` não conhece — que a documentação do Serverless publica sufixo `-amzn-N` e versão de Iceberg. O formato de tabela dessas páginas é diferente do das 24 numeradas. Não há como generalizar a partir de duas.

## 5. Hadoop, Iceberg e Python: o que foi procurado e o que foi achado

**Hadoop.** Nenhuma das 24 páginas de release do Serverless nomeia Hadoop. Nenhum valor, em nenhuma release. Não há o que comparar com a coluna `hadoop` de `EMR_MATRIX`.

**Iceberg.** A página *Using Apache Iceberg with EMR Serverless* ensina a configurar (`spark.jars=/usr/share/aws/iceberg/lib/iceberg-spark3-runtime.jar`) e **não declara versão nenhuma**; ela remete à *Iceberg release history* do ReleaseGuide. Essa página, por sua vez, se apresenta como *"the version of Iceberg included in each release version of Amazon EMR"* e manda ver os componentes nas páginas *Amazon EMR 7.x/6.x/5.x release versions* — que são as de EC2. Ela **inclui** `emr-6.8.1`, `emr-6.9.1`, `emr-6.10.1` e `emr-6.11.1`, que não existem no Serverless. Ou seja: é uma tabela que não se declara aplicável ao Serverless e que enumera releases que o Serverless não tem. Não serve como fonte para esta área.

O único dado de Iceberg com escopo de Serverless encontrado nesta coleta é uma linha de release note de `emr-7.12.0`: *"Iceberg version upgrade - Amazon EMR 7.12.0 supports Apache Iceberg version 1.10"*. Um ponto, com precisão de dois segmentos, contra os `1.10.0-amzn-0` da tabela de EC2. **Um ponto não é uma matriz.**

**Python.** A referência mais específica encontrada no guia do Serverless é uma nota de procedimento em *Using Python libraries with EMR Serverless*: *"You must run the following commands in a similar Amazon Linux 2 environment with the same version of Python as you use in EMR Serverless, that is, **Python 3.7.10 for Amazon EMR release 6.6.0**."* É uma release, num aviso de procedimento — não uma tabela. A página *Using different Python versions with EMR Serverless* fala em *"the version packaged in the Amazon EMR release for your Amazon EMR Serverless application"* no singular e **nunca cita o número**; o que ela declara por série é o sistema operacional base — Amazon Linux 2023 em 7.0.0+, Amazon Linux 2 em 6.15.0 e abaixo.

Nesta coleta **não foi encontrada nenhuma página oficial que declare o Python default do Serverless por release.** Existem respostas de fórum afirmando "6.x usa 3.7, 7.x usa 3.9"; não são fonte para este repositório e não estão registradas como tal.

## 6. A decisão, e por que ela é essa

**D-5 resolve como: o `releaseLabel` de uma application EMR Serverless não alimenta `RuntimeContext.emr`, e `EMR_MATRIX` não é reaproveitada para derivar versão a partir dele.**

O argumento não é que os números divirjam — nas 24 releases comparáveis a versão de comunidade do Spark bate, uma a uma. O argumento é que **três das quatro colunas não têm fonte**, e a quarta tem fonte em precisão menor do que a matriz guarda:

- derivar `spark: "3.5.6-amzn-2"` de um `emr-7.13.0` de Serverless afirmaria o fork que a fonte do Serverless não declara;
- derivar `hadoop`, `iceberg` ou `python` afirmaria valores que a fonte do Serverless não publica de forma nenhuma;
- e `EMR_MATRIX` não tem chave para `emr-spark-8.0.0`, que é label válido — a derivação falharia calada exatamente na release mais nova.

`knowledge/emr/runtime-matrix.md` §4.3 já fixou o princípio de que a derivação por matriz é **fallback** e perde para observação direta, marcada com o sufixo `:matrix` na origem. Aqui não há sequer a matriz para servir de fallback. A alternativa correta não é derivar com menos confiança: é não derivar, e deixar `RuntimeContext.emr` vazio, que faz toda regra com `emr` em `runtime_scope` ser pulada por ausência — **falha fechada**, a semântica que este projeto usa para "não detectada".

É o mesmo raciocínio que deixou a coluna *Python do PySpark* vazia em toda a série 6.x de EC2: escolher um valor porque ele é plausível seria inventar.

**O que o extrator emite, então:** `releaseLabel` cru em `attrs`, e `release_major`/`release_minor` em `measures` **quando o label tem a forma `emr-<major>.<minor>.<patch>`** — omitidos quando não tem. Nada disso vira `RuntimeContext`. As regras da área `SF-EMRS` declaram `runtime_scope: {}` e leem a série do próprio fact, no padrão de `rules/catalog/emr-infra.yaml:8-19`.

**O que reabriria a decisão:** a AWS publicar, para o Serverless, uma tabela de componentes por release comparável à de EC2 — com Hadoop, Iceberg e Python. Até lá, a divergência fica registrada como dívida no `STATUS.md`.

## 6.1 O que mudou em 2026-08-31, e o que não mudou

A §6 responde **D-5**, que é uma pergunta sobre o **extrator**: o `releaseLabel` que um `get-application` traz não alimenta `RuntimeContext`. **Isso continua exatamente como está escrito acima.** Nada em `emrs.application` vira eixo de runtime.

A dívida que fechou nesta data é **outra pergunta**, e foi medida no `STATUS.md`: com a flag `--emr` na mão, `sparkforge judge --facts <facts `emrs.*`> --emr 7.5.0` gravava `spark: "3.5.2-amzn-1"`, `python: "3.9"` e `iceberg: "1.6.1-amzn-1"` — **os quatro eixos derivados da `EMR_MATRIX` de EMR on EC2**, sobre um conjunto sem um único fact de EC2. Não derivar nada deixava três eixos inventados; **recusar a flag** — a saída que a fase de EMR on EKS tomou para `emrc.*` — deixaria o operador sem o eixo `spark`, que a §2 mede que **esta fonte publica**.

A saída escolhida foi a terceira das três que a dívida listava: **dar o que a fonte publica, e deixar vazio o que ela não publica.**

| | Antes | Depois |
|---|---|---|
| `emr` | `7.5.0` (a flag) | `7.5.0` (a flag, inalterado) |
| `spark` | `3.5.2-amzn-1` — o fork de EC2 | `3.5.2` — o que a §2 mede |
| `python` | `3.9` — da `EMR_MATRIX` | vazio |
| `iceberg` | `1.6.1-amzn-1` — da `EMR_MATRIX` | vazio |
| `detected_from` | `["cli"]` | `["cli", "cli:emr-serverless:matrix"]` |

Quatro coisas que essa troca **não** faz:

1. **Não muda o eixo `emr`.** O release label é o mesmo namespace nas duas plataformas — o próprio `get-application` traz `emr-7.5.0` — e apagá-lo trocaria invenção por perda de informação. Medido junto: **nenhuma regra do catálogo tem `emr` em `runtime_scope`** (13 têm `glue`, 5 `spark`, 1 `iceberg`), então o eixo preenchido não coloca regra de EC2 em escopo.
2. **Não vale para conjunto com artefato de EC2 junto.** A troca de matriz é estreita, no molde exato da recusa de EKS: com um `describe-cluster` presente, a flag declara o lado de EC2 que está de fato ali, e a matriz de EC2 é a certa — com o fork, que aquela fonte publica.
3. **Não deriva release que o Serverless não tem.** `emr-6.4.0` e `emr-6.5.0` e as quatro releases de patch da série 6.x não estão no espelho, então `--emr 6.4.0` sobre facts de Serverless deriva **nada** — que é o que a §3 sustenta.
4. **Não interpola nem completa.** O carregador tem vocabulário fechado de componente (`spark`, `iceberg`) e **estoura** se alguém acrescentar `python:` numa linha — a única forma prática de a invenção voltar era edição distraída de YAML.

O contrafactual inteiro está em `tests/test_emr_serverless_runtime_boundary.py`, e o guard de drift daquele arquivo compara o espelho contra as tabelas desta página célula a célula: **editar a tabela e esquecer o YAML derruba a suíte.**

## 7. Como manter esta página

O caminho de manutenção de `knowledge/emr/runtime-matrix.md` §5 — `aws emr describe-release-label` — **não** foi verificado para o Serverless nesta coleta, e não deve ser assumido. As 24 páginas por release são a fonte conferida.

O perfil de drift é o de churn estrutural descrito em `knowledge/emr/runtime-matrix.md` §6 para a série 7.x: cada minor novo **acrescenta uma página nova**, e a página-índice muda. Diferente do EC2, onde a coluna nova entra numa tabela existente, aqui a página antiga não muda — o que torna o hash de cada página individual um guard mais estável, e o da página-índice um alarme esperado a cada minor.

## Fontes

- Amazon EMR Serverless release versions (índice, e a declaração do piso 6.6.0). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/release-versions.html (retrieved 2026-08-04)
- As 24 páginas por release da §2, lidas uma a uma em 2026-08-04, no padrão `https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/release-version-<N>.html`, onde `<N>` é a release sem pontos: `7130`, `7120`, `7110`, `7100`, `790`, `780`, `770`, `760`, `750`, `740`, `730`, `720`, `710`, `700`, `6150`, `6140`, `6130`, `6120`, `6110`, `6100`, `690`, `680`, `670`, `660`. Nenhuma célula de Spark divergiu da versão de comunidade do EC2.
- AWS runtime for Apache Spark (emr-spark-8.0.0). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/release-version-emr-spark-8.0.0.html (retrieved 2026-08-04)
- AWS runtime for Apache Spark (emr-spark-8.0-preview). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/release-version-emr-spark-8.0-preview.html (retrieved 2026-08-04)
- Using Apache Iceberg with EMR Serverless (não declara versão). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-iceberg.html (retrieved 2026-08-04)
- Iceberg release history (não se declara aplicável ao Serverless). https://docs.aws.amazon.com/emr/latest/ReleaseGuide/Iceberg-release-history.html (retrieved 2026-08-04)
- Using Python libraries with EMR Serverless (a única citação de versão de Python, e só para 6.6.0). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python-libraries.html (retrieved 2026-08-04)
- Using different Python versions with EMR Serverless (não cita número). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/using-python.html (retrieved 2026-08-04)

### O que estas fontes NÃO sustentam

- **A versão de Hadoop de qualquer release do EMR Serverless.** Nenhuma das 24 páginas a nomeia. **Não citar número**, nem o do EC2 da mesma release.
- **A versão de Iceberg por release do EMR Serverless.** Há exatamente um ponto (`7.12.0` → "1.10", em release note) e uma tabela de EC2 que não se declara aplicável. **Não construir matriz**, nem afirmar que a de EC2 vale aqui.
- **O Python default por release do EMR Serverless.** Há um número, para uma release (`6.6.0` → 3.7.10), num aviso de procedimento. **Não interpolar** para as outras 23, e não importar `python_installed` do `EMR_MATRIX`.
- **Que `3.5.6` no Serverless e `3.5.6-amzn-2` no EC2 sejam o mesmo binário.** A fonte do Serverless não declara fork. A igualdade medida na §2 é entre versões de comunidade, e é só isso que ela é.
- **Que as releases do Serverless recebam os mesmos patches da AWS que as de EC2 na mesma release label.** Não foi encontrada declaração nesse sentido, em nenhum dos dois sentidos.
- **A ausência definitiva de `emr-6.4.0`, `emr-6.5.0` e das quatro releases de patch.** O que se mediu é que elas não constam da lista de releases do Serverless em 2026-08-04, e que a página declara 6.6.0 como piso. Isso sustenta "a documentação não as oferece"; não foi testado o que a API responde a um label desses.
- **Que `emr-spark-8.0.0` e `emr-spark-8.0-preview` sejam as únicas formas de label fora de `emr-X.Y.Z`.** São as duas que existem nesta coleta. O extrator deve tratar forma inesperada como não-parseável e omitir `release_major`/`release_minor`, não enumerar exceções.
- **O caminho de manutenção por API.** `aws emr describe-release-label` não foi verificado contra release de Serverless nesta coleta.
