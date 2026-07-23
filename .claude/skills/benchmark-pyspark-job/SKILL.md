---
name: benchmark-pyspark-job
description: Use quando precisar comprovar (não estimar) o efeito de uma mudança de performance em um job Glue, com comparação antes/depois de runtime, DPU-hours, shuffle, spill, custo e validação funcional, isolando uma variável por vez.
---

# Benchmark PySpark Job

## Princípios

- Mesmo input ou amostra reprodutível.
- Mesma versão/runtime.
- Uma mudança principal por comparação.
- Múltiplas execuções quando variabilidade for relevante.
- Separar cold start de tempo de processamento quando possível.
- Não usar apenas tempo de parede.
- Validar dados.

## Baseline

Colete:
- runtime;
- DPU-hours;
- input/output rows e bytes;
- shuffle read/write;
- spill;
- GC;
- peak heap;
- output files;
- retries/failures;
- snapshot Iceberg;
- custo estimado.

## Validação

- schema e nullability;
- row count;
- chaves/duplicidade;
- agregados de controle;
- hashes lógicos por partição;
- regras de negócio;
- partições e snapshot.

## Estatística

Quando houver execuções repetidas, reporte:
- n;
- min;
- mediana;
- média;
- p95 quando aplicável;
- desvio/variação.

## Saída

Tabela antes/depois, variação percentual calculada, limitações, conclusão e decisão:
- aceitar;
- rejeitar;
- testar novamente;
- aceitar condicionalmente.

## Quando NÃO usar

- Ainda está diagnosticando o gargalo: use `sparkforge-diagnose` primeiro.
- Não há mudança concreta para medir: defina a hipótese/experimento antes.
- Precisa validar correção funcional em profundidade: combine com `review-pyspark-pr`.

## Referência rápida

| Erro comum de benchmark | Consequência | Correção |
|---|---|---|
| medir só uma execução | ruído vira "ganho" | n≥3; reportar mediana e variação |
| mudar 2+ variáveis juntas | causa indistinguível | isolar uma variável por comparação |
| incluir cold start no tempo | comparação injusta | separar startup de processamento |
| olhar só runtime | esconde custo | comparar também DPU-hours |
| ignorar validação de dados | ganho com resultado errado | conferir count, schema, chaves, agregados |

## Red flags

- Reportar percentual de ganho sem intervalo/variação quando há variabilidade.
- Aceitar mudança que melhora tempo mas altera contagem/agregados de controle.
- Comparar execuções em runtimes/inputs diferentes.
