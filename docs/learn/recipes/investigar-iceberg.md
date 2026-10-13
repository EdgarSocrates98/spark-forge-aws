# Receita — investigar uma tabela Iceberg

**O quê:** `analyze iceberg` resume o dump das metadata tables — data
files, delete files, snapshots, manifests, partições — e o `judge` aplica
a área SF-ICE; `analyze s3-listing` e `analyze parquet-footer` cobrem o
layout fora do catálogo.
**Por que:** a dívida de Iceberg é física e acumulativa (arquivo pequeno,
delete file, manifest crescendo): ler a tabela no olho não mede nada
disso; o extrator mede deterministicamente.
**Quando:** consulta lenta no Athena, excesso de small files, delete
files acumulados, manutenção (compaction/expire) por evidência e não por
rotina.
**Quando não:** performance de job — o gargalo de execução é o event log;
o Iceberg responde sobre layout e metadados.

## Problema

"Esta tabela Iceberg está degradada — onde, e o que manter primeiro?"

## Pré-requisitos

Dump das metadata tables (`collect iceberg-metadata`) ou um dump já em
disco; listagem S3 para o lado de objetos.

## Passo a passo

```bash
# 1) facts das metadata tables
sparkforge-aws analyze iceberg --path dump_iceberg.json \
  --out .sparkforge_aws/facts_iceberg.json

# 2) layout físico no S3 (small files reais)
sparkforge-aws analyze s3-listing --path listing.json \
  --out .sparkforge_aws/facts_s3.json

# 3) julgar as fontes juntas
sparkforge-aws judge --facts .sparkforge_aws/facts_iceberg.json \
  --facts .sparkforge_aws/facts_s3.json \
  --out .sparkforge_aws/findings.json
```

## Saída esperada / interpretação

Findings da área `SF-ICE` (dívida de delete/data files, snapshots,
manifests) e `SF-PQ` (small files, estatística inútil), cada um com os
`fact_id` de evidência — ex.: `SF-ICE-002` (dívida de delete files),
`SF-PQ-001` (small files).

## Verificação

```bash
sparkforge-aws next-step --repo . --findings .sparkforge_aws/findings.json
# achado dominante SF-ICE → iceberg-performance-engineer
```

## Limitações

- O extrator resume o dump que recebe — dump velho é diagnóstico velho;
  o `collect` existe para refrescar.
- `analyze iceberg` não mede tempo de consulta — latência de Athena é
  `analyze sql` + workgroup, outro eixo.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| facts `iceberg.*` vazios | dump não é das metadata tables | `collect iceberg-metadata` produz o formato certo |
| só achados SF-PQ | listagem sem prefixo da tabela | aponte o listing do diretório da tabela |

## Uso por agentes

Skills: `optimize-iceberg-table` (manutenção por evidência),
`optimize-parquet-layout` (layout fora do catálogo),
`iceberg-v3-readiness` (upgrade de format version),
`athena-query-optimizer` para o lado da consulta.

## Leitura seguinte

- [iceberg-e-parquet](../../guia/usos/iceberg-e-parquet.md) — guia profundo,
  receita rápida com fixtures
- [avaliar-performance](avaliar-performance.md)
