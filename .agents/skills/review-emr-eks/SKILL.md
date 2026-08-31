---
name: review-emr-eks
description: Use quando revisar a execução de um job Amazon EMR on EKS pelo par `describe-virtual-cluster` + `describe-job-run` do `emr-containers` (segredo em texto claro nas duas superfícies de configuração, destino de log ausente, `persistentAppUI` desligado, alocação dinâmica sem `shuffleTracking` no Kubernetes). Use também quando a pergunta for "cadê os logs desse job run", "por que não tem Spark UI", "esse job rodou com qual configuração" ou "quem submeteu isso com senha na linha de submit", mesmo que ninguém fale em regra. Se você está prestes a ler `describe-job-run` no olho, rode `sparkforge analyze emr-eks` e `sparkforge judge` em vez disso. Esta skill NÃO julga capacidade de nó, pod pendente nem pod template — nada disso está no `emr-containers`, e supor que está é inventar. Para EMR on EC2 e EMR Serverless a skill é `review-emr-cluster`.
subagent: true
agent: emr-infra-reviewer
---

# Review EMR on EKS

## A fronteira, antes da capacidade

Três coisas esta área **não julga**. Elas vêm primeiro de propósito: nomeá-las é a única
diferença entre "não achei problema" e "não olhei".

**1. Capacidade de nó e pod pendente.** Nodegroup, Karpenter, Cluster Autoscaler,
`capacityType`, quota de namespace, `LimitRange` — tudo isso é do **Amazon EKS**, e o
artefato desta skill é do **`emr-containers`**. São dois serviços, dois IAM e duas matrizes
de versão. Nenhum achado seu pode dizer que o pod ficou pendente por falta de nó, nem que o
cluster está subdimensionado: essa pergunta não tem resposta neste dump, e a ausência é
**decidida**, não esquecimento. O `virtualCluster` traz um campo `nodeLabel`, e a própria
descrição dele carrega a ressalva ("it requires relevant scaling and policy engine addons"):
ele pode estar preenchido e não ter efeito nenhum. Ler esse campo seria afirmar sobre o EKS,
não sobre o EMR.

**2. Pod template.** Quando a configuração aponta `spark.kubernetes.driver.podTemplateFile`
(ou o par do executor), o YAML apontado mora **fora** deste artefato — lê-lo exigiria um
`GetObject` no S3 que este caminho não faz. O extrator emite
`emrc.pod_template.unresolved` **com o path**, e esse kind é o único da área que **nenhuma
regra lê**: ele existe para ser recusa visível. O operador vê que o template existe e que
não foi lido. `nodeSelector`, `tolerations` e `resources` moram lá — metade do diagnóstico de
pod pendente. Transformá-lo em achado acusaria alguém de ter usado um recurso legítimo;
omiti-lo faria o relatório parecer completo.

**3. O que o pod recebeu.** `DescribeJobRun` diz o que **uma execução pediu**. A AWS publica
uma precedência de cinco níveis, e o nível 1 — o mais alto — é "Configuration supplied when
creating SparkSession", isto é, `spark.conf.set` dentro do código do job, que este artefato
não vê. O nível 4, "optimized configurations chosen by Amazon EMR for the release", a AWS
declara existir e **não publica em tabela nenhuma**. Por isso ausência de uma propriedade no
artefato significa "o chamador não pediu", **nunca** "o valor não está setado" — e nenhuma
regra desta área dispara por ausência de propriedade.

**A inversão que vale a pena carregar na cabeça.** `get-application` do EMR Serverless devolve
o **padrão** da application, e `StartJobRun` o sobrepõe: nenhum achado de `SF-EMRS` prova o que
um job run executou. Aqui é o contrário na primeira metade — `describe-job-run` devolve **uma
execução**, e o `configurationOverrides` que voltou é o que **aquele** job run carregou,
ninguém o sobrepõe depois. E é **mais estreito** na segunda: o que voltou é o que o chamador
pediu, não a configuração efetiva dentro do executor.

## Procedimento

### 1. Colete as duas chamadas num arquivo só

Cluster virtual e execução são **APIs separadas** do `emr-containers`, e nenhuma contém a
outra — diferente do Serverless, onde `GetApplication` devolve tudo num objeto:

```bash
sparkforge collect emr-eks --repo . \
  --virtual-cluster-id 0abcXXXXXXXXXXXXXXXXXXXXXXXXX \
  --job-run-id 0runXXXXXXXXXXXXXXXXXXXXXXXXX \
  --now <ISO8601>
```

À mão, o equivalente é rodar os dois e juntar as respostas num JSON só, em camelCase, sob as
chaves de topo que o coletor grava:

| Subcomando `aws emr-containers` | Chave no dump | O que morre sem ele |
|---|---|---|
| `describe-virtual-cluster` | `virtualCluster` | `emrc.virtual_cluster` — identidade, estado, e o namespace ao qual o cluster virtual mapeia |
| `describe-job-run` | `jobRun` | tudo o mais: `emrc.job_run`, `emrc.configuration`, `emrc.spark_submit_parameters`, `emrc.monitoring`, e as quatro regras |

Tool MCP equivalente: `sparkforge_collect_emr_eks`, com `virtual_cluster_id`, `job_run_id`, `repo` e `now`.

**Os dois ids são obrigatórios, e nome não serve.** `DescribeJobRun` exige o
`virtual_cluster_id` junto do `job_run_id` — a própria API não aceita um job run sem o cluster
virtual que o contém. Resolver por nome escolheria uma entre homônimas em silêncio.

Ficam **fora por decisão**, não por limitação da API: `list-job-runs` (é listagem, não coleta
de uma execução identificada), o pod template apontado pela configuração (outra chamada), e
todo o lado EKS.

### 2. Extraia os facts

```bash
sparkforge analyze emr-eks --path <arquivo ou diretório com os dumps> \
  --out .sparkforge/facts_emr_eks.json
```

Tool MCP equivalente: `sparkforge_analyze_emr_eks`. Ela **não** chama a API do `emr-containers` — só lê o JSON já salvo em disco.

Oito kinds saem daqui, e três deles são declaração de limite, não observação:

| Kind | O que é |
|---|---|
| `emrc.virtual_cluster` | identidade e estado do cluster virtual — **nenhuma regra o lê** |
| `emrc.job_run` | a execução: release label, papel de execução, estado, tentativa |
| `emrc.configuration` | `configurationOverrides.applicationConfiguration` achatada por classificação |
| `emrc.spark_submit_parameters` | as propriedades tokenizadas da linha de `spark-submit` |
| `emrc.monitoring` | os destinos de log e `persistentAppUI` — **sai sempre**, inclusive quando o bloco não veio |
| `emrc.pod_template.unresolved` | a recusa visível, com o path do template |
| `emrc.unresolved` | classificação, unidade ou tokenização fora do documentado — contado, nunca adivinhado |
| `emrc.analyzed` | o que foi lido |

Leia `emrc.unresolved` e `emrc.pod_template.unresolved` **antes** de qualquer conclusão.
`sparkSubmitParameters` é uma string única de até 102400 caracteres — a linha de submit
inteira —, e tokenizar linha de shell é onde parsers erram: valor com espaço, aspas, `=`
dentro do valor. Falha de tokenização sai como `unresolved`, e um relatório que a ignora
afirma sobre uma linha que ninguém leu inteira.

### 3. Julgue

```bash
sparkforge judge --facts .sparkforge/facts_emr_eks.json --show-skipped
```

**Sem flag de versão, e aqui isso é uma decisão medida, não conveniência.** As quatro regras
desta área declaram escopo de runtime **vazio**, e a razão **não** é falta de matriz: a AWS
**publica** matriz de release para EMR on EKS, e ela está transcrita em
`knowledge/emr-eks/runtime-matrix.md`. A razão é a outra ponta, e está na DV-14 do design da
fase: **nenhuma fonte alimenta `RuntimeContext.spark` a partir de um artefato `emrc.*`**.
`sparkforge/facts/runtime_detect.py` deriva Spark de `GLUE_MATRIX` (por `glue_version`), de
`EMR_MATRIX` (por release de EMR on EC2) e da leitura direta de `spark.runtime_version` do
event log — o `releaseLabel` do EKS não entra em nenhuma das três. A matriz existe publicada e
ninguém a ligou ao contexto.

A consequência prática: uma regra desta área que restringisse por `spark` passaria no golden
(as fixtures declaram `runtime` no `meta.yaml`) e seria **pulada em toda execução real**,
porque `in_scope` falha fechada. Golden verde por SKIP é pior que vermelho — ninguém investiga
o que passou. Enquanto isso, versão que você cite entra **declarada** e rotulada como tal,
nunca derivada do `releaseLabel`.

