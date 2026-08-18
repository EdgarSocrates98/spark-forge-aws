---
name: optimize-athena-queries
description: Use quando for necessario otimizar consultas Athena, particionamento, Parquet, projection, federated query e custo.
---
# Amazon Athena

Use a especialidade para coletar evidencias, comparar alternativas, validar custo, risco, testes e rollback.

## Quando NAO usar

Nao use quando o problema estiver fora do dominio declarado.

## Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e proxima acao.

## Red flags

SELECT sem filtro, particao sem predicate, small files e bytes scanned nao medidos.

## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
## Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

## Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.
