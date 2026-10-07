# Configuração de application Amazon EMR Serverless

O que decide custo, capacidade de diagnóstico e exposição de segredo **antes** de qualquer job rodar — no modelo em que não existe cluster, nó, nem grupo de instância. A matriz de release está em [`runtime-matrix.md`](runtime-matrix.md); esta página é sobre a forma da *application*.

A forma executável deste conteúdo é [`../../rules/catalog/emr-serverless.yaml`](../../rules/catalog/emr-serverless.yaml).

Esta página cobre **a definição da application** (`get-application`). Job runs (`get-job-run`, `list-job-runs`) e `billedResourceUtilization` estão fora por decisão registrada na §2 do spec da Fase 5d, e EMR on EKS por inteiro.

## 0. O limite que vale para tudo o que vem abaixo

`get-application` devolve **o padrão da application**, não o que qualquer job efetivamente rodou. A documentação é explícita sobre o mecanismo de sobreposição:

> *"The priority of configurations that you provide at `StartJobRun` supersede the configurations that you provide at the application level."*

E a granularidade do merge é declarada: `applicationConfiguration` funde por **classificação** (`spark-defaults` inteiro é substituído), `monitoringConfiguration` funde por **tipo de configuração** (`s3MonitoringConfiguration` inteiro). Um job run pode:

| Operação no `StartJobRun` | Efeito sobre o que `get-application` mostra |
|---|---|
| repetir a classificação com outros valores | substitui aquela classificação |
| acrescentar classificação nova | soma |
| passar `properties: {}` na classificação | **remove** a classificação |
| `s3MonitoringConfiguration: {}` | **remove** o destino S3 |
| `managedPersistenceMonitoringConfiguration: {}` | volta ao **default ligado** |
| `cloudWatchLoggingConfiguration: {enabled: false}` | desliga o CloudWatch |

Consequência para toda regra da área `SF-EMRS`: o achado prova uma propriedade **da definição da application**, e o `explanation` precisa dizer isso. "Esta application não declara destino S3" é verdade; "os jobs desta application não gravam log em S3" **não é**, e afirmá-lo seria o tipo de achado confiante e falso que este projeto trata como o pior defeito possível.

É uma assimetria real em relação ao EMR on EC2, onde `Configurations` no nível de cluster vale para todos os nós salvo override de grupo — e o override de grupo **aparece no mesmo dump**. Aqui o override mora noutro artefato, que esta fase não lê.

## 1. O formato de `get-application`, com os tipos reais

Resposta de `GetApplication`, com a chave de topo `application`. Os campos que esta fase lê, e o tipo declarado na referência de API:

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `applicationId` | String | sim | 1–64, `[0-9a-z]+` |
| `arn` | String | sim | 60–1024 |
| `name` | String | **não** | 1–64, `[A-Za-z0-9._/#-]+` |
| `releaseLabel` | String | sim | 1–64, `[A-Za-z0-9._/-]+` — ver [`runtime-matrix.md`](runtime-matrix.md) §4 |
| `type` | String | sim | 1–64. Sem `Valid Values` declarado na referência |
| `state` | String | sim | `CREATING \| CREATED \| STARTING \| STARTED \| STOPPING \| STOPPED \| TERMINATED` |
| `stateDetails` | String | não | 1–256 |
| `architecture` | String | não | `ARM64 \| X86_64` |
| `createdAt` / `updatedAt` | Timestamp (`number` no JSON) | sim | |
| `autoStartConfiguration` | objeto `AutoStartConfig` | não | |
| `autoStopConfiguration` | objeto `AutoStopConfig` | não | |
| `initialCapacity` | **map** String → `InitialCapacityConfig` | não | 0–10 entradas; chave 1–50, `[a-zA-Z]+[-_]*[a-zA-Z]+` |
| `maximumCapacity` | objeto `MaximumAllowedResources` | **não** | |
| `monitoringConfiguration` | objeto `MonitoringConfiguration` | não | |
| `runtimeConfiguration` | **array** de `Configuration` | não | 0–100 itens |
| `networkConfiguration` | objeto | não | `subnetIds`, `securityGroupIds` |
| `imageConfiguration`, `workerTypeSpecifications` | objeto / map | não | imagem customizada |
| `interactiveConfiguration` | objeto | não | `livyEndpointEnabled`, `sessionEnabled`, `studioEnabled` |
| `schedulerConfiguration` | objeto | não | `maxConcurrentRuns`, `queueTimeoutMinutes`. Só em `emr-7.0.0` e acima |
| `diskEncryptionConfiguration`, `identityCenterConfiguration`, `jobLevelCostAllocationConfiguration`, `tags` | vários | não | fora do escopo desta fase |

