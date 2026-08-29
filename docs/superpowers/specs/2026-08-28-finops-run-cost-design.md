# SparkForge AWS — FinOps: o custo, a troca recurso-tempo, e onde a alavanca está

**Data:** 2026-08-28
**Status:** **proposto**. Nada implementado nesta data.
**Origem:** `prompt_tunning_foco_spark.md`, §22 (novo domínio FinOps), §37 (desperdício) e §38.
**É documento de entrada LOCAL e não versionado neste repositório.**
**Base:** o `dpu_seconds` por run de
[`2026-08-26-glue-run-history-collector-design.md`](2026-08-26-glue-run-history-collector-design.md),
os sintomas medidos por C1/C2, e a escolha de capacidade de
[`2026-08-28-capacity-sla-optimizer-design.md`](2026-08-28-capacity-sla-optimizer-design.md).
**Estado corrente:** [`../STATUS.md`](../STATUS.md)

---

## 1. Contexto: o último subprojeto

| # | Subprojeto | Estado |
|---|---|---|
| A | Correção de `SF-GLUE-001` | entregue em 2026-08-28 |
| B | Coletor de histórico de runs | entregue em 2026-08-28 |
| C1 | Métrica de scan por nó do plano | entregue em 2026-08-28 |
| C2 | WorkloadFingerprint | entregue em 2026-08-28 |
| C3 | Grafo de joins | entregue em 2026-08-28 |
| D | Capacity e SLA optimizer | entregue em 2026-08-28 |
| **E** | **FinOps** | **este documento** |

D já escolhe a capacidade mais barata que cabe, e escolhe **sem preço nenhum**: dentro da
mesma região a ordem por DPU-segundos é a ordem por dinheiro. Converter para moeda não muda a
escolha — muda o que o operador consegue levar para uma conversa sobre custo.

**A pergunta que E existe para responder é outra, e é mais interessante:** vale mais pagar
mais recurso por menos tempo, ou menos recurso por mais tempo? DPU-segundos **não é
invariante** nessa troca. Dobrar workers raramente divide o tempo por dois — e às vezes divide
por mais:

```
G.2X x10, 500 s  =  10 x 2 DPU x 500 s  =  10.000 DPU-s
G.2X x20, 200 s  =  20 x 2 DPU x 200 s  =   8.000 DPU-s
```

Mais recurso saiu **mais barato**, porque o ganho de tempo superou o dobro de capacidade — o
que acontece quando o overhead fixo domina, ou quando a memória a mais evita spill. O
contrário também acontece, e com a mesma frequência. Só os dois números medidos lado a lado
respondem, e é isso que E põe na mesa.

### 1.1 A restrição que a fonte impõe

`sparkforge/facts/pricing.py` abre com *"POR QUE ESTE MÓDULO NÃO CALCULA NADA"*, e a entrada
de preço, medida em 2026-08-28, é:

```
value: "0.44"   currency: USD
region: UNQUALIFIED           runtime_version: UNQUALIFIED
source: https://aws.amazon.com/glue/pricing/   retrieved: 2026-08-23
```

**Duas dimensões não qualificadas, não uma.** A página publica um número e a frase de que o
preço varia por região, sem a tabela por região no HTML servido; e não diferencia preço por
versão de runtime. `UNQUALIFIED` ali é valor de primeira classe — diz "a fonte foi lida e não
qualificou", que é diferente de "ninguém leu".

`value` é **string** no YAML, de propósito: quem consome converte e assume a conversão.

---

## 2. Escopo

**Entra:**

- `sparkforge/facts/run_cost.py`: o fact `glue.run_cost`, e o `glue.run_cost.unresolved`.
- Verbo de topo `sparkforge finops` e a tool MCP, reunindo **tudo o que é financeiro**: o custo
  por run (§3.1), a fronteira custo-versus-tempo entre as capacidades observadas (§3.5), o
  custo por desfecho de SLA (§3.6), os sintomas ao lado (§3.3), e **onde a alavanca está** —
  capacidade ou código (§3.7).
- Domínio de fixture próprio, com módulo golden.

**Não entra, e a razão de cada um:**

- **Limiar de "caro".** Não existe fonte dizendo que 2,32 USD por run é muito. Um limiar aqui
  seria `field-heuristic` escolhendo o orçamento de outra pessoa. E produz o custo com
  procedência; quem decide se dói é quem paga.
