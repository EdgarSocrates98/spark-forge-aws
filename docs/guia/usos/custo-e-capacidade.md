# Custo e capacidade de um job Glue

Este guia responde três perguntas: quanto o job custou, qual a capacidade mais barata que
cumpre o prazo, e se uma mudança melhorou de fato. Todos os exemplos usam arquivos sintéticos
da pasta `fixtures/` e foram rodados de verdade.

Os comandos rodam na raiz do repositório, no Git Bash. `sparkforge` é o comando instalado.
Se ele não for encontrado, troque por `python -m sparkforge.adapters.cli`.

## Receita rápida

```bash
# 1. pasta temporária e histórico de runs
SAIDA=/tmp/sparkforge-guia; mkdir -p "$SAIDA"
sparkforge analyze glue-job-runs --path fixtures/glue_job_run/correlated/runs \
  --cloudwatch fixtures/glue_job_run/correlated/cloudwatch --job-name synthetic-job --out "$SAIDA/facts_runs.json"
# 2. capacidade mais barata que cumpre o SLA
sparkforge capacity --facts fixtures/capacity/cheapest_that_fits/input/facts.json \
  --history fixtures/capacity/cheapest_that_fits/input/history --job-name etl_pedidos_diario --job-run jr_hoje_001
# 3. quanto custou e onde está a alavanca
sparkforge finops --facts fixtures/finops/cost_from_observed_dpu/input/facts.json --job-name etl_pedidos_diario
# 4. o que mudou entre os runs de antes e os de depois
G=fixtures/gain/ganho_por_capacidade
sparkforge gain $(for f in $G/baseline/*.json; do printf -- '--baseline %s ' "$f"; done) \
  $(for f in $G/candidate/*.json; do printf -- '--candidate %s ' "$f"; done)
```

No passo 2, a resposta escolhe `G.2X` com 10 workers. Não é a capacidade mais rápida: é a
mais barata entre as que cumprem o prazo.

## Termos em uma frase

- **Worker**: uma máquina do cluster do Glue. **Worker type** (`G.1X`, `G.2X`...) é o tamanho dela.
- **DPU**: a unidade de capacidade que o Glue cobra. **DPU-segundos** (`dpu_seconds`) é
  quanto de capacidade o run consumiu ao longo do tempo.
- **SLA**: o prazo combinado para o job terminar, em minutos.
- **Auto Scaling**: o Glue muda o número de workers durante o run. Nesse caso, o número
  configurado é um teto, e não o uso real.
- **p50 / p95**: a mediana e o valor abaixo do qual ficam 95% dos runs.

Os termos do próprio SparkForge estão em [01-conceitos.md](../01-conceitos.md).

## Para que serve cada verbo

| Pergunta | Verbo |
|---|---|
| Como foram os runs deste job? | `analyze glue-job-runs` |
| Que tipo de carga é este job? | `workload` |
| Qual a capacidade mais barata que cumpre o SLA? | `capacity` |
| Quanto custou, e a alavanca é código ou capacidade? | `finops` |
| Melhorou ou piorou entre os runs de antes e os de depois? | `gain` |

`workload`, `capacity`, `finops` e `gain` não leem artefato. Eles trabalham sobre facts que um
`analyze` já extraiu.

## Quando usar e quando não usar

Use quando a dúvida é de dinheiro, prazo ou número de workers.

Não use para achar a causa de lentidão. Primeiro veja [job-lento.md](job-lento.md). Com skew
ou spill, trocar capacidade não resolve a causa.

## Pré-requisitos: o que coletar

Os comandos abaixo acessam sua conta AWS. Por isso eles não foram rodados neste guia. As flags
foram conferidas no `--help`:

```bash
# histórico de execuções (um artefato por run terminado)
sparkforge collect glue-job-runs --repo . --job-name <job> --now <ISO8601>
# métricas do CloudWatch de um run
sparkforge collect cloudwatch --repo . --job-name <job> --job-run <id-do-run> --start <ISO8601> --end <ISO8601> --now <ISO8601>
```

`--now` é a data e hora atual, por exemplo `2026-09-13T10:00:00Z`. `collect glue-job-runs`
também aceita `--max-runs`, o teto de runs buscados.

Você também precisa **declarar o SLA** (veja a seção sobre o `workload.yaml`).

## Passo a passo

### 1. Leia o histórico de runs

```bash
sparkforge analyze glue-job-runs --path fixtures/glue_job_run/correlated/runs \
  --cloudwatch fixtures/glue_job_run/correlated/cloudwatch --job-name synthetic-job --detail-level summary
```

