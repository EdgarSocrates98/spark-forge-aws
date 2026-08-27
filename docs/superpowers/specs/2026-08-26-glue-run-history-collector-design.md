# SparkForge AWS — Coletor de histórico de runs Glue e extrator CloudWatch

**Data:** 2026-08-26
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_tunning_foco_spark.md`, §15, §16 e §19. **É documento de entrada LOCAL e
não versionado neste repositório** — a nota entra aqui porque um leitor de clone limpo
procuraria o arquivo e não o acharia. O que importa dele está reproduzido abaixo.
**Base:** o motor existente — artefato → facts → regras → findings — com o manifesto de
artefatos verificado por sha256 (`sparkforge/collect/base.py`).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o documento de origem não é uma spec, são cinco

`prompt_tunning_foco_spark.md` tem 41 seções e propõe quatro ondas de implementação. Não é
escopo de uma spec. A decomposição adotada, com a ordem de dependência:

| # | Subprojeto | Entrega | Depende de |
|---|---|---|---|
| A | Correção de `SF-GLUE-001` | regra, fixture golden e as quatro skills que a citam | — |
| B | **Coletor de histórico de runs** (este documento) | `collect glue-job-runs`, `analyze cloudwatch`, `analyze glue-job-runs` | — |
| C | Effective Workload e Fingerprint | facts de scan por fonte, join graph, classificador multidimensional | B |
| D | Capacity e SLA optimizer | candidatos de capacidade, simulação de SLA, escolha do menor custo que cabe | B, C |
| E | FinOps | `sparkforge/finops/`, custo por run, desperdício, custo por sucesso de SLA | B, D |

Cada um recebe spec própria. Este documento cobre **apenas B**.

### 1.1 O que motiva a ordem

O princípio central do documento de origem é que o volume da entrada principal não determina
o trabalho físico do DAG. Um job pode ter batch pequeno e varredura extrema. C existe para
medir isso; D existe para escolher capacidade a partir disso.

Mas C e D precisam de um baseline que hoje não existe. `sparkforge collect glue-job` traz a
*definição* do job via `glue.get_job` (`sparkforge/collect/aws.py:298`), não o histórico de
execuções. Sem p50/p95/p99 de runtime observado, "probabilidade de cumprir o SLA" não tem de
onde sair. B é a fundação, e entrega valor sozinha.

### 1.2 Dois achados do repositório que este documento consome

**O artefato CloudWatch é coletado e ninguém o consome.** `collect_cloudwatch`
(`sparkforge/collect/aws.py:340`) baixa 17 métricas de observabilidade Glue, grava o JSON e o
registra no manifesto. Existe a tool MCP `sparkforge_collect_cloudwatch`
(`sparkforge/adapters/tools.py:3405`) e o subcomando `collect cloudwatch`
(`sparkforge/adapters/cli.py:1023`). Não existe extrator em `sparkforge/facts/` que leia esse
artefato, e nenhuma regra do catálogo o consome — `glue.driver.*` aparece no catálogo apenas
em texto de `validation:` (`rules/catalog/glue-infra.yaml:36`, `parquet.yaml:204`,
`spark-ui.yaml:271`, `env.yaml:158`), nunca como `kind` de fact casado por um `when:`.
Correlacionar métrica com run, que é escopo desta entrega, não tem hoje com o que se juntar.
B fecha esse buraco.

**O período da query CloudWatch é fixo em 30 segundos.** `sparkforge/collect/aws.py:372`
codifica `"Period": 30`. A retenção do CloudWatch varia por período: pontos de granularidade
sub-minuto são descartados em poucas horas, enquanto períodos maiores sobrevivem por dias ou
meses. A consequência para um coletor de histórico é direta: a query com período 30 sobre um
run de vinte dias atrás devolve série vazia. Vazio que se parece com "observabilidade não
habilitada no job", que é uma causa completamente diferente.

**Este documento não fixa os valores de retenção.** Eles entram em
`knowledge/glue/observability.yaml`, legível por máquina, com carregador fail-closed no molde
de `knowledge/glue/pricing.yaml` mais `sparkforge/facts/pricing.py` — a mesma dupla que o
projeto já usa para conhecimento que vira número. A seção correspondente em
`knowledge/glue/observability.md` aponta para o YAML em vez de repetir a tabela, e a fonte é
registrada em `knowledge/sources.lock.json` com URL, data de consulta e sha256, como as outras
131. Retenção codificada direto no Python seria o defeito que `facts/pricing.py` existe para
não repetir. Se a documentação da AWS contradisser o parágrafo acima, a documentação vence e o
desenho se ajusta a ela.

### 1.3 Um achado que pertence a A, não a B

`rules/catalog/glue-infra.yaml:11` — `SF-GLUE-001`, `status: confirmed`, `severity_default:
P1` — afirma que habilitar Auto Scaling junto com `number_of_workers` é contraditório, e
propõe "remover number_of_workers e definir MinCapacity e MaxCapacity". A documentação atual
da AWS diz o oposto: com Auto Scaling, `NumberOfWorkers` é o número **máximo** de workers, e é
`MaxCapacity` que não convive com `WorkerType`/`NumberOfWorkers` em Glue 2.0 e posteriores.

A regra tem fixture golden (`fixtures/terraform/autoscaling_conflict/expected/findings.json`)
e é citada por quatro skills. Corrigi-la é conserto de conhecimento, não desenho novo — fica
em A. Registrado aqui porque foi encontrado durante o levantamento deste documento e porque,
até ser corrigido, o motor emite uma recomendação errada com severidade P1.

---

## 2. Escopo

**Dentro:**

1. Coletor `collect_glue_job_runs`, um artefato JSON por run terminal.
2. Extrator `analyze cloudwatch`, que transforma o artefato de métricas em facts.
3. Extrator `analyze glue-job-runs`, que emite fact por run, distribuições agregadas e
   correlação com os facts de CloudWatch presentes.
4. Derivação do período da query CloudWatch a partir da idade do run.
5. Superfície CLI e MCP, com as entradas de manifesto e paridade correspondentes.

**Fora:**

- Nenhuma regra nova no catálogo. B produz facts; julgar histórico é D.
- Nenhum fact de custo em dinheiro. `sparkforge/facts/pricing.py` recusa deliberadamente
  combinar preço com região `UNQUALIFIED`, e esta entrega não fura essa recusa. Custo é E.
- Nenhuma mudança em `SF-GLUE-001` — é A.
- Nenhum footprint por fonte, join graph ou fingerprint — é C.

---

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 Um artefato por run, não por janela

`GetJobRuns` devolve uma janela móvel: os N runs mais recentes, e o conjunto muda a cada dia.
O manifesto do repositório assume o contrário — artefato imutável, verificado por sha256
(`sparkforge/collect/base.py:142`), e `_offline_hit` (`aws.py:150`) trata divergência de hash
como "precisa recoletar".

Adotado: **um arquivo por run**, em
`.sparkforge/artifacts/glue_job_run/<job_name>_<job_run_id>.json`.

Recusado: um arquivo por janela `(job, start, end)`. Duas janelas sobrepostas rebaixariam os
mesmos runs, e uma janela que inclua um run ainda em execução congelaria um estado que vai
mudar, sem forma de descobrir depois.

Recusado: um arquivo acumulativo por job. O sha256 mudaria a cada coleta e o manifesto
registraria um artefato não reprodutível — quebra a propriedade da qual o resto do motor
depende.

Ganho colateral do modelo adotado: coleta incremental sai de graça. Run já em disco com hash
batendo é no-op via `_offline_hit`. Uma segunda coleta de 30 runs onde 28 já estão baixados
toca a rede uma vez, para a listagem, e escreve dois arquivos.

### 3.2 Só estado terminal é gravado

Estados terminais: `SUCCEEDED`, `FAILED`, `TIMEOUT`, `STOPPED`, `ERROR`.
Estados não-terminais: `STARTING`, `RUNNING`, `STOPPING`, `WAITING`.

Um run não-terminal não vira arquivo. Gravá-lo produziria um artefato cujo conteúdo muda
depois, e a próxima coleta veria o hash divergir — o cache offline-first viraria um falso
negativo permanente para aquele run. O run aparece na lista `skipped` do retorno, com o estado
observado, e não é erro.

### 3.3 CloudWatch entra por correlação, não por encadeamento

`collect glue-job-runs` não chama `collect_cloudwatch`. Os coletores continuam independentes,
cada um com uma responsabilidade e um artefato.

A correlação acontece em `analyze glue-job-runs`, que junta por `job_run_id` os facts de
CloudWatch já presentes. Run sem métrica coletada não é erro: sai em
`glue.job_run.unresolved` com a razão e o `collect_command` exato que a resolve — a mesma
convenção que o manifesto usa para não deixar `resume()` cego
(`sparkforge/collect/base.py:50`).

Recusado: `--with-metrics` fazendo fan-out. Uma chamada do operador viraria N chamadas
CloudWatch, com custo e permissão maiores, e um coletor passaria a chamar outro.

### 3.4 Distribuição agrupada por capacidade e por estado terminal

Chave de agrupamento: `(glue_version, worker_type, number_of_workers, autoscaling)`, com
`state` separando os terminais.

Um p95 de runtime que mistura dez runs em `G.1X`/10 workers com vinte em `G.2X`/20 é um
percentil de nada. Separar por estado impede que um run que morreu em trinta segundos puxe
para baixo o p50 de execuções bem-sucedidas.

Taxa de falha por capacidade não cabe numa distribuição que é por estado, e por isso ganha
fact próprio (§4.4). É o número que D vai comparar entre candidatos.

### 3.5 DPU: observado, derivado ou recusa declarada

`GetJobRuns` popula `DPUSeconds` apenas para runs com Auto Scaling. Três casos, três
tratamentos:

| Caso | Tratamento | `dpu_source` |
|---|---|---|
| Auto Scaling com `DPUSeconds` | usa o valor da API | `observed` |
| Capacidade estática | deriva `number_of_workers × DPU(worker_type) × duração` | `derived` |
| Auto Scaling sem `DPUSeconds` | não emite `dpu_seconds`; razão em `unresolved` | — |

A derivação é legítima porque a capacidade é fixa durante o run e os dois fatores estão
documentados no repositório com fonte datada: a fórmula em
`knowledge/glue/workers-and-capacity.md:79` e a tabela de DPU por worker type nas linhas 10 a
13 do mesmo arquivo. O fact derivado carrega em `provenance` a fórmula e a referência.

O terceiro caso é recusa, não estimativa. Sob Auto Scaling, a quantidade de DPU alocada variou
durante a execução, e `number_of_workers` é apenas o teto — multiplicá-lo pela duração
produziria um número superestimado com aparência de medido.

Recusado: derivar sempre da capacidade, ignorando `DPUSeconds`. Uniforme, e errado por excesso
em todo run com Auto Scaling.

---

## 4. Modelo de facts

Todos seguem o contrato de `Fact` (`sparkforge/findings/models.py:31`): `subject` identifica,
`measures` são números, `attrs` são categóricos que uma regra casa com `where`, `provenance`
diz de onde o valor veio.

### 4.1 `glue.metric`

De `analyze cloudwatch`. Um fact por métrica por run.

```
subject:  {job_name, job_run_id}
attrs:    {name, stat, period_s}
measures: {p50, p95, max, min, datapoints}
```

Um `kind` só, discriminado por `attrs.name`, no molde de `tf.attribute` — e não dezessete
kinds, um por métrica. Como nenhuma regra consome CloudWatch hoje (§1.2), a forma está livre;
a escolhida é a que o motor de regras já sabe casar.

Os nomes de métrica são os de `CLOUDWATCH_METRICS` (`sparkforge/collect/aws.py:57`),
reproduzidos sem correção — inclusive `glue.driver.bytesWrittten`, com três "t", que é como a
AWS escreve. `attrs.stat` preserva a estatística que a métrica exige: pedir `Average` de
`glue.error.ALL`, documentado como `Sum`, devolveria um número errado com aparência de certo.

### 4.2 `glue.job_run`

Um por run terminal.

```
subject:  {job_name, job_run_id}
measures: {execution_time_s, dpu_seconds, number_of_workers, timeout_min}
attrs:    {state, worker_type, glue_version, execution_class, autoscaling,
           error_category, started_on, completed_on, dpu_source}
