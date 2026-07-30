---
name: optimize-latest-per-key
description: Use quando o job calcula o registro mais recente por chave (row_number/Window, max_by, max(struct), join-back) sobre tabelas Spark/Iceberg grandes, e suspeitar de Window global sem partitionBy, sort/shuffle de todo o histórico, empates por timestamp mal tratados, late data ou recomputação a cada ciclo. Use também quando perguntarem "por que o latest demora tanto", "isso escala com o histórico inteiro" ou "o resultado muda entre execuções", mesmo sem citar Window ou row_number. Se você está prestes a inspecionar a chamada de Window de cabeça, rode `sparkforge analyze pyspark` e filtre por `pyspark.window` e `pyspark.chain` em vez disso — eles dizem se a Window tem partitionBy e onde o join entra na cadeia, mas não decidem se a chave escolhida é a correta: isso é julgamento seu.
---

# Optimize Latest Per Key

## O que o extrator responde e o que não responde

O extrator confirma **forma**: a `Window` tem `partitionBy`? Tem `orderBy`? O `join` de um join-back vem antes ou depois do `select`/`filter` que reduz o histórico? Isso é evidência mecânica, reproduzível, e é o ponto de partida.

O extrator **não** sabe se `partitionBy` usa a chave de negócio certa, se o desempate de timestamp é semanticamente correto, se late data é preservado, ou se `max(struct(...))` ordena as colunas do jeito que a regra de negócio espera. Isso é modelagem de domínio — a parte que continua sendo seu trabalho, não do extrator. Não finja que uma regra do catálogo decide isso por você.

## Procedimento

### 1. Extraia os facts

```bash
sparkforge analyze pyspark --path <arquivo-ou-diretório> --out .sparkforge/facts.json
```

### 2. Filtre pelas duas estratégias mais comuns

```bash
sparkforge analyze pyspark --path <arquivo> --kind pyspark.window --kind pyspark.chain --out .sparkforge/facts_latest.json
```

`pyspark.window` traz `attrs.has_partition_by`, `attrs.has_order_by`, `attrs.has_frame`. Uma `Window` **sem** `has_partition_by` é o pior caso possível: ela vira uma única partição lógica, e `row_number`/`rank` ordenam o histórico inteiro numa única task — o análogo, em memória de execução, de um `coalesce(1)`.

`pyspark.chain` traz `measures.join_index` e `measures.first_reduction_index` quando a cadeia tem join. Se a estratégia é agregação por `max(ts)` seguida de join-back, isso é literalmente o padrão que `SF-PY-003` julga: join antes de reduzir custa banda de shuffle por coluna e linha que serão descartadas.

### 3. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --glue <versão> --show-skipped
```

`SF-PY-003` cobre o join-back mal ordenado. Não existe regra estrutural própria para "Window sem partitionBy" no catálogo `SF-PY` — é um fact (`pyspark.window`) que você interpreta diretamente, não um `rule_id` pronto. Registre a leitura como hipótese com o `fact_id` do `pyspark.window`, não como se fosse um finding do catálogo.

### 4. Confirme com execução, se disponível

Forma correta no código não garante custo baixo — `partitionBy` presente ainda pode ser uma chave de baixa cardinalidade (poucas partições enormes) ou o histórico lido pode ser maior do que necessário. Se houver event log, `analyze-spark-ui` confirma shuffle read/write e spill do stage da Window; se não, isso fica registrado como hipótese não confirmada.

## Perguntas que o extrator não faz por você

- A coluna de desempate está definida, e o resultado é determinístico entre execuções com o mesmo dado?
- Registros com timestamp nulo ou timezone diferente entram no cálculo de "mais recente" corretamente?
- Correções retroativas (um evento antigo chega depois) mudam o resultado esperado, ou o job assume ordem de chegada = ordem de evento?
- O histórico completo precisa ser lido a cada execução, ou uma tabela current-state incremental resolveria sem reprocessar tudo?

Essas perguntas guiam qual das estratégias abaixo é apropriada — não há resposta genérica.

## Estratégias a comparar

- `row_number()` sobre `Window`: precisa de desempate e colunas do vencedor; correto exige `partitionBy` pela chave real e `orderBy` que resolva empate.
- `max_by(col, ts)`: mais barato para poucas colunas, mas semântica de empate e suporte variam por versão — confirme o runtime antes de usar.
- Agregação `max(ts)` + join-back: flexível, mas duplica linhas se houver empate não resolvido no lado agregado.
- Tabela current-state incremental: evita reprocessar o histórico inteiro a cada ciclo, mas exige idempotência e tratamento de late data — ver `design-incremental-processing`.
- Redução temporal segura (lookback): só quando o histórico completo comprovadamente não é necessário para correção.

## Quando NÃO usar

- Não é latest-per-key e sim skew genérico em join/agg: use `diagnose-data-skew`.
- O problema é a manutenção da tabela Iceberg em si (compactação, snapshots, delete files): use `optimize-iceberg-table`.
- Precisa desenhar todo o fluxo incremental ao redor do latest, não só a query em si: use `design-incremental-processing`.

## Referência rápida

| Fact | O que confirma | O que não confirma |
|---|---|---|
| `pyspark.window` (`has_partition_by`) | se a Window tem chave de particionamento declarada | se essa chave é a chave de negócio correta |
| `pyspark.window` (`has_order_by`, `has_frame`) | se há ordenação e frame declarados | se o desempate é semanticamente correto |
| `pyspark.chain` (`join_index` vs `first_reduction_index`) | se o join-back reduz antes ou depois do join | se o join-back duplica linhas em caso de empate |

## Red flags

- Aplicar `Window` global (sem `partitionBy`) sobre histórico grande e recomputar a cada execução.
- `max(struct(ts, ...))` sem garantir a ordem semântica correta das colunas dentro do struct.
- Ignorar empates de timestamp, timezone ou valores nulos ao definir "mais recente" — e não testar isso explicitamente.
- Tratar `has_partition_by: true` como prova de que o particionamento está correto, sem checar qual coluna é.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
