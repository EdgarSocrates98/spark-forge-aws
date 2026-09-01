# Configuração de job run Amazon EMR on EKS

O que decide capacidade de diagnóstico, exposição de segredo e precedência de
configuração **antes** de qualquer job rodar — no modelo em que o cluster é um
namespace de Kubernetes que o EMR não possui. A matriz de release está em
[`runtime-matrix.md`](runtime-matrix.md); esta página é sobre a forma do **job
run** e do **virtual cluster**.

Esta página cobre `DescribeJobRun` e `DescribeVirtualCluster` da API
`emr-containers`. Managed endpoints (`DescribeManagedEndpoint`), o Spark
operator, o Livy gerenciado e as sessões interativas estão fora.

## 0. O limite que vale para tudo o que vem abaixo, e ele é o inverso do Serverless

`DescribeJobRun` devolve **a definição de uma execução**, não um padrão. Isso é
a assimetria estrutural com o EMR Serverless, e ela inverte o sinal de toda
regra transposta de lá.

| | EMR Serverless | EMR on EKS |
|---|---|---|
| Artefato lido nesta fase | `get-application` — o **padrão** | `describe-job-run` — **uma execução** |
| Quem sobrepõe quem | `StartJobRun` sobrepõe a application | ninguém: já é o job run |
| O que o achado prova | uma propriedade da definição, não do run | uma propriedade **deste run** |

Em `knowledge/emr-serverless/application-configuration.md` §0 está escrito que
*"esta application não declara destino S3" é verdade; "os jobs desta application
não gravam log em S3" **não é**"*. Aqui a frase que não podia ser dita lá **pode**
ser dita: o `configurationOverrides` que volta no `describe-job-run` é o que
aquele job run carregou.

O que **continua** não podendo ser dito é a outra metade: `DescribeJobRun` não
devolve os defaults do runtime nem a configuração efetiva dentro do executor.
Ele devolve o que o chamador pediu — `configurationOverrides` e
`jobDriver.sparkSubmitParameters` — e nada da camada que a §3 chama de
*"Optimized configurations chosen by Amazon EMR for the release"*. Ausência de
uma propriedade no artefato significa **"o chamador não pediu"**, nunca
**"o valor não está setado"**.

E há uma superfície inteira que este artefato não vê: `spark.conf.set` dentro do
código, que a fonte declara ser a prioridade **mais alta** de todas (§3). Um job
run sem `spark.dynamicAllocation.enabled` no artefato pode ter dynamic
allocation ligada por uma linha de Python que este artefato não conhece.

## 1. O formato de `DescribeJobRun`, com os tipos reais

Resposta de `DescribeJobRun`, com a chave de topo `jobRun` (tipo `JobRun`). A
resposta é `GET /virtualclusters/{virtualClusterId}/jobruns/{jobRunId}`, sem
corpo de requisição.

| Campo | Tipo | Obrigatório | Constraints |
|---|---|---|---|
| `id` | String | **não** | 1–64, `[0-9a-z]+` |
| `name` | String | não | 1–64, `[\.\-_/#A-Za-z0-9]+` |
| `arn` | String | não | 60–1024, `^arn:(aws[a-zA-Z0-9-]*):emr-containers:.+:(\d{12}):\/virtualclusters\/[0-9a-zA-Z]+\/jobruns\/[0-9a-zA-Z]+$` |
| `virtualClusterId` | String | não | 1–64, `[0-9a-z]+` |
| `state` | String | não | `PENDING \| SUBMITTED \| RUNNING \| FAILED \| CANCELLED \| CANCEL_PENDING \| COMPLETED` |
| `stateDetails` | String | não | 1–256, `.*\S.*` |
| `failureReason` | String | não | `INTERNAL_ERROR \| USER_ERROR \| VALIDATION_ERROR \| CLUSTER_UNAVAILABLE` |
| `releaseLabel` | String | não | 1–64, `[\.\-_/A-Za-z0-9]+` — ver §9 |
| `executionRoleArn` | String | não | 20–2048, ARN de `role` |
| `createdBy` | String | não | 20–2048, ARN de `iam` ou `sts` |
| `createdAt` / `finishedAt` | Timestamp | não | |
| `clientToken` | String | não | 1–64, `.*\S.*` |
| `jobDriver` | objeto `JobDriver` | não | ver §2 |
| `configurationOverrides` | objeto `ConfigurationOverrides` | não | ver §2 |
| `retryPolicyConfiguration` | objeto | não | `maxAttempts` (número) |
| `retryPolicyExecution` | objeto | não | `currentAttemptCount` (número) |
| `tags` | map String → String | não | 0–50 entradas |

**Todo campo do `JobRun` é `Required: No`.** Não há um único campo obrigatório
na referência do tipo — nem `id`, nem `state`, nem `releaseLabel`. O extrator
não pode assumir presença de nada, e a diferença entre "ausente" e "vazio"
precisa sobreviver até o fact.

Três leituras que mudam o extrator:

1. **`state` e `failureReason` têm `Valid Values` declarados** e podem ser
   tratados como conjuntos fechados — ao contrário de `releaseLabel`, que só
   tem um pattern permissivo. Repare que `SUCCEEDED` **não** existe: o estado
   terminal de sucesso se chama `COMPLETED`.
2. **`failureReason` é um enum de quatro valores, não texto livre.**
   `CLUSTER_UNAVAILABLE` é o único que aponta para fora do job — e é o que
   distingue "o código falhou" de "o EKS não tinha onde rodar". Texto livre
   está em `stateDetails`, que é outro campo.
3. **`retryPolicyExecution.currentAttemptCount` é medida, não configuração.**
   Um `currentAttemptCount` maior que 1 com `state: COMPLETED` diz que o job
   passou **numa retentativa** — sintoma que nenhum outro campo carrega.

## 2. `jobDriver` e `configurationOverrides`

