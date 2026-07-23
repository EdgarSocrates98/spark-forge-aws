---
name: optimize-iceberg-table
description: Use quando tabelas Apache Iceberg no Glue Data Catalog degradam por excesso de data files pequenos, delete files, snapshots, manifests ou metadata growth, partition spec inadequado, falta de sort order, ou commits/merges frequentes, e precisa avaliar compaction, rewrite manifests, expire snapshots e retenção.
---

# Optimize Iceberg Table

## Compatibilidade primeiro

Leia `knowledge/runtime-compatibility.md`. Não use APIs/procedures sem confirmar suporte da versão embarcada ou dos JARs customizados.

## Diagnóstico

1. Identifique catalog, database, table, format-version e table properties.
2. Leia metadata tables disponíveis.
3. Avalie:
   - data file count e tamanhos;
   - delete files;
   - snapshots e frequência de commits;
   - manifests e metadata growth;
   - arquivos/bytes por partição;
   - partition spec e evolução;
   - sort order;
   - padrões de filtro;
   - append, merge, update e delete;
   - isolamento/conflitos de commit.
4. Diferencie:
   - problema de pequenos data files;
   - excesso de delete files;
   - excesso de manifests;
   - excesso de snapshots;
   - partições inadequadas;
   - falta de ordenação útil.

Use `knowledge/iceberg-diagnostics.sql` como ponto de partida.

## Manutenção

Considere, conforme suporte:
- rewrite data files/compaction;
- rewrite manifests;
- expire snapshots;
- remove orphan files;
- compactação de delete files;
- otimizadores gerenciados do Glue.

## Segurança

- Nunca expirar snapshots sem política de retenção.
- Nunca remover órfãos sem confirmar localização, idade mínima e concorrência.
- Não executar manutenção sobre tabela ativa sem avaliar conflitos.
- Preservar time travel e requisitos regulatórios.
- Propor dry run quando disponível.
- Produzir rollback ou explicar quando rollback não é possível.

## Particionamento

Baseie transform em filtros, volume por unidade, padrão de escrita e crescimento:
- identity;
- days/hours/months/years;
- bucket;
- truncate.

Não particionar apenas por cardinalidade. Use hidden partitioning e evolução quando aplicável.

## Saída

- Health score.
- Dívida de manutenção.
- Recomendações priorizadas.
- SQL/PySpark compatível.
- Política de execução e retenção.
- Benchmark.

## Quando NÃO usar

- A tabela é Parquet "puro" no S3 (sem metadados Iceberg): use `optimize-parquet-layout`.
- O foco é o cálculo latest-per-key sobre a tabela: use `optimize-latest-per-key`.
- Muitos commits vêm de um loop de batches na aplicação: veja `analyze-batch-loop`.

## Referência rápida

| Sintoma nas metadata tables | Dívida provável | Manutenção coerente |
|---|---|---|
| muitos `data_files` pequenos por partição | small files | rewrite data files (compaction) |
| `position/equality delete files` acumulando | leitura cara por merge-on-read | compactar deletes / rewrite |
| `manifests` crescendo sem parar | planning lento | rewrite manifests |
| centenas/milhares de `snapshots` | metadata growth, listagem cara | expire snapshots (com retenção) |
| bytes/partição muito desiguais | partition spec inadequado | rever transform / evolução de spec |
| filtros frequentes sem skipping | falta de sort order | definir sort order útil |

## Red flags

- Expirar snapshots ou remover órfãos sem retenção, idade mínima e checagem de concorrência.
- Usar procedure/propriedade da doc `latest` do Iceberg sem confirmar a versão embarcada pelo Glue.
- Rodar manutenção destrutiva sobre tabela ativa sem avaliar conflito de commit e sem rollback.