**`initialCapacity` é um map, não uma lista.** A chave é o worker type (`DRIVER`, `EXECUTOR`, `TEZ_TASK` nos exemplos oficiais), e o *value pattern* da chave — `[a-zA-Z]+[-_]*[a-zA-Z]+` — não fecha um vocabulário: qualquer identificador de duas letras ou mais passa. **Não tratar o conjunto de worker types como fechado.** O máximo de 10 entradas, esse sim, é declarado.

`InitialCapacityConfig` tem dois campos: `workerCount` (número) e `workerConfiguration` (objeto `WorkerResourceConfig`).

## 2. As unidades de capacidade, e por que o conjunto é fechado

Este era o ponto que o plano da Fase 5d marcou como "acredito, confira". A confirmação é mais forte do que a suposição: as unidades **não são só documentadas, são restringidas por regex na referência de API**.

`WorkerResourceConfig` (dentro de cada entrada de `initialCapacity`):

| Campo | Tipo | Obrigatório | Length | Pattern |
|---|---|---|---|---|
| `cpu` | String | **sim** | 1–15 | `[1-9][0-9]*(\s)?(vCPU\|vcpu\|VCPU)?` |
| `memory` | String | **sim** | 1–15 | `[1-9][0-9]*(\s)?(GB\|gb\|gB\|Gb)?` |
| `disk` | String | não | 1–15 | `[1-9][0-9]*(\s)?(GB\|gb\|gB\|Gb)` |
| `diskType` | String | não | — | `(SHUFFLE_OPTIMIZED\|[Ss]huffle_[Oo]ptimized\|STANDARD\|[Ss]tandard)`, default `STANDARD` |

`MaximumAllowedResources` (o `maximumCapacity` da application) usa **exatamente os mesmos três patterns**, com `cpu` e `memory` obrigatórios e `disk` opcional.

Cinco leituras que mudam o extrator:

1. **São strings, sim.** O plano acertou nisso. Comparar `initialCapacity` com `maximumCapacity` exige converter antes.
2. **O espaço é opcional, e os exemplos oficiais não o usam.** `(\s)?` — zero ou um. O exemplo de `create-application` da documentação escreve `"cpu": "2vCPU"` e `"memory": "4GB"`, colados. O plano supôs `"4 vCPU"` e `"16 GB"`, com espaço. As duas formas passam; um parser que exija o espaço quebra no formato que a própria AWS ensina.
3. **A unidade é opcional em `cpu` e `memory`, e obrigatória em `disk`.** Repare no `?` final: `cpu` e `memory` terminam em `)?`, `disk` não. Então `"4"` é `cpu` válido e `"16"` é `memory` válido, enquanto `disk` sempre traz `GB`. Um extrator que exija sufixo emitiria `unresolved` para valor legítimo.
4. **O conjunto de unidades é fechado, e é minúsculo.** vCPU em três grafias (`vCPU`, `vcpu`, `VCPU`); GB em quatro (`GB`, `gb`, `gB`, `Gb`). **`MB` não é expressável.** A armadilha que o plano descreveu — `"16 GB"` contra `"16384 MB"` sendo o mesmo número em unidades diferentes — **não pode acontecer neste artefato**, porque a segunda forma é inválida pelo pattern. A comparação numérica é segura desde que a unidade lida esteja no conjunto.
5. **O número é inteiro positivo, sem ponto decimal.** `[1-9][0-9]*` — sem `.`, sem zero à esquerda, sem `0`. `"2.5vCPU"` não passa. Ler com `float()` funciona, mas `int()` é o que a fonte sustenta.

