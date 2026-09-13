<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge validate`

Valida findings contra o JSON Schema e a regra de ganho sem benchmark_ref.

```bash
sparkforge validate --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--findings` | sim | texto |  |  |  |
| `--facts` | não | texto |  |  | Opcional. Arquivo de facts (tipicamente `sparkforge benchmark --out`). Sem ele, `benchmark_ref` so e cobrado na FORMA (`f_` + 6 hex); com ele, o `fact_id` citado precisa existir no conjunto -- achado que cita medicao ausente da evidencia passa a ser rejeitado. |

## Tool MCP equivalente

[`sparkforge_validate_output`](../tools/sparkforge_validate_output.md)