E a `EMR_MATRIX` do EMR on EC2 **não** vale aqui, por razão mais forte que falta de fonte: ela
é **medidamente errada** para EKS — Iceberg diverge em 6 de 26 releases comparáveis e Spark em
4. Nem a matriz do EKS pode restringir por `iceberg`, `python` ou `hadoop`: a linha
`Supported applications` é publicada por família e não por variante, e `emr-7.7.0-java8-latest`
não tem Iceberg.

### 4. Interprete pelas duas superfícies

A mesma propriedade pode chegar por `configurationOverrides.applicationConfiguration` (kind
`emrc.configuration`) ou por `jobDriver.sparkSubmitParameters` (kind
`emrc.spark_submit_parameters`), e o extrator emite **dois facts em vez de um**. A AWS declara
quem vence:

> *"If you pass the same configuration in an application override and in Spark submit
> parameters, the Spark submit parameters take precedence."*

Ao reportar, **escreva de qual superfície o valor veio**. Um valor lido só em
`applicationConfiguration`, sem conferir a linha de submit, pode ser um valor que **perdeu** —
e acusá-lo é acusar configuração correta.

## O que a área julga — as quatro regras

Limiares e severidades **não** estão aqui de propósito; a lista autoritativa é
`sparkforge rules lookup --category emr-eks`. Esta tabela é uma foto, e o catálogo cresce.

| Regra | Fact que consome | O que ela de fato afirma |
|---|---|---|
| `SF-EMRK-001` | `emrc.configuration` **ou** `emrc.spark_submit_parameters` com `attrs.secret_pattern_match` | Literal de credencial numa superfície que `DescribeJobRun` devolve **sem redação** a qualquer principal com permissão de leitura |
| `SF-EMRK-002` | `emrc.monitoring` com `measures.log_destination_count == 0` | Nenhum destino de log neste job run — o rastro morre com o pod |
| `SF-EMRK-003` | `emrc.monitoring` com `attrs.persistent_app_ui` **escrito** `DISABLED` | Este job run não gerou event log, e a Spark UI não existe |
| `SF-EMRK-004` | `emrc.spark_submit_parameters` (duas condições, mesma superfície) | Alocação dinâmica ligada com `shuffleTracking` desligado **por escrito** — no Kubernetes o ramo do external shuffle service não existe |

Quatro leituras que mudam o que você escreve:

**`SF-EMRK-001` é achado de segurança e tem precedência** sobre qualquer recomendação de
performance no mesmo relatório. O valor nunca aparece no fact — o extrator grava `<redigido>`
e marca `attrs.secret_pattern_match` — e não deve aparecer no seu relatório também. E o
remédio aqui é **diferente** do que a área do Serverless recomenda: a anotação
`EMR.secret@{{Nome}}` está documentada para EMR on EC2 e para EMR Serverless, e a página da
AWS que **enumera** quais deployments de EMR integram com o Secrets Manager tem exatamente
duas seções — EC2 e Serverless. EMR on EKS não aparece. Isso mede que a integração **não está
documentada** aqui, nunca que ela não exista; propor um mecanismo que nenhuma fonte declara
disponível seria inventar o conserto, e conserto inventado fecha a investigação. O que a fonte
deste serviço sustenta é Secret do Kubernetes montado no pod, com RBAC restringindo quem o lê.

**`SF-EMRK-002` dispara por ausência, e o Serverless não podia.** Lá,
`managedPersistenceMonitoringConfiguration.enabled` tem default `true` e a AWS publica 30 dias
de retenção: ausência significa **protegido**. Aqui não existe declaração equivalente, e a
fonte diz o contrário com `must` literal repetido em duas páginas — *"you must configure your
jobs to send log information to Amazon S3, Amazon CloudWatch Logs, or both"*. A ausência do
bloco **já é** zero destino, e por isso `emrc.monitoring` sai sempre, inclusive quando
`monitoringConfiguration` não veio no payload.

