# Matriz de runtime Amazon EMR on EKS

A `EMR_MATRIX` de EMR on EC2 (`knowledge/emr/runtime-matrix.md`) **não** se aplica
a EMR on EKS e não pode ser reusada para preencher eixo nenhum deste runtime.
O `STATUS.md` registra a dívida aberta em que exatamente isso aconteceu com EMR
Serverless: `judge --emr` grava `spark`, `python` e `iceberg` derivados da matriz
de EC2 sobre facts que não têm um único fact de EC2 — três campos inventados sobre
um artefato que não declara nenhum deles.

---

Esta página existe para responder a bifurcação **D-4** da fase de EMR on EKS: a
AWS publica, para EMR on EKS, uma matriz que ligue `releaseLabel` a versão de
Spark, Python e Iceberg?

**A resposta é sim para Spark, Iceberg, Hudi e Delta; é não para Python e não
para Hadoop.** E — este é o achado que decide o desenho — **onde a matriz existe,
ela diverge da de EC2 em células reais**, não só em grafia. A `EMR_MATRIX` não é
inaplicável por falta de fonte, como no Serverless: ela é inaplicável porque
**está medidamente errada** em 4 células de Spark e 6 de Iceberg.

Diferente de [`../emr-serverless/runtime-matrix.md`](../emr-serverless/runtime-matrix.md),
que concluiu "não há matriz", esta página conclui "há matriz, e ela é **outra**".
As duas conclusões levam ao mesmo lugar operacional — `EMR_MATRIX` não se
reaproveita — por razões opostas, e a diferença muda o que a Task 6 e a Task 10
podem fazer (§6).

## 1. Onde a fonte publica, e em que formato

Não existe página-resumo com tabela de componentes. A página-índice do EKS
(`https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-releases.html`,
lida em 2026-08-31) traz só prosa mais uma lista *Topics* de links por release — nenhuma
tabela. Confronte com as duas *Application versions* de EMR on EC2
(`.../ReleaseGuide/emr-release-app-versions-7.x.html` e `-6.x.html`), que são exatamente
a tabela que o EKS não tem. O que existe é **uma página por família de release**, e
o dado mora numa linha de release note:

> *"**Supported applications** ‐ AWS SDK for Java 2.42.12 and 1.12.797, Apache
> Spark 3.5.6-amzn-2, Apache Hudi 1.0.2-amzn-2, Apache Iceberg 1.10.0-amzn-1,
> Delta 3.3.2-amzn-2, Apache Spark RAPIDS 25.04.0-amzn-0, Apache Flink
> 1.20.0-amzn-7"*
> — release notes de `emr-7.13.0` em EMR on EKS

**34 páginas** foram lidas uma a uma em 2026-08-31: `emr-spark-8.0.0`, as 14 da
série 7.x (7.0.0–7.13.0), as 14 da série 6.x (6.2.0–6.15.0) e as 5 da série 5.x
(5.32.0–5.36.0).

O que cada coluna tem, e com que confiança:

| Componente | Publicado? | Formato | Confiança |
|---|---|---|---|
| Spark | **sim**, em 34 de 34 | `{comunidade}-amzn-{N}`, com **duas exceções** (§2) | **alta** — lido verbatim |
| Iceberg | **sim**, em 25 de 34 | `{versão}-amzn-{N}`, com exceções antigas sem sufixo | **alta** onde existe; **ausente**, não zero, onde não existe |
| Hudi | sim, em 26 de 34 | idem | alta |
| Delta | sim, em 22 de 34 | idem | alta |
| Spark RAPIDS, Flink, Flink Operator, JEG, AWS SDK | sim, parcial | variado | alta, fora de escopo do motor |
| **Hadoop** | **NÃO, em 34 de 34** | — | **não publicado** (§4) |
| **Python** | **quase não** — 2 de 34 | prosa, não tabela | **não publicado por release** (§4) |

**As contagens acima são das células das §2, §3 e da tabela de Hudi/Delta, e são
conferíveis linha a linha.** Quem não publica o quê:

| Componente | Releases em que a fonte **não** publica |
|---|---|
| Iceberg (9) | `emr-6.5.0`, `emr-6.4.0`, `emr-6.3.0`, `emr-6.2.0` e as cinco de 5.x |
| Hudi (8) | `emr-6.5.0`, `emr-6.4.0`, `emr-6.3.0`, `emr-6.2.0`, `emr-5.36.0`, `emr-5.34.0`, `emr-5.33.0`, `emr-5.32.0` |
| Delta (12) | as oito acima, mais `emr-6.8.0`, `emr-6.7.0`, `emr-6.6.0` e `emr-5.35.0` |

Ausente aqui significa **a linha *Supported applications* daquela release não nomeia o
componente**. Não significa que ele não exista na imagem — significa que a fonte não
o declara, e o extrator omite a chave.

Confronte com a de EC2, que publica Hadoop e Python por release em tabela, e com
a do Serverless, que publica só Spark, Hive e Tez. As três fontes têm **três
formatos diferentes** para o mesmo dado, e nenhuma é derivável das outras.

## 2. Matriz — série 7.x e `emr-spark-8.0.0`

Coluna *EKS* lida da página própria de cada release em 2026-08-31. Coluna *EC2*
copiada de [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md). A coluna
*bate* compara as duas **strings inteiras**, com o sufixo do fork.

| Release | Spark (EKS) | Spark (EC2) | bate | Iceberg (EKS) | Iceberg (EC2) | bate |
|---|---|---|---|---|---|---|
| emr-spark-8.0.0 | 4.0.2-amzn-0 | *(não está na `EMR_MATRIX`)* | — | 1.10.1-amzn-0 | — | — |
| emr-7.13.0 | 3.5.6-amzn-2 | 3.5.6-amzn-2 | sim | 1.10.0-amzn-1 | 1.10.0-amzn-1 | sim |
| emr-7.12.0 | 3.5.6-amzn-1 | 3.5.6-amzn-1 | sim | 1.10.0-amzn-0 | 1.10.0-amzn-0 | sim |
| emr-7.11.0 | 3.5.6-amzn-0 | 3.5.6-amzn-0 | sim | 1.9.1-amzn-0 | 1.9.1-amzn-0 | sim |
| emr-7.10.0 | 3.5.5-amzn-1 | 3.5.5-amzn-1 | sim | 1.8.1-amzn-0 | 1.8.1-amzn-0 | sim |
| emr-7.9.0 | **3.5.5** | 3.5.5-amzn-0 | **NÃO** | 1.7.1-amzn-2 | 1.7.1-amzn-2 | sim |
| emr-7.8.0 | **3.5.4** | 3.5.4-amzn-0 | **NÃO** | 1.7.1-amzn-1 | 1.7.1-amzn-1 | sim |
| emr-7.7.0 | **3.5.3-amzn-0** | 3.5.3-amzn-1 | **NÃO** | **1.6.1-amzn-2** | 1.7.1-amzn-0 | **NÃO** |
| emr-7.6.0 | 3.5.3-amzn-0 | 3.5.3-amzn-0 | sim | 1.6.1-amzn-2 | 1.6.1-amzn-2 | sim |
| emr-7.5.0 | 3.5.2-amzn-1 | 3.5.2-amzn-1 | sim | **1.6.1-amzn-0** | 1.6.1-amzn-1 | **NÃO** |
| emr-7.4.0 | 3.5.2-amzn-0 | 3.5.2-amzn-0 | sim | 1.6.1-amzn-0 | 1.6.1-amzn-0 | sim |
| emr-7.3.0 | 3.5.1-amzn-1 | 3.5.1-amzn-1 | sim | 1.5.2-amzn-0 | 1.5.2-amzn-0 | sim |
| emr-7.2.0 | **3.5.1-amzn-1** | 3.5.1-amzn-0 | **NÃO** | 1.5.0-amzn-0 | 1.5.0-amzn-0 | sim |
| emr-7.1.0 | 3.5.0-amzn-1 | 3.5.0-amzn-1 | sim | 1.4.3-amzn-0 | 1.4.3-amzn-0 | sim |
| emr-7.0.0 | 3.5.0-amzn-0 | 3.5.0-amzn-0 | sim | 1.4.2-amzn-0 | 1.4.2-amzn-0 | sim |

