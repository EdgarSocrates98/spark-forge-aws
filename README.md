# SparkForge AWS

Sistema especialista de diagnóstico, tuning, revisão e benchmarking para jobs **PySpark no AWS Glue e no Amazon EMR — on EC2 e Serverless**, com foco em **Amazon S3, Parquet, Apache Iceberg, Glue Data Catalog, Spark UI e CloudWatch**.

O eixo de infraestrutura é o único que é específico da plataforma: a análise de código, plano físico, event log, Parquet e Iceberg é agnóstica por construção, e por isso o mesmo motor julga um job Glue definido em Terraform, um cluster EMR on EC2 definido por `describe-cluster` e uma application EMR Serverless definida por `get-application`. Além de performance, o pacote lê **validação de dados** dentro do job — onde o check roda, se ele tem consequência e quantas passadas sobre o dado ele custa — que é pergunta de engenharia de dados, não de tuning.

O pacote foi estruturado para funcionar em:

- Claude Code: `.claude/skills` e `.claude/agents`
- Devin: `.agents/skills` e `.agents/agents` (o Devin também importa `.claude/agents`)
- GitHub Copilot: `.github/copilot-instructions.md`, `.github/instructions`, `.github/prompts` e `.github/agents`
- Qualquer agente compatível com o padrão Agent Skills: `skills/`


## Investigação de fluxos full e incrementais

Para casos com latest-per-key, tabelas Iceberg bilionárias, batching, OOM e cargas muito variáveis, comece por:

1. `PROMPT_INICIAL_MESTRE.md`
2. `GUIA_DE_USO.md`
3. Skill `glue-incremental-performance-architect`

Há Skills específicas para arquitetura incremental (`design-incremental-processing`), latest-per-key (`optimize-latest-per-key`), loops de batching (`analyze-batch-loop`), call graph da biblioteca (`analyze-library-call-graph`), OOM (`diagnose-oom`), Terraform (`review-glue-terraform`) e perfis de volume (`optimize-variable-volume-job`). Desde a versão 0.4.0 elas são *toolkit-first*: chamam os extratores determinísticos em vez de descrever leitura por amostragem.

## Base de conhecimento

`knowledge/` é a fonte de verdade sobre **como Spark, Glue, EMR, Athena, Parquet e Iceberg se comportam** — separada de `skills/` (procedimento) e de `.sparkforge/` (estado da investigação). Comece por [`knowledge/INDEX.md`](knowledge/INDEX.md).

Cobertura: modelo de execução do Spark, referência de configuração com defaults exatos, shuffle/join/skew, memória e as sete classes de OOM, leitura de plano físico, matriz de runtime Glue, worker types e capacidade, argumentos de job, métricas de observabilidade, matriz de runtime EMR e configuração de cluster EMR on EC2, configuração de application EMR Serverless, superfície corrente dos frameworks de validação de dados, performance de Athena, layout Parquet/S3 e Iceberg.

Ler [`knowledge/cross-service-constraints.md`](knowledge/cross-service-constraints.md) antes de recomendar mudança de versão, formato de tabela ou particionamento — são as armadilhas em que a mudança funciona no job e quebra no consumidor.

**AWS Glue 6.0** é suportado e analisado: matriz de runtime com procedência por fonte, áreas de regra para a fronteira do Spark 4 (`SF-SPARK4`) e para o Lake Formation FGAC (`SF-LF`), compatibilidade de feature Iceberg por engine como dado, e cenários de migração por par de versões. A documentação dedicada — incluindo o guia de decisão e o que a ferramenta **não** sabe — está em [`docs/aws/glue/6.0/`](docs/aws/glue/6.0/).

`rules/catalog/` é a forma **executável** desse conhecimento: 81 regras de diagnóstico em YAML com `rule_id`, limiar, guarda de versão e fonte com data, mais 24 rotas determinísticas em `routing.yaml` (16 de skill, `ROUTE-001`…`ROUTE-016`, e 8 de coordenador, `AGENT-001`…`AGENT-008`). Funciona como conhecimento consultável mesmo sem o motor Python — é o terceiro degrau da escada de portabilidade. Ver [`rules/catalog/README.md`](rules/catalog/README.md).

As 81 regras se distribuem em 15 áreas: `SF-PY` 12 (código PySpark), `SF-EMR` 9 (cluster EMR on EC2), `SF-EMRS` 6 (application EMR Serverless), `SF-GLUE` 6 (infraestrutura Glue), `SF-UI` 6 (event log), `SF-ATH` 5 (Athena), `SF-ENV` 5 (ambiente e versão), `SF-FVAL` 5 (validação funcional de uma mudança), `SF-ICE` 5 (Iceberg), `SF-PQ` 5 (Parquet/S3), `SF-BENCH` 4 (comparação entre execuções), `SF-DQ` 4 (validação de dados), `SF-GRAPH` 4 (processamento de grafo com GraphFrames), `SF-PLAN` 4 (plano físico) e `SF-CG` 1 (grafo de chamadas). A área não é etiqueta de serviço: o que gateia uma regra é `requires_facts` — provar que alguém coletou o artefato — e `runtime_scope`, que é guarda de **versão** e nada mais.

## Camada determinística (Fase 0)

Além da base de conhecimento e das Skills (que orientam um LLM), o pacote
inclui um analisador determinístico: extração de facts via AST estático
(nunca importa nem executa código analisado), julgamento contra um catálogo
de 81 regras versionado em YAML, e um ciclo de vida de case
(`.sparkforge/case.yaml`) que atravessa sessões e ferramentas.

### Sequência mínima