**`managedLogs` não é o managed storage do Serverless**, e confundir os dois é o erro caro
desta área. O escopo declarado de `allowAWSToRetainLogs` é estreito — "system namespace logs
when running a job using Native FGAC" —, é log de **sistema** sob um modo de auth específico e
não log de aplicação, não tem default declarado nem na referência de API nem na de CLI, e
**nenhuma retenção é publicada**. Ele não conta como destino, e sua presença **não desarma**
`SF-EMRK-002`. `containerLogRotationConfiguration` também não: rotação é quanto o arquivo dura
dentro do container, não para onde ele vai.

**`SF-EMRK-003` exige `DISABLED` escrito, e nunca a ausência do campo.** O default de
`persistentAppUI` **não é publicado** em lugar nenhum — nem na referência de API de
`MonitoringConfiguration`, nem na de CLI de `start-job-run`, nem nas páginas de logging do
guia. Disparar por ausência afirmaria um default que ninguém mediu. É a mesma disciplina de
`SF-EMRK-004` pelo caminho inverso: lá o default **é** conhecido (`shuffleTracking.enabled` é
`true` desde o Spark 3.0.0, na versão fixada) e por isso a ausência é o estado **seguro**;
aqui não se sabe, e não saber também proíbe o disparo.

**`SF-EMRK-004` é `confidence: medium` de propósito, e tem dois pontos cegos declarados.**
A disjunção que a fonte publica tem **quatro** ramos, não dois: external shuffle service,
shuffle tracking, decommission de blocos de shuffle, e um `ShuffleDataIO` customizado com
armazenamento confiável. O achado observa os dois primeiros; os ramos 3 e 4 são conferência
**do operador**. E ele lê **uma superfície só** — `sparkSubmitParameters`, o nível 2 da
precedência —, então um job run que configure alocação dinâmica apenas por
`applicationConfiguration` **não é julgado**: ele não aparece em `findings` nem em `skipped`, a
regra é avaliada e não casa. A alternativa seria pior — ler o override sem poder conferir a
linha de submit acusaria um valor que perdeu. Nenhuma fonte da AWS nomeia essa combinação como
defeito; o que existe é uma **relação declarada** entre duas propriedades. Escreva "relação a
conferir", nunca "o job vai falhar".

## O que está vetado, e por quê

Dois vetos apurados na pesquisa de fontes. Os dois são do tipo mais raro do repositório —
vetados **não** por falta de fonte, mas por **fonte que diz o oposto** —, e o primeiro é o
exemplar mais literal disso que existe aqui.

**V-EK-1 — imagem de container em tag móvel (`:latest` no fim do URI de ECR) não é achado.**
A página *Details for selecting a base image URI* dá o formato e o exemplo oficial, e a tag do
exemplo **é** `:latest`
(`895885662937.dkr.ecr.us-west-2.amazonaws.com/spark/emr-7.13.0:latest`); os três URIs da
página usam a mesma tag. As *Considerations for customizing images* têm seis itens — usuário
`hadoop:hadoop`, `applicationOverrides` em vez de editar `spark-defaults.conf`, seis diretórios
montados em runtime, repositório Docker, aviso de preço — e **nenhum** sobre imutabilidade de
tag, digest ou fixar versão. Uma regra aqui acusaria a configuração que a AWS ensina no próprio
exemplo. E o que destrava este veto **não é medida nenhuma**: nenhum plano físico, nenhum
baseline, nenhum event log muda a conta. É a AWS mudar de recomendação. Por isso ele não tem
`blocked_on`.

**V-EK-2 — release label com sufixo `-latest` (`emr-7.13.0-latest`) não é defeito.** Mesmo
tipo de fonte, e o objeto é **outro** — confundir os dois é o erro mais fácil desta área. A
página de releases declara `emr-x.x.x-latest` **ou** `emr-x.x.x-yyyymmdd` como as duas formas
legítimas, e o `-latest` é **recomendado**: *"When you use the `-latest` suffix, you ensure
that your Amazon EMR version always includes the latest security updates"*.

**A tensão que vai confundir quem vier depois, porque as duas metades são verdade ao mesmo
tempo.** Mobilidade de ponteiro **não** é defeito de segurança — é o que os dois vetos acima
registram. Mas ela **é** problema de **diagnóstico**: duas execuções com o mesmo
`emr-7.13.0-latest` podem ter rodado imagens diferentes, justamente porque o ponteiro se move
para pegar patch. Uma comparação entre dois runs que assuma runtime idêntico porque o
`releaseLabel` é idêntico está errada **por construção** quando o sufixo é `-latest`; com
`-yyyymmdd`, é sólida.

