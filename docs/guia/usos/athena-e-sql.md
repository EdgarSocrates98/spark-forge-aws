# Consultas no Athena e SQL

Este guia é para quando o problema está na **consulta**, e não no job: uma consulta cara ou
lenta no Athena, ou um `spark.sql(...)` dentro do PySpark. Todos os exemplos usam arquivos
sintéticos da pasta `fixtures/` e foram rodados de verdade.

Os comandos rodam na raiz do repositório, no Git Bash. `sparkforge` é o comando instalado.
Se ele não for encontrado, troque por `python -m sparkforge.adapters.cli`.

## Receita rápida

O caso mais comum: você tem a consulta e o schema da tabela no catálogo.

```bash
# 1. pasta temporária e a consulta
SAIDA=/tmp/sparkforge-guia; mkdir -p "$SAIDA"; F=fixtures/fusion/limit_no_filter_with_catalog/input
sparkforge analyze sql --path $F/query.sql --out "$SAIDA/facts_sql.json"
# 2. o schema e as partições da tabela
sparkforge analyze catalog-schema --path $F/catalog.json --out "$SAIDA/facts_catalog.json"
# 3. cruze a consulta com o catálogo
sparkforge fuse --facts "$SAIDA/facts_sql.json" --facts "$SAIDA/facts_catalog.json" --out "$SAIDA/facts_fused.json"
# 4. julgue
sparkforge judge --facts "$SAIDA/facts_fused.json"
```

A consulta é `SELECT order_id, amount FROM sales.orders LIMIT 10`. O passo 4 devolve
`SF-ATH-002`, "LIMIT usado como se fosse filtro", de severidade `P2`.

## Termos em uma frase

- **Bytes escaneados**: quanto dado o Athena leu para responder. É por isso que o Athena cobra.
- **Partição**: uma pasta do dado separada por uma coluna, por exemplo `dt=2026-07-30`.
- **Pruning de partição**: pular as partições que o `WHERE` descarta. Sem pruning, a consulta
  lê a tabela inteira.
- **Projeção de coluna**: ler só as colunas pedidas. Em formato colunar (Parquet), `SELECT *`
  lê todas.
- **Workgroup**: um grupo de configuração do Athena, com versão do engine e limites.
- **Engine version**: a versão do motor do Athena (2 ou 3).
- **Partition projection**: o Athena calcula as partições a partir de uma regra, em vez de
  listar cada uma no catálogo.

Os termos do próprio SparkForge estão em [01-conceitos.md](../01-conceitos.md).

## Por que o `fuse` é necessário

"A consulta filtra a coluna de partição?" só tem resposta com duas fontes juntas. A consulta
diz o que foi filtrado, e o catálogo diz quais colunas são de partição. As regras `SF-ATH`
disparam sobre facts **fundidos**. Sem o `fuse`, elas ficam mudas.

Trecho real do arquivo fundido da receita:

```text
sql.projection           {'column_count': 2}  {'star': False, 'has_limit': True, 'table': 'sales.orders', 'table_format_columnar': None}
sql.projection.enriched  {'column_count': 2}  {'star': False, 'has_limit': True, 'table': 'sales.orders', 'table_format_columnar': True, ...}
fusion.summary           {'enriched_count': 1, 'unmatched_projection_count': 0, 'unmatched_predicate_count': 0, 'tables_known': 1}
```

Só o fact enriquecido sabe que a tabela é colunar. `unmatched_*` conta o que não achou tabela
no catálogo.

## Quando usar e quando não usar

Use quando a consulta é cara ou lenta, antes de mudar a versão do engine, ou antes de mudar o
formato de uma tabela que o Athena lê.

Não use para job Glue lento: veja [job-lento.md](job-lento.md). Para layout de arquivos, veja
[iceberg-e-parquet.md](iceberg-e-parquet.md).

## Pré-requisitos: o que coletar

| Artefato | Como obter |
|---|---|
| A consulta | O arquivo `.sql`, ou o `.py` com `spark.sql("...")` |
| Schema e partições da tabela | Um dump JSON do Glue Data Catalog (formato abaixo) |
| Configuração do workgroup | `sparkforge collect athena-workgroup` (acessa AWS) |
| Quem consome a tabela | Um inventário `consumers.yaml`, escrito por você |