```bash
pip install -e .
sparkforge runtime detect --glue 5.0
sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json
sparkforge judge --facts .sparkforge/facts.json --glue 5.0 --out .sparkforge/findings.json
sparkforge next-step --repo . --findings .sparkforge/findings.json
```

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

### Por que extração e julgamento são verbos separados

`analyze` (extração) e `judge` (julgamento) nunca são o mesmo passo. Facts
extraídos de código-fonte são caros de recomputar — exigem re-parsear a
árvore inteira — mas o catálogo de regras evolui com frequência maior que o
código: um limiar corrigido, uma regra nova, uma fonte atualizada. Separar os
dois verbos permite **rejulgar facts antigos com um catálogo novo sem
reprocessar o código-fonte**, o que torna a evolução do conhecimento
auditável: cada revisão do catálogo pode ser aplicada retroativamente ao
mesmo conjunto de facts e o diff do resultado mostra exatamente o que mudou
no julgamento, isolado de qualquer mudança no código analisado.

### Canais de distribuição

| Canal | Como chega | Para quem |
|---|---|---|
| Plugin do Claude Code | `.claude-plugin/plugin.json`, instalado via marketplace ou path local | Claude Code |
| MCP (`sparkforge.adapters.mcp`) | `.mcp.json`, transportes `stdio` e `http` | Devin Desktop, Devin CLI, GitHub Copilot |
| `pip` | `pip install -e .` ou `pip install sparkforge-aws` | CLI `sparkforge` em qualquer shell/CI |
| Espelhos markdown | `rules/catalog/*.yaml`, `skills/`, `knowledge/` | Sem MCP e sem Python — leitura direta |

#### `pip install sparkforge-aws`: o pacote carrega o catálogo dentro dele

```bash
pip install sparkforge-aws            # CLI sparkforge sozinho
pip install "sparkforge-aws[aws]"     # + boto3, para os extratores que leem AWS
pip install "sparkforge-aws[mcp]"     # + servidor MCP (stdio e streamable HTTP)
```

Diferente de um `pip install` comum, este wheel não traz só código: `rules/catalog/`
(o catálogo de regras em YAML) e `knowledge/` (a base de conhecimento sobre
Spark, Glue, EMR, Athena, Parquet e Iceberg) vêm embarcados dentro do pacote,
resolvidos por `loader.catalog_dir()` na mesma ordem de sempre — variável de
ambiente, raiz do repositório e, faltando as duas, o fallback dentro do
próprio pacote instalado. É esse terceiro degrau que faz `analyze`, `judge`,
`next-step`, `resume` e `rules lookup` funcionarem **sem o repositório
clonado**: um agente autônomo que sobe um sandbox efêmero, roda `pip install
sparkforge-aws` e não tem mais nada em disco ainda assim consegue extrair
facts, julgar contra o catálogo completo e citar a fonte de cada limiar —
porque o catálogo veio junto no wheel, não porque o agente clonou o
repositório antes.

Para localizar `knowledge/` a partir do pacote instalado:

```bash
sparkforge knowledge path                                  # imprime a raiz
sparkforge knowledge path --file glue/runtime-matrix.md     # imprime um arquivo específico
```

`rules lookup` também devolve os caminhos já resolvidos: cada regra retornada
inclui os arquivos de `knowledge/` que a sua `explanation` cita, com o
caminho pronto para abrir — dentro do repositório em modo desenvolvimento,
dentro de `site-packages` quando instalado por `pip`.

Essa paridade não é promessa: o CI constrói o wheel, instala em venv limpo
**fora do repositório** e reproduz as 164 fixtures golden byte a byte a partir do
pacote instalado, em Linux e em Windows — o mesmo golden que o repositório
usa, não um corpus à parte. Se `sparkforge` acabar sendo importado do
repositório em vez do `site-packages` nesse processo, o gate falha com
mensagem explícita em vez de comparar o repositório consigo mesmo.

#### Os dois transportes MCP

```bash
pip install -e ".[mcp]"

# stdio — Claude Code, Devin CLI, CI. É o que .mcp.json configura no Claude Code.
python -m sparkforge.adapters.mcp --transport stdio

# streamable HTTP — Devin Desktop, que configura MCP por serverUrl.
python -m sparkforge.adapters.mcp --transport http --host 127.0.0.1 --port 8765
# serverUrl: http://127.0.0.1:8765/mcp
```

**No Devin, `.mcp.json` não basta, e o motivo é medido.** O Devin CLI importa MCP do
Claude Code (`read_config_from.claude`), mas o `.mcp.json` deste repositório é o do
**plugin**: ele parametriza `PYTHONPATH` e `SPARKFORGE_CATALOG` por
`${CLAUDE_PLUGIN_ROOT}`, variável do carregador de plugin do Claude Code que nenhuma
página do Devin documenta expandir — sem expansão, o servidor sobe e morre na primeira
leitura do catálogo com `CatalogError`. O Devin tem arquivo próprio
(`.devin/mcp_config.json`, chave `mcpServers`) e comando próprio (`devin mcp add`): o
procedimento dos dois, com o do Desktop por `serverUrl`, está em
[`GUIA_DE_USO.md`](GUIA_DE_USO.md) seção 3.4.

O extra `mcp` fixa `mcp>=1.0,<2`: o SDK 2.x removeu os decoradores que
`build_server()` usa para registrar os tools, e sem o teto uma instalação
limpa resolveria para 2.x e o servidor quebraria no import — nos dois
transportes. `tests/test_adapters_mcp.py` constrói o servidor e o app ASGI de
verdade, para que um erro de API apareça no CI e não na máquina do operador.