```json
  "by_kind": {
    "glue.job_run": 2,
    "glue.job_run.analyzed": 1,
    "glue.job_run.distribution": 1,
    "glue.job_run.outcome": 1,
    "glue.metric": 3,
    "glue.metric.analyzed": 2,
    "glue.metric.unresolved": 1
  },
  ...
    {
      "kind": "glue.job_run",
      "measures": { "execution_time_s": 600, "number_of_workers": 10, "timeout_min": 60, "dpu_seconds": 6000.0 },
      "symbol": "jr_0001",
  ...
    {
      "kind": "glue.job_run.distribution",
      "measures": { "n": 2, "runtime_min_s": 600.0, "runtime_p50_s": 600.0, "runtime_p95_s": 700.0, ...
                    "dpu_seconds_p50": 6000.0, "dpu_seconds_p95": 7000.0 },
```

- `glue.job_run` é um run: duração, workers e DPU-segundos.
- `glue.job_run.distribution` agrupa runs com a mesma capacidade.
- `glue.metric.unresolved` é uma métrica que não pôde ser lida. O SparkForge não inventa o valor.

### 2. Declare o SLA no `workload.yaml`

Arquivo real de `fixtures/workload/declared_source_not_observed/input/workload.yaml`:

```yaml
jobs:
  - name: etl_pedidos_diario
    sla_minutes: 30
    primary_source: db.eventos
```

| Campo | O que é |
|---|---|
| `name` | Nome do job. Obrigatório. |
| `sla_minutes` | Prazo em minutos. |
| `primary_source` | A tabela que dirige o volume do job. |
| `reliability_target` | Fração de runs que precisa cumprir o SLA, entre 0 e 1 (0.8 = 80%). |
| `volume_tolerance` | Quanto o volume pode variar e o run ainda contar como comparável (0.25 = 25%). |

Valor fora da faixa não é aceito em silêncio. Por exemplo, `reliability_target: 95` vira
`workload.unresolved` com `reason: reliability_target_out_of_range`. Um job declarado duas
vezes vira `job_declared_twice`, e a primeira declaração vale.

Transforme o arquivo em facts com `analyze workload` e passe o resultado junto dos outros
`--facts` de `capacity`, `finops` e `workload`:

```bash
sparkforge analyze workload --path workload.yaml --out facts_workload.json
```

O `scan` faz isso sozinho quando o `workload.yaml` está na **raiz** do repositório. Em subpasta
ele não lê, porque um repositório com vários jobs pode ter vários arquivos; use o comando acima.
O fact que sai tem esta forma (exemplo de `fixtures/capacity/cheapest_that_fits/input/facts.json`):

```json
{
  "kind": "workload.declared",
  "subject": { "type": "job_run", "symbol": "etl_pedidos_diario" },
  "measures": { "sla_minutes": 10, "reliability_target": 0.8, "volume_tolerance": 0.25 },
  "attrs": {},
  "provenance": { "extractor": "workload@0.1.0", "artifact": "workload.yaml" }
}
```

Sem esse fact, os verbos não inventam prazo. Eles dizem que falta. Por exemplo, o `finops`
sai com `"reason": "sla_not_declared"`.

### 3. Veja o perfil do workload

```bash
sparkforge workload --facts fixtures/workload/shuffle_heavy_small_scan/input/facts.json \
  --history fixtures/workload/shuffle_heavy_small_scan/input/history --job-name etl_pedidos_diario --job-run jr_006
```

```json
  "axes": {
    "scan_intensity": { "value": "low", "confidence": "measured", "basis": "history_percentile", ... },
    "file_pressure": { "value": "medium", "confidence": "measured", "basis": "files_per_mib", ... },
    "shuffle_intensity": { "value": "extreme", "confidence": "measured", "basis": "history_percentile", ... },
    "skew_risk": {
      "value": "unknown", "confidence": "unknown",
      "missing": "spark.stage.task_duration",
      "collect_command": "sparkforge analyze event-log --path <event-log.jsonl> --out <facts.json>"
    },
    ...
    "sla_class": {
      "value": "unknown", "missing": "workload.declared:sla_minutes",
      "collect_command": "declare o job em workload.yaml com `sla_minutes`"
    },
  ...
  "unknown_axes": ["join_intensity", "memory_pressure", "primary_input_class", "skew_risk", "sla_class"]
```

Este job lê pouco (`scan_intensity: low`) e redistribui muito dado (`shuffle_intensity: extreme`).
Cada eixo `unknown` traz `missing` (o fact que falta) e `collect_command` (o comando que o
produz). `--history` é o diretório com um arquivo de facts por run anterior.

### 4. Escolha a capacidade

```bash
sparkforge capacity --facts fixtures/capacity/cheapest_that_fits/input/facts.json \
  --history fixtures/capacity/cheapest_that_fits/input/history --job-name etl_pedidos_diario --job-run jr_hoje_001
```

