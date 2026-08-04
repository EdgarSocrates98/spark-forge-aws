---
name: benchmark-pyspark-job
description: Use quando precisar comprovar — não estimar — o efeito de uma mudança de performance num job Glue, com comparação antes/depois de duração de stage, spill, GC e executor perdido, isolando uma variável por vez. Use também quando for escrever "X% mais rápido", "reduziu o shuffle pela metade", "resolveu o OOM" ou qualquer alegação quantificada de ganho. Se você está prestes a escrever um percentual de ganho sem rodar `sparkforge validate --findings`, pare — o schema rejeita `expected_effect` quantificado (%, x, vezes) sem `benchmark_ref`, e ganho previsto sem benchmark é invenção, não resultado.
---

# Benchmark PySpark Job

`sparkforge validate --findings` rejeita qualquer `expected_effect` que quantifique ganho (`"40% mais rápido"`, `"3x"`, `"2 vezes"`) sem um `benchmark_ref` que o sustente. É essa rejeição que dá sentido a esta skill: um benchmark é exatamente o que transforma uma alegação em algo defensável, e o par de medições antes/depois é o que vira `benchmark_ref`.

O campo tem produtor desde a Fase 4a, e por isso deixou de ser texto livre: `benchmark_ref` cita o `fact_id` de um `bench.run_delta`, o fato que `sparkforge benchmark` emite ao comparar os facts de event log dos dois runs. Preencher o campo com prosa passou a ser rejeitado — satisfazer o gate digitando qualquer coisa era exatamente o que o campo permitia enquanto ninguém produzia a medição.

## Procedimento

1. **Antes da mudança:** `sparkforge collect event-log --repo . --job-run <id_antes> --bucket <bucket> --prefix <prefix> --now <ISO8601>`, depois `sparkforge analyze event-log --path .sparkforge/artifacts/eventlog/<id_antes>.jsonl --out .sparkforge/baseline_facts.json`.
2. Aplique a mudança — uma variável principal por comparação. Duas mudanças juntas tornam a causa indistinguível.
3. **Depois da mudança:** repita coleta e extração para o novo run, gerando `.sparkforge/after_facts.json`.
4. **Confirme runtime idêntico entre os dois runs** antes de comparar — Glue/Spark/Python/Iceberg diferentes invalidam a comparação. Isto deixou de ser conferência no olho: `runtime detect` aceita `--facts` (repetível) e cada event log declara a própria versão do Spark na primeira linha, extraída como `spark.runtime_version`.

   ```bash
   sparkforge runtime detect --facts .sparkforge/baseline_facts.json --facts .sparkforge/after_facts.json
   ```

   Leia `divergences`: **vazio é a condição de aceite** desta etapa. Se os dois runs rodaram em versões diferentes, aparece uma linha nomeando o componente e o valor de cada artefato (`spark: valores divergentes entre fontes (event_log:<a>=..., event_log:<b>=...)`), e a comparação está invalidada na origem — nenhum percentual medido depois disso vale como `benchmark_ref`. `detected_from` diz de quais fontes a detecção saiu; passe `--glue 5.1` apenas se souber a versão de fonte confiável e quiser preencher o eixo que o event log não preenche — o log declara `spark`, não `glue`, porque a matriz de compatibilidade deriva do Glue para o Spark e não o inverso.
5. **Compare os dois lados com o comparador, não no olho.** `sparkforge benchmark` (tool MCP `sparkforge_benchmark`) recebe os dois arquivos de facts e emite os cinco kinds `bench.*`:

   ```bash
   sparkforge benchmark \
     --before .sparkforge/baseline_facts.json \
     --after .sparkforge/after_facts.json \
     --out .sparkforge/bench_facts.json
   ```

   Ele **não executa nada** — não roda Spark, não chama AWS, não mede. Compara dois conjuntos que alguém já coletou. O que sai:

   - `bench.run_delta` — os totais dos dois lados e o percentual entre eles. É o fato que o `benchmark_ref` cita.
   - `bench.stage_delta` — o mesmo por stage, para os stages que casaram. O casamento é por `symbol` **idêntico**: `stage_id` não é estável entre execuções.
   - `bench.unmatched` — cada stage sem par do outro lado, com `attrs.reason` distinguindo renomeação (`symbol_absent_on_other_side`) de stage que o event log entregou sem nome (`empty_symbol`).
   - `bench.analyzed` — a sentinela com `matched_stage_count` e `unmatched_stage_count`.
   - `bench.unresolved` — o que ele **não** conseguiu comparar, nomeando a medida e o lado. Leia sempre: silêncio por medida ausente não é ausência de defeito.

   Uma chave `*_delta_pct` **ausente significa "não sei", nunca "zero"**. Ela é omitida quando o lado antes é zero (dividir por zero não produz "infinito por cento") e quando a medida falta ou está incompleta de um lado. Os totais observados ficam; o que cai é a razão entre eles.

   `total_task_ms` é **tempo de task somado** (`mean_ms * task_count` sobre os stages) — trabalho, não tempo de relógio. O event log lido não carrega duração wall-clock. Um job pode terminar antes no relógio somando mais tempo de task, ao paralelizar melhor. Confirme o relógio fora deste fluxo antes de reverter qualquer coisa.