### O que pode ser extraído

Os 24 extratores emitem 148 kinds distintos de fact, e todos são offline: leem
artefato que já está em disco e nunca chamam a AWS. Cada verbo abaixo tem uma
tool MCP de mesmo nome.

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
| **Validação de dados** | `analyze data-quality` | os mesmos `*.py`, pela ótica do check |
| **Processamento de grafo** | `analyze graph` | os mesmos `*.py`, pela ótica do GraphFrames |
| Listagem S3 | `analyze s3-listing` | dump de `s3api list-objects-v2` |
| Consumidores da tabela | `analyze consumers` | inventário declarado, versionado no repositório |
| Mudança de Terraform | `analyze terraform-diff` | dois estados do mesmo módulo |
| Grafo de chamadas | `analyze call-graph` | derivado dos facts de PySpark |
| Métricas do CloudWatch | `analyze cloudwatch` | artefato de `collect cloudwatch` já em disco |
| Histórico de runs Glue | `analyze glue-job-runs` | diretório de artefatos de run, um JSON por run terminal |
| **Duas execuções comparadas** | `benchmark` | dois conjuntos de facts de event log, antes e depois |
| **Plano de validação funcional** | `funcval plan` | facts de `analyze pyspark` e `analyze catalog-schema`, mais a chave que você declarar |
| **Antes contra depois, por resultado** | `funcval compare` | o plano e os dois resultados que **você** mediu |
| Correlação de fontes | `fuse` | facts de vários extratores ao mesmo tempo |
| Perfil de workload | `workload` | facts de `analyze sql-metrics`/`analyze event-log`, mais `--history` e `workload.yaml`, ambos opcionais |
| Runtime | `runtime detect` | todas as fontes acima, cruzadas |

Coletar o artefato bruto (`sparkforge collect *`) é a única parte que toca a
AWS, exige boto3 e credencial, e é opcional: quem já tem o dump em disco pula
essa etapa inteira. `collect glue-job-runs` grava um artefato por run em
estado terminal em `.sparkforge/artifacts/glue_job_run/`; run já em disco com
hash íntegro é no-op (coleta incremental de graça), e `--max-runs` é teto de
paginação, não filtro de data. `rules/catalog/` não tem nenhuma regra com
`blocked_on` — o que falta para uma regra disparar é sempre coleta, nunca
código.

Sete desses verbos mudam o alcance do projeto, e é por isso que aparecem
em negrito. `analyze emr-cluster` responde sobre a **definição do cluster** —
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
`knowledge/emr-serverless/runtime-matrix.md`. `analyze data-quality`
responde sobre **onde a validação está**, não sobre se o dado está correto:
reconhece o check artesanal, a `VerificationSuite` do PyDeequ e o Great
Expectations pela forma do código — nunca por lista de nomes —, e o achado é
sobre o check rodar depois do write, não ter consequência nenhuma, ou pesar N
passadas sobre um alvo que ninguém persistiu. Uma suíte não custa "uma
passada": ela compartilha scan por agrupamento, e restrição de unicidade paga
a sua própria.

`analyze graph` é o terceiro, e lê o **mesmo `.py` pela terceira vez** — depois de
`analyze pyspark` e `analyze data-quality` —, com um vocabulário fechado de
GraphFrames que só é lido em módulo que **importa** a biblioteca: `find`,
`degrees` e `validate` são nomes que qualquer objeto de usuário pode ter, e
casá-los sem essa evidência produziria acusação falsa. A área `SF-GRAPH` tem
quatro regras, e a primeira é a única P0 do repositório cujo modo de falha é o
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

`benchmark` é o quarto, e não é um `analyze`: ele não lê artefato nenhum e
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
derivável:** nenhum dos 118 kinds a nomeia, então ou ela entra declarada em
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

### Rigor: gates que trancam e relatório que carrega prova

Duas garantias que o motor não tinha, e as duas são **opcionais por construção**.

**Gates fail-closed.** O `case.yaml` tem quatro gates. Abrir o case com
`--strict-gates` grava a escolha de rigor **no case** — não na invocação —, e a
partir daí `set_phase` recusa a transição enquanto faltar a evidência dos gates
que guardam a fase pedida:

```bash
sparkforge case open --repo . --case-id perf-2026-08 \
  --now 2026-08-04T09:00:00Z --strict-gates

# `report` é guardada pelos TRÊS gates com produtor, então a transição precisa
# das três evidências: o benchmark destrava `baseline_captured`, o call graph
# destrava `flows_mapped` e o plano de validação destrava
# `functional_validation_defined`. Faltando uma, bloqueia — com a mensagem
# nomeando qual fact falta e o comando que o produz.
sparkforge analyze call-graph --facts .sparkforge/facts.json \
                              --out .sparkforge/facts_callgraph.json
sparkforge funcval plan --facts .sparkforge/facts.json \
                        --facts .sparkforge/facts-catalog.json \
                        --out .sparkforge/facts_funcval_plan.json
sparkforge case update --repo . --phase report \
  --facts .sparkforge/bench.json \
  --facts .sparkforge/facts_callgraph.json \
  --facts .sparkforge/facts_funcval_plan.json
```

O que destrava é **evidência**, nunca a flag: `case update --gate X --gate-value
true` continua gravando o booleano e não libera nada. Quem produz a chave de cada
gate é dado, no bloco `gates` de `rules/catalog/routing.yaml`, com o comando exato
em `produced_by`. Só gate **com** produtor endurece — hoje `baseline_captured`
(`bench.run_delta`, da Fase 4a), `flows_mapped`
(`callgraph.reachable_spark_work`) e `functional_validation_defined`
(`funcval.plan`, da Fase 4c). `dominant_bottleneck_identified` continua advisory,
porque endurecer gate sem produtor é o impasse que a Fase 0 recusou
conscientemente: gate rígido vira beco sem saída quando o dado simplesmente não
existe — e dominância é ordenação entre candidatos, que nenhum fact do
vocabulário afirma.

