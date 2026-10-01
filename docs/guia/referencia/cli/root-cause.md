<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge root-cause`

Ordena os achados por consequencia declarada e nomeia a lacuna. Nao calcula confianca e nao estima ganho.

```bash
sparkforge root-cause --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Arquivo de facts. REPETIVEL, e a repeticao e o contrato: uma regra pode exigir facts de mais de um extrator, e a lacuna publicada e sobre a UNIAO. |
| `--glue` | não | texto |  |  |  |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--emr` | não | texto |  |  |  |
| `--databricks` | não | texto |  |  |  |
| `--photon` | não | `on`, `off` |  |  |  |
| `--all-missing` | não | liga/desliga |  |  | Lista as regras nao avaliadas de TODAS as areas, e nao so das que ja tem achado. O TOTAL sai nos dois casos -- medido: 129 num case de Terraform sozinho, contra 5 no recorte. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` corta remediacao, validacao, rollback e os riscos da regra. Nunca corta `rule_id`, severidade, evidencia nem a lacuna. |

## Tool MCP equivalente

[`sparkforge_root_cause`](../tools/sparkforge_root_cause.md)
