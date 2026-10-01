# Tabelas Iceberg, arquivos Parquet e small files

Este guia mostra como achar problemas de **layout**, ou seja, de como o dado está guardado:
tabela Iceberg com dívida acumulada, arquivos pequenos demais e Parquet que não deixa pular
dado. Todos os exemplos usam arquivos sintéticos da pasta `fixtures/` e foram rodados de verdade.

Os comandos rodam na raiz do repositório, no Git Bash. `sparkforge` é o comando instalado.
Se ele não for encontrado, troque por `python -m sparkforge.adapters.cli`.

## Receita rápida

```bash
# 1. pasta temporária e metadata tables do Iceberg
SAIDA=/tmp/sparkforge-guia; mkdir -p "$SAIDA"
sparkforge analyze iceberg --path fixtures/iceberg/delete_debt/input/dump.json --out "$SAIDA/facts_iceberg.json"
# 2. listagem do S3 (quantos arquivos e de que tamanho)
sparkforge analyze s3-listing --path fixtures/s3/small_files_prefix/input/listing.json --out "$SAIDA/facts_s3.json"
# 3. rodapé (footer) do Parquet
sparkforge analyze parquet-footer --path fixtures/parquet_footer/espalhado_com_filtro/input/footer.json --out "$SAIDA/facts_footer.json"
# 4. a consulta que lê a tabela
sparkforge analyze sql --path fixtures/parquet_footer/espalhado_com_filtro/input/query.sql --out "$SAIDA/facts_query.json"
# 5. julgue tudo junto
sparkforge judge --facts "$SAIDA/facts_iceberg.json" --facts "$SAIDA/facts_s3.json" \
  --facts "$SAIDA/facts_footer.json" --facts "$SAIDA/facts_query.json" --glue 5.0
```

O passo 5 devolve três achados: `SF-ICE-002` (dívida de delete files), `SF-PQ-008`
(estatística presente e inútil) e `SF-PQ-001` (small files).

## As cinco camadas do Iceberg (regra 9)

Uma tabela Iceberg não é só "os arquivos". Ela tem cinco camadas, e cada problema mora em uma delas:

| Camada | O que é | Sintoma típico |
|---|---|---|
| **Data files** | Os arquivos Parquet com as linhas | Leitura lenta, arquivos pequenos |
| **Delete files** | Arquivos que marcam linhas apagadas, sem reescrever o data file (modo merge-on-read) | Leitura lenta: cada leitura aplica as marcas |
| **Manifests** | Listas de quais data files e delete files existem | Planejamento lento, antes de ler |
| **Snapshots** | Versões da tabela; cada escrita cria uma | Muitos commits pequenos acumulam versões |
| **Metadata files** | O arquivo raiz que aponta para o snapshot atual | Planejamento lento |

Regra prática: planejamento lento aponta para manifests, snapshots ou metadata files. Leitura
lenta aponta para data files ou delete files. Compactar data files quando o problema é
metadata gasta DPU sem efeito.

Outros termos em uma frase:

- **Small files**: muitos arquivos pequenos. Cada arquivo tem custo fixo de abrir e listar.
- **Row group**: um bloco dentro do arquivo Parquet. O footer guarda o mínimo e o máximo de
  cada coluna por row group.
- **Pruning**: pular partes do dado que o filtro descarta, seja partição, arquivo ou row group.

Os termos do próprio SparkForge estão em [01-conceitos.md](../01-conceitos.md).

## Quando usar e quando não usar

Use quando a leitura de uma tabela é lenta, quando o planejamento demora ou antes de rodar
manutenção numa tabela Iceberg.

Não use para lentidão de código ou de shuffle: veja [job-lento.md](job-lento.md). Para
consulta no Athena, veja [athena-e-sql.md](athena-e-sql.md).

## Pré-requisitos: o que coletar