Quando o dado genuinamente não existe — job descontinuado, ambiente que sumiu —,
passar por cima custa uma frase, e a frase fica gravada no case e aparece no
`resume`:

```bash
sparkforge case update --repo . --override-gate baseline_captured \
  --reason "job descontinuado; nao ha ambiente para rodar o depois" \
  --now 2026-08-04T11:30:00Z
```

Abrir um case por cima de outro é **recusado**: sobrescrever apagaria a fase, o
rigor e os overrides gravados, e uma invocação sem `--strict-gates` desligaria em
silêncio o rigor que alguém ligou. Recomeçar do zero continua possível, com nome:
`sparkforge case open --reopen`. Ele herda o `strict_gates` do case atual — o
rigor sobe com `--strict-gates` e nunca desce por omissão de flag.

O gate confere a **presença do kind**, não o conteúdo do fact: ele prova que a
análise rodou e produziu o artefato que destrava, e **não** que ela cobriu todo o
`scope.entrypoints` nem que o benchmark é do job certo. O limite é decisão
registrada, e vai escrito na própria mensagem de bloqueio.

**Assinatura de correspondência.** `report sign` escreve um bloco no fim do
relatório; `report verify` confere e diz **qual** das quatro partes divergiu —
versão da assinatura, evidência, catálogo ou corpo — em vez de devolver só
"inválido". Os dois existem na CLI e como tool MCP (`sparkforge_report_sign`,
`sparkforge_report_verify`):

```bash
sparkforge report sign   --report relatorio.md --findings .sparkforge/findings.json
sparkforge report verify --report relatorio.md --findings .sparkforge/findings.json
```

O arquivo é o de **findings**, e não o de facts: `rule_id`, `catalog_version` e
`schema_version` só existem lá. O hash cobre os `fact_id` citados, os `rule_id`
que dispararam, as duas versões e o **corpo** do relatório — sem o corpo, alguém
reescreveria o texto inteiro mantendo a assinatura válida. Editar a prosa depois
de assinar invalida, e é para isso que serve: reassinar é barato.

O bloco declara também o `signature_version` sob o qual foi assinado. Ele já
entrava dentro do hash — é o que garante que duas regras de normalização nunca
produzam a mesma assinatura —, mas sem a declaração o `verify` não tinha como
dizer **por que** não fechou: um relatório assinado sob a regra anterior saía
igual a um corpo adulterado. Com ela, versão diferente vira `version_mismatch`,
e o corpo sai como **não avaliável** em vez de acusado.

Ela prova **correspondência**, nunca **autoria**: não há chave nem segredo, e
qualquer pessoa com os mesmos findings produz exatamente a mesma assinatura.
Assinatura de autoria (HMAC, GPG) foi recusada no desenho — exigiria distribuir e
guardar um segredo, superfície que o projeto hoje não tem —, e o limite vai
escrito dentro do bloco que o relatório carrega, porque bloco que sugira
autoridade mente por omissão.

### Fluxo de handoff

`sparkforge handoff --repo <raiz>` escreve `.sparkforge/handoff.md` a partir
do mesmo payload que `sparkforge resume` produz — os dois nunca divergem
porque vêm da mesma função. Ao encerrar ou pausar uma investigação, commite:

```bash
git add .sparkforge/case.yaml .sparkforge/facts.json .sparkforge/findings.json .sparkforge/handoff.md .sparkforge/artifacts/manifest.json
```

Esses cinco arquivos são pequenos, derivados, e são o barramento de handoff
entre sessões e ferramentas (Devin, Claude Code, CI).

**`.sparkforge/artifacts/**` nunca é commitado**, exceto o `manifest.json`
acima — o `.gitignore` já bloqueia isso. É onde ficam os artefatos brutos
coletados (event logs, planos físicos, saída de Terraform): podem carregar
dados de negócio e chegar a centenas de MB. O que substitui o artefato bruto
no commit é o manifesto: ele registra `sha256`, `source` (origem) e
`collect_command` (comando exato de recoleta) para cada artefato, de modo
que uma sessão que retome em outra ferramenta saiba exatamente o que falta e
como coletar de novo.

## Objetivos

1. Encontrar o gargalo dominante antes de sugerir alterações.
2. Correlacionar código, plano físico, Spark UI, CloudWatch, definição do job Glue ou do cluster EMR, e layout de dados.
3. Produzir recomendações baseadas em evidências, com riscos, trade-offs, validação e rollback.
4. Melhorar runtime, DPU-hours, custo, escalabilidade e confiabilidade sem alterar o resultado funcional.
5. Tratar Parquet e Iceberg como camadas diferentes de otimização.
6. Ser consciente da versão do AWS Glue, da release do EMR, do Spark e do Iceberg.
7. Dizer onde a validação de dados está e o que ela custa, sem opinar se o dado está correto.

## Skills incluídas

Cada skill segue um formato padronizado: `description` orientada ao gatilho ("Use quando…"), procedimento, **Quando NÃO usar**, **Referência rápida** (sintoma → sinal/limiar → ação) e **Red flags**.

