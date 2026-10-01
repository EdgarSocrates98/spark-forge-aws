# SparkForge AWS — Capacity optimizer: a mais barata que cabe no SLA, entre as que rodaram

**Data:** 2026-08-28
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_tunning_foco_spark.md`, §17, §18 (SLA-Constrained Optimizer), §29 e §34.
**É documento de entrada LOCAL e não versionado neste repositório.**
**Base:** o histórico de
[`2026-08-26-glue-run-history-collector-design.md`](2026-08-26-glue-run-history-collector-design.md),
a métrica de scan de
[`2026-08-28-spark-sql-scan-metrics-design.md`](2026-08-28-spark-sql-scan-metrics-design.md)
e o inventário declarado de
[`2026-08-28-workload-fingerprint-design.md`](2026-08-28-workload-fingerprint-design.md).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: a primeira peça que recomenda

| # | Subprojeto | Estado |
|---|---|---|
| A | Correção de `SF-GLUE-001` | aberto |
| B | Coletor de histórico de runs | entregue em 2026-08-28 |
| C1 | Métrica de scan por nó do plano | entregue em 2026-08-28 |
| C2 | WorkloadFingerprint | entregue em 2026-08-28 |
| C3 | Grafo de joins | entregue em 2026-08-28 |
| **D** | **Capacity e SLA optimizer** | **este documento** |
| E | FinOps | aberto, depende de D |

Tudo o que veio antes **descreve**. D **recomenda**, e é a primeira vez que o projeto diz a alguém o que fazer com dinheiro e com um SLA. A diferença de risco é a razão de este documento ser mais paranoico que os anteriores.

### 1.1 O objetivo, como o documento de origem o escreve

```
MINIMIZE expected_cost
sujeito a:  P(runtime <= SLA) >= reliability_target
```

O exemplo do §18 é exato: entre três configurações que cumprem o SLA, escolher a mais barata — não a mais rápida. `C` é mais rápido que `B` e é a escolha errada, porque o SLA já estava satisfeito e o resto é dinheiro queimado.

---

## 2. Escopo

**Entra:**

- `sparkforge/capacity/`: o `CapacityPlan`, o `Candidate` e a `Refusal`.
- Verbo de topo `sparkforge capacity` e a tool MCP correspondente.
- Contrato de `--history`: um arquivo de facts por run anterior.
- `reliability_target` e `volume_tolerance` no `workload.yaml` que C2 criou.
- Domínio de fixture próprio, com módulo golden.

**Não entra, e a razão de cada um:**

- **Custo em dinheiro.** D minimiza DPU-segundos — ver §3.2. Converter para moeda é o subprojeto E, e `facts/pricing.py` recusa combinar preço com região não qualificada.
- **Capacidade nunca observada.** Ver §3.1: recomendar o que nunca rodou exigiria uma lei de escala sem fonte publicada.
- **Recomendação de configuração do Spark.** `spark.sql.shuffle.partitions` e vizinhos são outro problema (§36 do documento de origem, sobre configuração mínima com proveniência). D recomenda **capacidade**.
- **Aplicar a mudança.** §34 classifica troca de worker como `REVIEW`, e o documento de origem diz: *"nunca aplicar automaticamente mudanças REVIEW/EXPERIMENTAL em produção"*. D emite; quem aplica é gente.
- **Canary.** Comparar o antes e o depois de uma troca é o §35, e o `benchmark` do projeto já é metade disso.

---

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 Só capacidades que o job realmente rodou

D ordena as capacidades observadas no histórico e escolhe entre elas. Capacidade nunca tentada **não entra na lista**, e a ausência é declarada.

**Alternativa recusada:** extrapolar o runtime para capacidades não observadas com uma lei de escala do tipo `runtime ~ 1/workers` corrigida por um fator de eficiência. Não existe fonte publicada para esse fator; ele varia com o shape do DAG, com skew e com contenção de I/O. Seria `field-heuristic` com número inventado, e desta vez o número escolheria quanto alguém gasta.

**O custo declarado:** um job que sempre rodou em uma única capacidade não recebe recomendação nenhuma — recebe a constatação de que não há alternativa observada. É honesto e é pouco útil, e a saída diz isso em vez de disfarçar.

### 3.2 O custo é DPU-segundos, não moeda

`glue.job_run` carrega `dpu_seconds` **por run**, medido quando a API o publica e derivado quando a capacidade é estática. D calcula o p95 **sobre os runs comparáveis**, e não lê o `dpu_seconds_p95` de `glue.job_run.distribution`: aquele agrega todos os runs da capacidade, inclusive os que o filtro de volume de §3.4 acabou de excluir. Usar o agregado depois de filtrar seria comparar um custo de uma população com uma confiabilidade de outra.

Dentro da mesma região, a ordem por DPU-segundos **é** a ordem por dinheiro: o preço por DPU-hora é fator constante e não muda quem vence. Então D decide sem preço nenhum, e E depois converte sem mudar a escolha.

**Alternativa recusada:** esperar E. Inverteria a dependência do roadmap e bloquearia D atrás de um subprojeto cuja única contribuição para a decisão é um fator constante.

**Consequência:** capacidade com Auto Scaling e sem `DPUSeconds` na resposta da API **não tem custo observável** — B já recusou derivar DPU ali, porque `number_of_workers` sob Auto Scaling é teto, não uso. Ela sai da comparação com razão nomeada.

### 3.3 A confiabilidade é contada, e a resolução é declarada

`P(runtime <= SLA)` é contagem empírica sobre os runs comparáveis daquela capacidade:

```
P = (runs com execution_time_s <= SLA) / n
```

Sem interpolação e sem assumir distribuição. E, junto, a **resolução**: com `n` runs, a estimativa não distingue nada mais fino que `1/n`. Se `1/n > 1 − alvo`, a capacidade é **recusada por resolução grossa**, não aprovada.

Exemplo: alvo de 99% com 28 runs. A menor diferença observável é 3,6%, e afirmar 99% exigiria distinguir 1%. A recusa diz quantos runs faltam.

**Alternativa recusada:** comparar o SLA com o percentil publicado (`runtime_p99_s` para alvo de 99%). Só responde alvos que casem exatamente com um percentil publicado, e — pior — dá a mesma resposta para `n=5` e `n=500`, porque o fact de distribuição publica o percentil sem publicar quanta evidência há por trás dele.

**Alternativa recusada:** contar sem declarar resolução. Afirmar 99% a partir de 12 runs é precisão que o dado não tem, e o relatório sairia confiante exatamente onde mediu mal.

### 3.4 Só runs comparáveis entram na conta

**O problema que isto resolve.** O histórico mistura dias diferentes com volumes diferentes. Uma capacidade que cumpriu o SLA em 28 runs pode ter cumprido porque 25 deles foram dias pequenos, e recomendá-la para um dia grande seria usar evidência que não se aplica. Contar runs sem perguntar se são comparáveis é o modo de falha mais caro que este documento poderia ter.

A pergunta certa não é como dividir o histórico em faixas, e sim **quais runs passados são comparáveis a este**. Entram na conta os runs cujo volume varrido está dentro de uma tolerância declarada do volume do run corrente:

```
run corrente:  820 GB varridos
tolerancia:    +/-25%  (workload.yaml, com default)

