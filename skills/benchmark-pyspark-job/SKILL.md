---
name: benchmark-pyspark-job
description: Use quando precisar comprovar — não estimar — o efeito de uma mudança de performance num job Glue, com comparação antes/depois de duração de stage, spill, GC e executor perdido, isolando uma variável por vez. Use também quando for escrever "X% mais rápido", "reduziu o shuffle pela metade", "resolveu o OOM" ou qualquer alegação quantificada de ganho. Se você está prestes a escrever um percentual de ganho sem rodar `sparkforge validate --findings`, pare — o schema rejeita `expected_effect` quantificado (%, x, vezes) sem `benchmark_ref`, e ganho previsto sem benchmark é invenção, não resultado.
---

# Benchmark PySpark Job

`sparkforge validate --findings` rejeita qualquer `expected_effect` que quantifique ganho (`"40% mais rápido"`, `"3x"`, `"2 vezes"`) sem um `benchmark_ref` que o sustente. É essa rejeição que dá sentido a esta skill: um benchmark é exatamente o que transforma uma alegação em algo defensável, e o par de medições antes/depois é o que vira `benchmark_ref`.

## Procedimento

1. **Antes da mudança:** `sparkforge collect event-log --repo . --job-run <id_antes> --bucket <bucket> --prefix <prefix> --now <ISO8601>`, depois `sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id_antes>.jsonl --out .sparkforge/baseline_facts.json`.
2. Aplique a mudança — uma variável principal por comparação. Duas mudanças juntas tornam a causa indistinguível.
3. **Depois da mudança:** repita coleta e extração para o novo run, gerando `.sparkforge/after_facts.json`.
4. Confirme runtime idêntico entre os dois runs com `sparkforge runtime detect` antes de comparar — Glue/Spark/Python/Iceberg diferentes invalidam a comparação.
5. **Compare stage a stage.** O extrator calcula a distribuição de cada run isoladamente; ele não diferencia dois arquivos entre si. Achar o mesmo stage dominante nos dois facts.json e comparar suas medidas é o seu trabalho.
6. Se houver variabilidade relevante entre execuções, repita a coleta (n ≥ 3) e reporte mediana e dispersão — uma única execução vira "ganho" por ruído.
7. Registre o achado com `expected_effect` (ex.: "42% mais rápido no stage dominante") e `benchmark_ref` apontando para os dois `job-run` ids ou os dois arquivos de facts comparados.
8. `sparkforge validate --findings .sparkforge/findings.json` — falha se algum `expected_effect` tem número quantificado sem `benchmark_ref` correspondente. Não contorne; é o gate do item 5 do `AGENT_PROTOCOL.md`.

## Referência rápida

| Fact | O que compara no antes/depois | Por que importa |
|---|---|---|
| `spark.stage.task_duration` | p50/p95/max do stage dominante | evidência primária de "ficou mais rápido" — não olhe só o máximo isolado |
| `spark.stage.task_input` | mesma distribuição em bytes | garante que os dois runs processaram volume comparável |
| `spark.stage.spill` | spill de memória e disco vs. input | ganho de tempo à custa de mais spill não é ganho líquido |
| `spark.stage.gc` | `gc_ms / executor_run_ms` | a mudança pode ter deslocado custo para GC em vez de eliminá-lo |
| `spark.executor.lost` | contagem e `heap_oom_in_log` | a mudança não pode trocar tempo por instabilidade |
| `spark.stage.task_count` vs `spark.cluster.cores` | paralelismo | a mudança não pode ter reduzido paralelismo pra parecer mais rápida |

Se qualquer `SF-UI-*` disparar em um dos dois runs, use `sparkforge rules lookup --id <ID>` para saber se a diferença cruza um limiar versionado — não decida "melhorou" por opinião.

## Validação de dados

Duração menor com resultado diferente não é uma otimização, é um bug. Confira sempre: schema e nullability, contagem de linhas, chaves e duplicidade, agregados de controle, hashes lógicos por partição, regras de negócio, e — se houve escrita Iceberg — partições e snapshot resultantes.

## Quando NÃO usar

- Ainda está diagnosticando o gargalo: use `analyze-spark-ui`, `diagnose-data-skew` ou `diagnose-oom` primeiro.
- Não há uma mudança concreta para medir: defina a hipótese e o experimento antes de benchmarcar.
- Precisa validar correção funcional em profundidade, não só o número: combine com `review-pyspark-pr`.

## Red flags

- Reportar percentual de ganho sem `benchmark_ref` — o `validate` pega isso, mas não conte só com o gate para não escrever a alegação em primeiro lugar.
- Comparar execuções em runtimes ou volumes de entrada diferentes.
- Medir uma única execução com variabilidade conhecida e chamar o resultado de conclusão.
- Aceitar uma mudança que melhora tempo mas altera contagem ou agregados de controle.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