**O `unresolved` continua sendo necessário**, e por uma razão que não é a unidade. Os patterns descrevem o que a API **aceita na entrada**; nada na documentação garante que `get-application` só devolva valores que os satisfaçam, nem que os patterns não mudem. Valor fora do conjunto é `emrs.unresolved` com razão fechada — não é adivinhação, é o registro de que a fonte descreveu um conjunto e o artefato trouxe outra coisa. E o comprimento máximo de 15 caracteres já basta para um valor absurdo caber.

## 3. Capacidade pré-inicializada, e o faturamento com a application parada

**Esta é a pergunta que decide a regra P0 mais cara da fase, e a fonte a sustenta diretamente.**

A frase que decide, na página de capacidade pré-inicializada:

> *"You will be paying for provisioned pre-initialized workers even when the application is idle, hence we suggest enabling it for use cases that benefit from the fast start-up time and sizing it for optimal utilization of resources. **EMR Serverless applications automatically shut down when idle. We suggest keeping this feature on when using pre-initialized workers to avoid unexpected charges.**"*

A AWS não só confirma o faturamento em ociosidade — ela **nomeia a combinação defeituosa** (pré-init + auto-stop desligado) e **nomeia a consequência** (`unexpected charges`). É raro uma regra deste catálogo ter a fonte declarando o remédio na mesma frase.

O mecanismo, na mesma página:

> *"Pre-initialized capacity is available and ready to use when the application has started. The pre-initialized capacity becomes inactive when the application is stopped. An application moves to the `STARTED` state only if the requested pre-initialized capacity has been created and is ready to use. **The whole time that the application is in the `STARTED` state, EMR Serverless keeps the pre-initialized capacity available for use or in use by jobs or interactive workloads.** The feature restores capacity for released or failed containers."*

E o modelo de cobrança, na página de preços:

> *"You are charged for aggregate vCPU, memory, and storage resources used from the time workers are ready to run your workload until the time they stop, rounded up to the nearest second with a 1-minute minimum."*
>
> *"If you set up your application to start workers at application startup, the requested workers will start when you start your application and end when you stop the application, or when the application remains idle."*

Juntando: os workers de `initialCapacity` existem **do `STARTED` ao `STOPPED`**, e o que se cobra é worker existente, não job rodando. A única coisa que os faz parar é a application parar.

**Corolário que muda a forma da regra de auto-stop.** Se a cobrança é por worker existente, então uma application **sem** `initialCapacity` e ociosa não tem worker de que cobrar — a própria página diz que *"The state of an application with no pre-initialized capacity can immediately change from `CREATED` to `STARTED`"*, isto é, sem provisionar nada. Então:

| `initialCapacity` | auto-stop | O que custa enquanto ocioso |
|---|---|---|
| presente | desligado | **os workers, indefinidamente** |
| presente | ligado, janela longa | os workers, até a janela fechar |
| ausente | desligado | nada de worker (ver limite abaixo) |
| ausente | ligado | nada de worker |

Isso é a diferença estrutural com o `SF-EMR-009` do EMR on EC2, e ela não é de unidade. Num cluster EC2 ocioso a fatura corre **sempre** — as instâncias EC2 estão de pé. Numa application Serverless ociosa, a fatura de worker corre **só se houver pré-init**. Transpor `SF-EMR-009` mudando segundos para minutos transporia a pergunta errada.

**O limite declarado:** a linha "nada de worker" é dedução do modelo de cobrança, não frase da AWS. Nesta coleta não foi encontrada nenhuma página afirmando que uma application `STARTED` sem pré-init tem custo **zero**. O que está sustentado é que a cobrança de vCPU/memória/armazenamento é por worker do momento em que fica pronto até parar; se há alguma cobrança de outra natureza por application existente, esta coleta não a viu — **e não a viu não é o mesmo que não existe**.

Duas restrições operacionais que fecham o conserto:

- `initialCapacity` e `maximumCapacity` só mudam com a application em `CREATED` ou `STOPPED`. *"You can only change configurations when the application is in the `CREATED` or `STOPPED` state."*
- A modificação é total, não parcial: *"Because you can't make partial modifications, specify all compute configurations when you change values."*