- **Atribuição de custo a causa.** "Você desperdiçou X com spill" exige o custo do run que
  **não** aconteceu. Ver §3.3.
- **Recomendação de capacidade.** É D, e já está entregue. E não repete a escolha; ele mostra
  o custo do que aconteceu.
- **Preço por região ou por versão.** A fonte não publica nenhum dos dois. Escrever
  `us-east-1` porque é o default comum seria precisão fabricada, e precisão fabricada
  sobrevive à revisão melhor que ausência declarada.
- **Custo de EMR, Athena ou S3.** O `dpu_seconds` que existe é de Glue. Os outros exigem outra
  fonte de preço e outro coletor.
- **`sparkforge/finops/` com os sete módulos do §22.** Metade já existe em outro lugar:
  `optimizer.py` é o subprojeto D em `sparkforge/capacity/`, `pricing.py` é
  `sparkforge/facts/pricing.py`, e `dpu.py` é o `dpu_seconds` que B já emite. Reproduzir a
  árvore inteira criaria módulos vazios com nome de promessa.

---

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 O custo é fact, no precedente do DPU derivado

`glue.run_cost` é um fact, e não a saída de um mecanismo próprio.

**A razão é o precedente exato que B estabeleceu.** `glue.job_run` já carrega `dpu_seconds`
derivado de um fator documentado (`knowledge/glue/workers-and-capacity.md`), com
`dpu_source: derived` nos attrs e a fórmula na proveniência. Custo é a mesma forma: aritmética
sobre um número medido e uma constante com fonte. **Não há limiar, e não há juízo** — e é
limiar que obriga um mecanismo próprio, como em C2 e D.

Sendo fact, ele entra no motor de regras, e uma regra futura pode consumi-lo — coisa que a
saída de `sparkforge/capacity/` não permite.

**Alternativa recusada:** `sparkforge/finops/` como mecanismo, seguindo o §22 à letra. Manteria
`facts/pricing.py` fiel ao próprio docstring, e deixaria o número de custo fora do motor de
regras para sempre.

**Sobre o docstring de `pricing.py`:** ele diz que *aquele módulo* não calcula, e a razão
escrita é específica — proíbe combinar o preço publicado com o anúncio de redução do Glue 6.0,
porque o produto seria um preço por versão que fonte nenhuma publica. Multiplicar DPU-horas
medidas pelo preço publicado **não é essa combinação**: é o preço tal como publicado, aplicado
a uma medição, com as duas ressalvas da fonte carregadas. O extrator novo não toca em
`announcements`.

### 3.2 As duas ressalvas viajam com o número

O fact carrega `region: UNQUALIFIED` **e** `runtime_version: UNQUALIFIED` nos attrs, mais
`price_source` e `price_retrieved`. O número é tão qualificado quanto a fonte dele.

**Alternativa recusada:** emitir só o valor e deixar a ressalva no relatório. O fact viaja: ele
vai para `--out`, para a tool MCP, para o contexto de um agente. Uma ressalva que fica no
relatório e não no fact é uma ressalva que se perde no primeiro salto.

### 3.3 Custo ao lado do sintoma, sem atribuir

O §37 pede "custo de desperdício". E **não** emite isso.

Dizer "você desperdiçou 0,90 USD com spill" exige saber quanto o run teria custado **sem** o
spill — o custo do run que não aconteceu. Ninguém mediu esse run. Uma subtração contra um
número imaginado é modelo, e o subprojeto D já recusou modelo quando recusou extrapolar
capacidade.

O que E emite é o custo **e** os sintomas medidos, lado a lado, para o mesmo run:

```
run jr_0042   custo 2,32 USD   region UNQUALIFIED, runtime_version UNQUALIFIED
  workerUtilization p50   0,18     (glue.metric)
  skew task p95/p50      11,4x     (spark.stage.task_duration)
  spill / input           0,34     (spark.stage.spill)
  bytes lidos           820 GB     (spark.sql.scan)
```

A leitura é de quem paga. A ferramenta põe os números na mesma linha e para de falar.

**Alternativa recusada:** atribuir contra a linha de base do run mais barato comparável do
próprio histórico. É uma subtração entre dois números medidos, não um modelo — mas chamar a
diferença de "desperdício" atribui uma causa que a diferença não prova: dois runs comparáveis
em volume podem diferir por skew do dia, por contenção, por retry.