## 3. Matriz — séries 6.x e 5.x

| Release | Spark (EKS) | Spark (EC2) | bate | Iceberg (EKS) | Iceberg (EC2) | bate |
|---|---|---|---|---|---|---|
| emr-6.15.0 | 3.4.1-amzn-2 | 3.4.1-amzn-2 | sim | 1.4.0-amzn-0 | 1.4.0-amzn-0 | sim |
| emr-6.14.0 | 3.4.1-amzn-1 | 3.4.1-amzn-1 | sim | **1.3.0-amzn-0** | 1.3.1-amzn-0 | **NÃO** |
| emr-6.13.0 | 3.4.1-amzn-0 | 3.4.1-amzn-0 | sim | **1.3.0-amzn-0** | 1.3.0-amzn-1 | **NÃO** |
| emr-6.12.0 | 3.4.0-amzn-0 | 3.4.0-amzn-0 | sim | 1.3.0-amzn-0 | 1.3.0-amzn-0 | sim |
| emr-6.11.0 | 3.3.2-amzn-0 | 3.3.2-amzn-0 | sim | 1.2.0-amzn-0 | 1.2.0-amzn-0 | sim |
| emr-6.10.0 | 3.3.1-amzn-0 | 3.3.1-amzn-0 | sim | 1.1.0-amzn-0 | 1.1.0-amzn-0 | sim |
| emr-6.9.0 | 3.3.0-amzn-1 | 3.3.0-amzn-1 | sim | 0.14.1-amzn-0 | 0.14.1-amzn-0 | sim |
| emr-6.8.0 | 3.3.0-amzn-0 | 3.3.0-amzn-0 | sim | 0.14.0-amzn-0 | 0.14.0-amzn-0 | sim |
| emr-6.7.0 | 3.2.1-amzn-0 | 3.2.1-amzn-0 | sim | **0.13.1** | 0.13.1-amzn-0 | **NÃO** |
| emr-6.6.0 | 3.2.0-amzn-0 | 3.2.0-amzn-0 | sim | 0.13.1 | 0.13.1 | sim |
| emr-6.5.0 | 3.1.2-amzn-1 | 3.1.2-amzn-1 | sim | **não publicado** | 0.12.0 | **NÃO** |
| emr-6.4.0 | 3.1.2-amzn-0 | 3.1.2-amzn-0 | sim | não publicado | — | — |
| emr-6.3.0 | 3.1.1-amzn-0 | *(fora da `EMR_MATRIX`)* | — | não publicado | — | — |
| emr-6.2.0 | 3.0.1-amzn-0 | *(fora da `EMR_MATRIX`)* | — | não publicado | — | — |
| emr-5.36.0 | 2.4.8-amzn-2 | *(fora)* | — | não publicado | — | — |
| emr-5.35.0 | 2.4.8-amzn-1 | *(fora)* | — | não publicado | — | — |
| emr-5.34.0 | 2.4.8-amzn-0 | *(fora)* | — | não publicado | — | — |
| emr-5.33.0 | 2.4.7-amzn-1 | *(fora)* | — | não publicado | — | — |
| emr-5.32.0 | 2.4.7-amzn-0 | *(fora)* | — | não publicado | — | — |

Hudi e Delta, para as releases em que a fonte do EKS os publica, ficam
registrados aqui sem coluna de comparação — a `EMR_MATRIX` não guarda esses dois
eixos, então não há com o que confrontar:

| Release | Hudi (EKS) | Delta (EKS) |
|---|---|---|
| emr-spark-8.0.0 | 1.1.0-amzn-0 | 4.0.0-amzn-1-spark |
| emr-7.13.0 | 1.0.2-amzn-2 | 3.3.2-amzn-2 |
| emr-7.12.0 | 1.0.2-amzn-1 | 3.3.2-amzn-1 |
| emr-7.11.0 | 1.0.2-amzn-0 | 3.3.2-amzn-0 |
| emr-7.10.0 | 0.15.0-amzn-7 | 3.3.0-amzn-2 |
| emr-7.9.0 | 0.15.0-amzn-6 | 3.3.0-amzn-1 |
| emr-7.8.0 | 0.15.0-amzn-5 | 3.3.0-amzn-0 |
| emr-7.7.0 | 0.15.0-amzn-3 | 3.2.1-amzn-1 |
| emr-7.6.0 | 0.15.0-amzn-3 | 3.2.1-amzn-1 |
| emr-7.5.0 | 0.15.0-amzn-1 | 3.2.0-amzn-1 |
| emr-7.4.0 | 0.15.0-amzn-1 | 3.2.0-amzn-1 |
| emr-7.3.0 | 0.15.0-amzn-0 | 3.2.0-amzn-0 |
| emr-7.2.0 | 0.14.1-amzn-0 | 3.1.0 |
| emr-7.1.0 | 0.14.1-amzn-0 | 3.0.0 |
| emr-7.0.0 | 0.14.0-amzn-1 | 3.0.0 |
| emr-6.15.0 | 0.14.0-amzn-0 | 2.4.0 |
| emr-6.14.0 | 0.13.1-amzn-2 | 2.4.0 |
| emr-6.13.0 | 0.13.1-amzn-0 | 2.4.0 |
| emr-6.12.0 | 0.13.1-amzn-0 | 2.4.0 |
| emr-6.11.0 | 0.13.0-amzn-0 | 2.2.0 |
| emr-6.10.0 | 0.12.2-amzn-0 | 2.2.0 |
| emr-6.9.0 | 0.12.1-amzn-0 | 2.1.0 |
| emr-6.8.0 | 0.11.1-amzn-0 | não publicado |
| emr-6.7.0 | 0.11-amzn-0 | não publicado |
| emr-6.6.0 | 0.10.1-amzn-0 | não publicado |
| emr-5.35.0 | 0.9.0-amzn-2 | não publicado |

Repare em `emr-6.7.0`: **`0.11-amzn-0`**, com dois segmentos antes do sufixo,
não três. Qualquer parser de versão desta área precisa tolerar isso — e a
`emr-spark-8.0.0` traz `4.0.0-amzn-1-spark`, com um segmento **depois** do
sufixo. As duas formas são raras e as duas são reais.

## 4. As duas colunas que não existem, e uma que existe em prosa

**Hadoop: não publicado, em nenhuma das 34 páginas.** A linha *Supported
components* nomeia `hadoop-client` como componente — um nome, sem versão. Isso
não é uma versão de Hadoop; é a declaração de que o cliente está presente. A
coluna `hadoop` de `EMR_MATRIX` **não tem contraparte** no EKS, e copiá-la seria
afirmar um número que a fonte do EKS não publica.

**Python: publicado em 2 de 34 páginas, e nas duas em prosa de "Changes and
features", não em tabela.** Os dois pontos, verbatim:

> *"**Python 3.11 default for PySpark and Spark workloads** – Python 3.11 is now
> the default Python version for PySpark and Spark workloads. Python 3.9 remains
> the default for all other applications. Both Python 3.9 and 3.11 are included
> in the release."*
> — `emr-7.13.0` em EMR on EKS

> *"**Python 3.11 default** – Python 3.11 is the default for PySpark and Spark
> workloads. Python 3.12 and 3.13 are also available."*
> — `emr-spark-8.0.0` em EMR on EKS

Dois pontos não são uma matriz. Para as outras 32 releases, **o Python do
PySpark não tem valor de fonte no lado do EKS**. É a mesma situação que deixou a
coluna *Python do PySpark* vazia em toda a série 6.x de EC2, e a mesma decisão se
aplica: chave ausente, não valor plausível.

**Uma armadilha específica do EKS na coluna de Java**, que não tem análogo em
EC2 nem em Serverless: o runtime de Java **é escolhido pelo release label**, não
por configuração. `emr-7.13.0-java8-latest` e `emr-7.13.0-java11-latest` são o
mesmo Spark rodando em JVMs diferentes, e a partir de 7.0.0 o default é Java 17
(*"Amazon EMR on EKS 7.0.0 Spark uses Java 17 as default runtime"*). E há uma
consequência de escopo em 7.7.0: *"The Iceberg version in use as of EMR 7.7.0 no
longer supports Java 8. Additionally, Iceberg is excluded from the following
Java 8 images: `emr-7.7.0-java8-latest` and
`emr-7.7.0-spark-rapids-java8-latest`."* — isto é, **a mesma release tem ou não
tem Iceberg, dependendo do sufixo do label**. Nenhuma matriz indexada só pela
release resolve isso.

