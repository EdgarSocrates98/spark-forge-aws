# SparkForge AWS — Timeout Intelligence: qual timeout, e por que aumentá-lo não é o conserto

> Subprojeto F. Fecha o último item P0 do `prompt_tunning_foco_spark.md` (§39) e
> o critério 11 do §41: **diferenciar tipos de timeout**. Origem: §12 e §31 do
> documento.

## 1. Contexto: o que a auditoria encontrou aberto

A auditoria das 41 seções do documento de origem, registrada em
`docs/superpowers/STATUS.md`, mediu que a onda P0 estava fechada em sete dos
oito itens. O item que sobrou é o classificador de timeout, e ele é o critério
11 dos vinte critérios de aceite.

O motivo de ter sobrado é visível na árvore: hoje a palavra "timeout" existe em
três lugares que **não se falam**.

- `glue.job_run` carrega `measures.timeout_min` e o estado `TIMEOUT`, que
  `glue.job_run.outcome` conta junto dos outros desfechos.
- `spark.executor.lost` carrega a razão bruta que o Spark escreveu ao remover o
  executor — a frase onde um timeout de heartbeat aparece, quando aparece.
- `spark.conf_effective` carrega, uma chave por fact, os três valores que o
  documento separa: `spark.sql.broadcastTimeout`, `spark.network.timeout` e
  `spark.executor.heartbeatInterval`.

E há uma quarta fonte que o extrator **não lê hoje**, e sem ela duas das quatro
categorias não teriam evidência nenhuma: `SparkListenerStageCompleted` traz
`Stage Info["Failure Reason"]`, que é onde o Spark escreve "Could not execute
broadcast in N secs" e "Futures timed out after". O handler atual lê
`Stage ID`, `Stage Name` e `Number of Tasks` daquele evento, e descarta a razão
da falha. Ler essa chave é parte deste subprojeto.

Nenhuma regra do catálogo lê nenhum dos três com essa pergunta. Medido em
`load_catalog()`: das **130** regras carregadas, **nenhuma** tem "timeout" no id
ou no título. A única que a busca por texto encontra perto do assunto é
`SF-PY-009`, sobre `broadcast()` forçado por hint — que é o hint, e não o
timeout do broadcast.

### 1.1 Por que a distinção importa, e não é cosmética

`TIMEOUT` no Glue é wall-clock: a AWS define `Timeout` do `JobRun` como o tempo
máximo que a execução pode consumir recursos antes de entrar naquele estado.
Isso diz **que** o relógio acabou, e não **por quê**.

Os outros três são mecanismos distintos, cada um com default próprio, e
confundi-los produz a recomendação errada com confiança alta:

| Mecanismo | O que ele mede | Consequência de subir sem olhar a causa |
|---|---|---|
| `Timeout` do JobRun | relógio de parede do run | o run passa a custar mais e falha depois |
| `spark.sql.broadcastTimeout` | espera por um broadcast | mascara um lado grande demais para broadcast |
| `spark.network.timeout` | RPC e shuffle | mascara pressão de memória, GC ou skew |
| `spark.executor.heartbeatInterval` | pulso do executor | quebra a detecção de executor morto |

O Spark documenta que `heartbeatInterval` deve ser **significativamente menor**
que `network.timeout`. É uma relação entre duas propriedades, e é conferível.

## 2. Escopo

**Dentro:**

1. Classificar o timeout de um run em uma de quatro categorias nomeadas —
   `wall_clock`, `broadcast`, `network`, `heartbeat` — a partir de evidência
   que já está nos facts, e recusar nomeadamente quando a evidência não separa.
2. Conferir a relação `heartbeatInterval < network.timeout` quando as duas
   chaves foram observadas.
3. Registrar em regra o princípio do §31: aumentar timeout **não** é conserto
   de performance quando há spill, skew, GC, perda de executor ou baixa
   utilização ao lado.

**Fora:**

1. **Recomendar um valor novo de timeout.** Derivar valor de configuração é o
   critério 17, é outro subprojeto, e entra com a proveniência por propriedade
   que o §36 pede — ou não entra.
2. **Classificar sem artefato.** Um run em `TIMEOUT` sem event log tem uma
   resposta honesta (`wall_clock`, que é a definição do estado) e nenhuma
   outra; inferir `network` de um log que ninguém leu seria inventar.
3. **Executar qualquer coisa.** A fronteira do projeto inteiro.

## 3. Decisões de desenho, com a alternativa recusada

### 3.1 A categoria é fact, e não julgamento

Está no precedente de `heap_oom_in_log`, que já é um atributo de
`spark.executor.lost`: ler a frase que o runtime escreveu e nomear o que ela
diz é **leitura de artefato**, não juízo. Não há limiar, não há severidade e não
há recomendação na derivação da categoria.

A alternativa recusada era pôr a categoria só dentro de um Finding. Ela perderia
o número no primeiro salto — o fact vai para `--out`, para a tool MCP e para o
contexto de um agente, e o Finding não vai.

O que é julgamento — "não suba o timeout, olhe o spill primeiro" — fica onde
julgamento mora: no catálogo de regras, com `evidence`, `validation` e
`rollback` como toda regra tem.

### 3.2 Uma categoria por run, e a ordem de precedência é declarada

Um run pode ter evidência de mais de um mecanismo: o executor morreu por
heartbeat **e** o run estourou o relógio do Glue. Escolher em silêncio seria
escolher pelo operador.

A precedência é do mais específico para o mais genérico, porque o mais genérico
é consequência do outro sempre que os dois aparecem:

```
heartbeat  >  network  >  broadcast  >  wall_clock
```

O fact carrega `attrs.category` com a escolhida **e** `attrs.also_seen` com as
outras, em ordem. Nada é descartado; o que foi preterido continua legível.