O que sobra disso é **ressalva de comparabilidade dentro do texto**, e nunca um `Finding`. Um
achado que dissesse "você usou tag móvel" acusaria a recomendação da AWS; uma ressalva que diz
"estes dois runs não provam o mesmo binário" limita a inferência sem acusar ninguém. A
diferença entre as duas é a fronteira desta área inteira.

## O que o extrator emite e nenhuma regra lê

Nada disso é dívida, e o critério é herdado de `emr-infra.yaml` e `emr-serverless.yaml`:
capacidade de extrator sem consumidor é dívida; atributo descritivo transcrito de uma resposta
que o extrator **já** lê por outro motivo, não é. Aqui as duas chamadas produzem dado julgado,
então não há chamada de API que só alimente campo inerte.

- **`emrc.virtual_cluster` inteiro.** Deliberado, e a fonte é quem decide: "a single virtual
  cluster maps to a single Kubernetes namespace" e "virtual clusters do not create any active
  resources that contribute to your bill or that require lifecycle management outside the
  service". **Não existe regra de capacidade ociosa nesta área** — `SF-EMR-009` (cluster EC2
  ocioso) e a regra de pré-inicialização do Serverless não têm análogo. Um `virtualCluster` em
  `RUNNING` sem job nenhum não é sintoma de nada.
- **`attrs.state` e `attrs.failure_reason` do job run.** Descritivos. Estado não é defeito, e
  falha de execução não é configuração errada. `SUCCEEDED` não existe — o estado terminal de
  sucesso chama `COMPLETED`. `ARRESTED`, no estado do cluster virtual, está nos `Valid Values`
  e nenhuma página encontrada o define: valor conhecido, semântica desconhecida.
- **`measures.release_major` / `release_minor`.** Contexto, e a razão de existirem é negativa:
  elas provam que o label casou a forma numérica. São **omitidas** em `emr-spark-8.0.0-*` e em
  qualquer forma com barra (`notebook-spark/emr-7.13.0-latest`), que o pattern da API aceita.
- **`attrs.container_log_rotation_declared`** e **`attrs.managed_logs_declared`.** Descritivo o
  primeiro, lido por humano o segundo — ver a seção sobre `SF-EMRK-002`.

## Quando NÃO usar

- O dump é `describe-cluster` (EMR on EC2) ou `get-application` (EMR Serverless): a skill é
  `review-emr-cluster`, e as áreas são `SF-EMR` e `SF-EMRS`.
- O job roda em AWS Glue: a área é `SF-GLUE` e a skill é `review-glue-terraform`.
- A pergunta é sobre **capacidade do cluster EKS** — nó, pod pendente, autoscaler, quota de
  namespace. Não há fact deste repositório que descreva isso, e supor que `SF-EMRK` cobre é
  inventar. A resposta está no lado EKS, fora daqui.
- Você quer achar stage dominante, skew, spill ou GC de um run: isso é execução, e vem de
  `analyze-spark-ui` sobre o event log — que só existe se `SF-EMRK-002` e `SF-EMRK-003`
  estiverem verdes.
- O problema está no código ou no plano físico: comece por `sparkforge-diagnose`.
- A pergunta é sobre tabela Iceberg, small files ou layout: `optimize-iceberg-table` e
  `optimize-parquet-layout`.

## Red flags

- Escrever que o pod ficou pendente, que faltou nó ou que o cluster está subdimensionado. Nada
  disso é observável a partir de `emr-containers`, e afirmar é inventar a metade que falta.
- Ler um valor em `emrc.configuration` e concluir sobre o valor **efetivo** sem conferir
  `emrc.spark_submit_parameters`. A linha de submit vence, e o override que discorda dela é
  ruído que a próxima pessoa vai ler como verdade.
- Tratar `managedLogs` como destino de log, ou como o managed storage do Serverless. Ele é log
  de namespace de sistema sob Native FGAC, sem default declarado e sem retenção publicada.
- Disparar por ausência de propriedade. Ausência aqui significa "o chamador não pediu", e o
  nível 4 da precedência — as otimizações que o EMR escolhe pela release — não é publicado em
  tabela nenhuma.
- Acusar `:latest` na imagem ou `-latest` no release label como defeito. Ver V-EK-1 e V-EK-2:
  os dois estão nos exemplos e nas recomendações da própria AWS.