```bash
sparkforge collect athena-workgroup --repo . --workgroup <nome-do-workgroup> --now <ISO8601>
```

Esse comando acessa AWS e não foi rodado neste guia. As flags foram conferidas no `--help`.
Nesta versão não há um `collect` para o dump do catálogo na lista de `sparkforge collect --help`.
O formato que o `analyze catalog-schema` lê é este, de `fixtures/fusion/limit_no_filter_with_catalog/input/catalog.json`:

```json
{
  "tables": [
    {
      "name": "sales.orders",
      "storage_format": "parquet",
      "partition_keys": [{"name": "dt", "type": "string"}],
      "columns": [
        {"name": "order_id", "type": "bigint"},
        {"name": "amount", "type": "double"},
        {"name": "dt", "type": "string"}
      ]
    }
  ]
}
```

## Passo a passo

### 1. `LIMIT` não é filtro

A receita rápida mostra o caso. `LIMIT 10` corta o resultado, e não a leitura: sem `WHERE`
na coluna de partição, o Athena varre a tabela inteira e cobra por ela. A consulta volta
rápido, e por isso o erro passa despercebido.

A mesma consulta com um `WHERE` real sobre `dt` não dispara a regra. Esse caso está em
`fixtures/fusion/limit_partition_filter_guard`.

### 2. `SELECT *` em tabela colunar

```bash
F=fixtures/fusion/select_star_parquet/input
sparkforge analyze sql --path $F/query.sql --out "$SAIDA/sel_sql.json"
sparkforge analyze catalog-schema --path $F/catalog.json --out "$SAIDA/sel_cat.json"
sparkforge fuse --facts "$SAIDA/sel_sql.json" --facts "$SAIDA/sel_cat.json" --out "$SAIDA/sel_fused.json"
sparkforge judge --facts "$SAIDA/sel_fused.json"
```

A consulta é `SELECT * FROM db.eventos`, e o catálogo diz que `db.eventos` é Parquet.
Resultado: `SF-ATH-001`, "SELECT * em tabela colunar", de severidade `P1`.

Rodando só `analyze sql` sobre um `SELECT *` (`fixtures/sql/select_star/input/query.sql`), sai
apenas `sql.analyzed` e `sql.projection`. O achado precisa do catálogo.

### 3. SQL dentro do PySpark

`--from-pyspark` lê o texto das chamadas `spark.sql("...")` de um arquivo `.py`, em vez de um `.sql`:

```bash
sparkforge analyze sql --from-pyspark fixtures/migration/table_format/input/job.py --detail-level summary
```

```json
  "by_kind": { "sql.analyzed": 1, "sql.unresolved": 1 },
  "unresolved": 1,
  "unresolved_at": [
    { "file": "job.py", "line": 6, "reason": "unparsed_clause" }
  ],
```

A linha 6 é um `ALTER TABLE ... SET TBLPROPERTIES`. O extrator não entendeu essa cláusula e
disse onde parou (`unparsed_clause`), em vez de adivinhar.

### 4. Tabela com partições demais

```bash
sparkforge analyze catalog-schema --path fixtures/catalog/overpartitioned_multi_table/input --out "$SAIDA/cat.json"
sparkforge judge --facts "$SAIDA/cat.json"
```

```json
    { "kind": "catalog.table_partitions",
      "measures": { "partition_count": 150000, "distinct_values": 150000 },
      "symbol": "db.cliques_sem_projection_a" },
```

O `judge` devolve `SF-ATH-003`, "Tabela com muitas partições Hive sem partition projection", de
severidade `P1`, duas vezes: uma para cada tabela sem partition projection. A terceira tabela
tem projection e fica de fora.

### 5. Versão do engine do workgroup

```bash
sparkforge analyze athena-workgroup --path fixtures/athena/engine_v2_outdated/input/workgroups.json --out "$SAIDA/ath.json"
sparkforge judge --facts "$SAIDA/ath.json"
```

```json
    { "kind": "athena.workgroup", "measures": { "engine_version": 2, "bytes_scanned_cutoff": 10995116277760 },
      "symbol": "legacy-etl" },
    { "kind": "athena.workgroup", "measures": { "engine_version": 3 }, "symbol": "primary" }
```

