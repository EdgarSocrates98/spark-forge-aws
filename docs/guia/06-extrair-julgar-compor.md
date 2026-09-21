# Extrair, julgar, compor: o motor determinístico

O resumo está no [README](../../README.md). Aqui fica o detalhe: a sequência mínima em
cada plataforma, por que extração e julgamento são verbos separados, e o que cada
extrator lê. A anatomia dos comandos está em [CLI](03-cli.md); o glossário, em
[Conceitos](01-conceitos.md).

## A camada determinística

Além da base de conhecimento e das Skills (que orientam um LLM), o pacote
inclui um analisador determinístico: extração de facts via AST estático
(nunca importa nem executa código analisado), julgamento contra um catálogo
de regras versionado em YAML ([Conhecimento e catálogo](07-conhecimento-e-catalogo.md)),
e um ciclo de vida de case (`.sparkforge/case.yaml`) que atravessa sessões e
ferramentas.

## Sequência mínima

```bash
pip install -e .
sparkforge runtime detect --glue 5.0
sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json
sparkforge judge --facts .sparkforge/facts.json --glue 5.0 --out .sparkforge/findings.json
sparkforge next-step --repo . --findings .sparkforge/findings.json
```

## EMR on EC2

No EMR on EC2 a sequência é a mesma, com uma diferença que importa: a release
não precisa ser declarada, porque o dump do cluster a carrega. `--facts` é
repetível, e `judge` correlaciona as fontes numa chamada só — código e
infraestrutura juntos, que é o que faz um achado de código ser julgado contra
o Spark que aquele cluster realmente roda.

```bash
sparkforge analyze emr-cluster --path cluster.json --out .sparkforge/facts-emr.json
sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json
sparkforge judge --facts .sparkforge/facts-emr.json --facts .sparkforge/facts.json \
  --out .sparkforge/findings.json
```

`--emr` existe nos três verbos que aceitam runtime (`judge`, `case open`,
`runtime detect`) e serve a quem sabe a release e **não** tem o dump. É
declaração, não observação: perde para o dump e para o event log, e discordar
de um deles vira divergência reportada — nunca valor substituído em silêncio.

## Databricks

`--databricks <versão>` declara o Databricks Runtime (`15.4` ou
`15.4.x-scala2.12`) e deriva a versão do Spark pela matriz em
[`knowledge/databricks/runtime-matrix.md`](../../knowledge/databricks/runtime-matrix.md);
a versão também é lida do event log
quando ele traz `spark.databricks.clusterUsageTags.sparkVersion` — a fonte oficial
documenta essa chave só como propriedade local de TaskContext, e a presença dela no
event log entregue por cluster log delivery ainda não foi confirmada (lacuna U1):
sem ela, a plataforma só se sabe pela flag.

`--photon on|off` declara o Photon: ligado, as regras de plano saem em `skipped`
com `databricks.photon.unresolved`, exceto as que só exigem `plan.python_udf` ou
`plan.aqe` (os nós `ArrowEvalPython` e `AdaptiveSparkPlan` continuam no plano sob
Photon, observado). Um plano com operadores Photon (fact `plan.photon`) também
liga essa recusa, sem a flag, e a recusa vale sempre — com ou sem
`--databricks`, porque ela é movida só pelo fact do plano. Com a plataforma
databricks detectada, a observação também vence a declaração no runtime:
`off` diante do plano Photon vira divergência `photon:` e o estado fica
`on`; sem declaração nem plano Photon, SF-ENV-006 avisa. Sem
`--databricks`, a declaração vira a divergência "declarado sem plataforma" e
não entra no runtime — a observação do plano tampouco entra, e a recusa das
regras de plano continua valendo do mesmo jeito, pelo fact. Fora deste
incremento: `_delta_log`, Jobs API, billing em DBU e coleta pela REST API.

## Por que extração e julgamento são verbos separados

`analyze` (extração) e `judge` (julgamento) nunca são o mesmo passo. Facts
extraídos de código-fonte são caros de recomputar — exigem re-parsear a
árvore inteira — mas o catálogo de regras evolui com frequência maior que o
código: um limiar corrigido, uma regra nova, uma fonte atualizada. Separar os
dois verbos permite **rejulgar facts antigos com um catálogo novo sem
reprocessar o código-fonte**, o que torna a evolução do conhecimento
auditável: cada revisão do catálogo pode ser aplicada retroativamente ao
mesmo conjunto de facts e o diff do resultado mostra exatamente o que mudou
no julgamento, isolado de qualquer mudança no código analisado.

