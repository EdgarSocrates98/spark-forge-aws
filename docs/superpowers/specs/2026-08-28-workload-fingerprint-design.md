# SparkForge AWS — WorkloadFingerprint: os eixos, e a confiança de cada um

**Data:** 2026-08-28
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_tunning_foco_spark.md`, §1 (abandonar perfil por registros), §2 (Effective
Workload) e §21. **É documento de entrada LOCAL e não versionado neste repositório** — a nota
entra aqui porque um leitor de clone limpo procuraria o arquivo e não o acharia. O que importa
dele está reproduzido abaixo.
**Base:** o baseline de histórico de
[`2026-08-26-glue-run-history-collector-design.md`](2026-08-26-glue-run-history-collector-design.md)
e a métrica por nó de
[`2026-08-28-spark-sql-scan-metrics-design.md`](2026-08-28-spark-sql-scan-metrics-design.md).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o segundo recorte de C

| # | Subprojeto | Estado |
|---|---|---|
| A | Correção de `SF-GLUE-001` | aberto |
| B | Coletor de histórico de runs | entregue em 2026-08-28 |
| C1 | Métrica de scan por nó do plano | entregue em 2026-08-28 |
| **C2** | **WorkloadFingerprint** | **este documento** |
| D | Capacity e SLA optimizer | aberto, depende de C2 |
| E | FinOps | aberto, depende de D |

### 1.1 A tese que este documento executa

O documento de origem abre com um caso concreto: um job cujo batch de entrada é `SMALL` e cuja
varredura é `EXTREME`, com shuffle e join `HIGH`. O perfil por número de registros de entrada
classifica esse job como pequeno, e a classificação está errada em toda decisão que dela
depende.

> **volume do batch ≠ volume efetivamente processado pelo DAG.**

C1 entregou a metade da medição: `spark.sql.scan` diz quantos bytes e quantos arquivos cada
fonte custou, medido pelo Spark. Falta transformar isso em perfil — e perfil é classificação,
que é juízo.

### 1.2 As três decisões que este documento fixa

**A escala vem do histórico do próprio job.** `extreme` é o run acima do p99 daquele job
naquela capacidade, não um limiar universal. B entregou `glue.job_run.distribution` exatamente
para isso.

**Declarado nunca se confunde com medido.** `sla_class` e `primary_input_class` não são
mensuráveis a partir de artefato nenhum: um é decisão de negócio, o outro exige alguém dizer
qual das cinco fontes dirige o batch. Entram por inventário versionado, com
`confidence: declared`.

**Shuffle é medido antes de ser classificado.** É o eixo mais citado da tese e hoje não tem
medição alguma: `plan.exchange` diz que um shuffle existe, não quanto ele moveu.
`facts/event_log.py` lê `SparkListenerTaskEnd` desde a Fase 1 e ignora os dois blocos de
métrica de shuffle que estão dentro dele. Medido em 2026-08-28: zero ocorrências da palavra
`Shuffle` no módulo inteiro.

---

## 2. Escopo

**Entra:**

- Métrica de shuffle por stage em `facts/event_log.py`: um `kind` novo, `spark.stage.shuffle`.
- Extrator do inventário declarado, `facts/workload.py`, lendo `workload.yaml`.
- `sparkforge/workload/`: o objeto `WorkloadFingerprint` e o `Axis`, com valor, confiança,
  base e evidência por eixo.
- Superfície: `analyze workload` na CLI e a tool MCP correspondente.
- Domínio de fixture próprio, com módulo golden.

**Não entra, e a razão de cada um:**

- **Recomendação de capacidade.** É o subprojeto D. Descrever o workload e escolher worker são
  decisões diferentes, com custos de errar diferentes; fundir as duas faria a segunda herdar a
  confiança da primeira sem ter merecido.
- **Custo em dinheiro.** `facts/pricing.py` recusa combinar preço com região não qualificada.
  É o subprojeto E.
- **Os eixos `cpu_pressure` e `metadata_pressure`.** A evidência para os dois é parcial hoje —
  `spark.cluster.cores` não separa CPU saturada de CPU ociosa, e pressão de metadados exigiria
  correlacionar `iceberg.manifests_summary` com tempo de planejamento, que nada mede. Emitir os
  dois com lastro parcial seria vender como eixo o que é palpite. Eles entram quando a medição
  entrar.
- **Regra nova no catálogo.** Nenhuma. O fingerprint é o mecanismo de julgamento; regra que o
  consuma é fase seguinte, e escrevê-la agora seria limiar sobre um contrato que ainda não
  tem uso.
- **Grafo de joins.** O terceiro recorte de C, independente deste.

---

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 Mecanismo próprio, não mais um extrator

`WorkloadFingerprint` mora em `sparkforge/workload/`, não em `sparkforge/facts/`.

A razão é a regra que o projeto já aplica: **fact nunca aplica limiar e nunca atribui
severidade**. Dizer que `scan` é `extreme` é exatamente aplicar limiar. O precedente para
julgamento com mecanismo próprio já existe duas vezes — `MigrationAssessment` e o `benchmark`,
que também não cabem em regra do catálogo e também declaram o que garantem.

**Alternativa recusada:** emitir `workload.axis` como fact e deixar o catálogo classificar.
Pareceria mais uniforme e quebraria a regra de duas formas: o fact carregaria a classe, ou o
catálogo precisaria de um limiar por eixo sem fonte que o publique. A segunda é pior — vira
`field-heuristic` com número inventado, que é o que `knowledge/` existe para impedir.

### 3.2 A escala vem do histórico do job, não de um limiar universal

Um eixo de volume é classificado comparando o run corrente com a distribuição dos runs
anteriores **do mesmo job, na mesma capacidade** — `glue.job_run.distribution`, que B entrega
agrupado por `(glue_version, worker_type, number_of_workers, autoscaling)` e estado terminal.

```
scan = extreme   bytes_read do run  ≥  p99 do historico daquela capacidade
scan = high      ≥ p95
scan = medium    ≥ p50
scan = low       < p50
```

**Alternativa recusada:** tabela de limiares absolutos em `knowledge/`. Não existe fonte da AWS
ou do Spark dizendo que 1 TB de varredura é `extreme`; a tabela seria `field-heuristic` com
número que ninguém publica, aplicada igual a um job de dez minutos e a um de dez horas.

**O custo desta escolha, declarado:** job sem histórico coletado não classifica. O eixo sai
`unknown`, com o comando que resolve. É custo aceito de propósito — a alternativa é classificar
sem base e chamar isso de perfil.

### 3.3 `declared` e `measured` nunca se confundem na saída

`sla_class` e `primary_input_class` entram por `workload.yaml`, versionado no repositório, no
molde exato do inventário que `analyze consumers` já lê (`fixtures/consumers/*/input/consumers.yaml`).

O `Axis` carrega `confidence` como campo de primeira classe, e `declared` é um valor distinto
de `measured`. Um leitor — humano ou agente — que veja `sla = critical` sabe, sem procurar, que
alguém escreveu isso e nada mediu.

**Alternativa recusada:** `--sla-minutes` como argumento de linha de comando. Não fica
versionado, cada execução pode passar um valor diferente, e nada registra a divergência. A
declaração é dado do projeto, não da chamada.

### 3.4 Shuffle é medido antes de ser classificado

A primeira entrega deste recorte é a métrica que falta, não o objeto. `SparkListenerTaskEnd`
carrega `Shuffle Read Metrics` (bytes remotos, bytes locais, registros lidos, tempo de espera
de fetch) e `Shuffle Write Metrics` (bytes escritos, registros escritos, tempo de escrita).
`event_log.py` já lê esse evento para outra coisa.

**Alternativa recusada:** classificar shuffle a partir da contagem de `plan.exchange`. Número
de shuffles não é volume de shuffle: um `Exchange` movendo 40 GB e outro movendo 4 MB contam
igual, e a tese que este documento executa é precisamente sobre volume.

### 3.5 Eixo sem lastro é `unknown`, nunca um default no meio da escala

Eixo que não pôde ser medido nem declarado sai `unknown`, com `missing` nomeando o fact que
falta e `collect_command` dizendo como obtê-lo.

**Alternativa recusada:** `medium` por omissão. É a mentira mais cara possível aqui, porque
parece resposta: o operador lê um perfil completo, e metade dele é preenchimento. A convenção
oposta — lacuna declarada com o comando que a fecha — é a que o projeto já usa em todo
`*.unresolved`, e é o que faz `resume()` não ficar cego.

---

## 4. Modelo

### 4.1 `spark.stage.shuffle` — o fact que falta

Um por stage que moveu dados, no molde de `spark.stage.task_input`.

```
kind      spark.stage.shuffle
subject   {type: stage, symbol, stage_id}
measures  {read_bytes, read_records, write_bytes, write_records,
           remote_read_bytes, local_read_bytes, fetch_wait_ms, write_time_ms}
```

Só as measures que o event log publicou (mesma disciplina de C1: ausência não é zero). Stage
sem shuffle não produz fact — não é lacuna, é ausência de shuffle.

### 4.2 `workload.declared` — o inventário

`workload.yaml`, versionado, opcional:

```yaml
jobs:
  - name: etl-clientes
    sla_minutes: 45
    primary_source: db.clientes
```

Emite `workload.declared` por job, `workload.unresolved` para entrada malformada (entrada sem
`name`, entrada que nem objeto é, mesmo job declarado duas vezes — as três formas que o
inventário de `consumers` já trata), e `workload.declared_analyzed` como sentinela.

Arquivo ausente **não é erro**: é o caso comum. Sentinela declara `jobs_declared: 0`, e os
dois eixos declarados saem `unknown`.

### 4.3 `Axis` e `WorkloadFingerprint`

```python
Axis(
    value       = "extreme" | "high" | "medium" | "low" | "unknown",
    confidence  = "measured" | "declared" | "unknown",
    basis       = str,           # "history_p99", "declared", "structural", ""
    evidence    = list[str],     # ids dos facts que sustentam
    missing     = str,           # so quando unknown
    collect_command = str,       # so quando unknown e existe comando
)
```

Eixos deste recorte:

| Eixo | Base | Evidência |
|---|---|---|
| `scan_intensity` | histórico | `spark.sql.scan.bytes_read` × `glue.job_run.distribution` |
| `shuffle_intensity` | histórico | `spark.stage.shuffle` × histórico |
| `memory_pressure` | histórico | `spark.stage.spill`, `spark.stage.gc` |
| `skew_risk` | interna | `spark.stage.task_duration` p95/p50 |
| `file_pressure` | interna | `spark.sql.scan.files_read`, `s3.prefix_summary` |
| `join_intensity` | estrutural | `plan.join` — estratégia e contagem |
| `sla_class` | declarada | `workload.declared` |
| `primary_input_class` | declarada | `workload.declared` |

`skew_risk` e `file_pressure` usam razão interna ao run, e não o histórico, porque as duas já
são razões: p95/p50 de tarefa é dispersão, e arquivos por byte lido é densidade. Comparar uma
razão com o histórico dela seria uma segunda derivada sem consumidor.

`join_intensity` é estrutural e o `basis` diz isso: `CartesianProduct` e
`BroadcastNestedLoopJoin` são fatos do plano, não volume.

O objeto carrega também `source_count` (contagem de `spark.sql.scan`) e a lista de eixos
`unknown`, para que quem o lê saiba o que **não** foi respondido sem ter de varrer campo a
campo.

---

## 5. Superfície

```
sparkforge workload --facts <facts.json> --job-name <job> [--history <facts.json>] [--out F]
```

**Verbo de topo, e não `analyze workload`.** A razão está escrita no código, em
`_core.benchmark_runs`: *"os verbos sob `analyze` extraem facts de um artefato, e este não
extrai nada — ele compara dois conjuntos já extraídos. Mesma razão pela qual `fuse` é verbo
próprio."* O fingerprint consome facts já extraídos e não lê artefato nenhum, então cai
exatamente nessa regra, ao lado de `benchmark`, `fuse` e `funcval`.

`--facts` e `--history` são arquivos de `--out` de outros verbos, carregados por
`_load_facts_file` com o `producer` que diz qual comando produz cada lado — o mesmo mecanismo
que já orienta quem chama `benchmark` sem os dois arquivos.

Tool MCP `sparkforge_workload`, read-only local. O subject do resultado é
`{type: "job_run", symbol: <job_run_id>}` — a entidade é um run visto no contexto do seu
histórico, e `job_run` já está no enum fechado de `subject.type`.

---

## 6. Erros, cada um com o seu nome

| Situação | Saída |
|---|---|
| Sem `glue.job_run.distribution` para a capacidade do run | eixos de volume `unknown`, `missing` nomeado, `collect_command` = `sparkforge collect glue-job-runs …` |
| Histórico existe mas com `n` pequeno demais para p99 | eixo `unknown`, razão `history_too_short`, com o `n` observado |
| `workload.yaml` ausente | não é erro; os dois eixos declarados saem `unknown` |
| `workload.yaml` malformado | `workload.unresolved` por entrada, com a razão; as entradas válidas seguem |
| Nenhum `spark.sql.scan` nos facts | `scan_intensity` e `file_pressure` `unknown`, `collect_command` = `sparkforge analyze sql-metrics …` |
| `primary_source` declarado que nenhum scan casa | eixo `unknown`, razão `declared_source_not_observed` — declaração que não bate com o medido é lacuna, não silêncio |

---

## 7. Testes

### 7.1 Domínio de fixture próprio

`fixtures/workload/`, com `tests/test_fixtures_golden_workload.py` declarando
`FIXTURES = ROOT / "fixtures" / "workload"` — o que `test_every_fixture_domain_has_a_golden_module`
cobra, e o gate que a entrega de B deixou vermelho por não conhecer.

Cenários, todos sintéticos:

| Cenário | Prova |
|---|---|
| `small_batch_extreme_scan` | o caso que motivou o documento de origem inteiro |
| `no_history` | todos os eixos de volume `unknown`, com o comando que resolve |
| `history_too_short` | `n=2`: recusa de p99, com o `n` declarado |
| `declared_only` | `workload.yaml` presente e nenhum fact de medição |
| `declared_source_not_observed` | declaração que não bate com o medido |
| `shuffle_heavy_small_scan` | o eixo novo separando dois workloads que o scan não separa |

### 7.2 As duas garantias que valem mais que os seis cenários

**Nenhum eixo `measured` sem evidência.** Todo `Axis` com `confidence: measured` carrega
`evidence` não vazia, e todo id ali existe entre os facts de entrada. Verificado sobre o
corpus inteiro, não por cenário: um default que preenchesse a classe sem evidência passaria em
cada cenário isolado e quebraria aqui.

**Nenhum eixo `declared` promovido a `measured`.** Eixo cuja única fonte é `workload.yaml`
jamais sai como `measured`, em nenhum cenário. É a fronteira que separa o que alguém escreveu
do que a máquina mediu, e é a garantia de que D — que vai escolher capacidade em cima disto —
saiba em que está pisando.

---

## 8. Documentação

- `README.md`: o verbo novo, e os números de extratores e kinds **medidos**.
- `docs/superpowers/STATUS.md`: a fase, os desvios e o que ficou de fora.
- `knowledge/`: nada novo. Este documento não introduz limiar com fonte externa — é justamente
  o que §3.2 recusa.

---

## 9. Critérios de aceite

1. `spark.stage.shuffle` sai com `write_bytes` medido para um stage que moveu dados, e o stage
   sem shuffle não produz fact nenhum.
2. Job sem histórico produz fingerprint com os eixos de volume `unknown` e o `collect_command`
   correto — e com `skew_risk` e `file_pressure` **preenchidos**, porque esses não dependem do
   histórico.
3. Eixo declarado nunca sai `measured`, em cenário nenhum.
4. Eixo `measured` nunca sai sem `evidence`.
5. `primary_source` declarado que nenhum scan casa vira `unknown` com razão nomeada, não
   silêncio.
6. Nenhum eixo sai `medium` por omissão: todo valor tem `basis` não vazio ou é `unknown`.
7. Suíte completa verde, gate de números verde, bundle offline verde, gate de tool órfã verde,
   gate de domínio de fixture verde — os cinco que as duas entregas anteriores mediram como os
   que mordem.
