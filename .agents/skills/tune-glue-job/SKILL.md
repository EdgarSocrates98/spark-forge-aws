---
name: tune-glue-job
description: Use quando ajustar workers, worker type, Auto Scaling, execution class, argumentos e observabilidade de um job Glue para custo/DPU-hours, depois de já ter baseline de CPU, heap, spill, shuffle e curva de executors. Não substitui diagnóstico de código e dados.
---

# Tune AWS Glue Job

## Coletar

- Glue version.
- Worker type.
- Workers mínimos/máximos.
- Auto Scaling.
- Execution class.
- Runtime e DPU-hours.
- Driver/executor CPU e heap.
- Shuffle e spill.
- S3 bytes read/write.
- Executors ativos e máximos necessários.
- Frequência, concorrência e SLA.

## Diagnóstico

Classifique:
- falta real de CPU;
- falta de memória;
- driver limitado;
- I/O/S3;
- paralelismo insuficiente;
- excesso de capacidade;
- skew;
- código/layout ineficiente.

## Regras

- Não aumentar workers para mascarar skew ou small files.
- Não reduzir workers apenas por baixa CPU sem avaliar espera de I/O.
- Auto Scaling deve ser analisado junto da curva de executors e duração dos stages.
- Configurações Spark devem ser compatíveis com o runtime do Glue.
- Alterações de executor cores/memory fora dos controles suportados pelo Glue devem ser tratadas com cautela.
- Compare tempo e DPU-hours, não somente runtime.

## Saída

- Configuração atual.
- Gargalo comprovado.
- Cenários conservador, balanceado e agressivo.
- Custo relativo esperado como hipótese.
- Experimento A/B.
- Critério de rollback.

## Quando NÃO usar

- Ainda não sabe o gargalo: comece por `sparkforge-diagnose` / `analyze-spark-ui`.
- O problema é código, layout Parquet/Iceberg ou skew: resolva a causa antes de mexer em workers.
- A revisão é da configuração declarada em IaC: use `review-glue-terraform`.

## Referência rápida

| Evidência da baseline | Interpretação | Ação de tuning coerente |
|---|---|---|
| CPU alta e sustentada, sem spill | CPU-bound real | mais workers / worker type maior |
| CPU baixa + muito I/O/listing | I/O ou small files | corrigir layout antes de escalar |
| curva de executors nunca atinge o máximo | Auto Scaling ocioso / superprovisão | reduzir teto; rever concorrência |
| spill alto com heap saturada | Memória por task | worker com mais memória OU menos dados/task |
| microcargas pagando cold start caro | custo fixo domina | perfil/curto-circuito (`optimize-variable-volume-job`) |

## Red flags

- Escalar workers para esconder skew, small files ou collect no driver.
- Copiar configs de Spark 4.x para Glue 5.x sem confirmar suporte (`knowledge/runtime-compatibility.md`).
- Comparar só runtime de parede e ignorar DPU-hours (custo).

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