## O que pode ser extraído

Os 42 extratores emitem 245 kinds distintos de fact (recontado em 2026-09-21),
e todos são offline: leem artefato que já está em disco e nunca chamam a AWS.
Cada verbo abaixo tem uma tool MCP de mesmo nome.

**Quatro deles não leem artefato nenhum**, e a diferença é de natureza:
`call_graph.py`, `bridge.py`, `exception.py` e `lakeformation.py` são derivação
pura sobre a UNIÃO dos facts que os outros já resolveram. O par mais próximo
disso é `lakeformation.py` e `lakeformation_grants.py`: mesmo namespace, e um
deriva enquanto o outro lê artefato. Eles existem porque o
motor de regras avalia **um fact por condição** e nunca combina `attrs` de dois
— quando a pergunta precisa cruzar duas fontes, ou quando o predicado não cabe
nos seis comparadores de `sparkforge/rules/expr.py`, quem cruza é uma etapa
anterior.

| Artefato | Verbo | Lê |
|---|---|---|
| Código PySpark | `analyze pyspark` | árvore `*.py`, por AST — nunca importa o código |
| Plano físico | `analyze plan` | saída colada de `explain("formatted")` |
| Event log do Spark | `analyze event-log` | `*.jsonl` de uma execução |
| Métricas SQL do plano | `analyze sql-metrics` | o mesmo event log, pela ótica de quanto cada fonte custou |
| Metadata Iceberg | `analyze iceberg` | dump das metadata tables |
| Glue Data Catalog | `analyze catalog-schema` | dump de `GetTables`/`GetTable` |
| Terraform do Glue | `analyze terraform` | HCL com `aws_glue_job` |
| SQL | `analyze sql` | `*.sql` e literais de `spark.sql(...)` |
| Workgroup do Athena | `analyze athena-workgroup` | dump de `get_work_group` |
| **Cluster EMR on EC2** | `analyze emr-cluster` | dump de `describe-cluster` e os cinco que o completam |
| **Application EMR Serverless** | `analyze emr-serverless` | dump de `get-application` |
| **Job run EMR on EKS** | `analyze emr-eks` | dumps de `describe-virtual-cluster` **e** `describe-job-run` do `emr-containers`, num arquivo só |
| **Definição `Jobs-as-Code` do Control-M** | `analyze controlm-jobs` | o JSON de definição de job versionado no repositório — o mesmo que `ctm build` valida. Com `--version <v>`, cruza as capacidades observadas com a matriz do Automation API |
| **Definição ASL do AWS Step Functions** | `analyze step-functions` | o `.asl.json` versionado no repositório, ou a saída salva de `aws stepfunctions describe-state-machine`: um fact por estado Task, com padrão de integração, `JobName` e retry efetivo. Com o Terraform do job no mesmo pool, `fuse` liga o Task ao `aws_glue_job` |
| **Histórico de execução do AWS Step Functions** | `analyze sfn-history` | a saída salva de `aws stepfunctions get-execution-history`: uma tentativa por par `TaskScheduled`/terminal, com ordem, resultado, duração e o `JobRunId` do Glue. Com o ASL do mesmo state machine no pool, `fuse` confronta o retry declarado com o observado |
| **Arquivo `.py` de um DAG do Apache Airflow** | `analyze airflow-dag` | o DAG lido por AST e nunca executado: um fact por operador instanciado, com os argumentos literais que decidem se o fluxo espera o job, se o mata junto com a task e se segura o worker, mais as dependências declaradas. Com o Terraform do job no mesmo pool, `fuse` liga a task ao `aws_glue_job` |
| **Validação de dados** | `analyze data-quality` | os mesmos `*.py`, pela ótica do check |
| **Processamento de grafo** | `analyze graph` | os mesmos `*.py`, pela ótica do GraphFrames |
| Listagem S3 | `analyze s3-listing` | dump de `s3api list-objects-v2` |
| Consumidores da tabela | `analyze consumers` | inventário declarado, versionado no repositório |
| Mudança de Terraform | `analyze terraform-diff` | dois estados do mesmo módulo |
| Grafo de chamadas | `analyze call-graph` | derivado dos facts de PySpark |
| **Rodapé do Parquet** | `analyze parquet-footer` | dump de `collect parquet-footer` — row group, estatística por coluna, dicionário, page index, bloom filter e codec |
| **Log do CloudWatch** | `analyze cloudwatch-logs` | resposta de `filter_log_events` já em disco — artefato SEPARADO do de `analyze cloudwatch`, que lê `get_metric_data` |
| **Decisão de IAM** | `analyze iam-access` | artefato de `collect iam-access` — a resposta de `SimulatePrincipalPolicy`, com a CAMADA que negou (boundary, SCP, deny explícito ou implícito). Simulação, não parse de policy |
| **Permissão do Lake Formation** | `analyze lakeformation-grants` | artefato de `collect lakeformation` — grant por principal, registro da localização S3, e o data lake settings da conta. É o único artefato que descreve **quem pode o quê** em vez de o que o job faz |
| **Assinatura de erro** | `analyze error-signatures` | derivado de `spark.exception` e de `cloudwatch.log_event`: casa a exceção contra as 23 assinaturas de `knowledge/errors/` (contadas em 2026-09-18 como `knowledge/errors/**/*.json`), por três portas (`exception_class`, `message_head`, `log_line`) |
| Métricas do CloudWatch | `analyze cloudwatch` | artefato de `collect cloudwatch` já em disco |
| Histórico de runs Glue | `analyze glue-job-runs` | diretório de artefatos de run, um JSON por run terminal |
| **Duas execuções comparadas** | `benchmark` | dois conjuntos de facts de event log, antes e depois |
| **Plano de validação funcional** | `funcval plan` | facts de `analyze pyspark` e `analyze catalog-schema`, mais a chave que você declarar |
| **Antes contra depois, por resultado** | `funcval compare` | o plano e os dois resultados que **você** mediu |
| **O agente acertou, com as tools certas, e recusou onde devia?** | `python -m sparkforge.evals grade` / `compare` — fora da CLI `sparkforge`, porque o runtime não importa a avaliação (`tests/test_harness_boundary.py`) | transcripts do Claude Code gerados por `scripts/run_agentic_eval.py` (fora do CI) e o gabarito `evals/agentic/<suite>/suite.yaml`; o compare lê N scorecards por lado e não conclui — ver `evals/README.md` |
| Correlação de fontes | `fuse` | facts de vários extratores ao mesmo tempo |
| Perfil de workload | `workload` | facts de `analyze sql-metrics`/`analyze event-log`, mais `--history` e `workload.yaml`, ambos opcionais |
| Escolha de capacidade sob SLA | `capacity` | facts de `analyze glue-job-runs`, mais `--history` (um arquivo de facts por run anterior) e `workload.yaml` (`sla_minutes`, `reliability_target`, `volume_tolerance`) |
| Custo por run, e capacidade contra código | `finops` | `glue.job_run`/`glue.run_cost` de `analyze glue-job-runs`, `workload.declared` para o SLA, e os sintomas de `analyze event-log`/`analyze sql-metrics` quando a alavanca é código |
| Configuração Spark derivada da medida | `tune` | `spark.stage.shuffle` de `analyze event-log` para o shuffle medido, `spark.conf_effective`, `pyspark.conf_set` e `tf.spark_conf` para a procedência de cada propriedade |
| Contexto que a execução consumiu | `economy report` | os spans do ledger que `call_tool` alimenta, mais a superfície em repouso e o transcript do host quando houver |
| Runtime | `runtime detect` | todas as fontes acima, cruzadas |