O `judge` devolve `SF-ATH-004`, "Workgroup em engine version anterior à 3", de severidade `P2`,
uma vez só, para o `legacy-etl`. `bytes_scanned_cutoff` é o limite de bytes por consulta
configurado no workgroup.

Trocar a versão do engine troca o motor que avalia as expressões. Valide o resultado antes e depois.

### 6. Quem consome a tabela

Glue 5.1 escreve Iceberg em format V3, e o Athena não lê V3. O job continua verde e quem quebra
é o consumidor. Declare os consumidores num inventário:

```yaml
consumers:
  - table: glue_catalog.curated.pedidos
    service: athena
    owner: squad-analytics
    note: dashboard executivo, consulta diaria
  - table: glue_catalog.curated.pedidos
    service: quicksight
    owner: squad-bi
```

```bash
F=fixtures/consumers/v3_with_athena_consumer/input
sparkforge analyze consumers --path $F/consumers.yaml --out "$SAIDA/cons.json"
sparkforge analyze iceberg --path $F/dump.json --out "$SAIDA/cons_ice.json"
sparkforge judge --facts "$SAIDA/cons.json" --facts "$SAIDA/cons_ice.json" --glue 5.1
```

Resultado: `SF-ENV-002`, "Tabela Iceberg em format V3 com consumo por Athena", de severidade `P0`.
Antes de subir o format version, rode também `sparkforge iceberg assess-upgrade` (veja
[iceberg-e-parquet.md](iceberg-e-parquet.md#5-antes-de-subir-o-format-version-iceberg-assess-upgrade)).

## Como ler o resultado

- **`severity`**: vai de `P0` (mais grave) a `P4`.
- **`subject`**: onde está o problema (arquivo e linha, tabela ou workgroup).
- **`measured`**: o que foi medido, por exemplo `column_count: 2`.
- **`proposed_change`, `risks`, `validation`, `rollback`**: o que fazer, o que pode dar
  errado, como conferir e como desfazer.
- **`unresolved` / `unresolved_at`**: o que o extrator não entendeu, com o motivo.
- **`fusion.summary.unmatched_*`**: partes da consulta que não acharam tabela no catálogo. Sem
  a tabela, a regra não tem como avaliar.

## Erros comuns

- **Rodar `judge` sem `fuse`.** As regras `SF-ATH` de consulta precisam dos facts fundidos.
- **Achar que `LIMIT` economiza.** Ele não reduz os bytes escaneados.
- **Trocar `SELECT *` por colunas e não avisar quem consome.** O schema do resultado muda.
- **Esquecer `--glue 5.1` no caso dos consumidores.** A regra depende da versão.
- **Esperar que o SparkForge rode a consulta.** Ele só lê texto e dumps. Nada é executado.

## Para ir além

- Agent do Athena: [athena-query-optimizer](../referencia/agents/athena-query-optimizer.md).
- Especialista: [athena-query-optimizer](../referencia/agents/athena-query-optimizer.md).
- Skills: [iceberg-v3-readiness](../referencia/skills/iceberg-v3-readiness.md),
  [optimize-parquet-layout](../referencia/skills/optimize-parquet-layout.md).
- Referência dos comandos: [analyze](../referencia/cli/analyze.md), [fuse](../referencia/cli/fuse.md),
  [judge](../referencia/cli/judge.md), [collect](../referencia/cli/collect.md).
- Tools MCP: [sparkforge_analyze_sql](../referencia/tools/sparkforge_analyze_sql.md),
  [sparkforge_analyze_catalog_schema](../referencia/tools/sparkforge_analyze_catalog_schema.md),
  [sparkforge_analyze_athena_workgroup](../referencia/tools/sparkforge_analyze_athena_workgroup.md),
  [sparkforge_analyze_consumers](../referencia/tools/sparkforge_analyze_consumers.md),
  [sparkforge_fuse](../referencia/tools/sparkforge_fuse.md).

## Próximos passos

1. Adicione `WHERE` na coluna de partição e troque `SELECT *` pelas colunas necessárias.
2. Se a tabela tem partições demais, avalie partition projection.
3. Se o problema for o layout dos arquivos, siga para [iceberg-e-parquet.md](iceberg-e-parquet.md).