```json
{
  "job_name": "etl_pedidos_diario",
  "sla_minutes": 10.0,
  "reliability_target": 0.8,
  "volume_tolerance": 0.25,
  "current_volume_bytes": 2000000000,
  "candidates": [
    { "worker_type": "G.1X", "number_of_workers": 10, "runs_comparable": 10, "runs_within_sla": 0,
      "reliability": 0.0, "resolution": 0.1, "dpu_seconds_p95": 900.0, "meets_sla": false, "safety": "REVIEW", ... },
    { "worker_type": "G.2X", "number_of_workers": 10, "runs_comparable": 10, "runs_within_sla": 10,
      "reliability": 1.0, "resolution": 0.1, "dpu_seconds_p95": 1000.0, "meets_sla": true, "safety": "REVIEW", ... },
    { "worker_type": "G.2X", "number_of_workers": 20, "runs_comparable": 10, "runs_within_sla": 10,
      "reliability": 1.0, "resolution": 0.1, "dpu_seconds_p95": 2000.0, "meets_sla": true, "safety": "REVIEW", ... }
  ],
  "chosen": { "worker_type": "G.2X", "number_of_workers": 10, "dpu_seconds_p95": 1000.0, "meets_sla": true, ... },
  "refused": [],
  "discarded_runs": {},
  "only_one_capacity_observed": false
}
```

Como ler:

- `candidates` são as capacidades que o job **já rodou**. O SparkForge nunca interpola uma
  capacidade que não rodou (regra 12). DPU-segundos não se mantêm iguais quando você troca
  mais máquina por menos tempo.
- `runs_comparable` conta só os runs com volume parecido com o de hoje (dentro de `volume_tolerance`).
- `reliability` é a fração desses runs que cumpriu o SLA. `meets_sla` compara com `reliability_target`.
- `resolution` é o passo da medida de confiabilidade: 0,1 com 10 runs comparáveis. Se o passo
  for grosso demais para o alvo, a capacidade sai recusada com `resolution_too_coarse`.
- `chosen` é a mais barata (menor `dpu_seconds_p95`) entre as que cumprem o SLA. `G.2X x20`
  também cumpre e é mais rápida, mas custa o dobro.
- `safety: REVIEW`: uma pessoa aprova antes de mudar. `capacity` nunca aplica a mudança.
- `only_one_capacity_observed: true` avisa que não há com o que comparar.

Outros fixtures para ver recusas: `none_fits`, `single_capacity_observed`,
`autoscaling_without_cost` e `volume_filter_changes_the_answer`, todos em `fixtures/capacity/`.

### 5. Veja o custo e a alavanca

```bash
sparkforge finops --facts fixtures/finops/cost_from_observed_dpu/input/facts.json --job-name etl_pedidos_diario
```

```json
{
  "job_name": "etl_pedidos_diario",
  "currency": "USD",
  "region": "UNQUALIFIED",
  "runtime_version": "UNQUALIFIED",
  "frontier": [
    { "glue_version": "5.0", "worker_type": "G.2X", "number_of_workers": 5, "autoscaling": false, "runs": 3,
      "runtime_p50_s": 600.0, "runtime_p95_s": 600.0, "cost_per_run_p95": 0.88, "cost_relative": 1.0 }
  ],
  "per_sla_outcome": [],
  "symptoms": {},
  "levers": {
    "code": { "findings": [], "detail": "" },
    "capacity": { "detail": "A pergunta de capacidade tem resposta com evidencia em `sparkforge capacity`, ..." },
    "none_found": true
  },
  "refused": [
    { "reason": "sla_not_declared", "detail": "Sem `sla_minutes` e `reliability_target` em workload.yaml nao ha desfecho util a contar, ..." }
  ]
}
```

- `frontier` é o custo por capacidade observada. Aqui foram 7200 DPU-segundos medidos pela API
  do Glue (2 DPU-hora), a 0,44 por DPU-hora: 0,88 por run.
- `region: UNQUALIFIED` quer dizer que a fonte de preço não diferencia região. O relatório
  escreve isso em vez de fingir precisão.
- `levers` diz onde está a alavanca: no código (achados do `judge`) ou na capacidade.
- `symptoms` mostra sintomas ao lado do custo, como spill e skew. O SparkForge **nunca** diz
  "você desperdiçou X com spill" nem "você economizaria Y". Isso exigiria o custo de um run
  que não aconteceu (regra 13).

**Sem `dpu_seconds` não há custo** (regra 14). Sob Auto Scaling sem `DPUSeconds`, o número de
workers é teto, e não uso. Veja:

```bash
sparkforge finops --facts fixtures/finops/no_dpu_no_cost/input/facts.json --job-name etl_pedidos_diario
```