Coletar o artefato bruto (`sparkforge collect *`) é a única parte que toca a
AWS, exige boto3 e credencial, e é opcional: quem já tem o dump em disco pula
essa etapa inteira. `collect emr-eks` é o único que faz **duas** chamadas de API
(`describe-virtual-cluster` e `describe-job-run`) e grava **um** arquivo: os dois
ids são obrigatórios, porque a própria API não aceita um job run sem o cluster
virtual que o contém. `collect glue-job-runs` grava um artefato por run em
estado terminal em `.sparkforge/artifacts/glue_job_run/`; run já em disco com
hash íntegro é no-op (coleta incremental de graça), e `--max-runs` é teto de
paginação, não filtro de data. `rules/catalog/` não tem nenhuma regra com
`blocked_on` — o que falta para uma regra disparar é sempre coleta, nunca
código.

### Os verbos em negrito

Os verbos em negrito mudam o alcance do projeto. Oito deles são descritos
abaixo: `analyze emr-cluster`, `analyze emr-serverless`, `analyze emr-eks`,
`analyze data-quality`, `analyze graph`, `benchmark` e os dois `funcval`. Conte o
negrito na tabela, nunca numa lista escrita à mão: a frase que morava no README
dizia "sete" quando a tabela já trazia sete antes de `analyze emr-eks` entrar.

