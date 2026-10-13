# SparkForge: findings deste commit

| Severidade | Findings | No Code Scanning | Sem localizacao no repositorio |
|---|---|---|---|
| P0 | 1 | 1 | 0 |

**Gate:** desligado.

## No Code Scanning (1)

| Severidade | Regra | Local | Titulo |
|---|---|---|---|
| P0 | SF-UI-001 | `src/Etl.scala:120` | Skew de duração de task no stage (medido: max_ms=15000, mean_ms=3333.3333333333335, min_ms=1000, p50_ms=1000, p95_ms=15000, task_count=6) -- linha da acao `save` que originou o stage 2 (nao e a causa) |

## Sem localizacao no repositorio (0)

Todos os findings tem linha em arquivo do repositorio.
