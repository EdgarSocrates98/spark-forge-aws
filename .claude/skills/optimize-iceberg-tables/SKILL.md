---
name: optimize-iceberg-tables
description: Use quando for necessario otimizar tabelas Apache Iceberg e catalogos.
---
# Iceberg Tables

Revise catalogo, locking, commits, snapshots, manifestos, schema evolution, particionamento, compaction, orphan files, S3FileIO e rollback.

## Quando NAO usar

Nao use quando o problema estiver fora do escopo.

## Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e rollback.

## Red flags

Loop sem parada, evidencia ausente, risco nao autorizado, custo nao medido e rollback inexistente.

## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
## Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

## Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.
