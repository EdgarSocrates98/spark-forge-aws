# SparkForge: findings deste commit

| Severidade | Findings | No Code Scanning | Sem localizacao no repositorio |
|---|---|---|---|
| P0 | 2 | 2 | 0 |
| P1 | 1 | 1 | 0 |

**Gate:** `--fail-on P0`: disparou.

## No Code Scanning (3)

| Severidade | Regra | Local | Titulo |
|---|---|---|---|
| P0 | SF-UI-001 | `jobs/lib/carga.py:7` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) -- linha da acao `save` que originou o stage 0 (nao e a causa) |
| P0 | SF-UI-001 | `jobs/lib/job.py:42` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) -- linha da acao `collect` que originou o stage 0 (nao e a causa) |
| P1 | SF-WASTE-002 | `jobs/lib/job.py:58` | Worker ocioso com skew extremo — reduzir capacidade não toca a causa (medido: disk_used_pct_p95=9.0, memory_used_pct_p95=22.0, skew_p95_over_p50=11.4, worker_utilization_p50=0.31) -- linha da acao `count` que originou o stage 3 (nao e a causa) |

## Sem localizacao no repositorio (0)

Todos os findings tem linha em arquivo do repositorio.
