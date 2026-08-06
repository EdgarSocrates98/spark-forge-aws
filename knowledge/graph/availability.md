# GraphFrames × Spark × Glue/EMR — onde a biblioteca existe, e onde ninguém a instala

Esta página responde às perguntas 3 e 4 da §6 do
[spec da Fase 6a](../../docs/superpowers/specs/2026-08-05-sparkforge-fase6a-graph-design.md):
**quais releases não têm jar nenhum**, e **se a AWS documenta GraphFrames em
algum lugar**. É o que sustenta o `runtime_scope` das regras de disponibilidade
e a regra que cruza `graph.import` com o IaC. A API está em
[`graphframes-api.md`](graphframes-api.md); esta página é sobre **existir**.

A forma executável deste conteúdo será [`../../rules/catalog/graph.yaml`](../../rules/catalog/graph.yaml),
escrito na Task 5.

**Coleta desta rodada: 2026-08-05.** Esta página **envelhece com um release**, e
é por isso que a data importa mais aqui do que em qualquer outra página de
`knowledge/`.

---

## 1. Duas linhagens, e a fratura de 2025-07-17

| | Legada | Corrente |
|---|---|---|
| Coordenada | `graphframes:graphframes` | `io.graphframes:graphframes-spark{3,4}_2.1{2,3}` |
| Repositório | `repos.spark-packages.org` | Maven Central (`repo1.maven.org`) |
| Primeira | `0.1.0-spark1.4` (2016-02-25) | `0.9.0` (2025-07-17) |
| Última | `0.8.4-spark3.5` (2024-07-03) | `0.12.1` (2026-06-17) |
| Versão no nome do artefato | sufixo `-sparkX.Y-s_2.NN` | sufixo `-sparkN` no `artifactId` |
| Python | **dentro do jar** | pacote PyPI `graphframes-py` |

A `0.9.0` anuncia a mudança nas próprias release notes: _"New groupId
`io.graphframes`"_, _"New PyPi ID: `graphframes-py`"_, _"Spark 4.x support"_.

Versões publicadas em cada `artifactId` da linhagem corrente, lidas do
`maven-metadata.xml` (todos com `lastUpdated` de 2026-06-17):

| `artifactId` | Versões |
|---|---|
| `graphframes-spark3_2.12` | `0.9.0-spark3.5`, `0.9.2`, `0.9.3`, `0.10.0`, `0.10.1`, `0.11.0`, `0.12.0`, `0.12.1` |
| `graphframes-spark3_2.13` | idem |
| `graphframes-spark4_2.13` | `0.9.0-spark4.0`, `0.9.2`, `0.9.3`, `0.10.0`, `0.10.1`, `0.11.0`, `0.12.0`, `0.12.1` |

**A linhagem corrente compila contra Spark 3.5, e só.** Lido dos POMs:
`graphframes-spark3_2.12:0.9.2` declara `org.apache.spark:spark-sql_2.12:3.5.5`
(`provided`); `0.12.1` declara `3.5.8`. Não há `graphframes-spark3` construído
contra 3.3 ou 3.4 em release nenhuma.

## 2. Spark 3.3 não tem jar em linhagem nenhuma — e a release note mente

Medição por requisição HTTP direta ao repositório de artefatos, 2026-08-05:

| Artefato | HTTP |
|---|---|
| `graphframes-0.8.2-spark3.1-s_2.12.jar` | **200** |
| `graphframes-0.8.2-spark3.2-s_2.12.jar` | **200** |
| `graphframes-0.8.3-spark3.2-s_2.12.jar` | 404 |
| **`graphframes-0.8.3-spark3.3-s_2.12.jar`** | **404** |
| `graphframes-0.8.3-spark3.4-s_2.12.jar` | **200** |
| `graphframes-0.8.3-spark3.5-s_2.12.jar` | **200** |
| **`graphframes-0.8.4-spark3.3-s_2.12.jar`** | **404** |
| `graphframes-0.8.4-spark3.4-s_2.12.jar` | 404 |
| `graphframes-0.8.4-spark3.5-s_2.12.jar` | **200** |
| `graphframes-0.8.4-spark3.5-s_2.13.jar` | **200** |