`analyze emr-cluster` responde sobre a **definição do cluster** —
instance fleets contra instance groups, opção de compra por papel, managed
scaling, `Configurations` em dois níveis, bootstrap actions, `LogUri` — e
alimenta a release do EMR no `RuntimeContext`, de modo que os limiares passem
a ser avaliados contra a versão certa fora do Glue. `analyze emr-serverless` faz a
mesma pergunta sobre o **outro** modelo de execução do EMR — capacidade
pré-inicializada faturada com a application ociosa, janela de auto-stop, destino
de log e segredo em `runtimeConfiguration` — a partir de uma única chamada
(`get-application`), em namespace disjunto (`emrs.*`) e área própria (`SF-EMRS`);
ele **não** alimenta `RuntimeContext`, porque a AWS não publica a matriz de
release do Serverless, e a razão está escrita em
[`knowledge/emr-serverless/runtime-matrix.md`](../../knowledge/emr-serverless/runtime-matrix.md).
`analyze emr-eks` faz a mesma
pergunta sobre o **terceiro** modelo de execução — cluster virtual mapeado a um
namespace de Kubernetes, papel de execução declarado por job run, destino de log
por execução, e as **duas** superfícies de configuração
(`configurationOverrides.applicationConfiguration` e
`jobDriver.sparkSubmitParameters`, com a segunda vencendo a primeira) —, em
namespace disjunto (`emrc.*`) e área própria (`SF-EMRK`). Ele também **não**
alimenta `RuntimeContext`, mas por razão oposta à do Serverless: a AWS **publica**
a matriz de release do EKS, e ela **diverge** da de EC2 em células reais — por
isso `--emr` é **recusado** sobre um conjunto de facts `emrc.*`, em vez de
preencher `spark`, `python` e `iceberg` com a tabela errada. A medida está em
[`knowledge/emr-eks/runtime-matrix.md`](../../knowledge/emr-eks/runtime-matrix.md).
`analyze data-quality`
responde sobre **onde a validação está**, não sobre se o dado está correto:
reconhece o check artesanal, a `VerificationSuite` do PyDeequ e o Great
Expectations pela forma do código — nunca por lista de nomes —, e o achado é
sobre o check rodar depois do write, não ter consequência nenhuma, ou pesar N
passadas sobre um alvo que ninguém persistiu. Uma suíte não custa "uma
passada": ela compartilha scan por agrupamento, e restrição de unicidade paga
a sua própria.

`analyze graph` lê o **mesmo `.py` pela terceira vez** — depois de
`analyze pyspark` e `analyze data-quality` —, com um vocabulário fechado de
GraphFrames que só é lido em módulo que **importa** a biblioteca: `find`,
`degrees` e `validate` são nomes que qualquer objeto de usuário pode ter, e
casá-los sem essa evidência produziria acusação falsa. A área `SF-GRAPH` tem
seis regras executáveis (contadas com `area_of` em 2026-09-18), e a primeira é a
única P0 do repositório cujo modo de falha é o
algoritmo **levantar exceção** em vez de degradar: `connectedComponents` exige
diretório de checkpoint e lança `java.io.IOException` na primeira iteração — com
três saídas legítimas escritas no `.py` (`algorithm="graphx"`,
`checkpointInterval<=0`, `use_local_checkpoints=True`), mais duas por
`spark.conf.set` dentro do próprio job, e uma sexta forma em que a conf é
ilegível e o motor declara o ponto cego em vez de acusar. A segunda regra é a
única do catálogo guardada por uma **faixa de um minor de Spark**: não há
artefato de GraphFrames publicado para Spark 3.3 em linhagem nenhuma — nove das
34 células da matriz Glue×EMR —, e a capacidade de escrever `{spark: [">=3.3",
"<3.4"]}` num `runtime_scope` nasceu aí.