| Skill | Use quando… |
|---|---|
| `sparkforge-diagnose` | precisar do diagnóstico ponta a ponta e não souber o gargalo dominante |
| `glue-incremental-performance-architect` | orquestrar investigação de fluxos full + incremental (biblioteca, OOM, batching) |
| `optimize-pyspark-code` | revisar/refatorar código PySpark ou Spark SQL |
| `analyze-spark-plan` | interpretar `explain()`/`EXPLAIN` e o plano físico |
| `analyze-spark-ui` | ler Spark UI/event logs (stage lento, skew, spill, GC) |
| `analyze-library-call-graph` | mapear actions/reads/writes escondidos numa biblioteca Python |
| `analyze-batch-loop` | houver actions/writes dentro de loop e recomputação de DAG |
| `design-incremental-processing` | um "incremental" fizer scan global ou recomputar histórico |
| `optimize-latest-per-key` | calcular registro mais recente por chave em tabela grande |
| `optimize-variable-volume-job` | o mesmo job receber de dezenas a centenas de milhões de registros |
| `diagnose-data-skew` | poucas tasks dominarem o tempo por hot keys/nulls |
| `diagnose-oom` | houver OOM (driver, executor, broadcast, metadata, lineage) |
| `tune-glue-job` | ajustar workers, Auto Scaling, argumentos e custo (com baseline) |
| `optimize-parquet-layout` | small files, listing lento e pruning ausente em Parquet/S3 |
| `optimize-iceberg-table` | dívida de data/delete files, snapshots, manifests e manutenção Iceberg |
| `benchmark-pyspark-job` | comprovar (não estimar) o impacto de uma mudança antes/depois |
| `review-pyspark-pr` | revisar um PR buscando regressões de performance e custo |
| `review-glue-terraform` | revisar o IaC do job (workers, Auto Scaling, args, observabilidade) |
| `review-emr-cluster` | o risco estiver na definição do cluster EMR on EC2 (fleets/groups, Spot por papel, managed scaling, `Configurations`, `LogUri`) |
| `review-data-validation` | o job validar dado e a pergunta for onde o check está, se ele tem consequência e quanto custa |

## Coordenadores e executores

Além das Skills (procedimento) e da camada determinística (extração e julgamento), o
pacote tem duas camadas de agente:

- **Coordenador** — 8 agentes em `agents/*.md`, um por área de investigação
  (`spark-performance-architect`, `glue-incremental-performance-architect`,
  `glue-infra-reviewer`, `athena-query-optimizer`, `pyspark-code-reviewer`,
  `iceberg-performance-engineer`, `emr-infra-reviewer` e `data-quality-reviewer`). Não
  executa: lê o case, decide qual executor rodar em seguida e registra no case qual
  executor rodou e com que resultado. Cada um declara as `rule_areas` que consome —
  `emr-infra-reviewer` lê `SF-EMR`, `SF-EMRS` e `SF-ENV` — três desde a Fase 5d —,
  `data-quality-reviewer` lê `SF-DQ`, e
  `spark-performance-architect` acumulou `SF-BENCH` porque *o job ficou mais rápido, e por
  quê* é a mesma pergunta que ele já respondia — e acumulou `SF-FVAL` pela metade que falta
  dela, *e o resultado continuou o mesmo*, que é o mesmo par antes/depois da mesma mudança.
  É isso, não o nome, que faz o roteamento funcionar. Ver a tabela completa em `AGENTS.md`.
- **Executor** — 5 agentes em `agents/executors/*.md`, um por função do loop de fase
  (`sf-inventory`, `sf-extractor`, `sf-judge`, `sf-verifier`, `sf-synthesizer`). Cada um
  declara `## Faz`, `## Não faz`, `## Pressupõe` e `## Entrega` — a fronteira negativa e o
  contrato de handoff que fazem a cadeia ser determinística entre modelos.

Qual coordenador usar é dado, não julgamento: as rotas `AGENT-001`…`AGENT-010` de
`rules/catalog/routing.yaml` mapeiam fase do case e área do achado dominante para o
coordenador certo, e `sparkforge_next_step`/`sparkforge next-step` as consulta.

**Três plataformas despacham.** Em Claude Code, o coordenador despacha os cinco executores
como subagentes. No **Devin CLI** e no **Devin Local agent** do Devin Desktop (com o toggle
*Subagents (Preview)* ligado), os **oito coordenadores** são perfis de subagente nativos: o
Devin lê `.agents/agents/` e importa `.claude/agents/*.md`, dois diretórios que este
repositório já publica. **Os cinco executores não estão num layout de descoberta
documentado** — a fonte descreve `agents/<nome>.md` e `agents/<nome>/AGENT.md`, e a
importação casa `.claude/agents/*.md`, raso; `executors/sf-judge.md` não é nenhum dos
dois, e se a varredura recorre a documentação não diz. Nada se perde: `sparkforge playbook
<coordenador>` lê `agents/executors/` do próprio repositório e devolve os mesmos cinco
passos em qualquer plataforma. **E um coordenador despachado como subagente não despacha
os executores:** por default subagente não gera subagente, e este repositório não declara
`max-nesting` em perfil nenhum — a decomposição roda inline, que é o que o `playbook`
devolve. O espelho do Devin é **renderizado**, não copiado — ele sai sem
`tools:`, porque o mapeamento de valores desse campo não está documentado, e nunca com
`model:`, porque o modelo do subagente resolve por roteador no spawn e um admin da
organização o sobrescreve. **A omissão de `tools:` não é fronteira de segurança, e não
teria como ser:** os dois caminhos de descoberta estão ligados por default
(`read_config_from` tem `agents_standard` e `claude`, ambos `true`), a fonte é **silenciosa**
sobre qual vence quando os dois existem, e o default de `allowed-tools` é *"all tools"* —
omitir é a opção **mais permissiva**, não a mais restrita. O que carrega a fronteira é a
prosa de `## Não faz` no corpo do perfil, byte-idêntica nos dois espelhos. As doze skills
despacháveis declaram `subagent: true` no espelho `.agents/skills/`, e cada uma declara,
no próprio texto, que não executa manutenção destrutiva.