Sob `https://repos.spark-packages.org/graphframes/graphframes/<versão>/`.

**A release note da `v0.8.3` afirma o contrário.** Verbatim, da API do GitHub:

> _Support Spark 3.3 / Scala 2.12 , Spark 3.4 / Scala 2.12 and Scala 2.13, Spark 3.5 / Scala 2.12 and Scala 2.13_

A listagem do spark-packages para a `0.8.3` traz apenas `-spark3.4-s_2.12`,
`-spark3.4-s_2.13`, `-spark3.5-s_2.12` e `-spark3.5-s_2.13`. **Nenhum
`-spark3.3`.** O suporte foi construído e testado; o artefato não foi publicado.

**Aqui o repositório de artefatos vence a nota de release**, e a razão é a
pergunta que a área faz: a regra não pergunta "o projeto suporta?", pergunta
"há algo para instalar?". `--packages graphframes:graphframes:0.8.3-spark3.3-s_2.12`
resolve para 404.

O `maven-metadata.xml` do grupo legado não é servido (`NoSuchKey`), e a listagem
de diretório do S3 também não. Por isso a medição é por artefato, uma requisição
por coordenada, e não por índice.

## 3. A matriz, cruzada com `GLUE_MATRIX` e `EMR_MATRIX`

Fonte das versões de Spark: `sparkforge/facts/runtime_detect.py`, 2026-08-05.
**34 células** — 4 de Glue, 30 de EMR.

| Spark | Jar disponível | Glue | EMR |
|---|---|---|---|
| 3.1.x | `0.8.2-spark3.1-s_2.12` (2021-10-17) | **3.0** (3.1.1) | 6.4.0, 6.5.0 |
| 3.2.x | `0.8.2-spark3.2-s_2.12` (2021-10-17) | — | 6.6.0, 6.7.0 |
| **3.3.x** | **NENHUM** | **4.0** (3.3.0) | **6.8.0, 6.8.1, 6.9.0, 6.9.1, 6.10.0, 6.10.1, 6.11.0, 6.11.1** |
| 3.4.x | `0.8.3-spark3.4-s_2.1{2,3}` (2023-09-27) | — | 6.12.0, 6.13.0, 6.14.0, 6.15.0 |
| 3.5.x | `0.8.3-spark3.5`, `0.8.4-spark3.5`, e `io.graphframes` `0.9.0-spark3.5` a `0.12.1` | **5.0** (3.5.4), **5.1** (3.5.6) | 7.0.0 a 7.13.0 (14 releases) |

**Nove das 34 células não têm jar nenhum:** Glue 4.0, e as oito releases de EMR
de 6.8.0 a 6.11.1. É exatamente a medição que o plano trazia como hipótese, e
ela **se confirma**.

O recorte é limpo e vale escrever assim, porque é o que a regra vai testar:
`runtime_scope` cobre **Spark 3.3.x**, e as células caem por consequência.

**Também vale registrar o outro extremo:** as células de Spark 3.1 e 3.2 têm jar,
mas o jar tem **quase cinco anos** (2021-10-17) e é o último da série. Não é
"sem jar" — é "sem manutenção". Isso **não** entra na mesma regra, e a razão está
na §6.

## 4. O segundo eixo, que o spec não previu: o Python

A fratura da `0.9.0` mudou de onde vem o wrapper Python, e isso cria uma segunda
lista de células inalcançáveis.

Medido abrindo os dois jars:

| Jar | Arquivos `.py` dentro |
|---|---|
| `graphframes-0.8.2-spark3.2-s_2.12.jar` | **13** — `graphframes/graphframe.py`, `graphframes/lib/pregel.py`, `graphframes/__init__.py`, … |
| `graphframes-spark3_2.12-0.12.1.jar` | **0** |

