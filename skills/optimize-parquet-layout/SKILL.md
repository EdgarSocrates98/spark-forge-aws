---
name: optimize-parquet-layout
description: Use quando datasets Parquet no S3 (fora do Iceberg) sofrem com small files, listing lento, milhares de objetos por prefixo, arquivo por chave na escrita, ou leitura que não faz partition/predicate pushdown. Use também quando a pergunta for "o S3 tá cheio de arquivinho", "a leitura desse dataset demora antes mesmo da primeira task rodar" ou "cada execução gera um arquivo por cliente", mesmo que ninguém fale em Parquet. Se você está prestes a contar arquivo com `aws s3 ls` no olho, rode `sparkforge analyze pyspark` sobre o código de escrita e `sparkforge analyze catalog-schema` sobre o catálogo em vez disso — os extratores capturam o padrão de particionamento/escrita e a cardinalidade real da partição, e o catálogo aplica os limiares no que já tem extrator.
---

# Optimize Parquet Layout

Contar arquivo e medir listing no olho não escala e discorda entre analistas. Onde o projeto já tem extrator, ele resolve isso deterministicamente. Onde ainda não tem — e é o caso de parte deste catálogo, ver seção abaixo — o trabalho manual continua sendo necessário, e este documento diz exatamente qual parte é qual, para você não fingir automação que ainda não existe.

Seu trabalho é **coletar o que tem extrator, rodar, interpretar — e declarar honestamente o que ainda depende de leitura manual.**

## Procedimento

### 1. Escrita: extraia o padrão de particionamento do código

```bash
sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json --kind pyspark.write --kind pyspark.partitioning
```

`pyspark.write` traz modo e destino de cada escrita; `pyspark.partitioning` traz `coalesce`/`repartition`, se o argumento é literal, e o valor alvo. É aqui que aparece o writer por chave de alta cardinalidade e o `coalesce(1)` disfarçado de "arquivo único".

### 2. Catálogo: confirme a cardinalidade real da partição

```bash
sparkforge analyze catalog-schema --path <dump-glue-catalog.json> --out .sparkforge/facts_catalog.json
```

Produz `catalog.table_partitions` (valores distintos, bytes médios por partição) — é o que `SF-PQ-005` consome para decidir se a cardinalidade é baixa demais (não filtra nada) ou alta demais (small files por desenho).

### 3. Leitura: sintoma indireto no event log

```bash
sparkforge analyze event-log --path <log>.jsonl --out .sparkforge/facts_eventlog.json
```

`spark.stage.task_count` comparado a `spark.cluster.cores` (`SF-UI-006`) é o sinal indireto de small files do lado da leitura: contagem de tasks muito acima dos cores disponíveis, cada uma processando pouco dado, é a assinatura de ler muitos arquivos pequenos — mesmo sem um extrator de listagem S3 dedicado.

### 4. Julgue

```bash
sparkforge judge --facts .sparkforge/facts.json --glue <versão> --show-skipped
```

Rode uma vez por arquivo de facts (pyspark, catálogo, event log) ou consolide-os num único arquivo antes de julgar, se quiser todos os achados numa passada.

### 5. Interprete

## O que cada fact significa

| Fact | O que mede | Por que importa |
|---|---|---|
| `pyspark.write` | modo (append/overwrite) e destino de cada escrita | Ponto de partida para saber se a escrita é por lote, por chave, ou única |
| `pyspark.partitioning` | método (`coalesce`/`repartition`), se o argumento é literal, alvo | `coalesce(1)`/`repartition(1)` força tudo por uma task; alimenta `SF-PY-005` e `SF-PY-010` |
| `catalog.table_partitions` | valores distintos e bytes médios por partição | Cardinalidade baixa não filtra nada; cardinalidade alta é small files por desenho — os dois lados de `SF-PQ-005` |
| `spark.stage.task_count` | tasks do stage vs. `spark.cluster.cores` | Tasks muito acima dos cores, cada uma pequena, é sintoma indireto de arquivo pequeno na leitura |

## Um limite honesto do catálogo hoje

`SF-PQ-001` (small files na entrada), `SF-PQ-002` (partition pruning ausente no plano físico), `SF-PQ-003` (texto gzip não splitável) e `SF-PQ-004` (pruning de coluna ausente) dependem de `s3.prefix_summary` e `plan.file_scan` — facts que **nenhum extrator do projeto produz ainda**. Não existe `sparkforge analyze s3` nem `sparkforge analyze plan`; não invente esses comandos. `sparkforge rules lookup --id SF-PQ-001` continua devolvendo limiar e explicação — é conhecimento válido para diagnóstico manual — mas `sparkforge judge` não tem como avaliar essas quatro regras contra dado real hoje. Elas vão aparecer em `skipped` por falta de fact, e é assim que se distingue essa lacuna de "nenhum problema": leia `skipped`, não conclua "sem achado" quando o extrator simplesmente não existe ainda.

O que **é** avaliável agora com o toolkit: `SF-PQ-005` via `catalog.table_partitions`, e os sintomas de escrita via `SF-PY-005` e `SF-PY-010` no catálogo `pyspark` (categoria diferente de `SF-PQ`, mesmo efeito prático de small files).

## Referência rápida

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-PQ-001` | `s3.prefix_summary` (sem extrator ainda) | Small files na entrada — hoje só via `rules lookup`, não via `judge` |
| `SF-PQ-002` | `plan.file_scan` (sem extrator ainda) | Partition pruning ausente no plano físico — idem |
| `SF-PQ-003` | `s3.prefix_summary` (sem extrator ainda) | Texto `.gz` não splitável — idem |
| `SF-PQ-004` | `plan.file_scan` (sem extrator ainda) | ReadSchema muito maior que o uso — idem |
| `SF-PQ-005` | `catalog.table_partitions` | Cardinalidade de partição inadequada, alta ou baixa demais |
| `SF-PY-005` | `pyspark.partitioning` | `coalesce(1)` forçando tudo por uma task |
| `SF-PY-010` | `pyspark.partitioning` | `repartition(n)` com `n` literal arbitrário |

Não memorize os limiares — consulte com `sparkforge rules lookup --id <ID>`.

## Quando NÃO usar

- A tabela tem metadados Iceberg (data/delete files, manifests, snapshots): use `optimize-iceberg-table`.
- O desbalanceamento é hot key em join/agregação, não no layout de escrita: use `diagnose-data-skew`.
- Só quer ajustar workers ou argumentos do job: use `tune-glue-job`.
- Ainda não isolou se o layout de arquivo é mesmo o gargalo dominante: comece por `sparkforge-diagnose`.

## Red flags

- `coalesce(1)`/`repartition(1)` para "gerar um arquivo só" — é a causa mais comum de OOM disfarçado de otimização.
- Definir um "tamanho ideal de arquivo" universal sem considerar SLA, engine, concorrência e custo de listing — fica em `knowledge/storage/parquet-layout.md`, não decore um número aqui.
- Tratar `SF-PQ-001`–`004` como "avaliadas, sem achado" quando na verdade `judge --show-skipped` não rodou ou não mostrou o motivo do skip — confirme antes de dizer "sem achado".
- Compactar a cada escrita sem política de custo e frequência.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
