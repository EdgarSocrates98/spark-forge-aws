<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws capacity`

Escolhe a capacidade mais barata que cumpre o SLA, entre as capacidades que o job JA rodou. Nunca aplica a mudanca.

```bash
sparkforge-aws capacity --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto |  |  | Arquivo de facts (--out de analyze). |
| `--job-name` | sim | texto |  |  |  |
| `--job-run` | sim | texto |  |  | Id do run que este plano descreve. |
| `--history` | não | texto |  |  | Diretorio com um arquivo de facts por run anterior (`analyze glue-job-runs --out`), para as capacidades observadas. |
| `--out` | não | texto |  |  | Escreve o plano completo (JSON) neste arquivo. |

## Tool MCP equivalente

[`sparkforge_aws_capacity`](../tools/sparkforge_aws_capacity.md), [`sparkforge_aws_finops`](../tools/sparkforge_aws_finops.md)