Na linhagem legada, o Python vem **no jar**. Na corrente, vem do PyPI.

E o PyPI tem dois pacotes, com histórias diferentes:

| Pacote | Última | Data | `requires_python` |
|---|---|---|---|
| `graphframes` | `0.6` | **2018-12-05** | não declarado |
| `graphframes-py` | `0.12.1` | 2026-06-17 | **`>=3.10`** em todas as releases publicadas (`0.9.0` em diante) |

`graphframes` no PyPI parou em 2018, três releases antes da `0.8.2`. Não é a
linhagem legada mantida: é um pacote abandonado com o nome certo.

Cruzando `>=3.10` com o Python das matrizes:

| Runtime | Python | `graphframes-py` instala? |
|---|---|---|
| Glue 5.1, Glue 5.0 | 3.11 | sim |
| Glue 4.0 | 3.10 | sim — mas **não há jar** |
| Glue 3.0 | 3.7 | **não** |
| EMR 7.13.0 | 3.11 (default) | sim |
| EMR 7.1.0 – 7.12.0 | 3.9 default, 3.11 instalado | só trocando o interpretador |
| EMR 7.0.0 | 3.9 (único instalado) | **não** |
| EMR 6.4.0 – 6.15.0 | 2.7 e 3.7 | **não** |

Ou seja: em **toda a série EMR 6.x e em Glue 3.0**, o único caminho para o Python
de GraphFrames é o que vem dentro do jar legado. Onde há jar (3.1, 3.2, 3.4) isso
funciona; onde não há (3.3), não há nada. É a mesma forma de `V-GE-4` e `V-DQ-2`
em [`../dq/validation-frameworks.md`](../dq/validation-frameworks.md): o piso de
Python corta antes do piso de Spark.

**Isto não vira regra própria nesta fase**, e a razão é a mesma da §4.4 de
[`graphframes-api.md`](graphframes-api.md): o `.py` não diz qual linhagem o job
usa, e o job pode estar carregando o Python do jar legado por `--py-files`. Fica
como contexto do achado de disponibilidade, não como condição.

## 5. A AWS não documenta GraphFrames — em lugar nenhum

Isto é **argumento por ausência**, e está marcado como tal. As páginas lidas para
chegar à conclusão, todas em 2026-08-05:

**Amazon EMR.** A página de release da 7.13.0 lista, uma a uma: as **24
aplicações** do release (CloudWatch Agent, Delta, Flink, HBase, HCatalog, Hadoop,
Hive, Hudi, Hue, Iceberg, JupyterEnterpriseGateway, JupyterHub, Livy, Oozie,
Phoenix, Pig, Presto, Spark, TensorFlow, Tez, Trino, Zeppelin, ZooKeeper), a
tabela de versões de aplicação, a tabela de **componentes instalados** (~80
linhas, incluindo `spark-rapids`, `nvidia-cuda`, `opencv` e `r`) e a lista de
**classificações de configuração** (~140 linhas). **GraphFrames não aparece em
nenhuma das quatro.** Não é aplicação, não é componente, não tem classificação.

**AWS Glue.** A página `Using Python libraries with AWS Glue` lista os módulos
Python providos de fábrica para as versões 2.0, 3.0, 4.0, 5.0 e 5.1 — 44 a 68
pacotes por versão. **GraphFrames não está em nenhuma das cinco listas.** A
mesma página descreve os três mecanismos de instalação
(`--additional-python-modules` com zip-of-wheels, wheel ou `requirements.txt`),
e nenhum exemplo cita GraphFrames.

**Consequência, e é ela que sustenta a regra do IaC:** a plataforma não instala,
não versiona e não suporta a biblioteca. Se um `.py` importa `graphframes`,
**alguém** precisou declarar o jar — `--extra-jars` / `--conf spark.jars.packages`
no Glue, bootstrap action ou `--packages` no EMR. Um `graph.import` sem essa
declaração no IaC é lacuna real, não estilo. `SF-GLUE-004` é o precedente de
regra que cruza extratores.