`JobDriver` é união de dois, e a fonte é explícita: *"Exactly one of the two
available job drivers is required, either `sparkSqlJobDriver` or
`sparkSubmitJobDriver`."*

| Forma | Campos | Tipo / constraints |
|---|---|---|
| `sparkSubmitJobDriver` | `entryPoint` | String, **Required: Yes**, 1–256, `.*\S.*` |
| | `entryPointArguments` | Array de String, não, 1–10280, `.*\S.*` |
| | `sparkSubmitParameters` | String, não, **1–102400**, `.*\S.*` |
| `sparkSqlJobDriver` | `entryPoint` | String |
| | `sparkSqlParameters` | String |

**`sparkSubmitParameters` é uma string única de até 102400 caracteres**, não uma
lista nem um map. É a linha de `spark-submit` inteira, com `--class`, `--conf
k=v` repetidos, `--jars`, o que for. O extrator que quiser ler propriedade de
Spark daqui tem que **tokenizar**, e tokenizar linha de shell é onde parsers
erram: valor com espaço, aspas, `=` dentro do valor. A documentação não declara
gramática nenhuma para esse campo além de "não pode ser só espaço em branco".
Falha de tokenização é `unresolved`, não silêncio.

`ConfigurationOverrides`:

| Campo | Tipo | Obrigatório | Constraints |
|---|---|---|---|
| `applicationConfiguration` | Array de `Configuration` | não | **máximo 100 itens** |
| `monitoringConfiguration` | objeto `MonitoringConfiguration` | não | ver §4 |

`Configuration` tem a mesma forma dos outros dois runtimes de EMR —
`classification` (String, obrigatória), `properties` (map String → String),
`configurations` (array recursivo de `Configuration`). O achatamento precisa
descer o aninhamento, não ler só o primeiro nível.

## 3. A precedência entre `sparkSubmitParameters` e `applicationConfiguration` — a fonte declara

**Esta era a pergunta que decidia se uma regra pode acusar a superfície certa, e
a resposta é sim, com lista ordenada e completa.** A página *Managing job runs
with the AWS CLI*, na descrição de `--configuration-overrides`:

> *"If you pass the same configuration in an application override and in Spark
> submit parameters, **the Spark submit parameters take precedence**. The
> complete configuration priority list follows, in order of highest priority to
> lowest priority."*
>
> 1. *"Configuration supplied when creating `SparkSession`."*
> 2. *"Configuration supplied as part of `sparkSubmitParameters` using `—conf`."*
> 3. *"Configuration provided as part of application overrides."*
> 4. *"Optimized configurations chosen by Amazon EMR for the release."*
> 5. *"Default open source configurations for the application."*

Cinco níveis, e três consequências duras para o desenho de regra:

1. **Achado sobre `applicationConfiguration` precisa checar
   `sparkSubmitParameters` antes.** Uma regra que leia
   `spark.dynamicAllocation.enabled=true` em `applicationConfiguration` e não
   olhe se `--conf spark.dynamicAllocation.enabled=false` está na linha de
   submit acusa um valor que **perdeu**. A precedência é declarada, então errar
   isso não tem desculpa de fonte.
2. **O nível 1 é invisível neste artefato, e é o mais alto.** `spark.conf.set`
   no código do job vence tudo, e `DescribeJobRun` não o vê. Toda regra desta
   área que afirme um valor efetivo tem que dizer, no `explanation`, que a
   sessão pode sobrepor. Esse é o mesmo padrão de honestidade do `SF-EMRS` — só
   que aqui o que falta está no código, não noutro artefato de API.
3. **O nível 4 explica por que ausência não é "não setado".** *"Optimized
   configurations chosen by Amazon EMR for the release"* é uma camada que a AWS
   declara existir e **não publica**. O que ela contém, por release, não foi
   encontrado em nenhuma tabela nesta coleta.

Também declarado na mesma página, e vale como restrição de extrator: seis
configurações de Spark **não são suportadas** em EMR on EKS —
`spark.kubernetes.authenticate.driver.serviceAccountName`,
`spark.kubernetes.authenticate.executor.serviceAccountName`,
`spark.kubernetes.namespace`, `spark.kubernetes.driver.pod.name`,
`spark.kubernetes.container.image.pullPolicy` e
`spark.kubernetes.container.image` — com a exceção declarada em nota de que
`spark.kubernetes.container.image` **pode** ser usada para imagem customizada.

## 4. Destinos de log — e a diferença que reabre a regra que o Serverless fechou

**Este é o ponto em que EMR on EKS e EMR Serverless divergem de verdade, e a
divergência inverte a decisão da Fase 5d.**

No Serverless, a regra "nenhum destino de log" **não pode disparar por ausência**
porque `managedPersistenceMonitoringConfiguration.enabled` tem default `true` e
a AWS declara *"By default, EMR Serverless stores application logs securely in
Amazon EMR managed storage for a maximum of 30 days"*. Ausência ali significa
**protegido**.

Em EMR on EKS **não foi encontrada nenhuma declaração equivalente**. O que a
fonte diz é o contrário, em duas páginas, com a mesma frase quase literal:

> *"To be able to monitor the job progress and to troubleshoot failures, **you
> must configure your jobs to send log information to Amazon S3, Amazon
> CloudWatch Logs, or both.**"*
> — *Configure a job run to use Amazon S3 logs*

> *"To monitor job progress and to troubleshoot failures, **you must configure
> your jobs to send log information to Amazon S3, Amazon CloudWatch Logs, or
> both.**"*
> — *Configure a job run to use Amazon CloudWatch Logs*

Um `must` da própria AWS, repetido em duas páginas, sobre exatamente a condição
que a regra acusa.

Os **cinco** membros de `MonitoringConfiguration`, e o que a fonte diz de cada:

| Membro | Tipo | Default declarado | O que sustenta |
|---|---|---|---|
| `s3MonitoringConfiguration` | objeto (`logUri`, `encryptionKeyArn`) | **nenhum** | logs de submitter, driver e executor vão para S3 *"when `s3MonitoringConfiguration` is passed"* |
| `cloudWatchMonitoringConfiguration` | objeto (`logGroupName`, `logStreamNamePrefix`) | **nenhum** | idem, para CloudWatch Logs |
| `persistentAppUI` | String, `ENABLED \| DISABLED` | **nenhum** | ver §5 |
| `managedLogs` | objeto (`allowAWSToRetainLogs`, `encryptionKeyArn`) | **nenhum** | ver abaixo |
| `containerLogRotationConfiguration` | objeto (`maxFilesToKeep`, `rotationSize`) | **nenhum** | rotação, não destino |

**`managedLogs` não é o `managedPersistence` do Serverless, e confundir os dois
seria o erro caro desta área.** O que a fonte declara sobre ele é estreito:

> *"The `allowAWSToRetainLogs` configuration allows AWS to retain **system
> namespace logs when running a job using Native FGAC**. The `persistentAppUI`
> configuration allows AWS to save **event logs** which are used to generate the
> Spark UI. The `encryptionKeyArn` is used to specify the KMS key ARN you want
> to use to encrypt the logs stored by AWS."*
> — *Encrypting Amazon EMR on EKS logs with managed storage*

Três coisas, e as três importam:

- o escopo é **log de namespace de sistema**, sob **Native FGAC** — não é log de
  aplicação, e não é incondicional;
- `allowAWSToRetainLogs` é `ENABLED | DISABLED` com `Required: No` e **sem
  default declarado** na referência de API nem na referência de CLI;
- **nenhuma retenção é publicada.** O Serverless publica 30 dias; aqui não foi
  encontrado prazo nenhum.

**Consequência para a Task 10:** a regra "nenhum destino de log" em EMR on EKS
**pode** disparar por ausência de `s3MonitoringConfiguration` e de
`cloudWatchMonitoringConfiguration` — e essa é a forma *original* que o spec do
Serverless teve de abandonar. Ela **não** deve ser escrita como conjunção com
`managedLogs`, porque `managedLogs` não cobre log de aplicação e não tem default
conhecido; incluí-lo na condição transportaria uma semântica que a fonte do EKS
não sustenta.

## 5. `persistentAppUI`, e o default que ninguém publica

`persistentAppUI` é `String`, `Valid Values: ENABLED | DISABLED`,
`Required: No`. **O default não foi encontrado declarado** — nem na referência
de API (`MonitoringConfiguration`), nem na referência de CLI de `start-job-run`,
nem nas páginas de logging do guia de desenvolvimento.

O que a fonte declara é o **efeito**, em duas páginas:

> *"The `persistentAppUI` configuration allows AWS to save event logs which are
> used to generate the Spark UI."*
> — *Encrypting Amazon EMR on EKS logs with managed storage*

> *"For example, you start a long running Spark job with an event log enabled
> with the `persistentAppUI` parameter. The Spark driver generates an event log
> file."*
> — *Using Spark event log rotation*

Isso liga `persistentAppUI` diretamente à existência do **event log** — que é o
artefato que este motor lê em `analyze_event_log`. `persistentAppUI: DISABLED`
não é uma preferência de UI: é a ausência do insumo de diagnóstico mais rico que
o SparkForge consome.

**A forma que a regra precisa ter, e o motivo é o mesmo do `SF-EMRS` de log:**
a regra dispara com `persistentAppUI == "DISABLED"` **explícito**, e **não** por
ausência do campo. Sem default publicado, disparar por ausência afirmaria que o
default é desligado — o que esta coleta não mediu. É a mesma disciplina que
impediu a regra do Serverless de acusar a configuração default, aplicada ao caso
inverso: lá se sabia o default e ele era seguro; aqui **não se sabe**, e não
saber também proíbe o disparo.

Vale notar o único ponto em que a documentação toma partido: os três exemplos de
`start-job-run` do guia — os dois de `sparkSubmitJobDriver` e o de
`sparkSqlJobDriver` — escrevem `"persistentAppUI": "ENABLED"` explicitamente.
Isso é evidência de prática recomendada, **não** de default.

## 6. `dynamicAllocation` sem `shuffleTracking` — o que a fonte nomeia, e o que ela não nomeia

**Veredito: a fonte nomeia o requisito, mas nenhuma fonte nomeia a violação como
defeito, e a frase específica de Kubernetes vive num parágrafo sobre outro
assunto.** Os três achados, separados:

**(a) O requisito genérico está na referência de configuração do Spark, e é uma
disjunção — de QUATRO ramos, não de dois.** Esta é a leitura da versão FIXADA
`docs/3.5.6/`, que é a que corresponde ao Spark de EMR on EKS 7.5.0
(`3.5.2-amzn-1`), e ela **corrige** a leitura anterior desta seção. Na descrição
de `spark.dynamicAllocation.enabled` (default `false`, desde 1.2.0):

> *"This requires one of the following conditions: 1) enabling external shuffle
> service through `spark.shuffle.service.enabled`, or 2) enabling shuffle
> tracking through `spark.dynamicAllocation.shuffleTracking.enabled`, or 3)
> enabling shuffle blocks decommission through `spark.decommission.enabled` and
> `spark.storage.decommission.shuffleBlocks.enabled`, or 4) (Experimental)
> configuring `spark.shuffle.sort.io.plugin.class` to use a custom
> `ShuffleDataIO` who's `ShuffleDriverComponents` supports reliable storage."*

E `spark.dynamicAllocation.shuffleTracking.enabled` tem **default `true`** na
`docs/3.5.6/`, com `Since Version: 3.0.0` e a descrição *"Enables shuffle file
tracking for executors, which allows dynamic allocation without the need for an
external shuffle service. This option will try to keep alive executors that are
storing shuffle data for active jobs."* Nenhuma das descrições usa a palavra
"erro" ou "não suportado".