```

`dpu_seconds` ausente quando §3.5 manda recusar. `dpu_source` é `observed` ou `derived`.

`error_category` vem do campo que a resposta de `GetJobRuns` trouxer para essa finalidade, e
fica ausente quando ela não trouxer. Nunca é inferido do texto de `ErrorMessage` — classificar
mensagem de erro por heurística é julgamento, e fact não julga. A mensagem em si também não
entra no fact: ela pode carregar nome de tabela, caminho de S3 ou trecho de dado, e este
projeto redige segredo em vez de propagá-lo (`sparkforge/facts/secrets.py`).

### 4.3 `glue.job_run.distribution`

Um por grupo de capacidade e estado terminal.

```
subject:  {job_name, glue_version, worker_type, number_of_workers, autoscaling, state}
measures: {n, runtime_min_s, runtime_p50_s, runtime_p95_s, runtime_p99_s, runtime_max_s,
           dpu_seconds_p50, dpu_seconds_p95}
attrs:    {window_first, window_last, dpu_source}
```

Percentis por nearest-rank sem interpolação, a mesma fórmula que
`sparkforge/facts/event_log.py:120` usa para `spark.stage.task_duration`.

A fórmula é **reescrita neste extrator, não importada** — o que parece duplicação e é
convenção declarada: `sparkforge/facts/iceberg_metadata.py:128` já tomou essa decisão por
escrito, porque os extratores são módulos independentes por desenho e a fórmula é pequena
demais para acoplá-los. Consolidar as três seria refatoração de dois módulos que esta entrega
não toca. O que garante que continuam iguais é teste, não import: um caso que roda as
implementações sobre a mesma entrada e exige o mesmo resultado.

`attrs.dpu_source` vale `observed`, `derived` ou `mixed`. Um grupo que agrega os dois tipos sai
marcado `mixed`, nunca fundido em silêncio.

`n` é sempre declarado. Um grupo com `n = 1` produz distribuição com `n: 1`, e não um p95 que
finge ter amostra.

### 4.4 `glue.job_run.outcome`

Um por grupo de capacidade, atravessando os estados.

```
subject:  {job_name, glue_version, worker_type, number_of_workers, autoscaling}
measures: {n_total, n_succeeded, n_failed, n_timeout, n_stopped}
attrs:    {window_first, window_last}
```

Contagens, não taxa. A divisão é julgamento e pertence a D; o fact carrega o numerador e o
denominador.

### 4.5 `glue.job_run.unresolved` e `glue.metric.unresolved`

O que não deu para saber, com a razão e, quando existe, o comando que a resolve. Convenção já
usada por `spark.unresolved` e `plan.unresolved` (`sparkforge/facts/event_log.py:50`).

Razões previstas: run sem artefato CloudWatch correspondente; métrica fora da janela de
retenção do período consultado; `DPUSeconds` ausente em run com Auto Scaling; run em estado
não-terminal encontrado na listagem.

### 4.6 `glue.job_run.analyzed` e `glue.metric.analyzed`

Fechamento no molde de `spark.log_analyzed`, com as contagens do que entrou na análise. Uma
análise sobre três runs e uma sobre trinta não podem parecer a mesma coisa na saída.

Cada extrator declara o seu conjunto de `kind` emitidos, no molde do `frozenset` de
`sparkforge/facts/event_log.py:38`.

---

## 5. Superfície

### 5.1 CLI

```
sparkforge collect glue-job-runs --repo . --job-name <job> --max-runs 30 --now <ISO8601>

