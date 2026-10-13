# SparkForge: findings deste commit

| Severidade | Findings | No Code Scanning | Sem localizacao no repositorio |
|---|---|---|---|
| P0 | 5 | 0 | 5 |

**Gate:** `--fail-on P1`: disparou.

## No Code Scanning (0)

Nenhum finding com linha em arquivo do repositorio.

## Sem localizacao no repositorio (5)

| Severidade | Regra | Motivo | Sujeito | Titulo |
|---|---|---|---|---|
| P0 | SF-UI-001 | `callsite_ambiguo` | stage `stage-7` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) |
| P0 | SF-UI-001 | `callsite_ausente` | stage `stage-9` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) |
| P0 | SF-UI-001 | `callsite_nao_python` | stage `stage-4` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) |
| P0 | SF-UI-001 | `callsite_sem_forma` | stage `stage-1` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) |
| P0 | SF-UI-001 | `caminho_ambiguo` | stage `stage-6` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) |