E uma nota de dimensionamento que vale para o achado: Spark acrescenta overhead de memória (default 10%) ao pedido do driver e do executor, e *"For jobs to use pre-initialized workers, the initial capacity memory configuration should be greater than the memory that the job and the overhead request."* Pré-init subdimensionada é paga **e** não usada — o pior dos dois mundos, e invisível em métrica de Spark.

## 4. Auto-stop e auto-start

| Campo | Tipo | Default declarado | Faixa |
|---|---|---|---|
| `autoStopConfiguration.enabled` | Boolean | *"Defaults to true"* | — |
| `autoStopConfiguration.idleTimeoutMinutes` | Integer | *"Defaults to 15 minutes"* | *"Minimum value of 1. Maximum value of 10080"* |
| `autoStartConfiguration.enabled` | Boolean | *"Defaults to true"* | — |

Três leituras:

- **Auto-stop desligado é ato deliberado.** O default é ligado, com 15 minutos. Diferente do EMR on EC2, onde a política de auto-terminação precisa ser **anexada** e sua ausência é o estado natural, aqui a ausência de `autoStopConfiguration` significa **protegido**. Uma regra que dispare por ausência do campo acusaria exatamente as applications que estão no default seguro.
- **O teto é 10080 minutos = 7 dias**, o mesmo teto do `IdleTimeout` da auto-terminação do EMR on EC2 (604800 s). O ramo mais permissivo da regra tem, portanto, número de fonte nos dois modelos.
- **Nenhum ponto intermediário é declarado.** A documentação não nomeia janela "longa demais". Qualquer limiar entre 1 e 10080 é escolha de campo e precisa de `origin: field-heuristic` com nota, no padrão de `rules/catalog/README.md:57` — exatamente como o limiar de 86400 s do `SF-EMR-009`.

`autoStartConfiguration` é uma pergunta diferente e **não é candidata a regra nesta fase**: com auto-start ligado, uma application parada volta sozinha ao receber job — *"A stopped application starts automatically when you submit a new job."* Isso é conveniência, não defeito, e desligá-lo também não é. Não há custo nem risco de diagnóstico ligado a esse campo que a fonte sustente.

## 5. `initialCapacity` contra `maximumCapacity`

`maximumCapacity` é *"the maximum capacity of the application. This is cumulative across all workers at any given point in time during the lifespan of the application is created. No new resources will be created once any one of the defined limits is hit."*

A aritmética é bem definida e as unidades são comparáveis (§2): soma-se `workerCount × cpu`, `workerCount × memory` e `workerCount × disk` sobre as entradas de `initialCapacity`, e compara-se eixo a eixo com `maximumCapacity`. O `explanation` pode dizer **qual** eixo estourou, e "any one of the defined limits" sustenta tratar os eixos independentemente.

**O que a fonte NÃO diz, e é o que decide se a regra existe:** não foi encontrada nenhuma declaração de que a API **aceite** `initialCapacity` acima de `maximumCapacity`, nem de que a **rejeite**. A página de capacidade pré-inicializada diz que *"An application moves to the `STARTED` state only if the requested pre-initialized capacity has been created and is ready to use"* — o que torna plausível que uma application assim jamais chegue a `STARTED`, mas **plausível não é declarado**, e a página não trata do caso.

Consequência honesta: **a reachability do estado não está provada.** Ou a Task 5 veta a regra, ou ela entra marcada como `field-heuristic` com a nota de que a fonte não confirma que o estado é atingível — e nesse caso a fixture positiva é construída, não observada, o que precisa ficar escrito no golden.

Três casos que o extrator precisa distinguir, e o terceiro é o que erra:

| Situação | Decisão |
|---|---|
| algum eixo excede, com todos os valores lidos | `initial_exceeds_maximum: True` |
| nenhum eixo excede | `initial_exceeds_maximum: False` |
| `maximumCapacity` ausente (**`Required: No`** na referência), ou `disk` ausente num dos lados, ou unidade fora do conjunto | **omitir a chave** + `emrs.unresolved` |

`maximumCapacity` ser opcional na API não é hipótese: está declarado. O caso "não dá para decidir" é, portanto, comum, não excepcional.