`benchmark` não é um `analyze`: ele não lê artefato nenhum e
não executa nada — compara **dois conjuntos de facts** que `analyze event-log`
já produziu, um por execução, e emite `bench.run_delta`, `bench.stage_delta`,
`bench.unmatched`, `bench.analyzed` e `bench.unresolved`. É o produtor que o
gate de `benchmark_ref` nunca teve: `sparkforge validate --findings` rejeita
`expected_effect` que quantifique ganho sem citar o `fact_id` de um
`bench.run_delta`, e a área `SF-BENCH` julga a **validade da comparação** antes
de qualquer conclusão sobre o job. `total_task_ms` é tempo de task somado —
trabalho, não relógio: o event log não carrega duração wall-clock, e uma alta
ali pede confirmação no relógio antes de reverter a mudança.

`funcval` são os dois últimos, e formam a outra metade do mesmo experimento:
`benchmark` julga o tempo, `funcval` julga o **resultado**. `funcval plan` deriva
o que medir dos facts que já existem — o alvo vem do `pyspark.write`, o schema e
os agregados vêm do `catalog.table_schema`, e por isso `--facts` é repetível —, e
`funcval compare` lê os dois resultados que **o operador** mediu e emite
`funcval.check_delta`, `funcval.analyzed` e `funcval.unresolved`. Nenhum dos dois
executa consulta, roda Spark ou chama AWS.

Duas propriedades que o desenho não esconde. **A chave de negócio não é
derivável:** nenhum dos 245 kinds a nomeia, então ou ela entra declarada em
`funcval plan --key` (e o check sai com `origin: declared`) ou o plano escreve o
eixo em `undeclared_axes` **com a razão** — declarar chave errada produz P0 sobre
dado correto, e a procedência de cada check existe para que ninguém confunda o que
o repositório derivou com o que alguém afirmou. **Os quatro eixos são proxies:**
contagem, schema, chaves e agregados iguais não provam que o dado é o mesmo —
duas linhas podem trocar valores entre si e os quatro passam. A área afirma
"nenhum dos quatro proxies detectou divergência", nunca "o resultado é idêntico",
e o próprio comparador carrega esse limite em
`funcval.analyzed.attrs.proxy_limit`.

```bash
# o cluster inteiro num dump, e o julgamento sem flag de versão nenhuma
aws emr describe-cluster --cluster-id j-XXXX > cluster.json
sparkforge analyze emr-cluster --path cluster.json --out .sparkforge/facts.json

# onde o job valida dado, e o que acontece quando o check falha
sparkforge analyze data-quality --path lib/ --out .sparkforge/facts-dq.json

# o mesmo lib/, pela ótica do GraphFrames — sem import da biblioteca, só sentinela
sparkforge analyze graph --path lib/ --out .sparkforge/facts-graph.json

# o antes e o depois, comparados — e o fact_id que o benchmark_ref cita
sparkforge analyze event-log --path before.jsonl --out .sparkforge/before.json
sparkforge analyze event-log --path after.jsonl  --out .sparkforge/after.json
sparkforge benchmark --before .sparkforge/before.json \
                     --after .sparkforge/after.json \
                     --out .sparkforge/bench.json
sparkforge validate --findings .sparkforge/findings.json \
                    --facts .sparkforge/bench.json
```

## Próximos passos

- [Conhecimento e catálogo](07-conhecimento-e-catalogo.md): o que o `judge` consulta.
- [Rigor, assinatura e handoff](08-rigor-e-handoff.md): gates que trancam e relatório com prova.
- [Mudanças com prova](usos/mudancas-com-prova.md): `benchmark` e `funcval` rodando.
- [Índice de comandos](referencia/cli/README.md).
