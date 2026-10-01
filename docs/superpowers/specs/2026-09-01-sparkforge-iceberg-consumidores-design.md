# SparkForge AWS — Iceberg × consumidores × Lake Formation: `emr` não é uma engine

**Data:** 2026-09-01
**Status:** **entregue** em 2026-09-01, branch `feat/emr-eks`. Estado corrente e
números medidos: [`../STATUS.md`](../STATUS.md), seção *Iceberg × consumidores ×
Lake Formation*. Os desvios estão na §7.
**Origem:** quarto e último sub-projeto da decomposição do
`PROMPT MESTRE — EVOLUÇÃO TOTAL GLUE + EMR DO SPARKFORGE AWS.md` (§7).
Os três anteriores estão fechados.
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. O que existe

`knowledge/storage/iceberg-feature-support.yaml` já traz uma matriz
feature × engine com **9 features** (`variant`, `variant_shredding`,
`deletion_vectors`, `row_lineage`, `nanosecond_timestamp`, `geospatial_types`,
`default_values`, `multi_argument_transforms`, `native_table_encryption`) e
**6 engines** (`glue`, `athena`, `emr`, `pyiceberg`, `s3_tables`,
`lakeformation`).

Há `sparkforge/iceberg/`, `sparkforge/lakeformation/`, a tool
`sparkforge_iceberg_assess_upgrade`, a skill `iceberg-v3-readiness`, e o
`ConsumerGraph` em `sparkforge/facts/consumers.py`, que emite `env.consumer`.

## 2. O defeito medido, e ele é de granularidade

A matriz tem **uma** engine chamada `emr`. `facts/consumers.py` reconhece **um**
serviço chamado `emr`.

O sub-projeto 1 mediu que as **três** plataformas de EMR publicam versões de
Iceberg **diferentes**: divergência em **6 de 26** releases comparáveis entre EC2
e EKS. Dois casos que decidem:

- `emr-7.7.0` — Iceberg `1.7.1-amzn-0` no EC2 contra `1.6.1-amzn-2` no EKS.
  **Minor diferente**, e portanto aplicabilidade diferente de qualquer feature
  que tenha entrado entre as duas.
- `emr-6.5.0` — o EC2 publica Iceberg `0.12.0`; o EKS **não publica Iceberg
  nenhum**.

E o sub-projeto 1 mediu uma terceira coisa que a matriz não pode representar
hoje: `emr-7.7.0-java8-latest` **não tem Iceberg** enquanto `emr-7.7.0` tem — a
linha de componentes é publicada **por família, não por variante**.

**Consequência:** uma resposta de prontidão para v3 dada para "EMR" está errada
para pelo menos uma das três plataformas, e o operador não tem como saber qual.
Célula que responde por três coisas que divergem é pior que célula ausente:
ausência é recusa, e essa célula é uma afirmação.

## 3. Objetivo

Três coisas, e a primeira é pré-requisito das outras:

1. **Separar `emr` em três engines** — `emr_ec2`, `emr_serverless`, `emr_eks` —
   com a versão de Iceberg de cada uma vindo da matriz de runtime que o
   sub-projeto 2 normalizou.
2. **Completar a matriz** com as features do §7 do prompt mestre que faltam, e
   com os consumidores que o `ConsumerGraph` declara e a matriz não conhece —
   **só onde a fonte sustentar**.
3. **Cruzar com Lake Formation**, sem confundir permissão IAM com acesso efetivo
   ao dado.

### Não-objetivos, com razão registrada

- **Afirmar suporte sem fonte.** Célula sem fonte primária sai `UNKNOWN`, que já
  é vocabulário desta matriz. O §7 do prompt mestre lista seis estados
  (`SUPPORTED`, `UNSUPPORTED`, `PARTIAL`, `ENGINE_DEPENDENT`,
  `VERSION_DEPENDENT`, `UNKNOWN`) — use-os.
- **Regra nova de diagnóstico**, a menos que a fonte sustente julgamento. Se
  sustentar, ela entra com golden positivo e negativo, como toda regra.
- **Converter tabela v2→v3.** A conversão é `ONE_WAY` e `NON_REVERSIBLE`; este
  sub-projeto informa a decisão, não a executa.

## 4. Decisões de desenho

### D-1 — a engine é a plataforma, e a versão de Iceberg vem da matriz de runtime

`emr_ec2`, `emr_serverless` e `emr_eks` são engines distintas. A versão de
Iceberg de cada uma, por release, já está em
`knowledge/<plataforma>/runtime-matrix.yaml`, carregada por `runtime_matrix`.

**A matriz de feature não repete a versão** — ela declara a partir de qual versão
de Iceberg a feature existe, e o cruzamento com a release é calculado. Repetir a
versão criaria a terceira cópia do mesmo fato, que é o defeito que o sub-projeto 2
existiu para remover.

O que a granularidade **não** alcança está declarado: variante de imagem
(`emr-7.7.0-java8-latest`) não é chave da matriz de runtime, então a resposta é
por família e o limite fica escrito.

### D-2 — engine que o `ConsumerGraph` declara e a matriz não conhece é lacuna nomeada

`facts/consumers.py` reconhece hoje `athena`, `redshift`, `emr`, `quicksight`,
`sagemaker`, `glue`, `spark`, `trino`. O §7 do prompt mestre pede também `flink`,
`bigquery`, `pyiceberg` e clientes REST.

**Meça o overlap antes de acrescentar.** Consumidor declarado sem linha na matriz
precisa produzir `UNKNOWN` **nomeado** — não silêncio, e não `SUPPORTED` por
omissão. É a diferença entre "este consumidor não foi avaliado" e "este
consumidor está bem".