## 6. Destinos de log — a regra muda de forma

**Este é o ponto em que a pesquisa contrariou o desenho.** O spec propôs a regra como *"nenhum destino de log declarado"*, transposição do `SF-EMR-006`. No EMR on EC2 isso funciona porque `LogUri` ausente significa **sem destino**. No Serverless, não:

> *"**enabled** — Enables managed logging and **defaults to true**. If set to false, managed logging will be turned off."*
> — `ManagedPersistenceMonitoringConfiguration`

> *"**By default, EMR Serverless stores application logs securely in Amazon EMR managed storage for a maximum of 30 days.**"*
> — *Storing logs*

**`monitoringConfiguration` ausente significa managed persistence LIGADA**, com retenção de 30 dias e a UI de aplicação disponível. Uma regra que dispare por ausência acusaria a configuração default — que é a segura — e faria isso na área inteira de qualquer application que nunca tocou em monitoramento. Seria o pior tipo de defeito de regra segundo `rules/catalog/README.md`: acusar configuração correta.

Os três destinos, e o que a fonte diz de cada:

| Destino | Campo | Default | Como fica ausente |
|---|---|---|---|
| Managed storage | `managedPersistenceMonitoringConfiguration.enabled` | **`true`** | só com `enabled: false` explícito |
| Amazon S3 | `s3MonitoringConfiguration.logUri` | ausente | ausência do objeto ou do campo |
| CloudWatch | `cloudWatchLoggingConfiguration.enabled` | **`false`** — *"By default, CloudWatch logging is disabled for EMR Serverless"* | ausência do objeto, ou `enabled: false` |

(Existe um quarto: `prometheusMonitoringConfiguration`. Ele carrega `remoteWriteUrl`, **não** `enabled`, e é destino de **métrica**, não de log. Não conta como destino de log.)

**A forma correta da regra**, portanto, é uma conjunção com um termo explícito: `managedPersistenceMonitoringConfiguration.enabled == false` **e** nenhum `s3MonitoringConfiguration.logUri` **e** CloudWatch não habilitado. Isso é atingível — o exemplo oficial de `create-application` da própria documentação de configuração default mostra `"managedPersistenceMonitoringConfiguration": {"enabled": false}` combinado com S3 — mas exige um ato deliberado, e é isso que torna o achado interessante em vez de ruidoso.

A gravidade tem fonte, e é dura:

> *"If you turn off the default option, Amazon EMR can't troubleshoot your jobs on your behalf. Example: You cannot access Spark-UI from the EMR Serverless Console."*

E a tabela de opções da mesma página declara que **S3 sozinho não sustenta a UI de aplicação**:

| Option | Event logs | Container logs | Application UI |
|---|---|---|---|
| Managed storage | managed storage | managed storage | Supported |
| Both managed storage and S3 | ambos | S3 bucket | Supported |
| Amazon S3 bucket | S3 bucket | S3 bucket | **Not supported** |

com a recomendação explícita *"We suggest that you keep the **Managed storage** option selected. Otherwise, you can't use the built-in application UIs."*

Isso sustenta o argumento do spec — sem event log este motor não diagnostica nada — e sustenta **mais** do que o spec pediu: mesmo com S3 configurado, desligar managed storage custa a UI. Se isso deve virar um segundo achado, de severidade menor, é decisão da Task 5; a fonte permite.

Retenção: 30 dias no máximo em managed storage. Não há como estendê-la ali, então log que precise durar mais exige S3 — outro argumento que a fonte sustenta e que o `explanation` pode usar.

## 7. Segredo em `runtimeConfiguration`

`runtimeConfiguration` é array de `Configuration`, e `Configuration` tem a mesma forma do `Configurations` do EMR on EC2:

| Campo | Tipo | Obrigatório | Constraints |
|---|---|---|---|
| `classification` | String | **sim** | 1–1024, `.*\S.*` |
| `properties` | map String → String | não | 0–100 entradas; chave 1–1024, valor 0–1024 |
| `configurations` | array de `Configuration` | não | 0–100, **aninhado** |

O aninhamento é recursivo e declarado — o achatamento precisa descer, não só ler o primeiro nível.

