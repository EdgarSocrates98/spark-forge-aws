# Layout Parquet e S3

## 1. Estrutura de um arquivo Parquet

```
arquivo
└─ row group          (unidade de paralelismo de leitura e de estatística)
   └─ column chunk    (uma coluna dentro do row group)
      └─ page         (unidade de compressão e encoding)
         └─ dictionary page  (quando dictionary encoding é usado)
```

Metadados no **footer**: schema, offsets, e **estatísticas por coluna por row group** (min, max, null_count).

Consequências que decidem performance:

- **Pruning acontece em nível de row group**, usando as estatísticas do footer. Se min/max de um row group não excluem o predicado, o row group inteiro é lido.
- Ler o footer exige um round-trip a S3 por arquivo. 100.000 arquivos = 100.000 round-trips só para planejar.
- Row group grande demais aumenta memória por task; pequeno demais aumenta overhead de metadados. Alvo usual: 128–512 MB de arquivo, com row group na casta de 128 MB.

## 2. Por que sort order determina o pruning

Estatística min/max só é útil se os valores estiverem **agrupados**. Dado ordenado aleatoriamente faz cada row group ter min/max cobrindo quase todo o domínio → nenhum row group pode ser descartado → pruning inútil apesar de existir estatística.

Exemplo: tabela de 1 bilhão de linhas com `cliente_id` aleatório. Cada row group contém ids de 1 a 9.999.999. Filtro `cliente_id = 42` lê tudo.

A mesma tabela ordenada por `cliente_id`: cada row group cobre uma faixa estreita, e o filtro lê poucos row groups.

Isso é o que faz **sort order** ser alavanca de performance, não estética. Ordenar pela coluna que aparece nos filtros mais frequentes é frequentemente o maior ganho disponível numa tabela grande e já bem particionada.

Ordem de decisão: partição para os filtros de alta seletividade e baixa cardinalidade (data); sort order para os filtros de alta cardinalidade (id, chave de negócio).

## 3. Small files

O problema tem quatro custos distintos, e confundi-los leva à correção errada:

| Custo | Onde dói | Métrica |
|---|---|---|
| Listing | driver, no planejamento | tempo antes da primeira task; `partitionsRead` |
| Abertura de arquivo | executor | `openCostInBytes` (4 MB por arquivo no cálculo) |
| Overhead de task | scheduler | milhares de tasks de milissegundos |
| Metadados | driver heap | plan explosion, driver OOM |

`spark.sql.files.openCostInBytes = 4MB` significa que **um arquivo de 10 KB é contado como 4 MB** no empacotamento de partições. Com 100.000 arquivos minúsculos, o planejador raciocina sobre ~400 GB virtuais.

Mais workers **não corrige** small files. O gargalo é contagem de objetos e round-trips, não CPU. É a linha da tabela em `../glue/workers-and-capacity.md` §2 onde capacidade é a resposta errada.

### Causas de small files

1. `spark.sql.shuffle.partitions` alto com volume pequeno → N arquivos por partição de saída.
2. Escrita incremental frequente (append de poucos minutos) sem compactação.
3. `partitionBy` de alta cardinalidade → poucas linhas por partição.
4. Loop escrevendo lote por lote.
5. Streaming com micro-batch curto.

### Correções

| Correção | Quando |
|---|---|
| `REBALANCE` hint antes da escrita | quer arquivos equilibrados sem chutar `n` |
| `repartition(n)` calculado a partir do volume | conhece o volume-alvo por arquivo |
| Compactação periódica (job separado) | escrita incremental frequente |
| Reduzir cardinalidade de partição | `partitionBy` errado |
| Escrever uma vez em vez de por lote | loop de escrita |

**Nunca `coalesce(1)`.** Ele não faz shuffle, então força todo o dado por uma única task — memória e duração explodem. Para "poucos arquivos", `repartition(n)` com `n` calculado, ou compactação posterior.

## 4. Compressão

| Codec | Razão | CPU | Splitável |
|---|---|---|---|
| Snappy | média | baixa | sim (dentro do Parquet) |
| ZSTD | alta | média | sim |
| GZIP | alta | alta | sim dentro do Parquet; **não** para arquivos `.gz` de texto |
| Nenhuma | — | — | sim |

Dentro do Parquet, a compressão é por página e não afeta splitabilidade — o arquivo continua legível por row group.

O caso de não-splitabilidade é **arquivo de texto** `.gz` / `.csv.gz`: um arquivo = uma task, sempre. Um `.csv.gz` de 20 GB é uma task de 20 GB, e nenhum aumento de paralelismo ajuda. É a causa clássica de "poucas tasks longas" no Spark UI.

Snappy é o default razoável. ZSTD ganha quando o custo de armazenamento e de bytes escaneados (Athena) domina o de CPU.

## 5. Layout de partição S3

| Decisão | Efeito |
|---|---|
| Coluna de partição = coluna dos filtros reais | habilita pruning; sem isso não há pruning possível |
| Cardinalidade muito baixa (3 valores) | partição não filtra nada |
| Cardinalidade muito alta (id) | explosão de metadados, small files |
| Partição por data (`dt=YYYY-MM-DD`) | caso mais comum e geralmente correto |
| Muitos níveis aninhados | listing lento, metadados grandes |
| Tipo da coluna de partição inconsistente com o filtro | pruning silenciosamente ausente |

O último item é a falha mais difícil de ver: partição `dt` como `string`, filtro como `date` (ou vice-versa). O `cast` implícito pode impedir o pruning sem erro nenhum. **Verificar no plano físico**, no campo `PartitionFilters`, nunca no código.

Alvo prático de partição: cada partição com volume suficiente para produzir arquivos de 128–512 MB. Partição que produz 3 MB é small file por construção.

## 6. Diagnóstico

1. Contar arquivos e obter tamanho médio, p50 e p95 por partição.
2. Comparar tamanho médio com 128 MB.
3. Medir tempo do driver antes da primeira task (proxy de listing).
4. Ler `PartitionFilters` e `PushedFilters` no plano físico — confirmar que o pruning existe.
5. Comparar bytes lidos com tamanho total da tabela — razão de pruning efetivo.
6. Checar não-splitabilidade (`.gz` de texto) se houver poucas tasks longas.
7. Verificar sort order vs. colunas de filtro de alta cardinalidade.

Passo 5 é o número que resume tudo: se o job lê 100% da tabela para produzir 1% do resultado, o problema é layout ou pushdown, não capacidade.

## Fontes

- Apache Spark 3.5.6 — SQL Performance Tuning (`spark.sql.files.maxPartitionBytes` 128 MB, `openCostInBytes` 4 MB, configs de parallel partition discovery, hint `REBALANCE`). https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html (retrieved 2026-07-29)
- Top 10 performance tuning tips for Amazon Athena (formato colunar, particionamento, compressão). https://aws.amazon.com/blogs/big-data/top-10-performance-tuning-tips-for-amazon-athena (retrieved 2026-07-29)
- Alvos de 128–512 MB por arquivo e ~128 MB por row group são heurística de campo amplamente adotada, não valor normativo. Ajustar ao workload e medir.