6. **Julgue os facts `bench.*` contra o catálogo.** A área `SF-BENCH` tem quatro regras, e duas delas afirmam sobre a **validade da medição**, não sobre o job: `SF-BENCH-001` (volumes de entrada divergentes, P0) e `SF-BENCH-004` (parte grande dos stages sem par). Elas não calam as outras — leia as duas coisas juntas.

   ```bash
   sparkforge judge \
     --facts .sparkforge/bench_facts.json \
     --facts .sparkforge/baseline_facts.json \
     --facts .sparkforge/after_facts.json \
     --show-skipped
   ```

   Passe também os facts de event log dos dois lados, e não só os `bench.*`: é deles que o motor **infere** o runtime. Medido sobre `fixtures/bench/different_input_volume/`, o `judge` com os três arquivos devolve `runtime.spark` preenchido e `detected_from: ["event_log"]`; com o arquivo de benchmark sozinho o contexto sai vazio, `in_scope` falha fechada e 8 regras versionadas caem em `skipped` com `reason: "runtime_scope"`. Isso é o comportamento **correto**, não um bug — mas só é legível com `--show-skipped`, e sem ele "nenhum achado" e "não consegui avaliar" ficam indistinguíveis. `divergences` não vazio invalida a comparação na origem, e é achado próprio (`SF-ENV-001`). As quatro `SF-BENCH` não declaram versão nenhuma em `runtime_scope`, de propósito — a razão entre duas medidas do mesmo extrator é o que é em qualquer Spark —, então elas nunca são puladas por versão; quem é pulada é `SF-UI-*`, `SF-ENV-*` e companhia.

7. Se houver variabilidade relevante entre execuções, repita a coleta (n ≥ 3) e reporte mediana e dispersão — uma única execução vira "ganho" por ruído.
8. Registre o achado com `expected_effect` (ex.: "38% menos tempo de task somado") e `benchmark_ref` **citando o `fact_id` do `bench.run_delta`** — a forma é `f_` seguido de 6 dígitos hexadecimais, o `id` do fato que saiu do passo 5.
9. `sparkforge validate --findings .sparkforge/findings.json --facts .sparkforge/bench_facts.json` — sem `--facts`, o `benchmark_ref` é cobrado só na **forma**; com ele, o `fact_id` citado precisa **existir** naquele conjunto, e achado que cita medição ausente da evidência é rejeitado. Não contorne; é o gate do item 5 do `AGENT_PROTOCOL.md`.

## Referência rápida

| Fact | O que compara no antes/depois | Por que importa |
|---|---|---|
| `spark.stage.task_duration` | p50/p95/max do stage dominante | evidência primária de "ficou mais rápido" — não olhe só o máximo isolado |
| `spark.stage.task_input` | mesma distribuição em bytes | garante que os dois runs processaram volume comparável |
| `spark.stage.spill` | spill de memória e disco vs. input | ganho de tempo à custa de mais spill não é ganho líquido |
| `spark.stage.gc` | `gc_ms / executor_run_ms` | a mudança pode ter deslocado custo para GC em vez de eliminá-lo |
| `spark.executor.lost` | contagem e `heap_oom_in_log` | a mudança não pode trocar tempo por instabilidade |
| `spark.stage.task_count` vs `spark.cluster.cores` | paralelismo | a mudança não pode ter reduzido paralelismo pra parecer mais rápida |

O comparador já faz essa correlação e entrega o resultado em `bench.run_delta`, cujas cinco medidas saem nos dois lados mais o percentual entre eles:

| Medida em `bench.run_delta` | O que é | Regra que a lê |
|---|---|---|
| `total_task_ms` | soma de `mean_ms * task_count` — **trabalho**, não relógio | `SF-BENCH-002`, `SF-BENCH-003` |
| `total_input_bytes` | bytes lidos pelos stages dos dois lados | `SF-BENCH-001` |
| `total_spill_bytes` | spill de memória + disco | `SF-BENCH-003` |
| `total_gc_ms` | tempo de GC somado | `SF-BENCH-003` |
| `total_task_count` | tasks somadas — separa mudança de paralelismo de mudança de custo por task | leitura do operador |

E `bench.analyzed` carrega `matched_stage_count` / `unmatched_stage_count`, que é o que `SF-BENCH-004` lê para dizer se os totais estão somando o mesmo trabalho.

Se qualquer `SF-UI-*` disparar em um dos dois runs, use `sparkforge rules lookup --id <ID>` para saber se a diferença cruza um limiar versionado — não decida "melhorou" por opinião.

## Validação de dados

Duração menor com resultado diferente não é uma otimização, é um bug. Confira sempre: schema e nullability, contagem de linhas, chaves e duplicidade, agregados de controle, hashes lógicos por partição, regras de negócio, e — se houve escrita Iceberg — partições e snapshot resultantes.

## Quando NÃO usar

- Ainda está diagnosticando o gargalo: use `analyze-spark-ui`, `diagnose-data-skew` ou `diagnose-oom` primeiro.
- Não há uma mudança concreta para medir: defina a hipótese e o experimento antes de benchmarcar.
- Precisa validar correção funcional em profundidade, não só o número: combine com `review-pyspark-pr`.

## Red flags

- Reportar percentual de ganho sem `benchmark_ref` — o `validate` pega isso, mas não conte só com o gate para não escrever a alegação em primeiro lugar.
- Escrever prosa no `benchmark_ref` ("comparação dos runs A e B"). O campo cita um `fact_id`; texto livre é rejeitado, e era o que permitia satisfazer o gate digitando.
- Ler `total_task_ms` como duração e reverter a mudança por causa dele, sem conferir o relógio das duas execuções.
- Tratar `*_delta_pct` ausente como zero. Ausente é "não sei" — os totais dos dois lados continuam no fato, e é neles que se olha.
- Concluir sobre os totais com `SF-BENCH-001` ou `SF-BENCH-004` acesa: a medição não sustenta a conclusão, e nenhuma das duas cala as outras regras.
- Comparar execuções em runtimes ou volumes de entrada diferentes.
- Medir uma única execução com variabilidade conhecida e chamar o resultado de conclusão.
- Aceitar uma mudança que melhora tempo mas altera contagem ou agregados de controle.

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