**A diferença com o EMR on EC2, e ela importa.** O bloco *Warning* que sustenta o `SF-EMR-002` — *"Amazon EMR Describe and List API operations emit custom and configurable settings (...) in plaintext"* — **não foi encontrado na documentação do EMR Serverless** nesta coleta. O que existe é a afirmação equivalente pelo avesso, na página de Secrets Manager:

> *"When you store your data in Secrets Manager and use the secret ID in your configurations for EMR Serverless, **you don't pass sensitive configuration data to EMR Serverless in plain text and expose it to external APIs.**"*

A leitura é direta: sem o Secrets Manager, o dado **é** passado em texto claro e **é** exposto a APIs externas. E o *Response Syntax* de `GetApplication` confirma o que essa exposição é concretamente — `runtimeConfiguration[].properties` volta como map de string para string, sem redação. Isso sustenta a regra.

**O mecanismo oficial de correção é específico do Serverless e mais barato que o do EC2.** Anota-se o valor com `EMR.secret@`:

```json
{
  "classification": "spark-defaults",
  "properties": {
    "spark.hadoop.javax.jdo.option.ConnectionPassword": "EMR.secret@{{SecretName}}"
  }
}
```

> *"To indicate that a key-value pair for a configuration contains a reference to a secret stored in Secrets Manager, add the `EMR.secret@` annotation to the configuration value. For any configuration property with secret Id annotation, EMR Serverless calls Secrets Manager and resolves the secret at the time of job execution."*

Duas consequências para o achado:

- **A remediação não exige recriar nada.** Em EMR on EC2 a configuração de cluster não é editável em cluster em execução, então corrigir um segredo é sempre um cluster novo. Aqui `runtimeConfiguration` é alterável por `update-application` com a application em `CREATED` ou `STOPPED`. A rotação do segredo continua sendo a parte que não pode ser adiada — o valor já esteve exposto.
- **O extrator precisa reconhecer `EMR.secret@` como o estado correto**, e não acusá-lo. Um valor anotado com `EMR.secret@` é um *ID de segredo*, não um segredo — acusá-lo seria acusar exatamente a correção que o achado pede. Isso não existe no vocabulário de `emr_cluster.py` e é acréscimo desta área.

Nota de operação, da mesma página: *"EMR Serverless retrieves the secret value from an annotated configuration when the job transitions to a running state. If you or a process updates the secret value in Secrets Manager, you must submit a new job so that the job can fetch the updated value."* Jobs já em execução não pegam o valor novo.

## 8. Placar das cinco candidatas do spec

| Pergunta | Veredito | Fonte |
|---|---|---|
| Pré-init com auto-stop desligado | **sobrevive**, P0 | frase direta da AWS, incluindo a palavra `charges` (§3) |
| Auto-stop com `idleTimeoutMinutes` longo demais | **sobrevive com forma mudada** | defaults e teto documentados; limiar intermediário é `field-heuristic`; e o custo depende de haver pré-init (§4, §3) |
| `initialCapacity` acima de `maximumCapacity` | **sobrevive só como `field-heuristic`** | aritmética e unidades documentadas; **reachability do estado não documentada** (§5) |
| Nenhum destino de log declarado | **sobrevive com forma mudada** | não pode disparar por ausência: managed persistence é default `true` (§6) |
| Segredo em `runtimeConfiguration` | **sobrevive**, P0 | sustentada pelo avesso, via Secrets Manager; sem o *Warning* de texto claro que o EC2 tem (§7) |

Nenhuma das cinco foi vetada por falta de fonte. **Duas mudaram de forma**, e nas duas a mudança é o que impede a regra de acusar a configuração default.

## Fontes

