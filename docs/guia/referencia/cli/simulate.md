<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge simulate`

O que uma mudanca de configuracao move, estruturalmente: altera o valor de facts que ja existem, rederiva e julga os dois lados, e diz que achados somem e aparecem. Nunca preve spill, tempo ou custo.

```bash
sparkforge simulate --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Facts do case. Repetivel. |
| `--set` | sim | texto | sim |  | camada:chave=valor, camada em tf, code, effective, emr. Repetivel. |
| `--glue` | não | texto |  |  |  |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--emr` | não | texto |  |  |  |
| `--databricks` | não | texto |  |  |  |
| `--photon` | não | `on`, `off` |  |  | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (fact plan.photon) liga a mesma recusa sem a flag e vence a declaracao: declarar 'off' diante dele vira divergencia 'photon:'. Sem declaracao nem plano Photon, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |

## Tool MCP equivalente

[`sparkforge_simulate`](../tools/sparkforge_simulate.md)
