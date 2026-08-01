---
name: optimize-parquet-layout
description: Use quando datasets Parquet no S3 (fora do Iceberg) sofrem com small files, listing lento, milhares de objetos por prefixo, arquivo por chave na escrita, ou leitura que não faz partition/predicate pushdown. Use também quando a pergunta for "o S3 tá cheio de arquivinho", "a leitura desse dataset demora antes mesmo da primeira task rodar" ou "cada execução gera um arquivo por cliente", mesmo que ninguém fale em Parquet. Se você está prestes a contar arquivo com `aws s3 ls` no olho, salve `aws s3api list-objects-v2` num arquivo e rode `sparkforge analyze s3-listing` — ele emite `s3.prefix_summary` e o `judge` aplica `SF-PQ-001`, `SF-PQ-003` e `SF-PQ-005`. Para o lado da leitura, `sparkforge analyze plan` emite `plan.file_scan` e cobre `SF-PQ-002` e `SF-PQ-004`; `analyze pyspark` e `analyze catalog-schema` fecham escrita e cardinalidade.
---

# Optimize Parquet Layout

Contar arquivo e medir listing no olho não escala e discorda entre analistas. As cinco regras `SF-PQ-*` têm extrator e são avaliáveis por `judge` — o que elas exigem de você não é trabalho manual, é **coleta**: nenhuma delas se responde a partir de código, e duas dependem de artefatos que só existem se alguém for buscar (a listagem do prefixo e o `explain` da leitura).

Seu trabalho é **coletar as quatro fontes, rodar, e ler `--show-skipped` para saber qual coleta faltou.**

## Procedimento

### 1. Escrita: extraia o padrão de particionamento do código

```bash
sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json --kind pyspark.write --kind pyspark.partitioning
```

`pyspark.write` traz modo e destino de cada escrita; `pyspark.partitioning` traz `coalesce`/`repartition`, se o argumento é literal, e o valor alvo. É aqui que aparece o writer por chave de alta cardinalidade e o `coalesce(1)` disfarçado de "arquivo único".

### 2. Armazenamento: liste o prefixo e extraia o sumário

Não existe `sparkforge collect s3-listing`, e isso é decisão de desenho, não lacuna: listar um prefixo grande custa uma chamada por 1000 objetos, e quem paga essa conta decide o escopo e a paginação com o olho no bucket. **Você coleta, o extrator lê.**

```bash
aws s3api list-objects-v2 --bucket <bucket> --prefix <prefixo> > listing.json
sparkforge analyze s3-listing --path listing.json --out .sparkforge/facts_s3.json
```

Sai um `s3.prefix_summary` **por grupo (formato, compressão)**, não um por prefixo: um prefixo real mistura Parquet com `_SUCCESS` de 0 byte e log em `.gz`, e um sumário único faria a média de bytes ser puxada pelo arquivo de controle — e `SF-PQ-003` (`format: text` + `compression: gzip`) nunca casaria num prefixo majoritariamente Parquet, mesmo com um `.gz` de 4 GB ali.

**Se a listagem voltou truncada, colete de novo.** Com `IsTruncated: true` o dump tem no máximo 1000 objetos de um prefixo que pode ter milhões; `file_count`, `avg_file_bytes` e `max_file_bytes` alimentam limiar direto, então o extrator **não emite sumário nenhum** — emite `s3.unresolved` com `reason: truncated_listing`, e nenhuma regra dispara. Pagine (`--continuation-token`, ou `--path` apontando para um diretório com as páginas) até a listagem fechar. Um `SF-PQ-001` ausente por listagem truncada não é "prefixo saudável".

### 3. Leitura: extraia o plano físico

```bash
sparkforge analyze plan --path <explain>.txt --out .sparkforge/facts_plan.json
```

`plan.file_scan` é o que responde as duas perguntas do lado da leitura: `SF-PQ-002` (tabela particionada com `PartitionFilters` vazio — está lendo tudo) e `SF-PQ-004` (razão entre colunas de `ReadSchema` e colunas referenciadas). Gere o `explain` com `df.explain("formatted")`; o procedimento completo, e o que fazer quando o Spark trunca a lista de campos, está em `analyze-spark-plan`.

### 4. Catálogo: confirme a cardinalidade real da partição

```bash
sparkforge analyze catalog-schema --path <dump-glue-catalog.json> --out .sparkforge/facts_catalog.json
```

Produz `catalog.table_partitions` (valores distintos, bytes médios por partição) — é o que `SF-PQ-005` consome para decidir se a cardinalidade é baixa demais (não filtra nada) ou alta demais (small files por desenho).

### 5. Execução: sintoma indireto no event log

```bash
sparkforge analyze event-log --path <log>.jsonl --out .sparkforge/facts_eventlog.json
```

`spark.stage.task_count` comparado a `spark.cluster.cores` (`SF-UI-006`) é o sinal indireto de small files do lado da leitura: contagem de tasks muito acima dos cores disponíveis, cada uma processando pouco dado, é a assinatura de ler muitos arquivos pequenos. É corroboração, não substituto: quem responde sobre o armazenamento é a listagem do passo 2.

### 6. Julgue

```bash
sparkforge judge \
  --facts .sparkforge/facts.json \
  --facts .sparkforge/facts_s3.json \
  --facts .sparkforge/facts_plan.json \
  --facts .sparkforge/facts_catalog.json \
  --facts .sparkforge/facts_eventlog.json \
  --show-skipped
```