- Pre-initialized capacity for working with an application in EMR Serverless. https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/pre-init-capacity.html (retrieved 2026-08-04)
- Amazon EMR pricing (modelo de cobrança de worker do EMR Serverless). https://aws.amazon.com/emr/pricing/ (retrieved 2026-08-04)
- Storing logs (managed storage, S3, CloudWatch, retenção de 30 dias, tabela de UI). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/logging.html (retrieved 2026-08-04)
- Default application configuration for EMR Serverless (precedência de `StartJobRun` e granularidade do merge). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/default-configs.html (retrieved 2026-08-04)
- Secrets Manager for data protection with EMR Serverless (a anotação `EMR.secret@`). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/secrets-manager.html (retrieved 2026-08-04)
- Interact with and configure an EMR Serverless application (tabela de estados). https://docs.aws.amazon.com/emr/latest/EMR-Serverless-UserGuide/applications.html (retrieved 2026-08-04)
- GetApplication (Response Syntax). https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_GetApplication.html (retrieved 2026-08-04)
- Application (data type). https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_Application.html (retrieved 2026-08-04)
- WorkerResourceConfig (patterns de `cpu`, `memory`, `disk`, `diskType`). https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_WorkerResourceConfig.html (retrieved 2026-08-04)
- MaximumAllowedResources. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_MaximumAllowedResources.html (retrieved 2026-08-04)
- AutoStopConfig (defaults e faixa 1–10080). https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_AutoStopConfig.html (retrieved 2026-08-04)
- AutoStartConfig. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_AutoStartConfig.html (retrieved 2026-08-04)
- MonitoringConfiguration. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_MonitoringConfiguration.html (retrieved 2026-08-04)
- ManagedPersistenceMonitoringConfiguration (`enabled` defaults to true). https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_ManagedPersistenceMonitoringConfiguration.html (retrieved 2026-08-04)
- CloudWatchLoggingConfiguration. https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_CloudWatchLoggingConfiguration.html (retrieved 2026-08-04)
- Configuration (data type). https://docs.aws.amazon.com/emr-serverless/latest/APIReference/API_Configuration.html (retrieved 2026-08-04)

### O que estas fontes NÃO sustentam

- **Que uma application `STARTED` sem `initialCapacity` custe zero.** O que está declarado é que a cobrança de vCPU/memória/armazenamento vai do momento em que o worker fica pronto até ele parar. A ausência de cobrança de outra natureza não foi encontrada afirmada — **e não encontrar não é a mesma coisa que não existir**. A tabela da §3 marca essa linha como dedução.
- **Que a API aceite `initialCapacity` acima de `maximumCapacity`.** Nem que rejeite. **Não afirmar reachability** do estado que a regra da §5 acusa; se a regra entrar, a fixture positiva é construída e o golden precisa dizê-lo.
- **Um vocabulário fechado de worker types.** `DRIVER`, `EXECUTOR` e `TEZ_TASK` aparecem nos exemplos oficiais; a chave do map aceita `[a-zA-Z]+[-_]*[a-zA-Z]+`, que é aberto. **Não citar lista fechada.** O limite de 10 entradas, esse é declarado.
- **Um vocabulário fechado de `type` da application.** `SPARK` e `HIVE` aparecem nos exemplos; a referência de API declara só `String`, 1–64, **sem `Valid Values`**. Ao contrário de `state` e `architecture`, que trazem `Valid Values` explícitos e podem ser tratados como fechados.
- **Que os patterns de `cpu`/`memory`/`disk` valham para a resposta, e não só para a requisição.** Eles são restrições de entrada da API. O extrator trata valor fora do conjunto como `unresolved`, não como impossível.
- **Que `EMR.secret@` seja a única anotação de segredo do EMR Serverless**, nem em quais releases ela passou a existir. A página não declara release mínima, e esta coleta não achou onde ela esteja declarada.
- **O bloco *Warning* de texto claro em Describe/List que sustenta o `SF-EMR-002`.** Ele **não** foi encontrado na documentação do EMR Serverless. A regra da §7 se apoia na frase invertida da página de Secrets Manager mais o *Response Syntax* de `GetApplication` — **não citar o Warning do EC2 como fonte de uma regra `SF-EMRS`**.
- **Qualquer afirmação sobre o que um job run efetivamente executou.** `get-application` é o padrão da application, e `StartJobRun` o sobrepõe (§0). Nenhum achado desta área pode ser redigido como afirmação sobre execução.
- **A retenção de log em S3 ou CloudWatch.** Só a de managed storage (30 dias, máximo) foi encontrada declarada.
