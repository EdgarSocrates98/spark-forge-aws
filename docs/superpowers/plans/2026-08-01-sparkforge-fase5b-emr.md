# SparkForge Fase 5b — EMR on EC2: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** dar ao EMR o eixo de infraestrutura que hoje só existe para Glue, e fazer o motor perceber quando duas plataformas são detectadas ao mesmo tempo — mesmo quando as versões derivadas coincidem.

**Architecture:** cinco camadas, na ordem em que uma habilita a seguinte. Plataforma vira coisa rastreada com fact próprio, `emr` entra no `RuntimeContext` com matriz e guard de drift, um extrator lê dump de cluster já coletado, uma área `SF-EMR` julga esses facts, e um coordenador próprio a torna alcançável.

**Tech Stack:** Python stdlib, YAML declarativo, pytest.

**Spec:** [`../specs/2026-08-01-sparkforge-fase5-emr-design.md`](../specs/2026-08-01-sparkforge-fase5-emr-design.md) — §3.3, §4.2 a §4.5, e os critérios 3, 4, 5, 6, 7, 8, 9, 12 e 14. Os critérios 1, 2, 10, 11 e 13 foram fechados pela [Fase 5a](2026-08-01-sparkforge-fase5a-escopo.md).

**Base:** [Fase 5a](2026-08-01-sparkforge-fase5a-escopo.md) corrigiu o escopo e [5a.2](2026-08-01-sparkforge-fase5a2-dividas.md) fez o runtime vir dos facts. Esta fase nasce sobre uma base que diz a verdade sobre o próprio escopo — sem elas, toda regra `SF-EMR` nova herdaria os mesmos defeitos.

---

## Fatos do ambiente verificados antes de escrever este plano

```
RuntimeContext (findings/models.py:138-159)
    glue spark python iceberg athena detected_from divergences   -- sem `emr`

runtime_detect.py:174   glue_observations e SEPARADO de observations
runtime_detect.py:184   _build_facts itera SO observations
                        -> plataforma NUNCA vira env.runtime_signal

test_runtime_detect.py:5  test_matrix_matches_committed_knowledge
                          espelha knowledge/glue/runtime-matrix.md -- o guard de drift a copiar

test_agent_coverage.py:75 test_no_area_is_orphan
                          areas = {id.rsplit("-",1)[0]}; toda area precisa de `rule_areas` num coordenador

catalogo    48 regras | SF-ENV-001..004 usados, SF-ENV-005 livre
tools       30, todas alcancaveis
collect/aws.py  collect_event_log, collect_glue_job, collect_cloudwatch,
                collect_iceberg_metadata, collect_athena_workgroup
testes      2320 passando, 5 skipped
```

**A consequência que decide a Task 1.** O critério 12 exige sinal **mesmo quando as versões derivadas coincidem**. `SF-ENV-001` dispara sobre `env.runtime_signal` com `measures.distinct_versions > 1` — é comparação de *versão de componente*. Se Glue 4.0 e algum release EMR derivam o mesmo Spark 3.3.0, não há divergência de versão alguma, e a dupla detecção passa muda. Portanto o critério 12 **não é alcançável** por comparação de versão, sob nenhum ajuste. Identidade de plataforma precisa de fact próprio e regra própria.

---