| Artefato | Como obter |
|---|---|
| Metadata tables do Iceberg (`files`, `delete_files`, `snapshots`, propriedades) | `sparkforge collect iceberg-metadata` (roda consulta no Athena, acessa AWS) |
| Listagem do prefixo no S3 | `aws s3api list-objects-v2` (AWS CLI), salvo em JSON |
| Footer do Parquet | `sparkforge collect parquet-footer` (lê só o rodapé; exige pyarrow; acessa o S3 se o prefixo for `s3://`) |
| A consulta que lê a tabela | O arquivo `.sql`, ou o `.py` com `spark.sql("...")` |

Estes comandos acessam AWS e não foram rodados neste guia. As flags do `collect` foram
conferidas no `--help`:

```bash
sparkforge collect iceberg-metadata --repo . --table <db.tabela> --workgroup <workgroup-athena> \
  --output-location <s3://bucket/resultados/> --now <ISO8601>
aws s3api list-objects-v2 --bucket <bucket> --prefix <prefixo/> > listing.json
sparkforge collect parquet-footer --repo . --prefix <s3://bucket/tabela/ ou pasta local> \
  --max-files 20 --now <ISO8601>
```

**Sobre o footer.** O `collect parquet-footer` lê só o rodapé dos primeiros arquivos pelo nome
(20 por padrão, teto de 500), sem nenhuma linha de dado, e registra o artefato no manifesto:
depois dele, o `scan` roda o `analyze parquet-footer` sozinho. Ele exige o pyarrow
(`pip install 'sparkforge-aws[parquet]'`). Sem o pyarrow, ou com prefixo vazio, inexistente ou
sem permissão, o artefato sai com um `status` que diz o motivo, em vez de erro.

## Passo a passo

### 1. Leia as metadata tables do Iceberg

```bash
sparkforge analyze iceberg --path fixtures/iceberg/delete_debt/input/dump.json --detail-level summary
```

```json
  "by_kind": {
    "iceberg.delete_files_summary": 1,
    "iceberg.files_summary": 1,
    "iceberg.format_version": 1,
    "iceberg.snapshots_summary": 1,
    "iceberg.table_analyzed": 1,
    "iceberg.table_property": 2
  },
  ...
    { "kind": "iceberg.delete_files_summary",
      "measures": { "delete_file_count": 10, "data_file_count": 50, "total_bytes": 500000, "content_unresolved": 10 },
      "symbol": "analytics.delete_debt_demo" },
    { "kind": "iceberg.files_summary",
      "measures": { "data_file_count": 50, "total_bytes": 10000000000, "avg_file_bytes": 200000000.0, ... } },
    { "kind": "iceberg.format_version", "measures": { "version": 2 } },
    { "kind": "iceberg.snapshots_summary", "measures": { "snapshot_count": 3, "span_hours": 720.0 } },
```

Cada camada vira um fact próprio: data files em `files_summary`, delete files em
`delete_files_summary` e snapshots em `snapshots_summary`.

### 2. Julgue a tabela

```bash
sparkforge analyze iceberg --path fixtures/iceberg/delete_debt/input/dump.json --out "$SAIDA/facts_iceberg.json"
sparkforge judge --facts "$SAIDA/facts_iceberg.json" --glue 5.0
```

Trecho real do achado:

```text
SF-ICE-002  P1  Dívida de delete files em tabela merge-on-read
  measured:  delete_file_count 10, data_file_count 50
  threshold: ratio 0.1
  proposed:  Compactar delete files com rewrite_position_delete_files, ou rewrite_data_files com reconciliação. ...
  risks:     Compactação de delete files é reescrita e consome DPU; agendar fora do horário crítico.
```

10 delete files para 50 data files dá razão 0,2, acima do limite de 0,1. Outros fixtures em
`fixtures/iceberg/` mostram as outras camadas:

| Fixture | Achado |
|---|---|
| `small_files` | `SF-ICE-001` (data files pequenos) e `SF-ICE-005` (`write.distribution-mode none` com particionamento) |
| `snapshot_churn` | `SF-ICE-003` (snapshots acumulados por commits frequentes) |
| `delete_debt` | `SF-ICE-002` (dívida de delete files) |

### 3. Conte os arquivos no S3

```bash
sparkforge analyze s3-listing --path fixtures/s3/small_files_prefix/input/listing.json --detail-level summary
```

```json
    { "kind": "s3.analyzed",
      "measures": { "object_count": 1501, "control_object_count": 1, "group_count": 1, "unresolved_count": 0 } },
    { "kind": "s3.prefix_summary",
      "measures": { "file_count": 1500, "total_bytes": 3146852250, "avg_file_bytes": 2097901.5, ... },
      "symbol": "s3://lake/analytics/eventos/ [parquet/snappy]" }
```

- O `_SUCCESS` de 0 byte conta como `control_object_count`, e não como arquivo de dados.
- 1500 arquivos de cerca de 2 MB disparam `SF-PQ-001`, "Small files na entrada", de severidade `P2`.
- Uma listagem cortada (`IsTruncated`) tem fixture própria: `fixtures/s3/truncated_listing`.

### 4. Veja se o Parquet deixa pular dado

```bash
sparkforge analyze parquet-footer --path fixtures/parquet_footer/espalhado_com_filtro/input/footer.json --out "$SAIDA/facts_footer.json"
sparkforge analyze sql --path fixtures/parquet_footer/espalhado_com_filtro/input/query.sql --out "$SAIDA/facts_query.json"
sparkforge judge --facts "$SAIDA/facts_footer.json" --facts "$SAIDA/facts_query.json" --glue 5.0
```

A consulta é `SELECT id, cat FROM curated.espalhado WHERE id = 42`. O achado:

```text
SF-PQ-008  P1  Estatística presente e inútil — row groups cobrem quase todo o domínio da coluna filtrada
  measured:  num_row_groups 3.0, stats_coverage 1.0, avg_range_coverage 0.9993..., expected_row_groups_scanned 2.9979...
  threshold: cobertura_maxima 0.5
  proposed:  Ordenar a escrita pela coluna filtrada (`sortWithinPartitions` no Spark, `write.sort-order` em Iceberg) e reescrever ...
```

- `avg_range_coverage` perto de 1 quer dizer que o mínimo e o máximo de cada row group cobrem
  quase todos os valores. A estatística existe, mas nenhum row group pode ser pulado.
- `expected_row_groups_scanned` perto de 3, com 3 row groups, quer dizer que a leitura passa por todos.
- Sem a consulta, a regra fica de fora. Rode só o footer com `--show-skipped` e aparece
  `{'rule_id': 'SF-PQ-008', 'reason': 'requires_facts', 'missing': ['sql.predicate']}`.
  Cobertura alta numa coluna que ninguém filtra não é defeito.
- `parquet.unresolved` com `reason: tipo_sem_dominio_numerico` aparece para uma coluna cujo
  tipo não tem ordem numérica. O SparkForge não calcula a medida onde ela não se sustenta.

### 5. Antes de subir o format version: `iceberg assess-upgrade`

`sparkforge iceberg` tem um subcomando só, `assess-upgrade`. Ele avalia subir o `format-version`
da tabela contra quem a consome e **não executa** nada.

Ele lê o inventário de consumidores em `.sparkforge/consumers.yaml`, dentro do diretório do job.
Exemplo com o inventário de `fixtures/consumers/v3_with_athena_consumer/input/consumers.yaml`,
copiado para uma pasta temporária:

```bash
mkdir -p "$SAIDA/job_pedidos/.sparkforge"
cp fixtures/consumers/v3_with_athena_consumer/input/consumers.yaml "$SAIDA/job_pedidos/.sparkforge/consumers.yaml"
sparkforge iceberg assess-upgrade --from 2 --to 3 "$SAIDA/job_pedidos"
```