**As duas correções mudam a forma da regra, e a segunda a inverte.** A coleta
anterior desta seção registrou `default false` e uma disjunção de dois ramos; a
releitura na versão fixada mede `default true` e quatro ramos. Com o default
`true`, `dynamicAllocation` ligada **sem** `shuffleTracking` declarada está no
default SEGURO, e uma regra que disparasse por ausência acusaria configuração
correta. Só o `false` **explícito** é acusável. A divergência com a citação de
`latest` que a Task 1 registrou está aferida na §12.

**(b) O fechamento da disjunção no Kubernetes está declarado, e é literal:**

> *"This also requires `spark.dynamicAllocation.shuffleTracking.enabled` to be
> enabled **since Kubernetes doesn't support an external shuffle service at this
> time**."*

Como o primeiro ramo da disjunção (`spark.shuffle.service.enabled`) depende de um
serviço que a fonte diz não existir no Kubernetes, sobra um ramo só. O raciocínio
é curto e a fonte fornece as duas metades.

**(c) E aqui está a ressalva que precisa ir na regra:** essa frase **não** está
numa seção sobre dynamic allocation. Ela está em
*Configuration → **Stage Level Scheduling Overview*** — seção **irmã** de
*Resource Level Scheduling Overview*, não filha dela, as duas penduradas direto em
*Configuration* —, num parágrafo cujo assunto é `ResourceProfile` — o período completo
começa em *"When dynamic allocation is enabled: It allows users to specify task
and executor resource requirements at the stage level and will request the extra
executors."*. A página `running-on-kubernetes.html` **não tem** seção dedicada a
dynamic allocation; as outras menções são de passagem (uma nota sobre PVCs
sob demanda e a config `spark.kubernetes.dynamicAllocation.deleteGracePeriod`).

**Nenhuma página da AWS sobre EMR on EKS foi encontrada nomeando essa
combinação como defeito** nesta coleta.

**O que isso permite à Task 10:** a regra entra como **relação entre duas
propriedades**, no padrão da regra 16 do `CLAUDE.md` — `dynamicAllocation.enabled`
declarado `true` **e** `shuffleTracking.enabled` declarado `false`, os DOIS
explícitos, e nunca por ausência de nenhum dos dois. Ela **não** entra citando
uma fonte que a chame de defeito, porque não há; e ela carrega escrito que os
ramos 3 e 4 da disjunção existem e não são observados por ela. A leitura das
propriedades tem que respeitar a precedência da §3, senão acusa o valor que
perdeu — e é por isso que `SF-EMRK-004` lê **só** `sparkSubmitParameters`, a
superfície que a fonte declara vencedora entre as duas que este artefato traz.

## 7. Segredo em texto claro — a página que enumera não enumera o EKS

O `SF-EMR-002` de EMR on EC2 se apoia numa frase da *ReleaseGuide*:

> *"The Amazon EMR describe and list API operations that emit custom
> configuration data (such as `DescribeCluster` and `ListInstanceGroups`) do so
> in plaintext."*

**Essa página é de EMR on EC2 e não se declara aplicável ao EKS.** Ela nomeia
`DescribeCluster` e `ListInstanceGroups`, fala em *service role for Amazon EMR*,
em *"when you launch your cluster"*, e o procedimento de rotação é *"submit a
reconfiguration request to each instance group"*. Nada em `emr-containers`.

E existe uma página cuja **função é enumerar quais deployments de EMR integram
com o Secrets Manager**. Ela tem exatamente duas seções:

- *"How Amazon EMR running on Amazon EC2 uses Secrets Manager"*
- *"How EMR Serverless uses Secrets Manager"*

**EMR on EKS não aparece.** Isso é mais forte do que não achar: é uma ausência
numa lista que existe para ser completa. Ainda assim, a regra do repositório
vale — *ausência de evidência não prova ausência da capacidade*. O que está
medido é que a integração **não está documentada** para `emr-containers`, não que
ela não exista.

O que **está** medido do lado do EKS, e sustenta a regra por outro caminho:

- o *Response Syntax* de `DescribeJobRun` devolve
  `configurationOverrides.applicationConfiguration[].properties` como
  `{"string": "string"}`, **sem redação declarada**, e o mesmo vale para
  `sparkSubmitParameters`, que é uma string crua de até 102400 caracteres;
- a página *Data protection* do guia do EKS diz *"We strongly recommend that you
  never put sensitive identifying information (...) into free-form fields (...)
  Any data that you enter into Amazon EMR on EKS or other services might get
  picked up for inclusion in diagnostic logs"* — genérico, sobre campos livres,
  **não** sobre `properties` de configuração;
- as *security best practices* do EKS têm sete tópicos e **nenhum** sobre
  segredo em configuração; o que elas dizem sobre segredo é o oposto do
  esperado — *"Kubernetes RBAC permissions to read Kubernetes secrets ‐ to
  prevent users from reading confidential data stored in these secrets"*, isto
  é, sobre `Secret` do Kubernetes, não sobre `applicationConfiguration`.

**Consequência para a Task 10:** a regra sobrevive, apoiada no *Response Syntax*
(a superfície de exposição é medida) mais a ausência de qualquer mecanismo de
redação documentado para `emr-containers`. Ela **não** pode citar o *Warning* da
*ReleaseGuide* como fonte, e **não** pode recomendar `EMR.secret@` como remédio
— a anotação não está documentada para EMR on EKS, e recomendar um mecanismo não
documentado seria inventar o conserto. O remédio que a fonte sustenta é o do
Kubernetes: `Secret` montado, com a ressalva de RBAC das *security best
practices*.

## 8. Imagem de container em tag móvel — a fonte usa a tag móvel no próprio exemplo