## File Structure

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/emr_cluster.py` | extrator de dump de cluster EMR |
| `sparkforge/collect/` (função em `aws.py`) | coleta do dump, extra `[aws]` |
| `rules/catalog/emr-infra.yaml` | área `SF-EMR` |
| `knowledge/emr/runtime-matrix.md` | matriz de release, fonte do guard de drift |
| `agents/emr-infra-reviewer.md` | coordenador da área |
| `skills/review-emr-cluster/SKILL.md` | skill da investigação |
| `tests/test_facts_emr_cluster.py` | extrator |
| `tests/test_platform_divergence.py` | critério 12 |
| `fixtures/emr/*` | golden bidirecional por regra |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/findings/models.py` | `emr` em `RuntimeContext` |
| `sparkforge/facts/runtime_detect.py` | `EMR_MATRIX`, `env.platform`, `emr` observado |
| `sparkforge/adapters/_core.py`, `cli.py`, `tools.py` | verbos e tools novos |
| `rules/catalog/env.yaml` | `SF-ENV-005` |
| `knowledge/sources.lock.json` | fonte da matriz EMR na watchlist |

---

## Task 1: Plataforma vira coisa rastreada

Primeiro, e independente de todo o resto — fecha o critério 12, que a §3.3 do spec registrou como **não coberto** justamente para ninguém assumir que estava.

**Files:**
- Create: `tests/test_platform_divergence.py`
- Modify: `sparkforge/facts/runtime_detect.py`, `rules/catalog/env.yaml`

- [x] **Step 1: Reproduza o silêncio**

Monte um `sources` com Glue e EMR cujas versões derivadas **coincidam**, e mostre que hoje não sai sinal nenhum. Se você não conseguir fazer as versões coincidirem com a matriz atual, force o cenário — o ponto é o mecanismo, não o par de versões.

Cole a saída. Ela é a justificativa da task.

- [x] **Step 2: O teste, primeiro**

Em `tests/test_platform_divergence.py`. O invariante: **duas plataformas detectadas produzem sinal, independentemente das versões**. Cubra as versões coincidindo e as divergindo — o primeiro caso é o que o critério 12 exige e o que nenhum teste atual pega.

- [x] **Step 3: `env.platform`**

`_build_facts` itera só `observations`, e `glue_observations` está fora. Não force plataforma para dentro de `observations`: os dois têm semântica diferente — `observations` são versões de componente, e `SF-ENV-001` conta `distinct_versions`. Plataforma é **identidade**, e a pergunta é "quantas?", não "quais versões?".

Emita um fact próprio, `env.platform`, com as plataformas detectadas e de onde vieram. Decida o formato exato lendo como `env.runtime_signal` é montado, e mantenha `subject`, `attrs` e `provenance` no padrão do arquivo.

- [x] **Step 4: `SF-ENV-005`**

Regra irmã de `SF-ENV-001`, sobre `env.platform`, disparando quando mais de uma plataforma é detectada.

Escreva-a lendo `rules/catalog/README.md` — todos os campos obrigatórios, `sources` declarada, sem percentual de ganho. `explanation` tem que dizer **por que isso importa**: um job roda num runtime só, então duas plataformas detectadas significam que uma das fontes descreve outra coisa — e todo achado de infraestrutura daquele relatório está ancorado na plataforma errada.

Fixture bidirecional: uma que dispara, uma limpa.

- [x] **Step 5: `emr` no `RuntimeContext`**

O campo, com default `""`, e em `to_dict()`. Mínimo para a Task 1 funcionar; a matriz é a Task 2.

**Cuidado:** `to_dict()` sempre emite toda chave, e `in_scope` reprova valor vazio. Acrescentar `emr` significa que um futuro `runtime_scope: {emr: "*"}` falha fechado quando não há EMR — que é correto — mas **confirme que nenhuma regra existente passa a ser pulada**. `tests/test_rule_scope_by_nature.py::TestNoCatalogAreaVanishesEntirely` pega isso; rode-o.

- [x] **Step 6: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_platform_divergence.py tests/test_runtime_detect.py tests/test_rule_scope_by_nature.py -q
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
git add sparkforge tests rules/catalog fixtures
git commit -m "feat(runtime): plataforma vira coisa rastreada, com regra propria"
```

---
## Correcoes de fato ao spec, vindas da pesquisa de fontes

> A pesquisa desta fase (2026-08-01) leu a documentacao oficial e derrubou tres premissas do spec. Elas mudam o desenho do extrator, nao so o catalogo. Estao aqui, e nao enterradas numa task, porque quem ler o spec sozinho vai construir a coisa errada.

**1. `aws emr list-configurations` nao existe.** Conferido contra o indice de subcomandos do CLI. As classificacoes (`spark-defaults`, `spark`, `yarn-site`) chegam por **dois** caminhos, e a distincao importa: `Cluster.Configurations` (nivel de cluster, em `describe-cluster`) e `InstanceGroup.Configurations` / `InstanceTypeSpecification.Configurations` (nivel de grupo, nos dumps de instancia). Propriedade no grupo **sobrepoe** a do cluster para aquele grupo.

**2. Faltam dois dumps na lista do spec.** `get-managed-scaling-policy` — managed scaling **nao aparece** em `describe-cluster`, e sem ele tres regras nao tem gatilho — e `get-auto-termination-policy`.

**3. `Cluster.Applications[].Version` vem populado.** O dump **observou** a versao de Spark/Hadoop/Iceberg do cluster real. Isso e estritamente melhor que inferir da matriz, e muda a precedencia da Task 2.

---

## Task 2: `EMR_MATRIX` e o guard de drift

**Files:**
- Create: `knowledge/emr/runtime-matrix.md`
- Modify: `sparkforge/facts/runtime_detect.py`, `knowledge/sources.lock.json`
- Test: `tests/test_runtime_detect.py`

- [ ] **Step 1: O documento primeiro, o codigo depois**

`knowledge/emr/runtime-matrix.md`, no formato de `knowledge/glue/runtime-matrix.md` — **leia-o antes**. Duas paginas canonicas, uma por serie maior; nao existe uma unica cobrindo as duas:

- `https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-release-app-versions-7.x.html`
- `https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-release-app-versions-6.x.html`

A pesquisa levantou a tabela inteira (7.0.0 a 7.13.0, e 6.4.0 a 6.15.0). **Confirme cada linha contra a fonte** antes de escrever: matriz errada e bug de dado que se propaga para toda regra versionada.

- [ ] **Step 2: Quatro coisas que a matriz EMR tem e a `GLUE_MATRIX` nao**

Cada uma e uma decisao de desenho, nao um detalhe. Resolva as quatro **antes** de escrever `EMR_MATRIX`.

**Versoes `-amzn-N`.** `3.5.6-amzn-2` nao e o `3.5.6` do Apache — e um fork com patches da AWS. Todo `runtime_scope` com range compara contra versao Apache. Se o valor resolvido guardar o sufixo cru, **a comparacao falha, a regra e pulada, e a cobertura e apagada em silencio** — exatamente o modo de falha que as Fases 5a e 5a.2 acabaram de fechar. Normalize para comparacao, e decida se o valor cru sobrevive em algum lugar (provavelmente sim: e informacao real sobre o runtime). Escreva a decisao num comentario, e **teste os dois lados**.

**Python e um conjunto, nao um valor.** `"3.9, 3.11"` em 7.x, `"2.7, 3.7"` em 6.x. A `GLUE_MATRIX` declara um Python por release; aqui nao da. Mas o dump resolve: a classificacao `spark-env` carrega `PYSPARK_PYTHON`. Desenho proposto, e voce pode discordar com justificativa: a matriz guarda a **lista**, e `python` so resolve para um valor quando `spark-env`/`PYSPARK_PYTHON` esta no dump. Sem isso, a lista inteira entra em `observations` e a ambiguidade **aparece como divergencia** — que e o comportamento correto do projeto, nao um bug a esconder.

**Iceberg nao existe antes de 6.5.0.** A celula de `emr-6.4.0` e vazia. Regra `SF-ICE-*` ali tem que ser pulada por **ausencia**, nao por range.

**Observacao direta vence a matriz.** `Cluster.Applications[].Version` ja vem no dump. A matriz e **fallback e guard de drift**. Acrescente a fonte `describe_cluster` a `_PRECEDENCE` **acima** da derivacao por matriz — espelhando a decisao ja tomada e documentada para `event_log` vs. `terraform` na Fase 5a.2. A origem derivada mantem o sufixo `:matrix`, como a de Glue, senao `_resolve` a trata como observacao direta.

- [ ] **Step 3: O guard de drift, e ele nao pode ser um so**

`tests/test_runtime_detect.py::test_matrix_matches_committed_knowledge` faz isso para Glue — **leia-o e siga o mecanismo**, nao invente outro.

Mas as duas paginas EMR tem perfis de drift **opostos**, e trata-las igual produz um guard ruidoso — e guard ruidoso e guard ignorado:

- **6.x e estavel.** A serie nao recebe minors novos; o ultimo e 6.15.0. Mudanca na pagina e exatamente o evento que a watchlist existe para pegar.
- **7.x tem churn estrutural garantido.** A AWS se compromete a lancar um minor a cada 90 dias no maximo, e cada minor **prepende uma coluna** a tabela. Um guard por hash da pagina inteira vai alarmar umas quatro vezes por ano por motivo que nao e drift do que a matriz ja conhece.

Para 7.x, compare **os valores das colunas que `EMR_MATRIX` ja conhece**, nao o hash. Coluna nova e "matriz desatualizada, considere acrescentar" — informativo. Celula existente alterada e drift, e falha.

- [ ] **Step 4: Watchlist**

`knowledge/sources.lock.json`. Confirme como `refresh_knowledge` consome o arquivo antes de escrever — formato errado quebra o gate. Registre a diferenca de perfil das duas paginas.

Nota para o documento, nao para o codigo: `aws emr describe-release-label` devolve a mesma informacao com contrato de API em vez de HTML, e e a forma melhor de **manter** a matriz. Isso nao viola "entrada e artefato local": o extrator segue sem rede; so a manutencao humana usa a API. A URL citada em `sources` continua sendo a pagina da doc, que e o que um auditor consegue abrir.

- [ ] **Step 5: `emr` observado e derivado**

`detect_runtime` aceita `emr_release`/`emr` como chave direta e deriva Spark/Python/Iceberg/Hadoop de `EMR_MATRIX`, como ja faz com Glue.

- [ ] **Step 6: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_runtime_detect.py tests/test_runtime_inferred_from_facts.py tests/test_platform_divergence.py -q
rtk proxy python -m pytest -q
git add sparkforge knowledge tests
git commit -m "feat(runtime): EMR_MATRIX, com guard de drift contra o knowledge"
```

---

## Task 3: O extrator de EMR on EC2

**Files:**
- Create: `sparkforge/facts/emr_cluster.py`, `tests/test_facts_emr_cluster.py`
- Modify: `sparkforge/collect/aws.py`, `sparkforge/adapters/_core.py`, `cli.py`, `tools.py`

- [ ] **Step 1: Leia o analogo mais proximo**

`sparkforge/facts/athena_workgroup.py` e o modelo: le dump JSON ja coletado, **nao coleta nada**, tem sentinela e `unresolved`, e o docstring documenta o shape. `iceberg_metadata.py` e o segundo, para dump com secoes opcionais.

Disciplina nao negociavel: **entrada e artefato local, sem rede**. A coleta vive em `collect/aws.py`, atras do extra `[aws]`.

- [ ] **Step 2: Os dumps, corrigidos**

Nao use a lista do spec. Use esta:

| Dump | Traz |
|---|---|
| `describe-cluster` | `ReleaseLabel`, `Applications[].Version`, `Configurations` (nivel cluster), `LogUri`, `ScaleDownBehavior`, `AutoTerminate`, `InstanceCollectionType`, `Status.StateChangeReason.Code`, `UnhealthyNodeReplacement` |
| `list-instance-groups` | `InstanceGroupType`, `Market`, `InstanceType`, `RequestedInstanceCount`, `Configurations`, `LastSuccessfullyAppliedConfigurations`, `ConfigurationsVersion`, `AutoScalingPolicy`, `EbsBlockDevices` |
| `list-instance-fleets` | `InstanceFleetType`, `TargetSpotCapacity`, `TargetOnDemandCapacity`, `InstanceTypeSpecifications[]`, `LaunchSpecifications.SpotSpecification.AllocationStrategy` |
| `list-bootstrap-actions` | **so** `{Name, ScriptBootstrapAction{Path, Args}}` — sem status, sem exit code |
| `get-managed-scaling-policy` | `ComputeLimits{UnitType, Min/MaximumCapacityUnits, MaximumOnDemand/CoreCapacityUnits}` |
| `get-auto-termination-policy` | `IdleTimeout` |

**Ambiguidade de forma, e trate as duas.** O CLI parece embutir `InstanceGroups`/`InstanceFleets`/`BootstrapActions` dentro do objeto `Cluster`, o que contradiz `API_Cluster.html`, onde esses campos nao existem. Provavel forma legada. Leia embutido se existir, senao o dump separado, **sem depender de nenhuma**.

- [ ] **Step 3: Feche os kinds**

Decida a partir de duas restricoes, e diga no relatorio como cada uma pesou: o que os dumps devolvem, e o que as regras da Task 4 precisam julgar.

Nao emita kind que nenhuma regra consome — capacidade sem consumidor e mecanismo sem garantia declarada. E **nao use sentinela generico como unico gate de regra**: foi assim que `SF-GLUE-002` sumia de findings *e* de skipped, e a Fase 5a teve que reancora-la em `tf.resource`.

Obrigatorios: a sentinela `emr.analyzed` e o `emr.unresolved`. Secao presente mas malformada vira `unresolved`, **nao** silencio.

**Um kind e de qualidade da evidencia, e e o mais importante desta lista.** `InstanceGroup` traz `Configurations`, `LastSuccessfullyAppliedConfigurations` e `ConfigurationsVersion`. Divergencia entre os dois primeiros significa **reconfiguracao pedida e nao aplicada** — o cluster nao esta rodando com o que o dump parece dizer. Emita isso (`emr.configuration.unapplied` ou nome melhor) e use como guarda nas regras que leem `Configurations`, senao elas afirmam sobre configuracao que nao esta em vigor. E o mesmo papel de `tf.observability.unknown` e `plan.unresolved` no resto do projeto.

- [ ] **Step 4: Instance groups e instance fleets**

Modelos alternativos e mutuamente exclusivos, com respostas de forma diferente. Um cluster tem um ou outro. Trate os dois, e **decida se viram o mesmo kind com atributo discriminante ou kinds distintos** — justifique. Dump com nenhum dos dois e dump incompleto, nao cluster sem instancias: `unresolved`.

- [ ] **Step 5: Teste e fixture**

Golden por caminho. Cubra: groups, fleets, secao ausente, secao malformada, dump vazio, e configuracao nao aplicada.

- [ ] **Step 6: Verbo, tool e coleta**

`sparkforge analyze emr-cluster` e `sparkforge collect emr-cluster`, mais as tools MCP.

**Toda tool nova precisa ser alcancavel a partir de um coordenador** — `tests/test_agent_coverage.py::test_no_tool_is_orphan` trava, e quem fecha e a Task 5. Vermelho aqui e esperado e some quando a Task 5 entrar. **Nao contorne o teste.**

- [ ] **Step 7: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_facts_emr_cluster.py -q
rtk proxy python -m pytest -q
git add sparkforge tests fixtures
git commit -m "feat(facts): extrator de cluster EMR on EC2"
```

---

## Task 4: A area `SF-EMR`

**Files:**
- Create: `rules/catalog/emr-infra.yaml`, `knowledge/emr/*.md`, `fixtures/emr/*`

- [ ] **Step 1: As regras, com o que a pesquisa sustentou**

Seis com mecanismo duro, fonte oficial e observaveis nos dumps. **Confirme cada fonte lendo antes de escrever** — nao copie desta tabela.

| # | Regra | Gatilho | Por que custa | Sev |
|---|---|---|---|---|
| 1 | AM elegivel a Spot em 6.x sem node labels | release 6.x **e** grupo/fleet TASK com Spot **e** sem `yarn.node-labels.enabled=true` + `am.default-node-label-expression=CORE` | em `deploy-mode cluster` o AM **e** o driver; o EC2 reclama o Spot e a **aplicacao inteira falha**, nao uma task | P1 |
| 2 | `maximizeResourceAllocation` em cluster de fleets | `spark`.`maximizeResourceAllocation=true` **e** `InstanceCollectionType=INSTANCE_FLEET` | o EMR dimensiona o executor por **um** tipo do fleet, que pode ter ate 30; o executor nao cabe no menor ou desperdica o maior | P1 |
| 3 | Segredo em `Configurations` ou `Args` de bootstrap | padrao de segredo em qualquer nivel | as APIs Describe/List devolvem em texto claro para quem tem permissao de leitura | P0 |
| 4 | DRA desligada com managed scaling | `spark.dynamicAllocation.enabled=false` **e** politica de managed scaling | o Spark pede executores fixos e nunca devolve; o scaling le pressao estatica e sobe ate o teto, onde fica | P1 |
| 5 | Primary em Spot com core On-Demand | MASTER Spot **e** CORE com capacidade On-Demand | contradicao: pagou-se durabilidade no core e deixou-se o ponto unico de falha do cluster em Spot | P1 |
| 6 | `partitionOverwriteMode=dynamic` em `spark-defaults` | a propriedade no cluster | desliga o committer otimizado do EMRFS; o commit **renomeia diretorio por diretorio no driver**, e em S3 rename e COPY+DELETE | P1 |

Mais `LogUri` ausente — analoga de `SF-GLUE-002`, e regra de **capacidade de diagnostico**, nao de performance: em release <= 6.8.0 o log morre com o no, e logging **so pode ser definido na criacao**. `severity_by`: P1 se `AutoTerminate`, senao P2.

**A #6 tem trade-off de semantica, e ele e obrigatorio declarar.** `static` faz o overwrite apagar o destino inteiro, nao so as particoes escritas. Trocar a propriedade sem mudar o codigo **muda o resultado**. A recomendacao certa nao e "troque"; e retirar do `spark-defaults` do cluster e deixar cada job declarar. A `validation` tem que pedir contagem **por particao**, nao so total — e onde o erro aparece.

- [ ] **Step 2: O que a pesquisa vetou, e nao reintroduza**

Tres dos quatro candidatos do spec nao sobreviveram na forma escrita. Isto esta aqui para ninguem "melhorar" a area depois reinventando-os:

- **Bootstrap action que falha em silencio: morto, por dois motivos independentes.** `ListBootstrapActions` devolve **so** `{Name, ScriptBootstrapAction{Path, Args}}` — sem status, sem exit code, sem timestamp. E a premissa esta errada: bootstrap que falha **nao** falha em silencio, o EMR termina a instancia e, com falhas demais, o cluster. O caso genuinamente mudo e script que sai com 0 sem fazer o trabalho, e isso e invisivel a qualquer API por construcao. **O que se salva** e diferente: `Status.StateChangeReason.Code` inclui `BOOTSTRAP_FAILURE`, o que permite uma regra **post-mortem** sobre cluster ja terminado.
- **Ausencia de EBS: morto como escrito.** EBS **nunca** esta ausente — o EMR aloca gp2/gp3 por default desde 5.22.0, proporcional ao tamanho da instancia. `EbsBlockDevices: []` significa "nenhum volume **adicional**", e a leitura ingenua produziria falso positivo em quase todo cluster. E "se o workload derrama" nao esta no dump. Salvavel so numa forma bem mais estreita, P3, com o limiar declarado como heuristica.
- **`spark-defaults` conflitando com runtime: morto na forma generica.** A precedencia do Spark e `SparkConf` > `--conf` > `spark-defaults` — entao "o job seta e o cluster tem outro valor" e, quase sempre, **o contrato funcionando**. Uma regra generica acusaria configuracao correta, que o README do catalogo trata como o pior tipo de defeito de regra. Sobrevive so o subconjunto de **propriedades de deploy** que a doc do Spark nomeia como nao afetadas por `SparkConf` em runtime — e essa precisa de fusao com `pyspark.conf_set`, entao **nasce `blocked_on`**, como `SF-ATH-001/002/005` nasceram.
- **Spot no master: morto como absoluto.** A AWS **recomenda** primary em Spot em dois dos quatro cenarios da propria tabela. Acusar todo primary Spot e acusar a recomendacao oficial. Sobrevive como **correlacao** — e a #5.

- [ ] **Step 3: Escreva-as**

Lendo `rules/catalog/README.md` e usando `rules/catalog/glue-infra.yaml` como modelo — e o analogo direto.

Obrigatorio por regra: `sources` com URL e data de recuperacao (2026-08-01 para as desta pesquisa), ou `origin: field-heuristic` declarado; `risks`, `tradeoffs`, `validation`, `rollback`; **sem percentual de ganho**.

Onde a fonte sustenta so parte da afirmacao, **declare qual parte**. A pesquisa marcou isso caso a caso — por exemplo, a fonte da #1 sustenta o mecanismo e o default de 6.x, e **nao** sustenta incidencia.

`runtime_scope` segue o criterio que a Fase 5a fixou: **nao-vazio so quando o gatilho genuinamente varia com a versao, e essa versao vem do runtime, nao de um fact que a regra ja le**. Regra que le `ReleaseLabel` do proprio dump **nao** precisa de `runtime_scope` — o fact ja prova a plataforma. A #1 e a excecao candidata, porque a serie 6.x vs. 5.x muda o default; leia e decida.

- [ ] **Step 4: Conhecimento**

Regra com profundidade aponta para `knowledge/emr/`. Siga o formato de `knowledge/glue/workers-and-capacity.md`.

- [ ] **Step 5: Fixture bidirecional por regra**

Invariante da Fase 2: fixture que dispara **e** contraparte negativa, por regra. `tests/test_fixtures_kind_coverage.py` trava.

- [ ] **Step 6: Verifique e commite**

```bash
rtk proxy python -m pytest -q
python scripts/check_evals.py
git add rules/catalog knowledge fixtures tests
git commit -m "feat(rules): area SF-EMR, infraestrutura de cluster"
```

---

## Task 5: Coordenador e skill

Fecha o invariante de órfão que a Task 3 abriu de propósito.

**Files:**
- Create: `agents/emr-infra-reviewer.md`, `skills/review-emr-cluster/SKILL.md`

- [ ] **Step 1: A decisão, e ela já está tomada**

O spec deixou duas saídas: alargar `glue-infra-reviewer` ou criar um irmão. **Crie `emr-infra-reviewer`.**

A razão: `rule_areas` no frontmatter é contrato de roteamento, não rótulo. Um coordenador chamado `glue-infra-reviewer` declarando `SF-EMR` mente para quem lê a descrição — e a descrição é o gatilho de seleção do agente, como a Fase 5a.2 descobriu do jeito caro. A Fase 4 estabeleceu coordenadores por domínio; EMR é domínio.

Se ao escrever você concluir que a duplicação com `glue-infra-reviewer` é grande demais para justificar, **pare e relate** em vez de decidir sozinho.

- [ ] **Step 2: Escreva o coordenador**

Leia `agents/glue-infra-reviewer.md` inteiro — frontmatter (`name`, `description`, `tools`, `skills`, `rule_areas`, `executors`) e as seções de corpo. A `description` começa com "Use quando" e descreve o **gatilho**, não o que o agente faz.

`rule_areas` inclui `SF-EMR`. `executors` fecha a cadeia de handoff — `tests/test_agent_coverage.py` verifica que todo executor declarado existe.

- [ ] **Step 3: A skill**

`skills/review-emr-cluster/SKILL.md`, seguindo o padrão: seções `## Quando NÃO usar`, `## Referência rápida`, `## Red flags`, e `description` começando com "Use quando".

Duas coisas que a Fase 5a.2 travou com teste e você vai acertar de primeira lendo o que ela fez:
- **não negue capacidade que existe**, e não anuncie subcomando que o parser não aceita — o teste é derivado de `build_parser()`
- **runtime é opcional declarado**, não placeholder `<versão>`: `judge` infere dos facts, e a skill deve dizer de onde vem e o que fazer quando não vem

- [ ] **Step 4: Espelhos**

```bash
python scripts/sync_skills.py
python scripts/sync_skills.py --check
```

- [ ] **Step 5: Verifique e commite**

```bash
rtk proxy python -m pytest tests/test_agent_coverage.py tests/test_skill_content.py -q
rtk proxy python -m pytest -q
git add agents skills .claude .agents .github tests
git commit -m "feat(agents): emr-infra-reviewer, coordenador da area SF-EMR"
```

---

## Task 6: A prova do objetivo

O critério 8 e o último da tabela §5 do spec: **investigação sobre EMR produz achados de código, plano e armazenamento normalmente, e reporta as SF-GLUE como puladas em vez de sumirem em silêncio**.

**Files:**
- Modify: `tests/test_rule_scope_by_nature.py` ou módulo próprio

- [ ] **Step 1: O teste ponta a ponta**

Monte facts de um cenário EMR — cluster, código PySpark, e o que mais fizer sentido — e prove numa asserção só:

- as regras agnósticas disparam normalmente
- as `SF-EMR` disparam
- as `SF-GLUE` aparecem em `skipped`, com `reason`
- nenhuma área some em silêncio

`tests/test_rule_scope_by_nature.py` já tem `TestNoCatalogAreaVanishesEntirely` derivando runtimes de `GLUE_MATRIX`. Acrescente os runtimes EMR ao conjunto — derivados de `EMR_MATRIX`, não escritos à mão, para que release novo entre sozinho.

- [ ] **Step 2: Varredura**

```bash
rtk proxy python -m pytest -q
python -m ruff check sparkforge scripts tests
python scripts/sync_skills.py --check
python scripts/gen_requirements.py --check
python scripts/check_evals.py
```

Prove com comando cada critério que esta fase fecha: **3, 4, 5, 6, 7, 8, 9, 12**.

- [ ] **Step 3: Docs — critério 14**

`README.md`, `AGENTS.md`, `STATUS.md`, `knowledge/`, as skills afetadas e o spec. Números medidos, não copiados. O spec sai de "implementado em parte" para implementado, e a 5b ganha seção própria em `STATUS.md` com o que ficou de fora.

**O que fica de fora, e deve ser escrito como dívida, não omitido:** EMR Serverless e EMR on EKS. Esta fase é EMR on EC2, por decisão registrada no spec.

- [ ] **Step 4: Commit**

```bash
git add docs knowledge README.md AGENTS.md
git commit -m "docs: fecha a Fase 5b"
```

---

## Resultado esperado

| | Antes | Depois |
|---|---|---|
| Plataformas conhecidas pelo `RuntimeContext` | 1 (`glue`) | 2 (`glue`, `emr`) |
| Glue e EMR detectados juntos | passa mudo se as versões coincidem | `SF-ENV-005`, sempre |
| Extratores de facts | 13 | 14 |
| Áreas do catálogo | 9 | 10 |
| Coordenadores | 6 | 7 |
| Investigação sobre EMR | `SF-GLUE` avalia e nunca dispara | `SF-GLUE` pulada, com motivo |
