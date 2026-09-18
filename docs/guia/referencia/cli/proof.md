<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge proof`

Obrigacoes de prova de cada recomendacao APLICADA: resolucao (a regra deixou de disparar no depois?) e um eixo por item de action.moves (funcval, benchmark ou sem comparador). Desfechos: refuted, not_refuted, inconclusive, unproven -- nunca provado.

```bash
sparkforge proof --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--findings` | sim | texto |  |  | Findings do antes (`judge --out`). |
| `--facts` | sim | texto | sim |  | Uniao de facts do case, com os de funcval e benchmark. Repetivel. |
| `--after-facts` | sim | texto | sim |  | Facts extraidos dos artefatos do depois. Repetivel. |
| `--applied` | sim | texto | sim |  | RULE_ID ou RULE_ID:simbolo de cada recomendacao aplicada. Repetivel. |
| `--glue` | não | texto |  |  |  |
| `--spark` | não | texto |  |  |  |
| `--python` | não | texto |  |  |  |
| `--iceberg` | não | texto |  |  |  |
| `--athena` | não | texto |  |  |  |
| `--emr` | não | texto |  |  |  |
| `--databricks` | não | texto |  |  |  |
| `--photon` | não | `on`, `off` |  |  | Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com 'on', regra que depende de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf; sem declaracao, SF-ENV-006 avisa que regra de plano calada nao e evidencia. Sem --databricks, a declaracao vira divergencia 'photon:' e nao entra no runtime. |

## Tool MCP equivalente

[`sparkforge_proof`](../tools/sparkforge_proof.md)