Além disso, sob o modelo de responsabilidade compartilhada que a própria página
do Glue invoca, a manutenção e as correções de segurança da biblioteca são do
cliente. Não há SLA nem correção de compatibilidade vinda da AWS para esta
dependência.

## 6. Bloco de vetos, para o cabeçalho de `rules/catalog/graph.yaml`

```
# VETOS DE DISPONIBILIDADE (2026-08-05).
# Detalhe e URLs: knowledge/graph/availability.md
#
# V-AV-1  As nove celulas sem jar sao Glue 4.0 e EMR 6.8.0-6.11.1, e o
#         discriminador e Spark 3.3.x -- nao a release. runtime_scope escrito
#         por Spark cobre as nove de uma vez e nao envelhece a cada release
#         nova de EMR.
# V-AV-2  NAO tratar "jar antigo" como "sem jar". Spark 3.1/3.2 tem
#         0.8.2 (2021-10-17), ultimo da serie. Sem manutencao NAO e sem
#         artefato, e juntar os dois numa regra so apaga a diferenca que o
#         usuario precisa para decidir.
# V-AV-3  NAO afirmar que o Python de GraphFrames falta em EMR 6.x/Glue 3.0.
#         graphframes-py exige Python >= 3.10 e nao instala la, MAS o jar
#         legado carrega 13 arquivos .py dentro dele (medido). O caminho por
#         --py-files sobre o jar continua valido.
# V-AV-4  A regra do IaC se apoia em ausencia MEDIDA na doc da AWS, nao em
#         inferencia: 4 listas do release 7.13.0 do EMR e 5 listas de modulos
#         do Glue, todas lidas, nenhuma citando GraphFrames.
# V-AV-5  NAO citar a release note da 0.8.3 como fonte de suporte a Spark 3.3.
#         Ela afirma o suporte; o artefato -spark3.3 responde 404. Para a
#         pergunta "ha o que instalar?", o repositorio vence.
```

## 7. O que a fonte NÃO sustenta

**Não afirmar que um jar de Spark 3.4 roda em Spark 3.3.** Compatibilidade
binária entre minors de Spark não é declarada por nenhuma das fontes lidas, nem
pelo projeto GraphFrames nem pela AWS. Pode funcionar; a evidência não diz. O que
está medido é **o que foi publicado para cada minor**, e a regra afirma
exatamente isso — "não há artefato para este Spark" —, nunca "não funciona".

**Não citar número para downloads, adoção ou uso em produção.** Nenhuma fonte
lida publica isso.

