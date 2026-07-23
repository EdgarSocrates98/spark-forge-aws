---
name: diagnose-data-skew
description: Use quando uma ou poucas tasks demoram muito mais que a mediana, há spill localizado, uma chave/partição concentra os dados, ou joins, agregações, windows e particionamento ficam desbalanceados por hot keys, nulls ou valores default.
---

# Diagnose Data Skew

## Medidas

Calcule quando possível:

- total de linhas;
- distinct keys;
- null percentage;
- top keys;
- max, p50, p95 e p99 rows/key;
- max/median ratio;
- participação da maior chave;
- distribuição de bytes/linhas por partition;
- coefficient of variation.

## Diagnóstico semântico

Antes de alterar a distribuição, entenda:
- o significado de null/UNKNOWN/default;
- duplicidade esperada;
- relacionamento 1:1, 1:N ou N:N;
- se hot keys podem ser processadas separadamente;
- se pré-agregação preserva o resultado.

## Estratégias em ordem de simplicidade

1. Filtrar/reduzir dados cedo.
2. Corrigir chave ou regra de negócio.
3. Broadcast do lado pequeno.
4. Pré-agregar.
5. Usar AQE skew join quando suportado e comprovado.
6. Separar hot keys.
7. Salting seletivo.
8. Reprojetar a operação.

## Salting

Nunca aplique salting global sem:
- identificar hot keys;
- escolher número de salts por evidência;
- replicar apenas o lado necessário;
- estimar expansão;
- validar duplicidade e semântica.

## Saída

- Métricas de distribuição.
- Chaves críticas.
- Operação afetada.
- Estratégias comparadas.
- Código proposto.
- Benchmark e validação.

## Quando NÃO usar

- A task gigante vem de sub-paralelismo ou small files, não de uma chave quente: veja `analyze-spark-ui` / `optimize-parquet-layout`.
- O desbalanceamento é de arquivos por partição na escrita: use `optimize-parquet-layout` ou `optimize-iceberg-table`.
- Ainda não confirmou skew no Spark UI: comece por `analyze-spark-ui`.

## Referência rápida

| Sinal | Limiar indicativo | Ação preferida |
|---|---|---|
| max/median rows por chave | > 3–5 | tratar hot keys / pré-agregar |
| participação da maior chave | domina o stage | separar hot key; broadcast do outro lado |
| null/default em chave de join | alto | filtrar/segregar nulls antes do join |
| AQE `skewedPartitions` no plano final | presente | validar se já mitigou; medir residual |
| expansão pós-salting | estimar antes | limitar nº de salts; replicar 1 lado só |

## Red flags

- Aplicar salting global sem identificar as hot keys.
- Usar `repartition` achando que corrige skew (redistribui uniformemente, não a chave quente).
- Alterar a chave/regra de join sem validar duplicidade e semântica do resultado.