### D-3 — IAM não é prova de acesso ao dado

O §7 do prompt mestre é explícito: *"Não trate permissão IAM como prova de acesso
efetivo aos dados."* Lake Formation, S3, KMS e Glue Catalog são camadas
**separadas**, e a matriz precisa refletir isso — uma feature pode ser suportada
pela engine e inacessível pela FGAC.

As combinações que o prompt nomeia (`VARIANT × FGAC`, `v3 × FGAC`,
`DELETE/MERGE × FGAC`, `REST Catalog × Lake Formation`) entram **somente quando
confirmadas por fonte**, e o resto sai `UNKNOWN`.

### D-4 — o veredito de conversão continua sendo bloqueio, não conselho

`v2 → v3` é `ONE_WAY` e `NON_REVERSIBLE`. Quando um consumidor **declarado** não
tiver suporte demonstrado, o resultado é bloqueio — não aviso. A skill
`iceberg-v3-readiness` já existe e não é despachável de propósito, porque exige o
inventário de consumidores; preserve essa fronteira.

## 5. Testes e gates

- Toda célula da matriz: ou tem estado com fonte, ou é `UNKNOWN` com razão.
  Nenhuma vazia.
- **O contrafactual da granularidade:** prontidão de `emr-7.7.0` responde
  **diferente** para `emr_ec2` e `emr_eks` em pelo menos uma feature. É o teste
  que prova que a separação não foi cosmética.
- `emr-6.5.0` no EKS: Iceberg ausente produz recusa nomeada, não `UNSUPPORTED`
  (não saber que versão roda é diferente de saber que não suporta).
- Consumidor declarado sem linha na matriz produz `UNKNOWN` nomeado.
- Nenhuma regressão em `sparkforge_iceberg_assess_upgrade` nem nos goldens de
  `fixtures/iceberg/` e `fixtures/consumers/`.
- Gates de sempre: `refresh_knowledge --offline --update`,
  `check_surface_lock.py --update`, `check_vnext_claims.py` em exit 0, suíte em
  lotes.

## 6. Critérios de conclusão

- `emr` não existe mais como engine única; as três plataformas respondem
  separadamente, e há teste que as vê divergir.
- Toda feature do §7 do prompt mestre ou está na matriz com fonte, ou está
  registrada como lacuna com a medida que a destravaria.
- Consumidor sem avaliação sai `UNKNOWN` nomeado, nunca silêncio.
- IAM e Lake Formation aparecem como camadas separadas.
- Gates verdes.

## 7. Desvios

Quatro, e os quatro são de *como*, não de *o quê*. A spec é registro histórico;
o estado corrente está em [`../STATUS.md`](../STATUS.md).

1. **A D-1 dizia "a versão de Iceberg vem da matriz de runtime" e não dizia
   COMO.** O mecanismo escolhido é `min_library_version` por feature — a primeira
   release cujas notas curadas do Apache Iceberg nomeiam a capacidade — e um
   módulo novo, `sparkforge/storage/readiness.py`, que cruza esse limite inferior
   com a versão publicada por cada plataforma. A escolha carrega uma restrição
   que a spec não previa e que está gravada em código: atender o mínimo **nunca**
   promove uma célula a `SUPPORTED`. O mínimo só decide na direção negativa.

2. **Duas features ficaram sem mínimo, e isso não estava previsto.**
   `variant_shredding` e `multi_argument_transforms` não são nomeadas em release
   nenhuma nas notas curadas lidas (1.6.0 a 1.10.1). Elas saem `UNKNOWN` com a
   razão `min_library_version_ausente` em vez de receberem um número plausível.

3. **Dois status novos entraram no vocabulário fechado.** O §7 do prompt mestre
   lista `ENGINE_DEPENDENT` e `VERSION_DEPENDENT`, e a matriz não os tinha. Eles
   entraram **com consumidor real** — `ENGINE_DEPENDENT` em
   `rest_catalog.rest_client`, `VERSION_DEPENDENT` disponível para célula cuja
   resposta só existe com a release na mão. Vocabulário sem consumidor seria
   etiqueta decorativa, e este repositório recusa isso em toda parte.

4. **`emr` continua reconhecido pelo `ConsumerGraph`.** A D-2 pedia que
   consumidor sem linha na matriz produzisse `UNKNOWN` nomeado, e a leitura mais
   simples seria remover `emr` de `KNOWN_SERVICES`. Medido antes de decidir:
   remover converteria todo inventário já escrito em `known_service: false`, que
   é um alarme sobre **grafia** para um problema que é de **ambiguidade**. O nome
   fica reconhecido, e quem o resolve é `assess_upgrade`, com uma frase própria
   que nomeia as três plataformas a declarar.

### O que ficou como lacuna registrada

- Nenhuma fonte de feature de Iceberg foi lida para `emr_ec2`, `emr_serverless`,
  `emr_eks`, `redshift`, `trino`, `spark`, `flink`, `pyiceberg`, `bigquery` e
  `s3_tables`. As células de engine dessas dez são `UNKNOWN`; o que responde por
  três delas é o cruzamento por release.
- `quicksight` e `sagemaker` continuam declaráveis no inventário e **não têm
  linha** na matriz: saem como `UNKNOWN` nomeado, com a medida que destravaria.
- `v3 × FGAC` e `REST Catalog × Lake Formation` ficaram `UNKNOWN`. As medidas que
  as destravariam estão escritas em `engines.lakeformation.note`.