### 3.5 A fronteira custo-versus-tempo, entre as capacidades observadas

O núcleo de E. Para cada capacidade que o job **realmente rodou**, os dois eixos medidos lado
a lado, em moeda e em segundos:

```
etl-pedidos, runs comparaveis por capacidade

capacidade      runtime p50   runtime p95   custo/run p95   custo relativo
G.1X x10            900 s        1100 s        1,10 USD          1,38x
G.2X x10            500 s         620 s        1,22 USD          1,53x
G.2X x20            200 s         260 s        0,80 USD          1,00x   <- mais barata
G.4X x10            240 s         300 s        1,17 USD          1,46x

leitura: G.2X x20 tem o DOBRO do recurso de G.2X x10 e custa 34% MENOS,
porque o tempo caiu para 42% -- mais que a metade. O ganho superou a
capacidade acrescentada.
```

A tabela é a resposta. Não há modelo, não há extrapolação: cada linha é a distribuição medida
daquela capacidade, e a comparação é entre números que existem.

**A mesma restrição de D vale aqui, e pelo mesmo motivo:** só capacidade observada entra, e só
runs comparáveis contam. Comparar o custo de uma capacidade que rodou em dias pequenos com o
de outra que rodou em dias grandes produziria uma fronteira que descreve o calendário, não a
capacidade. E reusa o filtro de volume que D já estabeleceu.

**Alternativa recusada:** desenhar a curva completa custo × workers, interpolando entre as
observadas. Ela seria bonita e mentiria entre os pontos, exatamente onde alguém olharia.

### 3.6 Curto e longo prazo são perguntas diferentes

**Curto prazo** é o custo de um run. **Longo prazo** não é esse número multiplicado pela
frequência — é o custo por **desfecho útil**, e é aí que a confiabilidade de D entra na conta:

```
capacidade    custo/run   P(dentro do SLA)   custo por run DENTRO do SLA
G.2X x20       0,80 USD        0,98                    0,82 USD
G.2X x10       1,22 USD        0,71                    1,72 USD
```

Uma capacidade mais barata por run que estoura o SLA com frequência custa mais por resultado
que serve — e o run que estourou custou dinheiro sem entregar o que precisava. É a *SLA
Efficiency* do §38 do documento de origem, escrita como divisão entre dois números medidos.

**A ressalva que viaja junto:** `custo / P` só faz sentido quando `P` tem resolução para ser
afirmado. E reusa o predicado `resolution_supports` que D já expõe — capacidade cujo `n` não
sustenta o alvo sai da comparação de longo prazo com a razão nomeada, e continua na de curto.

**Alternativa recusada:** multiplicar o custo do run pela frequência declarada de execução.
Daria um custo mensal, e o número extra não muda a comparação entre capacidades — a frequência
é a mesma para todas, então ela escala todas igualmente e não informa a escolha.

### 3.7 Onde a alavanca está: capacidade ou código

**As duas falhas que E existe para evitar**, e elas são simétricas:

- **Projeto caro desnecessariamente.** Capacidade acima do que o SLA exige, pagando por tempo
  que ninguém precisava economizar.
- **Projeto barato que demora demais.** Capacidade abaixo do que o trabalho pede, estourando o
  SLA para poupar centavos.

E existe uma terceira, que é a mais cara das três e não aparece em nenhum eixo de capacidade:
**o custo que está no código**. Um job que varre dez vezes o que precisa, que derrama para
disco, ou que roda uma UDF Python por linha é caro em qualquer capacidade — e trocar o worker
para consertar isso é comprar saída de um defeito. O custo cai um pouco, o defeito continua, e
a conta volta maior quando o volume crescer.

**E não atribui quanto do custo é de cada lado** — isso exigiria o contrafactual que §3.3
recusa. Ele diz **qual alavanca se aplica**, nomeando a evidência:

```
etl-pedidos, run jr_0042   custo 2,32 USD (region UNQUALIFIED)

  ALAVANCA DE CAPACIDADE
    ver `sparkforge capacity` -- ele responde com a distribuicao medida.

  ALAVANCA DE CODIGO -- 4 achados, e nenhum deles muda trocando worker:
    SF-PQ-002  scan sem filtro de particao        plan.file_scan
    SF-PY-004  action dentro de laco              pyspark.loop
    SF-UI-006  subparalelismo                     spark.stage.task_count
    SF-PLAN-00x  UDF Python no plano              plan.python_udf

  NAO HA achado de codigo para: skew observado (11,4x).
    O catalogo nao tem regra que explique este skew, e a leitura fica
    declarada como lacuna em vez de silencio.
```