sparkforge analyze cloudwatch \
  --path .sparkforge/artifacts/cloudwatch/<job>_<run>.json \
  --out <facts.json>

sparkforge analyze glue-job-runs \
  --path .sparkforge/artifacts/glue_job_run/ \
  --job-name <job> \
  --cloudwatch .sparkforge/artifacts/cloudwatch/ \
  --out <facts.json>
```

`--now` é parâmetro, nunca lido do relógio — a convenção de todo o projeto
(`sparkforge/collect/aws.py:16`), e o que torna `collected_at == now` a forma barata de a CLI
saber se a chamada foi um no-op.

`--max-runs` é teto de paginação, não filtro de data. `GetJobRuns` devolve do mais recente
para trás e não aceita janela temporal; expor `--start`/`--end` seria filtro do lado do
cliente disfarçado de parâmetro de API.

`--cloudwatch` é opcional. Ausente, os facts de distribuição saem completos e a correlação
inteira vai para `unresolved` com o comando de coleta que falta.

### 5.2 MCP

`sparkforge_collect_glue_job_runs`, `sparkforge_analyze_cloudwatch` e
`sparkforge_analyze_glue_job_runs` em `sparkforge/adapters/tools.py`, cada uma com handler e
entrada fechada no despacho.

Três lugares com gate próprio recebem as novas entradas:

- `manifest.json`, lista `tools` (linha 80).
- `parity.yaml`: a capability *collect real AWS artifacts and verify the manifest* (linha 438)
  ganha `collect glue-job-runs` e a tool correspondente; os dois `analyze` pertencem à
  capability de análise, não a essa.
- Espelhos `.claude/` e `.agents/` — `tests/test_arvore_versionada.py` reprova espelho
  atrasado.

### 5.3 Novo `kind` de artefato

`ARTIFACT_KINDS` (`sparkforge/collect/base.py:29`) é tupla fechada, validada em
`ArtifactEntry.__post_init__`. Entra `"glue_job_run"`. Sem isso, a construção da entrada
levanta `ValueError`.

---

## 6. Erros, cada um com o seu nome

| Situação | Tratamento |
|---|---|
| boto3 ausente ou credencial indisponível | `CollectorUnavailable` — a chamada nunca aconteceu |
| Job inexistente | `CollectionFailed` — a chamada aconteceu e não deu em artefato |
| Job existe, zero runs terminais | Sucesso. Nenhum artefato, `skipped` preenchido |
| Run em estado não-terminal | Não gravado, entra em `skipped`. Não é erro |
| Métrica fora da retenção | `glue.metric.unresolved`, razão *expirada* |
| Métrica ausente com observabilidade desligada | `glue.metric.unresolved`, razão *série vazia* |

As duas últimas linhas são a razão de a tabela existir. As duas produzem série vazia no
CloudWatch e têm causas e remédios opostos: uma é dado que existiu e expirou, a outra é dado
que nunca foi publicado. A saída tem que dizer qual.

---

## 7. Testes

Coletor no padrão de `tests/test_collect_aws.py`: `FakeGlueClient` com `get_job_runs`
paginado, `require_boto3` monkeypatchado, AWS nunca tocada de verdade.

Os quatro casos que aquele arquivo já cobre para cada coletor, repetidos aqui:

1. Chama a API e registra o artefato no manifesto.
2. Cache hit não toca boto3.
3. Arquivo local corrompido é recoletado.
4. boto3 ausente produz mensagem acionável.

Os desta entrega:

5. Run em estado não-terminal não vira arquivo e aparece em `skipped`.
6. Segunda coleta com 28 de 30 runs já em disco escreve exatamente dois arquivos.
7. `dpu_source` sai `observed` no run com Auto Scaling e `derived` no de capacidade estática.
8. Grupo que agrega os dois sai `mixed`.
9. Auto Scaling sem `DPUSeconds` não emite número — vai para `unresolved`.
10. Percentis conferem contra `event_log._nearest_rank` e `iceberg_metadata._nearest_rank`
    sobre a mesma entrada, com resultado idêntico nos três.
11. Grupo com `n = 1` declara `n: 1` e não apresenta p95 como se tivesse amostra.
12. Distribuição nunca mistura `worker_type` ou `number_of_workers` diferentes no mesmo grupo.
13. Período derivado da idade do run, e run fora da retenção produz `unresolved` com razão
    *expirada*, distinguível de série vazia por observabilidade desligada.

Fixtures golden em `fixtures/glue_job_run/`, com respostas sintéticas de `GetJobRuns`. Nenhum
nome, número, dimensão ou particularidade de ambiente real — o documento de origem pede isso
explicitamente, e a §40 dele lista as classes de cenário sintético a cobrir.

---

## 8. Documentação

- `knowledge/glue/observability.yaml`: tabela de retenção do CloudWatch por período, legível
  por máquina, no molde de `knowledge/glue/pricing.yaml`.
- `knowledge/glue/observability.md`: seção nova apontando para o YAML, e a fonte na lista de
  fontes do arquivo.
- `knowledge/sources.lock.json`: a URL da documentação de retenção, com `retrieved`,
  `checked_at` e `sha256`.
- `README.md`: os três comandos novos.
- `docs/superpowers/STATUS.md`: a fase e o que ela entregou.
- Número novo que entrar em documentação passa por `scripts/check_vnext_claims.py` e
  `docs/claims.lock.json`.

---

## 9. Critérios de aceite

A entrega está pronta quando:

1. `collect glue-job-runs` grava um artefato por run terminal, registra cada um no manifesto e
   é no-op para os já presentes com hash íntegro.
2. Run em estado não-terminal nunca vira artefato.
3. `analyze cloudwatch` emite `glue.metric` para as métricas de `CLOUDWATCH_METRICS`,
   preservando nome e estatística de cada uma.
4. `analyze glue-job-runs` emite `glue.job_run` por run, `glue.job_run.distribution` por grupo
   de capacidade e estado, e `glue.job_run.outcome` por grupo de capacidade.
5. Percentis usam a fórmula nearest-rank dos extratores irmãos, com teste que compara as
   implementações sobre a mesma entrada e exige resultado idêntico.
6. `dpu_source` distingue observado de derivado, e o grupo misto sai `mixed`.
7. Auto Scaling sem `DPUSeconds` recusa em vez de estimar.
8. O período da query CloudWatch é derivado da idade do run, com a retenção vinda de
   `knowledge/glue/observability.yaml` por carregador fail-closed, nunca de constante Python.
9. Métrica expirada e observabilidade desligada produzem razões distintas.
10. As três tools aparecem em `manifest.json`, em `parity.yaml` e nos espelhos, com os gates
    existentes passando.
11. Nenhuma regra nova no catálogo, e nenhum fact de custo em dinheiro.