**O `playbook` é o piso das cinco plataformas, não um degrau que o despacho substitui.**
**`sparkforge playbook <coordenador>`** (CLI) ou a tool MCP `sparkforge_playbook` devolve a
mesma decomposição em passos sequenciais, lendo os mesmos arquivos de `agents/`: perde o
paralelismo do despacho, mantém o método. Ele é o **único** caminho em Codex e Copilot CI
— nenhuma pesquisa de fontes mediu despacho de subagente nas duas, e afirmar sem medir é o
defeito que `parity.yaml` existe para não repetir. E continua sendo o caminho nas três que
despacham sempre que o despacho estiver desligado: `subagents_enabled: false` é escolha do
usuário, a opção *None* de "Default subagent model" é de um admin da organização, e nenhum
arquivo versionado deste repositório impede qualquer uma das duas. Ver
[`knowledge/devin/agents-and-subagents.md`](knowledge/devin/agents-and-subagents.md).

## Instalação

### Instalar no próprio repositório

```bash
cd /caminho/do/repositorio && python /caminho/do/sparkforge/scripts/install_skills.py --all
```

### Apenas Claude Code

```bash
python scripts/install_skills.py --target . --claude
```

### Apenas Devin

```bash
python scripts/install_skills.py --target . --devin
```

### Apenas GitHub Copilot

```bash
python scripts/install_skills.py --target . --copilot
```

Use `--force` para substituir arquivos existentes.

A instalação escreve **no diretório atual** — por isso o `cd` no primeiro
exemplo. `--target` é opcional e serve como confirmação explícita do destino:
se for passado e não for o diretório atual, o script recusa e mostra o `cd`
correto, em vez de escrever num lugar que você não estava olhando.

### Manutenção dos espelhos (contribuidores)

A fonte da verdade das skills é `skills/`, e a dos perfis é `agents/`. `.claude/skills/` e `.claude/agents/` são espelhos byte-a-byte; `.github/agents/` também. `.agents/` é **renderizado** por plataforma: as skills despacháveis ganham `subagent: true` (e `agent:` quando há coordenador único **e** ele não é o perfil que orquestra — hoje duas das doze), e os perfis perdem `tools:`. Após editar uma skill em `skills/` ou um perfil em `agents/`, regenere os espelhos:

```bash
python scripts/sync_skills.py          # regenera os espelhos
python scripts/sync_skills.py --check   # falha se algo divergir (útil em CI)
```

O repositório tem **três** espelhos gerados, e cada um tem seu `--check` rodando no CI.
Editar a fonte e esquecer o espelho quebra a build — de propósito, porque drift em
manifesto silencioso é pior que erro barulhento:

| Espelho | Fonte | Comando | Por que existe |
|---|---|---|---|
| `.claude/`, `.agents/`, `.github/` | `skills/`, `agents/` | `python scripts/sync_skills.py --check` | Cada plataforma lê de um diretório próprio |
| `requirements.txt` | `pyproject.toml` | `python scripts/gen_requirements.py --check` | Ferramenta de SCA não lê `pyproject.toml` sem lockfile — e scan que não roda não é scan que passa |
| `sparkforge/rules/catalog/`, `sparkforge/knowledge/` (só no artefato) | `rules/catalog/`, `knowledge/` | `python scripts/verify_wheel.py` | `force-include` do hatchling embarca no build, sem duplicar arquivo em git |

O terceiro não existe em disco: nasce no build e é verificado pelo gate de paridade, que
constrói o artefato, instala num venv limpo e reproduz as 164 fixtures golden byte a byte.

`locks/py3.10.txt` e `locks/py3.11.txt` **não** entram nessa tabela, e a diferença importa.
Espelho é projeção: sai do `pyproject.toml` sozinho, offline, e por isso `--check` pode
regenerá-lo e comparar. Lock é **resolução**: ele diz qual versão de cada pacote — diretos e
transitivos — o ambiente instala, e produzir isso exige consultar o índice do PyPI. Por isso
`python scripts/gen_lock.py` precisa de rede e de `uv`, enquanto
`python scripts/gen_lock.py --check`, o que roda no CI, é offline e confere forma, cobertura
e consistência. O CI instala com `pip install --require-hashes`, modo em que qualquer
dependência fora do arquivo vira erro em vez de virar versão escolhida na hora — e é isso
que dá sentido ao job `audit`: auditar piso não responde nada, porque `PyYAML>=6.0` não tem
CVE, a versão instalada é que tem.

Os testes (`pytest`) validam frontmatter, seções padronizadas, referências e — desde a fase
de perfis de subagente do Devin — um invariante mais forte que "as cópias são iguais": **o
espelho é exatamente o que o tradutor produz para aquela plataforma**. Igualdade nunca
poderia pegar campo que a plataforma exige e a fonte não tem, nem campo que a fonte tem e a
plataforma não deve receber; a derivação pega os dois, e o gate acusa também **órfão em
qualquer profundidade e de qualquer extensão** — `.agents/agents/<nome>/AGENT.md` é layout
de descoberta do Devin, e passar por ali publicaria perfil que ninguém revisou.

## Ecossistema caveman — economia de token nativa