**Veredito: vetada.** E o veto precisa ser exatamente do tamanho da fonte, porque a
Task 10 vai herdá-lo. São **dois objetos diferentes**, e só um deles é o objeto da
candidata (e):

| Objeto | O que carrega a parte móvel | É o objeto da candidata (e)? |
|---|---|---|
| **tag de imagem de container** | `:latest` no fim do URI de ECR | **sim** |
| **release label** | sufixo `-latest` em `emr-7.13.0-latest` | não — é outro campo, ver §9 |

**A perna que sustenta o veto é a primeira, e ela é sozinha suficiente.** A página
*Details for selecting a base image URI* dá o formato e o exemplo:

```
{ECR-registry-account}.dkr.ecr.{Region}.amazonaws.com/spark/{container-image-tag}
895885662937.dkr.ecr.us-west-2.amazonaws.com/spark/emr-7.13.0:latest
```

A tag do exemplo oficial da AWS, para o objeto que a regra acusaria, **é `:latest`**.
Os três exemplos de URI da página (`spark/`, `notebook-spark/`, `notebook-python/`)
usam a mesma tag. E as *Considerations for customizing images* têm seis itens —
usuário `hadoop:hadoop`, `applicationOverrides` em vez de editar
`spark-defaults.conf`, seis diretórios montados em runtime, repositório Docker, e o
aviso de preço — e **nenhum** sobre imutabilidade de tag, digest, ou fixar versão.
Uma regra "imagem em tag móvel" acusaria o que a AWS escreve no próprio exemplo, sem
nenhuma página que desaconselhe a prática. É o defeito que o
`rules/catalog/README.md` chama de pior: acusar configuração correta.

**A segunda perna corrobora a disposição da AWS, e não é sobre a tag.** Ela vale
como contexto e não como fundamento:

> *"Amazon EMR on EKS images are regularly patched with latest security patches.
> **To get the latest image, you must rebuild the custom images whenever there is a
> new base image version** of the Amazon EMR release."*
> — *Amazon EMR on EKS security best practices*

Essa frase é sobre **imagem**, e empurra na direção de frescor — mas o mecanismo que
ela pede é *rebuildar*, não *apontar para tag móvel*. Já a frase que a versão anterior
desta página usava no mesmo fôlego — *"When you use the `-latest` suffix, you ensure
that your Amazon EMR version always includes the latest security updates"*, da página
de releases — é sobre **release label**, objeto diferente. Ela **não** entra no veto.

**A tensão, dita em voz alta.** Esta seção conclui que a mobilidade não é defeito de
segurança; a §9 desta página e a §6 de [`runtime-matrix.md`](runtime-matrix.md)
concluem que a mobilidade **é** um problema de **diagnóstico** — dois runs com o mesmo
ponteiro móvel não provam o mesmo binário, e uma comparação entre eles é inválida por
construção. As duas coisas são verdade ao mesmo tempo, e a fonte só sustenta a
segunda como **limite de inferência**, nunca como acusação contra a configuração.

Então o que sobra para a Task 10 é estreito e precisa ficar estreito: **nada acusa a
tag móvel**; o que existe é uma **ressalva de comparável** — quando o artefato traz
ponteiro móvel (tag `:latest` ou release label `-latest`), qualquer achado que compare
dois runs declara que o runtime não foi provado idêntico. Isso é nota em `explanation`,
não `Finding`. Uma regra de verdade sobre reprodutibilidade precisaria de fonte
própria, e esta coleta não achou nenhuma.

## 9. O formato do `releaseLabel` — a hipótese estava certa, e é pior do que ela supunha

A página de releases declara a forma, literal:

> *"Amazon EMR on EKS uses the following form of release label: `emr-x.x.x-latest`
> or `emr-x.x.x-yyyymmdd` with a specific release date. For example,
> `emr-7.13.0-latest` or `emr-7.13.0-20210129`."*

Confirmado: **o sufixo é obrigatório na forma**, e um `releaseLabel` de EMR on
EKS **nunca** tem a forma `emr-X.Y.Z` pura que o Serverless publica.

Mas o espaço de formas é maior do que essas duas. As páginas por release
enumeram, para uma mesma release, variantes que **também** são release labels:

| Família | Exemplo (de `emr-7.13.0`) |
|---|---|
| base | `emr-7.13.0-latest`, `emr-7.13.0-20260410` |
| acelerador | `emr-7.13.0-spark-rapids-latest` |
| runtime de Java | `emr-7.13.0-java11-latest`, `emr-7.13.0-java8-latest` |
| combinado | `emr-7.13.0-spark-rapids-java8-20260410` |
| notebook | `notebook-spark/emr-7.13.0-latest`, `notebook-python/emr-7.13.0-latest` |
| Livy | `livy/emr-7.13.0-latest` |
| Flink | `emr-7.13.0-flink-latest` |
| sistema operacional (série 6.x) | `emr-6.15.0-java17-al2023-latest` |
| fora de `emr-X.Y.Z` | `emr-spark-8.0.0-latest`, `emr-spark-8.0.0-20260421` |

O pattern da API é `[\.\-_/A-Za-z0-9]+` — que aceita a barra, e portanto aceita
`notebook-spark/emr-7.13.0-latest` como valor legítimo do campo.

**Consequência para o extrator**, no padrão "chave ausente é como este motor diz
que não sabe": `release_major` e `release_minor` só saem em `measures` quando o
label casa com `emr-<major>.<minor>.<patch>-<sufixo>`; **omitidos** para
`emr-spark-8.0.0-*` e para qualquer forma com prefixo de barra. Enumerar as
famílias acima como lista fechada seria errado — elas são o que existe nesta
coleta, e a série 6.x já mostrou uma família (`al2023`) que a 7.x não tem.