O insumo já existe inteiro: `judge` produz achados a partir do catálogo, e as áreas que tocam
custo por código são as de PySpark, Parquet/S3, plano físico e Spark UI. E **não escreve regra
nova** — ele agrupa os achados que o motor já produz sob o eixo financeiro, que é a leitura que
falta hoje.

**A recusa que dá sentido ao resto:** quando não há achado de código e a capacidade está
dimensionada para o SLA, E diz que **não encontrou alavanca** — e isso é uma resposta, não uma
falha. Um job pode simplesmente custar o que custa.

**Alternativa recusada:** ranquear os achados por "economia estimada". Cada número desses seria
um contrafactual disfarçado de prioridade, e a ordem sairia com aparência de medição.

### 3.4 A única coisa que E afirma é a correlação do §37

O documento de origem traz a distinção que separa um especialista de um verificador de regras:

> utilização de worker baixa **com** skew extremo não significa reduzir workers. Pode
> significar que 90% dos workers estão ociosos porque uma task ficou 14 minutos numa partição
> enviesada.

E emite essa leitura, nomeada, e **recusa a leitura oposta**:

| Sintoma medido | O que E diz |
|---|---|
| utilização baixa, skew baixo | capacidade possivelmente ociosa — e a pergunta de capacidade é de D, com evidência |
| utilização baixa, skew **extremo** | **não é capacidade**: os workers esperam uma task |
| utilização alta, spill alto | pressão de memória, não número de workers |
| sem `glue.metric` coletado | leitura indisponível, com o comando que a resolve |

É uma leitura sobre sintomas medidos, não um limiar de custo — e é por isso que ela mora no
relatório e não no fact.

---

## 4. Modelo

### 4.1 `glue.run_cost`

```
subject   {type: job_run, symbol: <job_run_id>, job_name, job_run_id}
attrs     {region, runtime_version, price_source, price_retrieved, currency,
           dpu_source}
measures  {dpu_seconds, dpu_hours, price_per_dpu_hour, cost}
provenance {extractor, formula: "dpu_hours * price_per_dpu_hour"}
```

`dpu_source` é copiado do `glue.job_run` de origem (`observed` ou `derived`): um custo
calculado sobre DPU derivado é uma derivação sobre outra, e o leitor precisa saber.

### 4.2 `glue.run_cost.unresolved`

| Razão | Quando |
|---|---|
| `dpu_seconds_unavailable` | o run não tem `dpu_seconds` — sob Auto Scaling sem `DPUSeconds`, B recusou derivar, e sem DPU não há custo |
| `price_unavailable` | a tabela de preço não carregou, ou não tem entrada de DPU-hora |
| `price_ambiguous` | a tabela publica mais de um preço por DPU-hora sem eixo que os separe — escolher um seria escolher pelo operador |

### 4.3 O relatório

Não é fact. `sparkforge finops` compõe, por run: o custo, os sintomas, e a leitura de §3.4.

---

## 5. Superfície

```
sparkforge finops --facts <facts.json> [--job-name <job>] [--out F]
```

**Verbo de topo**, pela mesma regra de `benchmark`, `fuse`, `workload` e `capacity`: consome
facts já extraídos e não lê artefato nenhum.

Tool MCP `sparkforge_finops`, read-only local, com os parâmetros de caminho terminando em
`_path`.

O fact `glue.run_cost` sai por onde os facts de run já saem — o extrator novo é chamado pelo
verbo que já extrai facts de run, e a decisão de qual verbo é da implementação, desde que o
fact não exija verbo próprio só para existir.

---

## 6. Erros, cada um com o seu nome

| Situação | Saída |
|---|---|
| Run sem `dpu_seconds` | `glue.run_cost.unresolved`, razão `dpu_seconds_unavailable`, nomeando a recusa de B |
| Tabela de preço ausente ou ilegível | `price_unavailable`. O carregador é fail-closed e levanta; o extrator converte em lacuna, nunca deixa passar zero |
| Mais de um preço por DPU-hora sem eixo | `price_ambiguous`, listando os candidatos |
| Sem `glue.metric` para o run | o relatório declara a leitura indisponível, com `sparkforge collect cloudwatch …`; o custo continua saindo |
| Sem nenhum `glue.job_run` | relatório vazio com a razão, não um relatório de zero runs que parece "nada a pagar" |