- Comparar dois runs de `-latest` como se fossem o mesmo binário. É a ressalva de
  comparabilidade, e ela vale mesmo com os dois vetos de pé.
- Recomendar a anotação `EMR.secret@{{Nome}}` aqui. Ela está documentada para EC2 e para
  Serverless, e a página que enumera as integrações com o Secrets Manager **não tem seção** para
  EMR on EKS.
- Prometer que a correção entra neste job run. **Não existe `update-job-run`**: o artefato é uma
  execução que já aconteceu, e a correção mora onde o `start-job-run` é montado — código, IaC ou
  orquestrador.
- Derivar versão de Spark, Iceberg ou Python do `releaseLabel`. A matriz existe e não está
  ligada ao contexto de runtime; versão citada entra declarada.

## Preservar o resultado, com o verbo que produz a evidência

Toda recomendação desta área toca a linha de submit ou o `configurationOverrides` da **próxima**
submissão, e duas delas mudam o comportamento de execução: trocar a origem de uma credencial
(`SF-EMRK-001`) e mexer em alocação dinâmica (`SF-EMRK-004`). Nenhuma das duas pode mudar o
conjunto de linhas escrito, e é exatamente isso que precisa ser provado — não assumido.

`sparkforge funcval plan --facts <facts.json> --out <plano.json>` deriva o plano — `--facts` é
repetível, porque o alvo vem do `pyspark.write` e o schema e os agregados vêm do
`catalog.table_schema` —, e `sparkforge funcval compare --plan <plano.json> --before
<antes.json> --after <depois.json>` compara os dois lados **que o operador mediu**: nenhum dos
dois executa consulta, roda Spark ou chama AWS. Tools MCP: `sparkforge_funcval_plan` e
`sparkforge_funcval_compare`. O plano é a evidência do gate `functional_validation_defined`, e
`ROUTE-015` é a rota que manda defini-lo. O lado `--before` só existe se alguém o mediu **antes**
de a mudança tocar o alvo.

Os quatro eixos são **proxies**, e escrever o contrário promete o que a ferramenta não entrega:
contagem, schema, chaves e agregados iguais **não provam** que o dado é o mesmo — duas linhas
podem trocar valores entre si e os quatro passam. Escreva "nenhum dos quatro proxies detectou
divergência", nunca "o resultado é idêntico". Sem `--key`, a chave de negócio sai em
`undeclared_axes` com a razão, e isso vai dito. `SF-FVAL-005` acesa invalida a leitura das outras
quatro.

E há um recorte que só esta área tem: **sem destino de log e sem `persistentAppUI`, a validação
de comportamento fica sem prova**. `DescribeJobRun` mostra o que foi pedido; o efeito sobre o
número de executores, sobre `FetchFailed` e sobre stages reexecutados só existe no event log. Se
`SF-EMRK-002` ou `SF-EMRK-003` estiverem acesas, o primeiro passo de qualquer experimento é
apagá-las — senão a mudança seguinte não tem como ser medida.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved` — nesta área os dois que
mais importam são `emrc.unresolved` e `emrc.pod_template.unresolved`; confirme o runtime, e
lembre que aqui ele **não** vem do artefato. Feche assinando com `sparkforge report sign` e
conferindo com `sparkforge report verify`.

Manutenção destrutiva você **não executa**. Nesta área ela tem uma forma dominante e uma
armadilha: rotacionar um segredo exposto (`SF-EMRK-001`) derruba todo consumidor que ainda usa o
valor antigo, e apagar o prefixo de log de um job run apaga justamente a evidência com que você
trabalha. Escreva qual segredo, quem consome, e o que precisa estar reconfigurado antes — a
confirmação de escopo e retenção **sobe** a quem pode ser perguntado: o agente pai que
despachou, ou o operador na sessão. E **derive o plano de validação funcional** com
`funcval plan` antes de fechar a recomendação, comparando os dois lados medidos com
`funcval compare` — a regra 10, e ela nomeia o produtor de propósito: exigência sem verbo é
prosa.

Esta skill é **despachável** (`subagent: true` no espelho `.agents/skills/`), e
`ask_user_question` é **sempre negado** a um subagente. Dentro do despacho, obter a confirmação
aqui não é difícil: é impossível — por isso a regra 9 de `AGENT_PROTOCOL.md` manda não executar e
devolver a decisão a quem pode ser perguntado.