`emr-x.x.x-latest` também tem uma consequência de diagnóstico que nenhum outro
runtime de EMR tem: **duas execuções com o mesmo `releaseLabel` podem ter rodado
imagens diferentes.** `-latest` é ponteiro, e a fonte diz que ele se move para
pegar patch de segurança. Uma comparação de dois runs (`benchmark`) que assuma
runtime idêntico porque o `releaseLabel` é idêntico está errada por construção
quando o sufixo é `-latest`. Com sufixo `-yyyymmdd`, a comparação é sólida.

## 10. O `virtualCluster`, e o que ele é de verdade

`DescribeVirtualCluster` é `GET /virtualclusters/{virtualClusterId}`. A resposta
tem a chave de topo `virtualCluster` (tipo `VirtualCluster`), e **todos** os
campos são `Required: No`.

| Campo | Tipo | Constraints |
|---|---|---|
| `id` | String | 1–64, `[0-9a-z]+` |
| `name` | String | 1–64, `[\.\-_/#A-Za-z0-9]+` |
| `arn` | String | 60–1024 |
| `state` | String | `RUNNING \| TERMINATING \| TERMINATED \| ARRESTED` |
| `containerProvider` | objeto | ver abaixo |
| `securityConfigurationId` | String | 1–64, `[0-9a-z]+` |
| `sessionEnabled` | Boolean | |
| `schedulerConfiguration` | objeto | `maxConcurrentJobRuns`, `maxInQueueJobRuns` |
| `schedulerStatus` | objeto | `currentConcurrentJobRuns`, `currentInQueueJobRuns` |
| `createdAt` | Timestamp | |
| `tags` | map String → String | 0–50 entradas |

`ContainerProvider` tem três campos, e dois são **obrigatórios**:

| Campo | Tipo | Obrigatório | Constraints |
|---|---|---|---|
| `id` | String | **sim** | 1–100, `^[0-9A-Za-z][A-Za-z0-9\-_]*` — o nome do cluster EKS |
| `type` | String | **sim** | `Valid Values: EKS` — *"Amazon EKS is the only supported type as of now"* |
| `info` | `ContainerInfo` | não | **é uma união**: *"Only one member of this object can be specified or returned"* |

E `EksInfo`, o único membro conhecido de `ContainerInfo`:

| Campo | Tipo | Obrigatório | Constraints |
|---|---|---|---|
| `namespace` | String | não | 1–63, `[a-z0-9]([-a-z0-9]*[a-z0-9])?` |
| `nodeLabel` | String | não | 1–64, `^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$` |

**O que o virtual cluster é, na definição da própria AWS** — e isso decide o que
uma regra pode dizer sobre ele:

> *"A single virtual cluster maps to a single Kubernetes namespace. Given this
> relationship, you can model virtual clusters the same way you model Kubernetes
> namespaces to meet your requirements."*

> *"Multiple virtual clusters can be backed by the same physical cluster.
> However, each virtual cluster maps to one namespace on an Amazon EKS cluster.
> **Virtual clusters do not create any active resources that contribute to your
> bill or that require lifecycle management outside the service.**"*

Duas consequências:

1. **Não existe regra de custo de capacidade ociosa nesta área.** A AWS declara
   que o virtual cluster não cria recurso ativo que entre na fatura. O
   `SF-EMR-009` (cluster ocioso) e a regra de pré-init do Serverless **não têm
   análogo aqui** — o que custa é o pod, que vive no EKS, que este artefato não
   descreve. Um `virtualCluster` em `RUNNING` sem job nenhum não é sintoma de
   nada.
2. **`ARRESTED` é o estado que não tem equivalente nos outros runtimes.** Está
   nos `Valid Values` e a referência do tipo não o explica. Esta coleta não achou
   página que defina o que ele significa — fica registrado como valor conhecido
   e semântica desconhecida.

`nodeLabel` traz a própria ressalva na descrição: *"the nodeLabel of the nodes
where the resources of this virtual cluster can get scheduled. **It requires
relevant scaling and policy engine addons**"* — ou seja, o campo pode estar
preenchido e não ter efeito, se o addon não estiver instalado. Regra que leia
`nodeLabel` estaria afirmando sobre o EKS, não sobre o EMR.

## 11. Placar das cinco candidatas

| Candidata | Veredito | Fonte, e o que exatamente ela sustenta |
|---|---|---|
| (a) Segredo em claro em configuração | **sobrevive, com fonte mais fraca que a do EC2 e a do Serverless** | *Response Syntax* de `DescribeJobRun` devolve `properties` como map de string sem redação, e `sparkSubmitParameters` cru. **Sem** o *Warning* de texto claro (aquele é de EC2) e **sem** mecanismo de redação documentado para `emr-containers` — a página que enumera as integrações com Secrets Manager lista EC2 e Serverless e **não** lista EKS (§7) |
| (b) Nenhum destino de log | **sobrevive, e na forma original que o Serverless obrigou a abandonar** | *"you must configure your jobs to send log information to Amazon S3, Amazon CloudWatch Logs, or both"*, em duas páginas. **Não existe** managed persistence ligada por default como no Serverless; `managedLogs` cobre log de namespace de sistema sob Native FGAC, com escopo estreito e sem default declarado (§4) |
| (c) `persistentAppUI` desligado | **sobrevive só com `DISABLED` explícito** | O efeito é declarado (*"allows AWS to save event logs which are used to generate the Spark UI"*), o **default não é**. Disparar por ausência afirmaria um default que esta coleta não mediu (§5) |
| (d) `dynamicAllocation` sem `shuffleTracking` | **sobrevive como relação entre propriedades, sem fonte que a chame de defeito** | O requisito é declarado em `configuration.html` como **disjunção**; o fechamento no Kubernetes é declarado em `running-on-kubernetes.html`, mas dentro de *Stage Level Scheduling Overview*. Nenhuma fonte da AWS sobre EMR on EKS nomeia a combinação (§6) |
| (e) Imagem de container em tag móvel | **VETADA** | O exemplo oficial de URI de imagem base usa **`:latest`** — a própria tag que a regra acusaria — e nenhuma página desaconselha tag móvel; as *Considerations for customizing images* têm seis itens e nenhum sobre imutabilidade. Acusaria a configuração que a AWS ensina. O `-latest` de **release label** é outro objeto e não entra no veto (§8) |