```json
{
  "consumers": ["athena", "quicksight"],
  "target_spec_version": 3,
  "verdict": "BLOCKED",
  "cells": [
    ...
    { "feature": "variant", "engine": "athena", "status": "UNSUPPORTED",
      "source": "https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html",
      "note": "Tabela com 'format-version'='3' nao e lida pelo Athena SQL: \"Cannot read unsupported version 3\". ..." },
    ...
  ],
  "unresolved": [
    "athena: nenhuma fonte sobre `default_values` -- a matriz tem UNKNOWN, e UNKNOWN e desconhecimento declarado, nao ausencia de risco",
    ...
    "quicksight: consumidor declarado e AUSENTE da matriz -- nenhuma celula foi avaliada para ele, ..."
  ],
  "unevaluated_consumers": ["quicksight"],
  "source_spec_version": 2
}
```

- `verdict: BLOCKED`: o Athena não lê tabela em format V3, e o Glue 5.1 escreve V3.
- `UNKNOWN` não quer dizer "sem risco". Quer dizer que ninguém tem fonte sobre aquela feature.
- `unevaluated_consumers` lista quem nem entrou na conta.

## Nunca rode manutenção destrutiva sem confirmar (regra 10)

`expire_snapshots` e `remove_orphan_files` não têm rollback. Eles apagam o histórico
(time travel) e podem apagar arquivo em uso por uma escrita que está rodando ao mesmo tempo.
Eles também apagam o lado "antes" de qualquer comparação.

Antes de rodar qualquer um deles, confirme por escrito:

- **escopo**: qual tabela e qual intervalo;
- **retenção**: quantos dias de snapshot precisam continuar existindo, e quem depende deles.

O SparkForge só recomenda. Ele não roda manutenção.

## Erros comuns

- **Compactar data files quando o problema é planejamento.** Veja a camada certa primeiro.
- **Contar o `_SUCCESS` como arquivo.** O extrator já separa, mas uma conta feita à mão não separa.
- **Esperar `SF-PQ-008` sem a consulta.** Ela exige um `sql.predicate` no mesmo `judge`.
- **Subir para format V3 sem olhar os consumidores.** O job continua verde e o dashboard do
  Athena quebra dias depois.
- **Ler `unresolved` como erro.** É a lacuna nomeada: o SparkForge diz o que não sabe.

## Para ir além

- Agent de Iceberg: [iceberg-performance-engineer](../referencia/agents/iceberg-performance-engineer.md).
- Skills: [optimize-iceberg-table](../referencia/skills/optimize-iceberg-table.md),
  [optimize-parquet-layout](../referencia/skills/optimize-parquet-layout.md),
  [iceberg-v3-readiness](../referencia/skills/iceberg-v3-readiness.md).
- Referência dos comandos: [analyze](../referencia/cli/analyze.md), [iceberg](../referencia/cli/iceberg.md),
  [judge](../referencia/cli/judge.md), [collect](../referencia/cli/collect.md).
- Tools MCP: [sparkforge_analyze_iceberg](../referencia/tools/sparkforge_analyze_iceberg.md),
  [sparkforge_analyze_parquet_footer](../referencia/tools/sparkforge_analyze_parquet_footer.md),
  [sparkforge_analyze_s3_listing](../referencia/tools/sparkforge_analyze_s3_listing.md),
  [sparkforge_iceberg_assess_upgrade](../referencia/tools/sparkforge_iceberg_assess_upgrade.md).

## Próximos passos

1. Ache a camada do problema e corrija só ela.
2. Antes de reescrever a tabela, defina o que conferir no resultado com `sparkforge funcval plan`
   (veja a [referência do funcval](../referencia/cli/funcval.md)).
3. Se quem lê a tabela é o Athena, siga para [athena-e-sql.md](athena-e-sql.md).