## 5. As releases que só um dos dois tem

**8 famílias existem no EKS e não na `EMR_MATRIX`:** `emr-spark-8.0.0`,
`emr-6.3.0`, `emr-6.2.0` e as cinco de 5.x (5.32.0 a 5.36.0). A `EMR_MATRIX`
para em 6.4.0 por decisão registrada em `../emr/runtime-matrix.md` §3 — abaixo
disso não há Iceberg nem Spark ≥ 3.2 e nenhuma regra muda de aplicabilidade. A
série 5.x do EKS roda **Spark 2.4.x**, que está abaixo do piso de quase tudo
neste catálogo.

O piso do EKS é declarado: *"Beginning with Amazon EMR releases 5.32.0 and
6.2.0, you can deploy Amazon EMR on EKS. This deployment option is not available
with earlier Amazon EMR release versions."*

**4 releases existem na `EMR_MATRIX` e não no EKS:** `emr-6.8.1`, `emr-6.9.1`,
`emr-6.10.1` e `emr-6.11.1` — exatamente as quatro de patch que usam a forma de
sufixo de dois níveis (`3.3.2-amzn-0.1`) e que quebraram `version_scope.py` na
Fase 5b. **No EKS elas não existem**, do mesmo jeito que não existem no
Serverless. Aquele modo de falha não tem como reaparecer por esta porta.

## 6. A decisão, e o que ela permite que a do Serverless não permitia

**D-4 resolve como: a AWS publica matriz de release para EMR on EKS, ela cobre
Spark, Iceberg, Hudi e Delta, não cobre Hadoop nem Python, e a `EMR_MATRIX` de
EC2 continua proibida como fonte para este runtime.**

O argumento contra reusar `EMR_MATRIX` aqui é **mais forte** do que o do
Serverless, e por natureza diferente:

- No Serverless, a fonte não publica — reusar a de EC2 seria afirmar sem base.
- No EKS, a fonte **publica**, e em **4 de 26** releases comparáveis o Spark
  discorda, e em **6 de 26** o Iceberg discorda. Reusar a de EC2 não seria
  afirmar sem base: seria afirmar **contra** a base.

As divergências não são de arredondamento. `emr-7.7.0` roda Iceberg
`1.6.1-amzn-2` no EKS e `1.7.1-amzn-0` no EC2 — **minor diferente**, o que muda a
aplicabilidade de qualquer regra `SF-ICE-*` com range. `emr-6.5.0` **não publica
Iceberg nenhum** no EKS enquanto o EC2 publica `0.12.0` — uma regra derivada da
matriz de EC2 avaliaria regra de Iceberg num runtime que não declara Iceberg.

**A consequência para as Tasks 6 e 10 é diferente da do Serverless, e é a parte
que muda o escopo:**

| | EMR Serverless (Fase 5d) | EMR on EKS (esta fase) |
|---|---|---|
| Existe matriz da própria fonte? | não | **sim**, para Spark e Iceberg |
| `runtime_scope` das regras | `{}`, sempre | **pode carregar `spark` e `iceberg`** — ver a condição abaixo |
| `runtime` das fixtures | `{}`, sempre | **pode ser preenchido** para as releases da §2/§3 |
| Espelho executável desta página | não existe | **pode existir**, e seria `EMR_EKS_MATRIX`, separada |

**A condição, e ela é dura.** Preencher `runtime_scope` a partir do
`releaseLabel` só é honesto se três coisas valerem juntas:

1. **O label é parseável até a release**, isto é, casa com
   `emr-<major>.<minor>.<patch>-<sufixo>`. `emr-spark-8.0.0-latest` não casa, e
   `notebook-spark/emr-7.13.0-latest` só casa depois de descartar o prefixo. Sem
   parse, `runtime_scope: {}` e fact `emrk.unresolved`.