**A `0.11.0` roda testes contra Spark 4.1** (_"run tests agains spark 4.1"_, PR
#787), mas nenhum `artifactId` `graphframes-spark41` existe no Maven Central. Não
inferir suporte publicado a partir de CI.

**A ausência de GraphFrames na documentação da AWS foi verificada em duas
páginas, não na documentação inteira.** As duas foram escolhidas por serem as
listas canônicas e exaustivas — aplicações/componentes do EMR, módulos providos
do Glue. Busca dirigida no domínio `docs.aws.amazon.com` também não devolveu
página alguma sobre GraphFrames. Não há blog da AWS sobre o assunto nos
resultados. Isso é forte, e ainda assim é ausência: se surgir página, esta seção
está errada e o jeito de descobrir é o alarme de frescor.

**As datas desta página vêm da API do GitHub (`published_at`), do
`maven-metadata.xml` e da listagem do spark-packages.** A renderização HTML da
página de releases do GitHub, lida por resumo automático, devolveu anos errados
para a série 0.10–0.12 e **não** foi usada.

## Fontes

**Artefatos, que é onde "existe" se decide**

- `maven-metadata.xml` de `io.graphframes:graphframes-spark3_2.12`. https://repo1.maven.org/maven2/io/graphframes/graphframes-spark3_2.12/maven-metadata.xml (retrieved 2026-08-05)
- `maven-metadata.xml` de `io.graphframes:graphframes-spark3_2.13`. https://repo1.maven.org/maven2/io/graphframes/graphframes-spark3_2.13/maven-metadata.xml (retrieved 2026-08-05)
- `maven-metadata.xml` de `io.graphframes:graphframes-spark4_2.13`. https://repo1.maven.org/maven2/io/graphframes/graphframes-spark4_2.13/maven-metadata.xml (retrieved 2026-08-05)
- POM de `graphframes-spark3_2.12:0.12.1` — `spark-sql_2.12:3.5.8` `provided`. https://repo1.maven.org/maven2/io/graphframes/graphframes-spark3_2.12/0.12.1/graphframes-spark3_2.12-0.12.1.pom (retrieved 2026-08-05)
- POM de `graphframes-spark3_2.12:0.9.2` — `spark-sql_2.12:3.5.5` `provided`. https://repo1.maven.org/maven2/io/graphframes/graphframes-spark3_2.12/0.9.2/graphframes-spark3_2.12-0.9.2.pom (retrieved 2026-08-05)
- Listagem de versões da linhagem legada no spark-packages. https://spark-packages.org/package/graphframes/graphframes (retrieved 2026-08-05)
- Presença/ausência dos jars `0.8.2-spark3.1`, `0.8.2-spark3.2` (200), `0.8.3-spark3.3`, `0.8.4-spark3.3`, `0.8.4-spark3.4` (404), `0.8.3-spark3.4`, `0.8.3-spark3.5`, `0.8.4-spark3.5` (200), sob `https://repos.spark-packages.org/graphframes/graphframes/<versão>/` (retrieved 2026-08-05). A base está em crase de propósito: ela responde `NoSuchKey`/404 e vigiá-la daria alarme permanente — é o caso que `refresh_knowledge.py:210-214` descreve
- Conteúdo `.py` dos jars `graphframes-0.8.2-spark3.2-s_2.12.jar` (13 arquivos) e `graphframes-spark3_2.12-0.12.1.jar` (zero), lidos como zip (retrieved 2026-08-05)
- Release notes por tag, via API. https://api.github.com/repos/graphframes/graphframes/releases (retrieved 2026-08-05)
- Installation — coordenadas Maven e `pip install graphframes-py`. https://graphframes.io/02-quick-start/01-installation.html (retrieved 2026-08-05)

**PyPI**

- Metadados de `graphframes-py` (`0.12.1` de 2026-06-17, `requires_python >=3.10` em todas as releases). https://pypi.org/pypi/graphframes-py/json (retrieved 2026-08-05)
- Metadados de `graphframes` (`0.6`, 2018-12-05, abandonado). https://pypi.org/pypi/graphframes/json (retrieved 2026-08-05)

**AWS — as listas onde GraphFrames não aparece**

- Amazon EMR release 7.13.0 — aplicações, versões de aplicação, componentes instalados e classificações de configuração. https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-7130-release.html (retrieved 2026-08-05)
- Using Python libraries with AWS Glue — "Python modules already provided in AWS Glue" para 2.0, 3.0, 4.0, 5.0 e 5.1, e os mecanismos de instalação. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-python-libraries.html (retrieved 2026-08-05)

**Deste repositório**

- `GLUE_MATRIX` e `EMR_MATRIX` em [`../../sparkforge/facts/runtime_detect.py`](../../sparkforge/facts/runtime_detect.py) — 4 releases de Glue e 30 de EMR, com a versão de Spark de cada.
- [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md) — a mesma matriz em prosa, e a nota de que a AWS não documenta o Python do PySpark na série 6.x.
- [`../dq/validation-frameworks.md`](../dq/validation-frameworks.md) — a forma de `V-GE-4`/`V-DQ-2`, em que o piso de Python corta antes do piso de Spark.