`--facts` é repetível: informe todos os arquivos (pyspark, listagem S3, plano, catálogo, event log) na mesma chamada para ter todos os achados numa passada — `judge` une e deduplica antes de julgar. Regra que correlaciona fontes diferentes só dispara assim, e `SF-PQ-005` é exatamente isso: exige `s3.prefix_summary` **e** `catalog.table_partitions`, e nenhum dos dois responde sozinho.

Isso é também o que resolve a versão, sem você digitar nenhuma: unir os facts é unir as fontes de runtime junto. O event log do passo 5 declara a versão do Spark observada (`spark.runtime_version`); se você acrescentar `sparkforge analyze terraform`, o `glue_version` do `.tf` preenche `glue` e a matriz de compatibilidade deriva o resto. Leia o campo `runtime` da saída — ele traz o contexto efetivamente usado, `detected_from` diz de quais fontes saiu, e `divergences` aparece quando elas discordam.

Nenhuma das regras desta skill (`SF-PQ-*`, `SF-PY-005`, `SF-PY-010`) declara `runtime_scope`, então um `runtime` vazio não custa nada aqui: o que `--show-skipped` listar com `reason: runtime_scope` é infraestrutura Glue, e o que interessa nesta análise vai aparecer em `skipped` com `reason: requires_facts` — coleta que faltou, tratada na seção abaixo. Não confunda os dois motivos ao ler a lista. Use `--glue 5.1` apenas para declarar uma versão que você sabe de fonte confiável.

### 7. Interprete

## O que cada fact significa

| Fact | O que mede | Por que importa |
|---|---|---|
| `pyspark.write` | modo (append/overwrite) e destino de cada escrita | Ponto de partida para saber se a escrita é por lote, por chave, ou única |
| `pyspark.partitioning` | método (`coalesce`/`repartition`), se o argumento é literal, alvo | `coalesce(1)`/`repartition(1)` força tudo por uma task; alimenta `SF-PY-005` e `SF-PY-010` |
| `catalog.table_partitions` | valores distintos e bytes médios por partição | Cardinalidade baixa não filtra nada; cardinalidade alta é small files por desenho — os dois lados de `SF-PQ-005` |
| `s3.prefix_summary` | por grupo (formato, compressão): contagem, bytes médios e máximo | `SF-PQ-001` (small files), `SF-PQ-003` (`.gz` de texto não splitável) e metade de `SF-PQ-005` |
| `plan.file_scan` | tabela particionada, `PartitionFilters` vazio, colunas lidas vs. referenciadas | `SF-PQ-002` (lê tudo) e `SF-PQ-004` (lê coluna demais) |
| `spark.stage.task_count` | tasks do stage vs. `spark.cluster.cores` | Tasks muito acima dos cores, cada uma pequena, é sintoma indireto de arquivo pequeno na leitura |

## O limite real hoje: coleta, não extrator

As cinco `SF-PQ-*` têm extrator. O que elas não têm é o artefato **até você ir buscar**, e é aí que uma análise incompleta se disfarça de análise limpa:

- `SF-PQ-001` e `SF-PQ-003` só existem se houver uma listagem S3 completa. Sem ela, saem em `skipped` com `reason: requires_facts` e `missing: ["s3.prefix_summary"]`. Com ela truncada, o extrator emite `s3.unresolved` e o resultado é o **mesmo skip** — a diferença aparece no `unresolved` da saída de `analyze`, não no `judge`. Confira os dois.
- `SF-PQ-002` e `SF-PQ-004` só existem se alguém rodou `df.explain("formatted")` e salvou. `SF-PQ-004` some também quando o Spark truncou a lista de campos (`plan.unresolved`, `reason: truncated_field_list`), porque contar lista parcial infla a razão em silêncio.

A regra de leitura é uma só: **`skipped` com `reason: requires_facts` é coleta faltando, não ausência de problema.** `sparkforge rules lookup --id SF-PQ-001` devolve o limiar e a explicação para diagnóstico manual quando a coleta é inviável, mas isso é hipótese sua, não achado do motor.

## Referência rápida

| Regra | Fact que consome | O que acusa |
|---|---|---|
| `SF-PQ-001` | `s3.prefix_summary` (via `analyze s3-listing`) | Small files na entrada — média por arquivo abaixo do limiar com contagem alta |
| `SF-PQ-002` | `plan.file_scan` (via `analyze plan`) | Partition pruning ausente no plano físico — tabela particionada lendo tudo |
| `SF-PQ-003` | `s3.prefix_summary` (via `analyze s3-listing`) | Texto `.gz` não splitável — um arquivo, uma task, qualquer que seja o tamanho |
| `SF-PQ-004` | `plan.file_scan` (via `analyze plan`) | ReadSchema muito maior que o uso |
| `SF-PQ-005` | `s3.prefix_summary` **+** `catalog.table_partitions` | Cardinalidade de partição inadequada, alta ou baixa demais — exige as duas fontes |
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
- Tratar `SF-PQ-001`–`004` como "avaliadas, sem achado" quando na verdade a listagem ou o `explain` nunca foram coletados — elas saem em `skipped` com `reason: requires_facts`, e isso é coleta faltando, não prefixo saudável.
- Apresentar um `s3.prefix_summary` obtido de listagem truncada como número do prefixo: o extrator se recusa a emitir justamente para impedir isso, e recolher a listagem paginada é o único caminho.
- Compactar a cada escrita sem política de custo e frequência.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
