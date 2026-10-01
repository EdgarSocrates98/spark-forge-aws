<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge gain`

Ganho OBSERVADO entre runs medidos antes e depois de uma mudanca: por lado, N, mediana, minimo e maximo de tempo, DPU-segundos e custo, e o delta das medianas. Nunca projeta economia nem atribui causa.

```bash
sparkforge gain --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--baseline` | sim | texto | sim |  | Facts de runs do antes. Repetivel. |
| `--candidate` | sim | texto | sim |  | Facts de runs do depois. Repetivel. |

## Tool MCP equivalente

[`sparkforge_gain`](../tools/sparkforge_gain.md)