**Quatro sobrevivem, uma é vetada por fonte que recomenda o contrário, e a (b)
sobrevive numa forma que o runtime irmão proibia.** Nenhuma das quatro entra com
a mesma fonte que a sua equivalente de EMR on EC2 ou de EMR Serverless — a
transposição de fonte entre runtimes de EMR é, nesta área, sempre errada.

## 12. A releitura na versão fixada do Spark, e as duas divergências que ela mediu

A Task 1 citou `spark.apache.org/docs/latest/`. Este repositório **fixa versão**
nas fontes de Spark que sustentam regra — `docs/3.5.6/` e `docs/4.1.1/` já estão
em `knowledge/sources.lock.json` —, e `emr-7.5.0-latest`, a release das quatro
fixtures desta área, roda Spark `3.5.2-amzn-1`. A versão fixada correspondente é
`docs/3.5.6/`, e é dela que `SF-EMRK-004` cita.

Medido em 2026-08-31, nas duas páginas, comparando `docs/3.5.6/` com
`docs/latest/`:

| Afirmação registrada pela Task 1 (de `latest`) | O que a `docs/3.5.6/` diz | O que a `docs/latest/` diz **hoje** |
|---|---|---|
| a disjunção tem dois ramos: `shuffle.service.enabled` **ou** `shuffleTracking.enabled` | **quatro** ramos: os dois, mais decommission de blocos de shuffle, mais `ShuffleDataIO` customizado (experimental) | **quatro** ramos, texto idêntico ao da 3.5.6 |
| `spark.dynamicAllocation.shuffleTracking.enabled` tem default `false` | default **`true`**, `Since Version: 3.0.0` | default **`true`** |
| a frase que fecha a disjunção no Kubernetes vive em *Stage Level Scheduling Overview* | **confere** — mesma seção, mesma frase literal | confere |

**Duas leituras, e a segunda é a que importa.** A primeira divergência é entre a
coleta da Task 1 e as páginas: o texto de dois ramos não é o que `latest` publica
hoje, nem o que a 3.5.6 publica — ele é redação de uma série anterior do Spark.
A segunda é a que inverte a regra: com `shuffleTracking` em `true` por default,
disparar por **ausência** acusaria o default seguro da AWS e do Apache, que é o
pior defeito de regra segundo `rules/catalog/README.md`.

A regra que sobrevive exige os **dois valores explícitos**. E ela declara o que
não observa: os ramos 3 e 4 satisfazem o requisito sem `shuffleTracking`, e nem
o motor de regras (que compara um fact por vez, por igualdade) nem este artefato
(que não vê `spark.conf.set` no código) conseguem descartá-los. Por isso o
achado nomeia uma **relação declarada entre duas propriedades**, e nunca afirma
que o job falha — a §"O que estas fontes NÃO sustentam" já proibia essa
afirmação por outro caminho.

## Fontes

- DescribeJobRun (Response Syntax e erros). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_DescribeJobRun.html (retrieved 2026-08-31)
- JobRun (data type — tipos, patterns e `Valid Values` de `state` e `failureReason`). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_JobRun.html (retrieved 2026-08-31)
- DescribeVirtualCluster (Response Syntax, e a definição "a single virtual cluster maps to a single Kubernetes namespace"). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_DescribeVirtualCluster.html (retrieved 2026-08-31)
- VirtualCluster (data type — `Valid Values` de `state`, e "do not create any active resources that contribute to your bill"). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_VirtualCluster.html (retrieved 2026-08-31)
- ContainerProvider (`type` fechado em `EKS`, `info` declarado como união). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_ContainerProvider.html (retrieved 2026-08-31)
- EksInfo (`namespace` e `nodeLabel`). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_EksInfo.html (retrieved 2026-08-31)
- JobDriver ("Exactly one of the two available job drivers is required"). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_JobDriver.html (retrieved 2026-08-31)
- SparkSubmitJobDriver (`sparkSubmitParameters` como string de até 102400). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_SparkSubmitJobDriver.html (retrieved 2026-08-31)
- ConfigurationOverrides (limite de 100 itens em `applicationConfiguration`). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_ConfigurationOverrides.html (retrieved 2026-08-31)
- MonitoringConfiguration (`persistentAppUI` com `Valid Values` e sem default). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_MonitoringConfiguration.html (retrieved 2026-08-31)
- ManagedLogs (`allowAWSToRetainLogs` com `Valid Values` e sem default). https://docs.aws.amazon.com/emr-on-eks/latest/APIReference/API_ManagedLogs.html (retrieved 2026-08-31)
- Managing job runs with the AWS CLI (a lista de precedência de cinco níveis, e as seis configs não suportadas). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-jobs-CLI.html (retrieved 2026-08-31)
- Submit a job run with StartJobRun (os três exemplos com `persistentAppUI: ENABLED`). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-jobs-submit.html (retrieved 2026-08-31)
- Configure a job run to use Amazon S3 logs (o `must` de destino de log, e os três caminhos de log). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-jobs-s3.html (retrieved 2026-08-31)
- Configure a job run to use Amazon CloudWatch Logs (o mesmo `must`). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-jobs-cloudwatch.html (retrieved 2026-08-31)
- Encrypting Amazon EMR on EKS logs with managed storage (o escopo estreito de `managedLogs`, e o efeito de `persistentAppUI`). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/security_iam_fgac-logging-kms.html (retrieved 2026-08-31)
- Using Spark event log rotation (`persistentAppUI` como o que liga o event log). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-log-rotation.html (retrieved 2026-08-31)
- Amazon EMR on EKS security best practices (rebuildar imagem, RBAC de secrets do Kubernetes, e a ausência de tópico sobre segredo em configuração). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/security-best-practices.html (retrieved 2026-08-31)
- Data protection (EMR on EKS — só a recomendação genérica sobre campos livres). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/data-protection.html (retrieved 2026-08-31)
- Customizing Docker images for Amazon EMR on EKS. https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/docker-custom-images.html (retrieved 2026-08-31)
- Details for selecting a base image URI (o exemplo oficial com `:latest`). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/docker-custom-images-tag.html (retrieved 2026-08-31)
- Considerations for customizing images (seis itens, nenhum sobre imutabilidade de tag). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/docker-custom-images-considerations.html (retrieved 2026-08-31)
- Amazon EMR on EKS releases (a forma declarada do release label). https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/emr-eks-releases.html (retrieved 2026-08-31)
- Store sensitive configuration data in AWS Secrets Manager (o Warning de texto claro — **de EMR on EC2**). https://docs.aws.amazon.com/emr/latest/ReleaseGuide/storing-sensitive-data.html (retrieved 2026-08-31)
- How Amazon EMR uses Secrets Manager (a página que enumera os deployments, e não enumera o EKS). https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating-emr.html (retrieved 2026-08-31)
- start-job-run (AWS CLI Command Reference — sem default para `persistentAppUI` nem para `allowAWSToRetainLogs`). https://docs.aws.amazon.com/cli/latest/reference/emr-containers/start-job-run.html (retrieved 2026-08-31)
- Running Spark on Kubernetes (a frase sobre external shuffle service, e a seção em que ela está). https://spark.apache.org/docs/latest/running-on-kubernetes.html (retrieved 2026-08-31)
- Spark Configuration (defaults de `spark.dynamicAllocation.enabled` e `.shuffleTracking.enabled`). https://spark.apache.org/docs/latest/configuration.html (retrieved 2026-08-31)
- Spark Configuration, VERSÃO FIXADA — a que `SF-EMRK-004` cita, e a que corresponde ao Spark 3.5.2-amzn-1 de `emr-7.5.0`. Disjunção de quatro ramos, e `shuffleTracking.enabled` com default `true` (§12). https://spark.apache.org/docs/3.5.6/configuration.html (retrieved 2026-08-31)
- Running Spark on Kubernetes, VERSÃO FIXADA — *"since Kubernetes doesn't support an external shuffle service at this time"*, dentro de *Stage Level Scheduling Overview* (§12). https://spark.apache.org/docs/3.5.6/running-on-kubernetes.html (retrieved 2026-08-31)