A compressão de output, de [Julius Brussee](https://github.com/JuliusBrussee), está
embutida neste repositório e **ligada por padrão**. Clonar é a instalação inteira:
não há `npm install`, não há `npx`, não há `package.json`, e nada aqui vai à rede.

| Peça | O que faz | Como chega | Instalar? |
|---|---|---|---|
| [`caveman`](https://github.com/JuliusBrussee/caveman) | Modo de comunicação comprimido: corta o output do agente preservando a substância técnica | `vendor/caveman/`, plugin declarado em `.claude/settings.json` | **Nada** |
| [`cavekit`](https://github.com/JuliusBrussee/cavekit) (`ck`) | Loop de spec-driven development sobre um `SPEC.md`: grill → spec → research → review → build, com backprop de bug para invariante | `vendor/cavekit/`, mesmo marketplace | **Nada** |

Créditos, licenças, SHAs pinados e os patches locais: [`vendor/CREDITS.md`](vendor/CREDITS.md).

O invariante "nenhum caminho padrão usa `npm` ou `npx`" tem gate próprio em
`tests/test_vendor_caveman.py::TestSemNpm` — inclusive contra o `plugin.json` do
projeto de terceiro, que pode mudar num bump futuro.

### O que já está ligado sem instalar nada

`vendor/` é um **marketplace de plugin local**, declarado em `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "sparkforge-caveman": { "source": { "source": "directory", "path": "./vendor" } }
  },
  "enabledPlugins": { "caveman@sparkforge-caveman": true, "ck@sparkforge-caveman": true }
}
```

O caminho é **relativo**, para que funcione em qualquer clone; ele é resolvido a partir
do diretório em que o Claude Code foi aberto, então abra-o na raiz do repositório.
A instalação é cópia de disco — não há rede envolvida.

**Sem Node na máquina também funciona.** Os dois hooks do plugin caveman são
`node ...`; sem Node eles não rodam e o ruleset não seria injetado — as skills
continuariam carregando, e o caveman deixaria de ser "ligado por padrão" sem que nada
acusasse. O `.claude/settings.json` tem um fallback em shell que só dispara quando
`node` não está no `PATH`:

```sh
command -v node >/dev/null 2>&1 || cat "$CLAUDE_PROJECT_DIR/vendor/caveman/src/rules/caveman-activate.md"
```

Com Node é no-op, sem injeção dupla. Sem Node, perde-se apenas o flag de modo
(`/caveman lite|full|ultra`) e o `/caveman-stats`, que dependem do hook em JS.

O modo é fixado em [`.caveman/config.json`](.caveman/config.json) como `full` — o
*repo-local config* que o caveman resolve **antes** da configuração de usuário. Quem já
usa caveman em outro nível não perde a própria configuração fora deste repositório, e
troca o modo só na sessão atual com `/caveman lite|full|ultra`.

As mesmas duas linhas de `enabledPlugins` **desligam** `caveman@caveman` e `ck@cavekit`
dentro deste projeto. Não é hostilidade com quem já os instalou globalmente: dois
caveman ligados injetam o ruleset duas vezes por sessão, que é exatamente o oposto de
economizar token. Vale a cópia vendorizada, que é a pinada e revisada.

### Vendorizado, medido e **não** ligado: `caveman-shrink`

`vendor/caveman/src/mcp-servers/caveman-shrink/` é um proxy MCP do mesmo autor, **sem
dependência nenhuma**, que comprime o campo `description` do catálogo de tools antes do
modelo lê-lo. Está em disco e pronto — e continua desligado, porque foi medido contra os
41 tools do servidor `sparkforge` em 2026-08-07:

| | bytes |
|---|---|
| `tools/list` cru | 146 438 |
| `tools/list` pelo proxy | 146 295 |
| **Economia** | **143 bytes — 0,1 %** |

As regras dele cortam artigo, filler e hedging **em inglês** (`the`, `just`, `really`); as
descrições deste catálogo são em português. Nomes de tool e `inputSchema` saem idênticos —
o proxy está correto, só não tem o que cortar aqui. Pôr um proxy no caminho do MCP por
0,1 % seria risco sem retorno. Como ligar, se o catálogo passar a ter descrição em inglês:
[`vendor/CREDITS.md`](vendor/CREDITS.md).

### O que ficou de fora, e por quê

Duas peças do mesmo autor **não** entram aqui, porque nenhuma das duas cabe em
"clonar é a instalação inteira":

| Projeto | Por que fica fora |
|---|---|
| [`cavemem`](https://github.com/JuliusBrussee/cavemem) | Memória entre sessões. Depende de `better-sqlite3`, módulo **nativo** compilado por plataforma — vendorizar prebuilds seria commitar binário para win32/linux/darwin × x64/arm64. E **não economiza token**: o `SessionStart` dele *injeta* contexto da sessão anterior. É memória, não compressão. |
| [`caveman-code`](https://www.npmjs.com/package/@juliusbrussee/caveman-code) | Agente de terminal próprio, 15 MB desempacotados com `better-sqlite3` nativo na árvore. Roda **fora** do Claude Code — é um cliente alternativo, não um componente deste projeto. |

Quem quiser qualquer um dos dois instala globalmente, por conta própria e fora deste
repositório: `npm install -g cavemem && cavemem install`.

### Procedência e atualização

`vendor/` não é espelho gerado de nada deste repositório — é código de terceiro pinado.
O que o mantém honesto:

| Arquivo | Papel |
|---|---|
| [`vendor/PINS.json`](vendor/PINS.json) | SHA upstream, lista de arquivos mantidos e patches locais, por projeto |
| `vendor/MANIFEST.sha256` | sha256 de cada arquivo vendorizado |
| `scripts/vendor_caveman.py` | Reconstrói a árvore a partir dos pins (usa rede) |
| `python scripts/vendor_caveman.py --check` | Gate **sem rede**: falha se qualquer byte divergir. Roda em `tests/test_vendor_caveman.py` |

Atualizar é editar o `sha` em `PINS.json`, rodar o script, revisar o diff e rodar a suíte.

### Agentes que não são o Claude Code

Devin, GitHub Copilot e Codex não carregam plugin nem hook. Para eles o ruleset caveman
está inline em [`AGENTS.md`](AGENTS.md), seção "Output compression — caveman mode", junto
com o que a compressão **não** pode tocar aqui: o schema `recommendation:`/`Finding`
inteiro, números, versões, `rule_id`, `fact_id`, strings de erro e blocos de código. A
forma portátil de arquivo único é `vendor/caveman/dist/caveman.skill`.

## Uso rápido

### Claude Code

```text
/sparkforge-diagnose
/optimize-pyspark-code
/analyze-spark-plan
/optimize-iceberg-table
/review-emr-cluster
/review-data-validation
```

### GitHub Copilot

No Copilot Chat:

```text
/sparkforge-diagnose
/analyze-spark-plan
/review-pyspark-performance
```

### Devin

Peça explicitamente:

```text
Use a skill sparkforge-diagnose para analisar este job Glue.
```

`sparkforge-diagnose` **não** despacha subagente de propósito: ela abre o case e roteia, e
o ciclo de vida do case tem que ficar na sessão que continua. As doze skills despacháveis
— as quatro `review-*`, as quatro `analyze-*`, `diagnose-oom`, `diagnose-data-skew`,
`optimize-pyspark-code` e `optimize-parquet-layout` — declaram `subagent: true` e podem
rodar como subagente. Detalhe em [`GUIA_DE_USO.md`](GUIA_DE_USO.md), seção 3.

```text
Use o perfil emr-infra-reviewer como subagente para revisar este cluster EMR.
```

## Dados mínimos recomendados

Forneça, sempre que possível:

- Código do job.
- Versão do AWS Glue, ou a release do EMR e o `describe-cluster` do cluster.
- Tipo e quantidade de workers (ou instance groups/fleets, no EMR).
- Argumentos e Spark configs.
- Runtime e DPU-hours.
- Volume de entrada e saída.
- `df.explain("formatted")`.
- Screenshots ou event logs do Spark UI.
- Métricas do CloudWatch.
- Quantidade e tamanho dos arquivos.
- Metadados da tabela Iceberg.
- SLA e frequência do job.

## Regra central

> Não ajustar por intuição. Medir, formular hipótese, testar isoladamente e validar o resultado funcional.

## Segurança

### Superfície de execução

Clonar este repositório e abrir o Claude Code **executa código** antes de alguém digitar
qualquer coisa: hooks de `SessionStart` e o comando de cada servidor MCP. Um PR que toque
nesses arquivos não muda "a configuração do projeto" — muda o que roda na máquina de todo
contribuidor, e num diff grande passa como linha de JSON.

`tests/test_execution_surface.py` é a lista fechada disso. Não é allowlist de *padrão* —
padrão vaza, `node .*` autorizaria `node -e "..."` — é a **string exata** de cada comando,
em três superfícies: `.claude/settings.json` (nosso), o `plugin.json` do caveman
vendorizado (de terceiro) e os servidores de `.mcp.json`. Mudar qualquer uma obriga a
passar pelo teste, e a mudança aparece na revisão como o que de fato é.

Camada dois: um deny-list das construções que transformam um hook em canal de execução
arbitrária — `curl`/`wget`, `| sh`, `base64`, `eval`, `$(...)`, crase, `chmod +x`, `npm`.
`>/dev/null` e `2>&1` ficam de fora do deny-list de propósito: redirecionar não busca nem
decodifica nada, e o fallback legítimo usa os dois.

O que executa hoje, na íntegra:

| Superfície | Comando |
|---|---|
| `.claude/settings.json`, `SessionStart` | `command -v node >/dev/null 2>&1 \|\| { echo '...'; cat "$CLAUDE_PROJECT_DIR/vendor/caveman/src/rules/caveman-activate.md"; }` |
| `vendor/caveman` plugin, `SessionStart` | `node "${CLAUDE_PLUGIN_ROOT}/src/hooks/caveman-activate.js"` |
| `vendor/caveman` plugin, `UserPromptSubmit` | `node "${CLAUDE_PLUGIN_ROOT}/src/hooks/caveman-mode-tracker.js"` |
| `.mcp.json` | `python -m sparkforge.adapters.mcp --transport stdio` |

Os dois hooks em JS são código de terceiro. Auditados em 2026-08-07 no SHA pinado:
**nenhuma chamada de rede**, um único `execFileSync` em forma argv (sem shell, sem caminho
de injeção), e escritas confinadas a `~/.claude/.caveman-*` e aos arquivos de agente do
próprio plugin. `caveman-stats.js` **lê os transcripts de sessão** (`~/.claude/projects/**`)
para calcular economia de token — leitura local, sem rede.

`.claude/settings.local.json` é por máquina e nunca commitado: guarda o allowlist de
permissões de quem trabalha ali. Está no `.gitignore` do repositório desde 2026-08-07 —
antes disso dependia do gitignore global de uma máquina só.

### Operações destrutivas

As Skills não executam automaticamente alterações destrutivas. Operações como expiração de snapshots, remoção de arquivos órfãos, mudanças de particionamento e overwrite devem ser propostas com escopo, retenção, dry run quando disponível e plano de rollback.
