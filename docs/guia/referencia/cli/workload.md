<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge workload`

Perfil de workload por eixos, a partir de facts ja extraidos.

```bash
sparkforge workload --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto |  |  | Arquivo de facts (--out de analyze). |
| `--job-name` | sim | texto |  |  |  |
| `--job-run` | sim | texto |  |  | Id do run que este perfil descreve. |
| `--history` | não | texto |  |  | Diretorio com um arquivo de facts por run anterior (`analyze glue-job-runs --out`), para a escala. |
| `--out` | não | texto |  |  | Escreve o fingerprint completo (JSON) neste arquivo. |

## Tool MCP equivalente

[`sparkforge_workload`](../tools/sparkforge_workload.md)
