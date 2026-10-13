# Workers, capacidade e custo no AWS Glue

## 1. Tipos de worker

### Série G — compute padrão

| Worker | DPU | vCPU | Memória | Disco |
|---|---:|---:|---:|---:|
| G.025X | 0,25 | 2 | 4 GB | 84 GB |
| G.1X | 1 | 4 | 16 GB | 94 GB |
| G.2X | 2 | 8 | 32 GB | 138 GB |
| G.4X | 4 | 16 | 64 GB | 256 GB |
| G.8X | 8 | 32 | 128 GB | 512 GB |
| G.12X | 12 | 48 | 192 GB | 768 GB |
| G.16X | 16 | 64 | 256 GB | 1024 GB |

### Série R — otimizada para memória

| Worker | M-DPU | vCPU | Memória | Disco |
|---|---:|---:|---:|---:|
| R.1X | 1 | 4 | 32 GB | 94 GB |
| R.2X | 2 | 8 | 64 GB | — |
| R.4X | 4 | 16 | 128 GB | — |
| R.8X | 8 | 32 | 256 GB | — |

**A série R dá o dobro de memória do G equivalente com o mesmo vCPU.** É a resposta correta para job memory-bound comprovado — e a errada para job CPU-bound ou I/O-bound, onde só encarece.

`G.025X` existe para streaming e jobs muito pequenos. Usar em batch de volume real é subprovisão.

Disco importa mais do que parece: spill de shuffle vai para o disco local do worker. `DISK_NO_SPACE_ERROR` num G.1X (94 GB) pode ser resolvido por G.4X (256 GB) sem mudar nada no código — e é a única situação em que "worker maior" é a resposta direta e correta.

## 2. Regra de decisão: qual eixo aumentar

| Evidência | Eixo correto | Não faça |
|---|---|---|
| CPU alta, memória e disco OK, tasks equilibradas | mais workers (paralelismo) | worker maior |
| Heap de executor alto, spill alto, tasks equilibradas | worker R ou G maior (memória/executor) | mais workers G.1X |
| `DISK_NO_SPACE_ERROR`, disco alto | worker maior (mais disco) ou mais workers | mais memória |
| Executor perdido sem OOM no log | `memoryOverhead`, não worker | worker maior |
| `max/median` de task alto | corrigir skew | qualquer aumento de capacidade |
| `workerUtilization` baixo | Auto Scaling, ou reduzir workers | mais workers |
| Tempo em listing S3, CPU baixa | corrigir layout de arquivos | qualquer aumento de capacidade |
| Driver heap alto, executores ociosos | corrigir trabalho no driver | qualquer aumento de capacidade |

As últimas quatro linhas cobrem a maioria dos casos reais, e em nenhuma delas mais capacidade é a resposta. Daí a regra do projeto: **não recomendar mais workers como primeira resposta.**

## 3. Cálculo de paralelismo

Cores disponíveis para tasks ≈ `número de workers × vCPU por worker` (menos o driver, que consome um worker).

Sinais de desalinhamento:

- Tasks por stage **muito menor** que cores ativos → subparalelismo. Cores pagos e ociosos. Causa comum: poucos arquivos de entrada grandes e não splitáveis (gzip), ou `spark.sql.shuffle.partitions` baixo demais para o volume.
- Milhares de tasks com duração de milissegundos → over-partitioning. Overhead de agendamento domina. Causa comum: small files, ou `shuffle.partitions` alto para volume pequeno.
- Duração média de task saudável: dezenas de segundos a poucos minutos. Nem 200 ms, nem 40 minutos.

## 4. Auto Scaling

Habilitado por `--enable-auto-scaling = true`. Com ele, configure **`MinCapacity` e `MaxCapacity`** na job definition, **não** `NumberOfWorkers` — configurar `NumberOfWorkers` junto é o erro de IaC mais comum aqui.

O Glue monitora métricas de stage e sobe executores quando estão saturados, descendo quando ficam ociosos.