G.2X x10:  28 runs no total
           19 dentro da faixa 615-1025 GB
           17 desses dentro do SLA
  P = 17/19 = 89,5%     resolucao = 1/19 = 5,3%
```

**Duas consequências assumidas de frente:**

- **O `n` cai, e a resolução piora.** Uma capacidade que "cabia" com o histórico inteiro pode passar a ser recusada por resolução grossa. Essa recusa é o desenho funcionando, não falhando: a evidência que sobrou é a única que se aplica ao dia de hoje.
- **Run sem volume medido não entra.** Vai para uma lista de descartados, contada e nomeada, para que o operador veja quanto do histórico foi ignorado e por quê. Descarte silencioso faria o `n` encolher sem explicação.

**Alternativa recusada:** dividir o histórico em terços por volume e comparar dentro do terço. Cria fronteiras arbitrárias — dois runs quase idênticos caem em faixas diferentes por um byte — e não responde a pergunta que importa, que é sobre o run corrente.

### 3.5 O contrato de `--history`: um arquivo por run

Para saber a duração, a capacidade **e** o volume de cada run, D precisa dos três juntos, por run. Eles vêm de dois artefatos diferentes: a duração e a capacidade de `glue.job_run` (o histórico de B), o volume de `spark.sql.scan` (o event log daquele run, por C1).

Então `--history` é um **diretório com um arquivo de facts por run**, e cada arquivo precisa conter:

```
exatamente UM  glue.job_run     -- id, execution_time_s, capacidade
zero ou mais   spark.sql.scan   -- bytes varridos daquele run
```

Arquivo com zero ou com mais de um `glue.job_run` é **recusado com o caminho**, porque a premissa "um arquivo é um run" deixou de valer e nada mais no arquivo pode ser atribuído com confiança.

**Alternativa recusada:** um único arquivo com todos os facts, correlacionando run e event log por chave. `spark.sql.scan` é ancorado em `execution_id`, que é por aplicação Spark e não identifica run de Glue; a correlação exigiria uma chave que nenhum dos dois artefatos publica. A separação por arquivo é a mesma que C2 adotou, pela mesma razão.

### 3.6 Toda recomendação nasce `REVIEW`

§34 do documento de origem classifica `worker change` como `REVIEW`, e diz explicitamente: *"nunca aplicar automaticamente mudanças REVIEW/EXPERIMENTAL em produção"*. A saída inteira de D é uma troca de worker.

`safety: "REVIEW"` é campo do candidato, não nota de rodapé, e não há caminho no código que aplique coisa alguma. D escreve um plano; executar é decisão de gente.

---

## 4. Modelo

Mecanismo próprio em `sparkforge/capacity/`, não extrator — escolher capacidade é juízo, e o precedente é o `WorkloadFingerprint` de C2 e o `MigrationAssessment`.

```python
Candidate(
    glue_version, worker_type, number_of_workers, autoscaling,
    runs_total,            # runs desta capacidade no historico
    runs_comparable,       # dentro da tolerancia de volume
    runs_within_sla,
    reliability,           # runs_within_sla / runs_comparable
    resolution,            # 1 / runs_comparable
    dpu_seconds_p95,       # p95 sobre os runs COMPARAVEIS, recomputado aqui
    runs_without_cost,     # comparaveis sem `dpu_seconds` medido
    meets_sla,             # bool
    safety = "REVIEW",
)