### O que estas fontes NÃO sustentam

- **Um default para `persistentAppUI`.** Nem `ENABLED` nem `DISABLED`. A
  referência de API declara `Valid Values` e `Required: No`, a referência de CLI
  repete, e nenhuma página do guia nomeia um default. **Não disparar regra por
  ausência do campo**, nos dois sentidos.
- **Um default para `managedLogs.allowAWSToRetainLogs`.** Mesma situação. E o
  escopo declarado é *system namespace logs* sob *Native FGAC* — **não citar
  `managedLogs` como armazenamento gerenciado de log de aplicação**, e não
  transportar o default `true` do `managedPersistence` do EMR Serverless.
- **Qualquer prazo de retenção de log em EMR on EKS.** O Serverless publica 30
  dias em managed storage; aqui nenhuma página encontrada publica prazo, para
  nenhum dos destinos.
- **Que `EMR.secret@` funcione em EMR on EKS.** A anotação está documentada para
  EMR on EC2 e para EMR Serverless. A página que enumera as integrações com
  Secrets Manager tem seção para esses dois e **não tem** para o EKS. Isso mede
  que a integração não está documentada — **não** que ela não exista. Não
  recomendar `EMR.secret@` como remédio numa regra `SF-EMRK`.
- **Que Spark falhe, avise ou degrade de algum modo específico quando
  `dynamicAllocation` está ligada sem `shuffleTracking` no Kubernetes.** A fonte
  declara o requisito; ela **não** declara o comportamento na violação. Não
  afirmar "o job falha ao iniciar" nem "os executores nunca são liberados" sem
  medida própria.
- **Os defaults efetivos de Spark por release de EMR on EKS.** A própria lista de
  precedência nomeia uma camada — *"Optimized configurations chosen by Amazon EMR
  for the release"* — que **não** é publicada em tabela nenhuma encontrada nesta
  coleta. Nenhum achado desta área pode afirmar o valor efetivo de uma
  propriedade que o artefato não traz.
- **Que a lista de famílias de release label da §9 seja fechada.** São as que
  aparecem nas páginas por release em 2026-08-31. A série 6.x já traz uma família
  (`al2023`) que a 7.x não tem. Tratar forma inesperada como não-parseável e
  omitir `release_major`/`release_minor`, **não** enumerar exceções.
- **O que `ARRESTED` significa.** Está nos `Valid Values` de
  `VirtualCluster.state` e nenhuma página encontrada o define.
- **Que um `virtualCluster` sem job custe zero.** O que está declarado é que ele
  *"não cria recurso ativo que contribua para a sua fatura"*; o custo do pod, do
  nó do EKS e do plano de controle do EKS é de outro serviço e não é objeto
  desta declaração.
- **Que `sparkSubmitParameters` tenha gramática declarada.** O único constraint é
  `.*\S.*` e o comprimento. Não há especificação de escape, aspas ou
  precedência entre `--conf` repetidos. Falha de tokenização é `unresolved`.
- **Que `spark.shuffle.service.enabled` seja realmente inefetiva em EMR on EKS.**
  O que a fonte do Spark diz é que *"Kubernetes doesn't support an external
  shuffle service at this time"*; ela não descreve o que acontece se a
  propriedade for setada mesmo assim, e a AWS não fala do assunto.
