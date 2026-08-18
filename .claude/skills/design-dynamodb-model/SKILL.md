---
name: design-dynamodb-model
description: Use quando for necessario modelar DynamoDB, chaves, access patterns, indexes, capacity, streams e consistencia.
---
# Amazon DynamoDB

Use a especialidade para coletar evidencias, comparar alternativas, validar custo, risco, testes e rollback.

## Quando NAO usar

Nao use quando o problema estiver fora do dominio declarado.

## Referencia rapida

Entrada: objetivo, workload, evidencias e restricoes. Saida: decisao, riscos, validacao e proxima acao.

## Red flags

Scan no caminho quente, partition key de baixa cardinalidade, hot key e item grande.

## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
## Quando NÃO usar

Nao use fora do escopo desta especializacao ou quando faltarem fatos e evidencias verificaveis.

## Referência rápida

Comece pelo diagnostico, consulte as fontes e regras aplicaveis, produza uma saida estruturada e valide o resultado antes do handoff.