Quando **não** compensa:
- Jobs abaixo de ~3 minutos: o overhead de scaling não se paga.
- Volume muito baixo com `MaxCapacity` muito alto: o teto grande não ajuda e complica o diagnóstico.

Efeito documentado: jobs tendem a rodar com 75–100% de eficiência com Auto Scaling, contra 20–40% com executores fixos mal dimensionados. Tratar como ordem de grandeza esperada, não como garantia — a evidência para o job em análise é `glue.driver.workerUtilization`.

## 5. Execution class Flex

`--execution-class FLEX` roda em capacidade não garantida, com custo menor. Adequado a workload insensível a tempo: ETL noturno, jobs de fim de semana, reprocessamento.

Não usar quando: há SLA rígido, o job é parte de cadeia com dependência de horário, ou a variabilidade de duração impede o planejamento downstream. Flex pode ter início retardado e duração menos previsível.

Combinação a avaliar sempre em job de bootstrap/full: **Flex + Auto Scaling** costuma ser a maior redução de custo disponível sem tocar em uma linha de código — desde que o job realmente não tenha SLA.

## 6. Custo

Custo ≈ `DPU-hours × preço por DPU-hora`, onde `DPU-hours = DPUs alocadas × duração`.

Consequências que operadores erram:

- **Reduzir duração dobrando workers não reduz custo.** 10 workers × 2 h = 20 DPU-h ≈ 20 workers × 1 h = 20 DPU-h. Só ganha se a escalabilidade for superlinear (raro) ou se havia ociosidade.
- **Worker maior não é mais caro por unidade de trabalho** — G.2X é 2 DPU, e 5 × G.2X ≈ 10 × G.1X em DPU. A escolha entre eles é de memória por executor, não de preço.
- **Reduzir trabalho é a única alavanca que reduz custo e duração juntos.** Daí a hierarquia em `../performance-principles.md`.

Sempre reportar custo em DPU-hours, não em duração. Duração sozinha esconde superprovisão.

## 7. Baseline mínimo antes de tunar capacidade

Sem estes números, qualquer mudança de worker é chute:

1. Runtime e DPU-hours atuais.
2. `glue.driver.workerUtilization`.
3. `glue.ALL.memory.heap.used.percentage` (série temporal).
4. `glue.ALL.disk.used.percentage`.
5. Spill do stage dominante.
6. `max/median` de duração de task do stage dominante.
7. Volume de entrada (bytes, linhas, contagem de arquivos).

## Fontes

- AWS Glue worker types. https://docs.aws.amazon.com/glue/latest/dg/worker-types.html (retrieved 2026-07-29)
- AWS Glue now supports new workers for larger and memory intensive workloads (série R). https://aws.amazon.com/about-aws/whats-new/2025/07/aws-glue-supports-new-workers-larger-memory-intensive-workloads (retrieved 2026-07-29)
- Scale your AWS Glue for Apache Spark jobs with new larger worker types G.4X and G.8X. https://aws.amazon.com/blogs/big-data/scale-your-aws-glue-for-apache-spark-jobs-with-new-larger-worker-types-g-4x-and-g-8x (retrieved 2026-07-29)
- Using auto scaling for AWS Glue. https://docs.aws.amazon.com/glue/latest/dg/auto-scaling.html (retrieved 2026-07-29)
- Introducing AWS Glue Flex jobs: Cost savings on ETL workloads. https://aws.amazon.com/blogs/big-data/introducing-aws-glue-flex-jobs-cost-savings-on-etl-workloads/ (retrieved 2026-07-29)
- Improving AWS Glue performance. https://docs.aws.amazon.com/glue/latest/dg/performance.html (retrieved 2026-07-29)
- Disco de R.2X/R.4X/R.8X não foi confirmado nesta coleta. Verificar antes de citar.
- Preço por DPU-hora varia por região e execution class; consultar pricing vigente, nunca fixar número aqui.