CapacityPlan(
    job_name, job_run_id,
    sla_minutes, reliability_target, volume_tolerance,
    current_volume_bytes,
    candidates,            # ordenados por dpu_seconds_p95
    chosen,                # Candidate | None
    refused,               # [Refusal] -- capacidade que saiu, com a razao
    discarded_runs,        # runs que nao entraram, contados por razao
)
```

`chosen` é o primeiro candidato com `meets_sla` na ordem de `dpu_seconds_p95` — a mais barata que cabe. Nunca a mais rápida.

---

## 5. Superfície

```
sparkforge capacity --facts <facts.json> --job-name <job> --job-run <id> --history <dir> [--out F]
```

**Verbo de topo**, pela mesma regra que `benchmark`, `fuse` e `workload`: os verbos sob `analyze` extraem facts de um artefato, e este não extrai nada — classifica o que outros já extraíram.

Tool MCP `sparkforge_capacity`, read-only local. Parâmetros de caminho terminam em `_path`, como o resto do catálogo.

---

## 6. Erros, cada um com o seu nome

| Situação | Saída |
|---|---|
| `1/n > 1 − alvo` depois do filtro de volume | `resolution_too_coarse`, com o `n` comparável e quantos runs faltam |
| Nenhum run comparável com `dpu_seconds` | `cost_unobservable`, apontando a recusa de B: sob Auto Scaling sem `DPUSeconds`, `number_of_workers` é teto e não uso |
| Sem `workload.declared` para o job | plano `unknown`: sem SLA não há restrição a satisfazer |
| Nenhuma capacidade cumpre o SLA | `chosen: None`, todas as candidatas listadas com o quanto cada uma erra. Não escolhe a menos pior |
| Uma única capacidade observada | ela é avaliada, e o plano declara que não há alternativa a comparar |
| Run sem `spark.sql.scan` | descartado, contado em `discarded_runs` com razão `volume_unknown` |
| Arquivo de histórico com ≠ 1 `glue.job_run` | recusado, com o caminho e a contagem encontrada |
| `--history` vazio ou ausente | plano `unknown`, com o comando que produz o histórico |

---

## 7. Testes

### 7.1 Domínio de fixture próprio

`fixtures/capacity/`, com `tests/test_fixtures_golden_capacity.py` declarando
`FIXTURES = ROOT / "fixtures" / "capacity"`.

| Cenário | Prova |
|---|---|
| `cheapest_that_fits` | o exemplo do §18: três capacidades, duas cabem, escolhe a mais barata |
| `none_fits` | `chosen: None`, com o quanto cada uma erra |
| `resolution_too_coarse` | alvo de 99% com poucos runs: recusa, não aprovação frágil |
| `volume_filter_changes_the_answer` | a capacidade que ganharia com o histórico inteiro perde ao comparar só runs comparáveis |
| `autoscaling_without_cost` | capacidade sem custo observável sai da comparação |
| `single_capacity_observed` | sem alternativa, e o plano diz isso |

### 7.2 As três garantias sobre o corpus inteiro

**Nunca escolhe uma capacidade mais cara do que outra que também cabe.** É o objetivo do §18, e um erro de ordenação passaria em cada cenário isolado.

**Nunca escolhe uma capacidade que não cumpre o SLA.** Nem quando nenhuma cumpre: aí `chosen` é `None`.

**Todo candidato com `meets_sla` tem `resolution <= 1 − reliability_target`.** É a garantia que separa "medimos que cabe" de "não temos como saber", e é dela que depende a confiança em tudo o que D diz.

---

## 8. Documentação

- `README.md`: o verbo novo junto de `benchmark`, `fuse` e `workload`, e os números medidos.
- `docs/superpowers/STATUS.md`: a fase, os desvios e o que ficou de fora.
- `knowledge/`: nada novo. D não introduz limiar com fonte externa — a escala é o histórico do próprio job, e o alvo é declarado por quem opera.

---

## 9. Critérios de aceite

1. Três capacidades onde duas cumprem o SLA: escolhe a de menor `dpu_seconds_p95`, não a mais rápida.
2. Nenhuma cumpre: `chosen` é `None`, e todas aparecem com o quanto erram.
3. Alvo de 99% com 28 runs comparáveis: recusa por resolução, dizendo quantos faltam.
4. Filtrar por volume muda a resposta em pelo menos um cenário do corpus, e o golden mostra as duas contagens.
5. Capacidade com Auto Scaling e sem `DPUSeconds` sai com `cost_unobservable`, e não é escolhida.
6. Arquivo de histórico com dois `glue.job_run` é recusado com o caminho.
7. Todo candidato aprovado tem `safety: "REVIEW"`, e nenhum caminho do código aplica a mudança.
8. Suíte completa verde, gate de números verde, gate de tool órfã verde, gate de domínio de fixture verde.
