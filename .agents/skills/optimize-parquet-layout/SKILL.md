---
name: optimize-parquet-layout
description: Use quando datasets Parquet no S3 sofrem com small files, listing lento, muitos objetos, falta de partition/predicate pushdown, schema merge caro, arquivos desbalanceados por partição ou escrita gerando um arquivo por chave.
---

# Optimize Parquet Layout

## Leitura

Verifique:
- projection pruning;
- predicate pushdown;
- partition pruning;
- schema explícito;
- mergeSchema;
- codec;
- número de objetos listados;
- tamanhos dos arquivos;
- distribuição por partição;
- compatibilidade de schema.

## Escrita

Analise:
- volume total comprimido;
- número de partições Spark;
- número esperado de arquivos;
- distribuição das chaves;
- cardinalidade da partição física;
- consumidores e padrões de filtro;
- concorrência de escrita;
- codec e custo CPU/I/O.

## Small files

Calcule:
- file count;
- bytes totais;
- avg, p50, p95;
- percentual abaixo de limites definidos pelo workload;
- arquivos por partição;
- desvio entre partições.

Não declare um tamanho universal. Use SLA, volume, engine, concorrência, custo de listing e paralelismo.

## Recomendações possíveis

- compactação controlada;
- repartition por colunas adequadas antes da escrita;
- redução da cardinalidade de diretórios;
- mudança do padrão de ingestão;
- batch maior;
- evitar um writer por registro/chave;
- sortWithinPartitions quando beneficiar compressão/skipping.

## Validação

- bytes lidos;
- tempo de listing/planning;
- tasks;
- runtime;
- output file count;
- tamanho médio;
- pruning;
- custo S3.

## Quando NÃO usar

- A tabela é Apache Iceberg (data/delete files, manifests, snapshots): use `optimize-iceberg-table`.
- O desbalanceamento é por hot key em join/agg, não na escrita: use `diagnose-data-skew`.
- Só quer ajustar workers/argumentos: use `tune-glue-job`.

## Referência rápida

| Observação | Sinal | Direção |
|---|---|---|
| milhares de arquivos pequenos por partição | avg << alvo do workload | compactar; repartition antes de escrever |
| planning/listing longo antes das tasks | muitos objetos no prefixo S3 | reduzir nº de arquivos / diretórios |
| filtro não reduz bytes lidos | sem partition/predicate pushdown | particionar por coluna de filtro; schema explícito |
| um arquivo por chave na saída | writer por chave de alta cardinalidade | repartition por coluna de menor cardinalidade |
| leitura lê colunas demais | sem projection pruning | selecionar colunas; evitar `select("*")` |

## Red flags

- Definir um "tamanho ideal de arquivo" universal sem considerar SLA/engine/concorrência.
- `coalesce(1)`/`repartition(1)` para gerar arquivo único.
- Compactar a cada escrita sem política de custo e frequência.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
