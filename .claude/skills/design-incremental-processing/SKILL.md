---
name: design-incremental-processing
description: Use quando um job dito incremental continua lento mesmo com pouca entrada, faz scan global, recomputa estado histórico, ou você precisa projetar bootstrap, ciclos, backfill, late data, deletes e idempotência de forma que a entrada pequena realmente reduza bytes e arquivos lidos. Use também quando perguntarem "por que o incremental demora igual ao full", "isso é realmente incremental" ou "como eu desenho o reprocessamento disso", mesmo sem citar watermark ou bookmark. Se você está prestes a comparar full e incremental lendo os dois caminhos de código de cabeça, rode `sparkforge analyze pyspark` nos dois e compare os facts — mas saiba de antemão que o extrator mostra a forma do código, não se o volume lido caiu de fato: isso só o event log confirma.
---

# Design Incremental Processing

## O que a comparação de facts prova e o que não prova

Rodar o extrator nos dois caminhos (full e incremental) e comparar `pyspark.read`, `pyspark.chain` e `pyspark.write` mostra **forma**: os dois caminhos leem o mesmo `target`? O incremental filtra antes de qualquer redução, ou herda o mesmo plano do full com um filtro colado por cima? Isso é evidência estática, útil e barata.

O que a comparação de facts **não** prova é se, em execução, a entrada pequena de fato reduziu bytes lidos, arquivos planejados e registros antes dos exchanges. Um filtro que existe no código pode não chegar ao pushdown (cast implícito incompatível, UDF na condição, coluna sem ser a de partição) e o "incremental" lê tudo do mesmo jeito. Essa parte só o event log confirma — feche o loop com `analyze-spark-ui` ou `benchmark-pyspark-job` antes de declarar sucesso.

## Procedimento

### 1. Extraia os facts dos dois caminhos

```bash
sparkforge analyze pyspark --path <arquivo-ou-módulo-full> --out .sparkforge/facts_full.json
sparkforge analyze pyspark --path <arquivo-ou-módulo-incremental> --out .sparkforge/facts_incremental.json
```

Se full e incremental são branches do mesmo módulo (um `if is_full: ... else: ...`), um único `analyze pyspark` já captura os dois; separe por linha/função na leitura, não rode duas vezes o mesmo arquivo esperando facts diferentes.

### 2. Compare `pyspark.read`

Mesmo `attrs.target` nos dois caminhos, sem filtro de partição/coluna de controle na cadeia logo após, é o sinal mais forte de "incremental na entrada, full na execução": o incremental recebe menos linhas de origem mas o Spark ainda planeja ler a tabela inteira.

### 3. Compare `pyspark.chain` e `pyspark.join`

No caminho incremental, o filtro pela chave/janela de controle deveria aparecer **antes** de qualquer `join` ou `groupBy` na cadeia (`measures.first_reduction_index` baixo). Se o incremental faz join contra o histórico inteiro antes de filtrar, o volume do lado grande não caiu — o job só ficou com uma condição a mais no final. Isso é o mesmo raciocínio de `SF-PY-003`, aplicado à pergunta de desenho, não só à regra pontual.

### 4. Julgue cada caminho separadamente

```bash
sparkforge judge --facts .sparkforge/facts_incremental.json --glue <versão> --show-skipped
```

Um `pyspark.window` sem `partitionBy` no cálculo de current-state, ou um `pyspark.loop` escrevendo por lote, dentro do caminho "incremental" são sinais de que ele herdou os mesmos problemas do full — combine com `optimize-latest-per-key`/`analyze-batch-loop` quando aparecerem.

### 5. Teste central

> Uma entrada de 26 mil registros reduz bytes lidos, arquivos planejados, registros antes dos exchanges e arquivos reescritos?

Responda com número real (event log ou plano físico), não com leitura do código. Se a resposta é não, o fluxo é incremental apenas na entrada — reporte isso como o achado principal, não como detalhe.

## Investigar (além dos facts)

Origem das mudanças; watermark; coluna de controle; snapshots; chaves afetadas; late-arriving data; correções retroativas; deletions; idempotência; replay; backfill; full inicial; modo de escrita Iceberg. Nenhum desses tem fact dedicado — são perguntas de desenho que você registra e responde no contrato de saída abaixo.

## Contrato de saída

```yaml
incremental_design:
  source_of_changes:
  watermark:
  affected_keys:
  required_lookback:
  current_state_table:
  history_table:
  deduplication:
  late_data_policy:
  delete_policy:
  idempotency:
  replay_strategy:
  full_load_strategy:
  cyclic_load_strategy:
  backfill_strategy:
  failure_recovery:
  observability:
```

## Regras

- Não assumir que filtro por lista de chaves garante file pruning — confirme arquivos e bytes lidos.
- Preservar late data e correções retroativas na estratégia de lookback.
- Não usar bookmark do Glue como solução universal de incremental.
- Separar estratégia full e incremental quando as cargas forem radicalmente diferentes em volume ou forma.

## Quando NÃO usar

- A carga é sempre full/bootstrap homogênea, sem um caminho incremental separado: foque em `sparkforge-diagnose`/`tune-glue-job`.
- O gargalo é especificamente o cálculo do latest-per-key, não o desenho incremental ao redor: use `optimize-latest-per-key`.
- O "incremental" é um loop de batches na aplicação, não uma estratégia de leitura: veja `analyze-batch-loop`.

## Referência rápida

| Falso incremental (sintoma) | Causa provável | O que os facts mostram |
|---|---|---|
| entrada pequena, runtime igual ao full | scan global / recomputação | `pyspark.read` idêntico nos dois caminhos, sem redução antes de join/agg |
| filtra por lista de chaves mas lê tudo | sem file pruning real | filtro presente no `pyspark.chain`, mas pushdown não confirmado sem o plano |
| late data quebra o resultado | janela sem lookback | não visível nos facts — é pergunta de desenho, registre no contrato |
| replay duplica dados | escrita não idempotente | `pyspark.write` com `mode` incompatível com replay (ex.: `append` sem chave) |
| deletes não propagam | política de delete ausente | ausência de operação de delete/merge nos facts do caminho incremental |

## Red flags

- Tratar `job.commit()`/bookmark do Glue como solução universal de incremental.
- Confundir "entrada pequena" com "trabalho pequeno" sem medir bytes/arquivos lidos.
- Misturar estratégia full e incremental no mesmo código quando as cargas são radicalmente diferentes, sem separar os caminhos.
- Declarar o desenho correto só porque os facts têm a forma certa, sem fechar o loop com execução real.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