2. **O sufixo não é `-latest`, ou o achado tolera imprecisão.** `-latest` é
   ponteiro móvel: a fonte diz que ele existe justamente para se mover. Duas
   execuções com o mesmo `emr-7.13.0-latest` podem ter rodado imagens
   diferentes. A release **família** continua conhecida; o binário exato, não.
3. **O sufixo de variante não muda a resposta.** `emr-7.7.0-java8-latest` **não
   tem Iceberg**, e a matriz da §2 diz `1.6.1-amzn-2` para `emr-7.7.0`. Uma
   derivação que ignore o sufixo erra nessa célula. Enquanto a §4 não tiver uma
   tabela por variante — e ela não tem —, **derivar `iceberg` a partir do label
   é seguro só quando o label não carrega variante de Java**.

Dado o item 3, a recomendação desta página para a Task 10 é conservadora:
**derivar `spark` sim, derivar `iceberg` não**, até que alguém meça a tabela por
variante. Spark é o mesmo em todas as variantes de uma release (o que muda é a
JVM); Iceberg comprovadamente não é. Uma regra `SF-ICE-*` com `runtime_scope`
derivado do label seria pulada ou aplicada errado exatamente nas imagens Java 8.

O princípio de `../emr/runtime-matrix.md` §4.3 continua valendo em cima disso: a
derivação por matriz é **fallback** e perde para observação direta, marcada com o
sufixo `:matrix` na origem. Aqui a observação direta seria o event log (a aba
*Environment* traz a versão efetiva) — e o event log só existe se
`persistentAppUI` estiver `ENABLED`, o que liga esta página à §5 de
[`job-run-configuration.md`](job-run-configuration.md).

**O que reabriria a decisão:** a AWS publicar uma tabela de componentes **por
release label completo** (com a variante), ou publicar Python por release. Até
lá, as duas colunas ficam vazias e a derivação de Iceberg fica de fora.

## 7. Como manter esta página

O caminho de manutenção de `../emr/runtime-matrix.md` §5 —
`aws emr describe-release-label` — **não** foi verificado contra release de EMR
on EKS nesta coleta, e não deve ser assumido. As 34 páginas por família de
release são a fonte conferida.

O perfil de drift é o mesmo churn estrutural do Serverless, com um agravante: além
de a página-índice ganhar uma entrada a cada minor, **cada página por release
ganha entradas novas de release label** quando sai uma imagem com data nova
(`emr-7.13.0-20260410` hoje, outra data amanhã, e a `-latest` apontando para a
mais nova). Isto é: o hash de uma página de release **não** é estável entre
coletas como é no Serverless. A linha *Supported applications* é a parte estável;
a lista de labels não é.

## Fontes

- Amazon EMR on EKS releases (índice, o piso 5.32.0/6.2.0 e a forma declarada do release label). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-releases.html (retrieved 2026-08-31)
- **As 34 páginas por família de release**, lidas uma a uma em 2026-08-31 pela linha *Supported applications*. Elas são a fonte de **todas** as células das §2, §3 e da tabela de Hudi/Delta, e por isso estão listadas uma a uma — são o que a §7 mede como tendo o **maior** drift do documento, e descrevê-las por padrão de URL as deixaria fora da vigilância de frescor:
  - AWS runtime for Apache Spark (emr-spark-8.0.0) on EKS (Spark 4.0.2-amzn-0; declara Python 3.11 default). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-spark-8.0.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.13.0 releases (a única página numerada que declara Python). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.13.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.12.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.12.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.11.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.11.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.10.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.10.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.9.0 releases (Spark **sem** sufixo de fork — divergência da §2). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.9.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.8.0 releases (Spark **sem** sufixo de fork — divergência da §2). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.8.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.7.0 releases (Iceberg excluído das imagens Java 8; diverge do EC2 em Spark **e** Iceberg). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.7.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.6.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.6.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.5.0 releases (Iceberg diverge do EC2). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.5.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.4.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.4.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.3.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.3.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.2.0 releases (Spark diverge do EC2). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.2.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.1.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.1.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 7.0.0 releases (Java 17 como default, e Amazon Linux 2023). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-7.0.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.15.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.15.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.14.0 releases (Iceberg diverge do EC2). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.14.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.13.0 releases (Iceberg diverge do EC2). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.13.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.12.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.12.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.11.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.11.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.10.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.10.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.9.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.9.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.8.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.8.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.7.0 releases (Iceberg sem sufixo, e Hudi em dois segmentos: `0.11-amzn-0`). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.7.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.6.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.6.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.5.0 releases (**não publica Iceberg**, enquanto o EC2 publica `0.12.0`). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.5.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.4.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.4.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.3.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.3.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 6.2.0 releases (piso da série 6.x). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-6.2.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 5.36.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-5.36.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 5.35.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-5.35.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 5.34.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-5.34.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 5.33.0 releases. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-5.33.0.html (retrieved 2026-08-31)
  - Amazon EMR on EKS 5.32.0 releases (a release mais antiga que existe). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-5.32.0.html (retrieved 2026-08-31)