```json
  "frontier": [],
  ...
  "refused": [
    { "reason": "cost_unobservable", "capacity": "G.2X x10", "runs": 3,
      "detail": "Nenhum run desta capacidade tem custo: sem `dpu_seconds` nao ha o que converter. ..." },
    { "reason": "sla_not_declared", ... }
  ]
```

O custo sai como lacuna nomeada (`glue.run_cost.unresolved` no nível do fact), nunca como zero.

### 6. Meça o ganho observado

`gain` compara runs que já aconteceram, antes e depois de uma mudança. Cada `--baseline` e
cada `--candidate` é um arquivo de facts de run, e as duas flags podem ser repetidas.

```bash
G=fixtures/gain/ganho_por_capacidade
sparkforge gain $(for f in $G/baseline/*.json; do printf -- '--baseline %s ' "$f"; done) \
  $(for f in $G/candidate/*.json; do printf -- '--candidate %s ' "$f"; done)
```

```json
  "metrics": {
    "execution_time_s": {
      "baseline": { "n": 10, "median": 900.0, "min": 900.0, "max": 900.0 },
      "candidate": { "n": 10, "median": 500.0, "min": 500.0, "max": 500.0 },
      "delta": -400.0, "delta_pct": -44.4, "marks": []
    },
    "dpu_seconds": {
      "baseline": { "n": 10, "median": 900.0, ... },
      "candidate": { "n": 10, "median": 1000.0, ... },
      "delta": 100.0, "delta_pct": 11.1, "marks": []
    },
    "cost": { ..., "delta": null, "delta_pct": null, "marks": ["custo_indisponivel"] }
  },
  ...
  "refused": [
    { "field": "economia_mensal", "reason": "projecao_sobre_runs_que_nao_aconteceram" },
    { "field": "atribuicao_causal", "reason": "sem_run_de_controle" },
    { "field": "intervalo_de_confianca", "reason": "amostra_pequena_use_mediana_e_faixa" }
  ]
```

- O tempo caiu 44,4% e os DPU-segundos subiram 11,1%. O ledger mostra os dois e não escolhe
  qual deles é "o ganho".
- `marks` avisa quando o delta não sustenta a palavra ganho: `amostra_insuficiente` (menos de
  3 runs), `volume_desconhecido`, `volume_diverge` e `custo_indisponivel`.
- `refused` lista o que ele nunca calcula: economia mensal, causa e intervalo de confiança.

Detalhes em [docs/realized-gain.md](../../realized-gain.md).

## Erros comuns

- **Esperar custo de run sob Auto Scaling sem `DPUSeconds`.** Sai `cost_unobservable`, e isso está certo.
- **Esperar que `capacity` sugira uma capacidade nova.** Ele só compara as que o job já rodou.
- **Chamar `delta_pct` de economia.** É a diferença observada, sem causa atribuída.
- **Ler `sla_class: unknown` como defeito do job.** Falta declarar o SLA.
- **Reduzir workers porque a utilização é baixa.** Com skew, a ociosidade é sintoma. Veja
  [job-lento.md](job-lento.md#utilização-baixa-não-é-capacidade-sobrando). As regras que
  separam os dois casos (`SF-WASTE-001` e `SF-WASTE-002`) aparecem quando os facts do
  CloudWatch e do event log passam pelo `fuse` antes do `judge`: é o `fuse` que monta o resumo
  de utilização. O `scan` já faz isso sozinho.

## Para ir além

- Agent de infraestrutura do job: [glue-infra-reviewer](../referencia/agents/glue-infra-reviewer.md).
- Agent de custo: [sf-cost-reviewer](../referencia/agents/sf-cost-reviewer.md).
- Skills: [tune-glue-job](../referencia/skills/tune-glue-job.md),
  [optimize-variable-volume-job](../referencia/skills/optimize-variable-volume-job.md),
  [aws-billing-and-cost-management](../referencia/skills/aws-billing-and-cost-management.md).
- Referência dos comandos: [capacity](../referencia/cli/capacity.md), [finops](../referencia/cli/finops.md),
  [workload](../referencia/cli/workload.md), [gain](../referencia/cli/gain.md),
  [analyze](../referencia/cli/analyze.md), [collect](../referencia/cli/collect.md).
- Tools MCP: [sparkforge_capacity](../referencia/tools/sparkforge_capacity.md),
  [sparkforge_finops](../referencia/tools/sparkforge_finops.md),
  [sparkforge_gain](../referencia/tools/sparkforge_gain.md).

## Próximos passos

1. Se `levers.code` tiver achados, corrija o código antes de mexer em capacidade.
2. Se o `capacity` escolher outra capacidade, rode alguns runs nela e meça com `gain`.
3. Se o job for lento por causa de tabela ou arquivos, siga para [iceberg-e-parquet.md](iceberg-e-parquet.md).