---

## 7. Testes

### 7.1 Domínio de fixture próprio

`fixtures/finops/`, com `tests/test_fixtures_golden_finops.py`.

| Cenário | Prova |
|---|---|
| `cost_from_derived_dpu` | custo sobre DPU derivado, com `dpu_source` propagado |
| `cost_from_observed_dpu` | custo sobre `DPUSeconds` medido |
| `no_dpu_no_cost` | Auto Scaling sem `DPUSeconds`: lacuna, não zero |
| `idle_workers_low_skew` | a leitura de capacidade ociosa |
| `idle_workers_extreme_skew` | **a leitura oposta**: não é capacidade |
| `no_cloudwatch` | custo sai, leitura declarada indisponível |
| `more_resource_costs_less` | o caso que motivou E: o dobro de workers custando menos |
| `more_resource_costs_more` | o mesmo eixo no sentido oposto, para que o corpus não prove só um lado |
| `cheap_but_misses_sla` | mais barata por run e mais cara por desfecho dentro do SLA |
| `cost_is_in_the_code` | achados de código presentes: a alavanca não é worker |
| `no_lever_found` | sem achado e com capacidade dimensionada: o job custa o que custa |

### 7.2 As três garantias sobre o corpus inteiro

**Todo `glue.run_cost` carrega as duas ressalvas.** `region` e `runtime_version` nunca saem
vazios nem ausentes — se a fonte não qualifica, o fact diz `UNQUALIFIED` em ambos. Um fact de
custo sem ressalva é um número que parece preciso.

**Nenhum fact de custo existe sem `dpu_seconds`.** Custo sobre DPU ausente seria zero
disfarçado, e zero de custo é a mentira mais confortável que este projeto poderia contar.

**Nenhum achado de código aparece sob a alavanca de capacidade.** As duas listas nunca se
misturam: sugerir troca de worker para um `SF-PY` seria exatamente a compra de saída de um
defeito que §3.7 recusa.

**Nenhuma saída de E contém a palavra "desperdício" atribuída a uma causa.** Verificada sobre
o corpus: o relatório põe custo e sintoma lado a lado e não os subtrai. É a garantia de §3.3, e
sem ela a próxima pessoa a mexer aqui vai achar que atribuir é o objetivo.

---

## 8. Documentação

- `README.md`: o verbo novo, e os números de extratores e kinds **medidos** — nos **dois**
  lugares que os citam.
- `docs/superpowers/STATUS.md`: a fase, e o fechamento do roadmap de cinco subprojetos.
- `knowledge/`: nada novo. E não introduz preço; ele lê o que já está versionado com fonte e
  data.

---

## 9. Critérios de aceite

1. Um run com `dpu_seconds` medido produz `glue.run_cost` com `cost` igual a
   `dpu_seconds / 3600 * price_per_dpu_hour`, e com `region` e `runtime_version` iguais a
   `UNQUALIFIED`.
2. Um run sem `dpu_seconds` produz `dpu_seconds_unavailable`, e **nenhum** `glue.run_cost`.
3. `dpu_source` do fact de custo é o mesmo do `glue.job_run` de origem.
4. Utilização baixa com skew extremo produz a leitura "não é capacidade", e **não** a de
   capacidade ociosa.
5. Sem `glue.metric`, o custo continua saindo e a leitura sai declarada indisponível.
6. Nenhuma saída atribui custo a uma causa.
7. A fronteira mostra, em pelo menos um cenário do corpus, uma capacidade com **mais** recurso
   e **menor** custo por run — e o golden traz os dois eixos que provam por quê.
8. Capacidade cuja resolução não sustenta o alvo sai da comparação de longo prazo com razão
   nomeada, e permanece na de curto prazo.
9. Um run com achados de código lista os `rule_id` sob a alavanca de código, e **não** sugere
   troca de capacidade para nenhum deles.
10. Um run sem achado de código e com capacidade dimensionada produz "nenhuma alavanca
    encontrada" — uma resposta, não uma omissão.
11. Nenhuma saída ordena achados por economia estimada.
7. Suíte completa verde, gate de números verde, gate de tool órfã verde, gate de domínio de
   fixture verde, bundle offline verde.