- Matriz de runtime Amazon EMR on EC2 (a coluna *EC2* das §2 e §3 vem daqui, não de coleta nova). [`../emr/runtime-matrix.md`](../emr/runtime-matrix.md)

### O que estas fontes NÃO sustentam

- **A versão de Hadoop de qualquer release de EMR on EKS.** Nenhuma das 34
  páginas a nomeia; `hadoop-client` na linha *Supported components* é um nome de
  componente, não uma versão. **Não citar número**, nem o do EC2 da mesma
  release.
- **O Python do PySpark de 32 das 34 releases.** Há dois pontos, em prosa
  (`emr-7.13.0` e `emr-spark-8.0.0`), e ambos anunciam uma **virada**, não um
  estado por release. **Não interpolar** para as outras, e não importar
  `python_installed` da `EMR_MATRIX`.
- **A versão de componente por *variante* de release label.** A linha *Supported
  applications* é publicada por família (`emr-7.7.0`), e a própria 7.7.0 declara
  que Iceberg **não está** nas imagens Java 8. Não existe tabela por variante
  nesta coleta, e por isso a derivação de `iceberg` a partir do label fica
  vetada (§6).
- **Que a imagem por trás de `-latest` seja estável.** A fonte declara o
  contrário: *"When you use the `-latest` suffix, you ensure that your Amazon EMR
  version always includes the latest security updates."* Dois runs com o mesmo
  label `-latest` **não** provam o mesmo binário.
- **Que as divergências medidas nas §2 e §3 sejam erro de documentação de um dos
  dois lados.** O que se mediu é que as duas fontes publicam strings diferentes
  para a mesma release label. Se isso reflete binários diferentes ou apenas
  redação diferente das release notes, esta coleta **não sabe** — e as duas
  leituras levam à mesma proibição de reuso.
- **Que `3.5.5` no EKS e `3.5.5-amzn-0` no EC2 sejam o mesmo binário.** As duas
  páginas de 7.8.0 e 7.9.0 do EKS omitem o sufixo do fork que todas as suas
  vizinhas trazem. Isso é a fonte sendo inconsistente consigo mesma; não é
  evidência de que o fork não exista ali, nem de que exista.
- **A ausência definitiva de `emr-6.8.1`, `emr-6.9.1`, `emr-6.10.1` e
  `emr-6.11.1` no EKS.** O que se mediu é que não constam do índice de releases
  em 2026-08-31. Não foi testado o que a API responde a um label desses.
- **Que a lista de famílias de sufixo seja fechada.** `-latest`, `-yyyymmdd`,
  `-spark-rapids`, `-java8`, `-java11`, `-java17`, `-al2023`, `-flink`, e os
  prefixos `notebook-spark/`, `notebook-python/`, `livy/` são os que aparecem
  nesta coleta. A série 6.x tem `al2023` e a 7.x não; a 7.x tem `java8` e a 6.x
  tem `java17`. Tratar forma inesperada como não-parseável.
- **O caminho de manutenção por API.** `aws emr describe-release-label` não foi
  verificado contra release de EMR on EKS nesta coleta.