### 3.3 Sem evidência, `spark.timeout.unresolved` — nunca uma categoria default

Três recusas com nome próprio:

- `no_timeout_evidence` — nenhum sinal de timeout em fonte nenhuma.
- `state_without_log` — o run está em `TIMEOUT` e não há event log; a categoria
  é `wall_clock` e a lacuna registra que nada mais pôde ser separado.
- `conf_not_observed` — a relação do §3.4 não pôde ser conferida porque uma das
  duas chaves não apareceu em `spark.conf_effective`.

### 3.4 A relação entre as duas propriedades é conferível, e o valor isolado não é

`spark.network.timeout = 120s` não é certo nem errado sozinho. `heartbeatInterval
>= network.timeout` é errado sempre, porque quebra o mecanismo que detecta
executor morto. A regra confere a **relação**, e só quando as duas chaves foram
observadas no mesmo run.

### 3.5 O §31 é regra, e a lista de sintomas é a condição

`SF-TIMEOUT-001` não dispara por haver timeout: dispara por haver timeout **com
sintoma ao lado**. Sem sintoma, subir o timeout pode ser exatamente a decisão
certa — o documento diz isso por escrito, e a regra respeita.

## 4. Modelo

### 4.0 `spark.stage.failure`, a fonte que faltava

Emitido por `sparkforge/facts/event_log.py` quando `Stage Info` traz
`Failure Reason` não vazia. `subject` é o stage, `attrs.reason` é a frase
literal — passando pelo mesmo `redact` que `spark.conf_effective` usa, porque
razão de falha carrega URL de JDBC com senha dentro com a mesma facilidade que
configuração carrega.

O fact vale por si, e não só para timeout: é a primeira vez que a razão de uma
stage falhada entra no barramento.

### 4.1 `spark.timeout.diagnosis`

| campo | conteúdo |
|---|---|
| `subject` | `{type: job_run, symbol: <job_run_id ou app_id>}` |
| `attrs.category` | `wall_clock` \| `broadcast` \| `network` \| `heartbeat` |
| `attrs.basis` | a fonte que decidiu: `glue_job_run_state`, `executor_removed_reason`, `broadcast_exception`, `rpc_timeout` |
| `attrs.evidence_text` | o trecho literal do artefato, já redigido pelo mesmo caminho de `redact` |
| `attrs.also_seen` | as categorias preteridas, na ordem da precedência |

### 4.2 `spark.timeout.unresolved`

`attrs.reason` ∈ {`no_timeout_evidence`, `state_without_log`, `conf_not_observed`}, com `attrs.detail` dizendo o que preencheria a lacuna.

### 4.3 As duas regras

| id | dispara quando | severidade |
|---|---|---|
| `SF-TIMEOUT-001` | há `spark.timeout.diagnosis` **e** pelo menos um de: spill sobre input, razão p95/p50 de duração de task acima do limiar do catálogo, GC acima do limiar, `spark.executor.lost` | P1 |
| `SF-TIMEOUT-002` | `spark.executor.heartbeatInterval >= spark.network.timeout`, com as duas chaves observadas | P1 |

## 5. Superfície

Nenhum verbo novo. A categoria sai por `sparkforge analyze event-log` junto dos
outros facts do event log, e as duas regras saem por `sparkforge judge` como
qualquer outra. O documento pede uma skill `diagnose-spark-timeout`; ela entra
como skill que compõe os dois verbos que já existem, e não como quarto caminho
de código.

## 6. Erros, cada um com o seu nome

Ver §3.3. Nenhuma recusa é silenciosa e nenhuma vira zero.

## 7. Testes

### 7.1 Domínio de fixture próprio

`fixtures/timeout/`, com oito cenários:

| Cenário | Prova |
|---|---|
| `wall_clock_sem_event_log` | estado `TIMEOUT` sozinho: categoria `wall_clock`, lacuna nomeada |
| `heartbeat_perdido` | a frase do executor removido decide |
| `broadcast_estourado` | `broadcastTimeout` excedido no log |
| `network_futures_timeout` | timeout de RPC |
| `heartbeat_vence_wall_clock` | os dois presentes: precedência escolhe, `also_seen` preserva |
| `timeout_com_spill_e_skew` | `SF-TIMEOUT-001` dispara |
| `heartbeat_maior_que_network` | `SF-TIMEOUT-002` dispara |
| `timeout_sem_evidencia` | `no_timeout_evidence`, e nenhuma regra dispara |

### 7.2 As garantias sobre o corpus inteiro

1. Todo `spark.timeout.diagnosis` carrega `basis` **e** `evidence_text` não
   vazios — categoria sem a frase que a produziu é opinião.
2. Nenhum fact de diagnóstico existe sem sinal de timeout na entrada.
3. Nenhum campo do relatório recomenda um valor de timeout novo — o corpus
   inteiro é varrido em busca das palavras que denunciariam a recomendação.
4. Todo fact emitido passa por `validate_fact`.

## 8. Documentação

README (o kind novo e os números medidos de extratores e kinds), STATUS (a fase
e a auditoria atualizada), e o gate de números até `0 divergencia(s).`

## 9. Critérios de aceite

1. `spark.timeout.diagnosis` classifica as quatro categorias, cada uma provada
   por fixture.
2. A precedência é declarada e testada com os dois sinais presentes.
3. As três recusas têm nome e teste.
4. `SF-TIMEOUT-001` não dispara sem sintoma ao lado.
5. `SF-TIMEOUT-002` só dispara com as duas chaves observadas.
6. Nada no caminho novo recomenda valor de timeout.
7. Os dois ids novos são alcançados por golden, como o gate de cobertura exige.
