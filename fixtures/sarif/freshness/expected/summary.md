# SparkForge: findings deste commit

| Severidade | Findings | No Code Scanning | Sem localizacao no repositorio |
|---|---|---|---|
| P0 | 5 | 1 | 4 |
| P1 | 1 | 0 | 1 |

**Gate:** `--fail-on P0`: disparou.

## No Code Scanning (1)

| Severidade | Regra | Local | Titulo |
|---|---|---|---|
| P0 | SF-ERR-006 | `a/main.tf:24` | Permissão do Lake Formation negada em runtime, num job que lê o Data Catalog de outra conta |

## Fontes que pedem releitura (3)

| Severidade | Regra | Sujeito | Fonte | Estado | Datas |
|---|---|---|---|---|---|
| P0 | SF-ERR-006 | job_run `jr_lf1` | https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account.html | `stale` | validada 2026-08-15, mudou 2026-09-01 |
| P0 | SF-PLAN-003 | plan_node `(4) BroadcastNestedLoopJoin` | https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-hints.html | `aging` | conferida 2026-08-20 (22 dias) |
| P0 | SF-PLAN-003 | plan_node `(5) CartesianProduct` | https://spark.apache.org/docs/latest/sql-ref-syntax-qry-select-hints.html | `aging` | conferida 2026-08-20 (22 dias) |

1 finding(s) citam fonte nunca conferida por hash (`unverified`).

## Sem localizacao no repositorio (5)

| Severidade | Regra | Motivo | Sujeito | Titulo |
|---|---|---|---|---|
| P0 | SF-BENCH-001 | `evidencia_ausente` | job_run `different_input_volume` | Comparação entre execuções com volumes de entrada diferentes (medido: total_gc_ms_after=1500, total_gc_ms_before=1100, total_gc_ms_delta_pct=36.4, total_input_bytes_after=280000000, total_input_bytes_before=140000000, total_input_bytes_delta_pct=100.0, total_spill_bytes_after=0, total_spill_bytes_before=0, total_task_count_after=10, total_task_count_before=10, total_task_count_delta_pct=0.0, total_task_ms_after=37600.0, total_task_ms_before=22000.0, total_task_ms_delta_pct=70.9) |
| P0 | SF-PLAN-003 | `arquivo_fora_do_repo` | plan_node `(4) BroadcastNestedLoopJoin` | Join sem equi-condição — nested loop ou produto cartesiano |
| P0 | SF-PLAN-003 | `arquivo_fora_do_repo` | plan_node `(5) CartesianProduct` | Join sem equi-condição — nested loop ou produto cartesiano |
| P0 | SF-PY-004 | `caminho_ambiguo` | source_location `processar` | Action ou write dentro de loop (medido: loop_depth=1) |
| P1 | SF-CTM-001 | `sem_linha` | source_location `PagamentosDiarios/ExtraiExtrato` | Job usa capacidade que a versão declarada do Control-M Automation API não tem |
