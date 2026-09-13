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

## Tool MCP equivalente

[`sparkforge_simulate`](../tools/sparkforge_simulate.md)
