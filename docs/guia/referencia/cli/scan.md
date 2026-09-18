<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge scan`

Roda sozinho os analyzes que cabem num repositorio: artefato coletado pelo manifesto, codigo pela extensao; depois fuse, judge e um resumo em .sparkforge/scan/. Sem rede.

```bash
sparkforge scan --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `raiz` (posicional) | sim | texto |  | `.` | Pasta a varrer (padrao: .). |
| `--dry-run` | não | liga/desliga |  |  | So mostra o plano; nao roda nem grava nada. |
| `--format` | não | `json`, `sarif` |  | `json` | sarif grava tambem o SARIF e o resumo de PR, como `report github`. |
| `--fail-on` | não | `P0`, `P1` |  |  | Sai 1 se houver finding nesta severidade (P1 inclui P0). |
| `--glue` | não | texto |  |  |  |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--emr` | não | texto |  |  |  |
| `--databricks` | não | texto |  |  |  |
| `--photon` | não | `on`, `off` |  |  | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf; sem declaracao, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |

## Tool MCP equivalente

[`sparkforge_scan`](../tools/sparkforge_scan.md)
