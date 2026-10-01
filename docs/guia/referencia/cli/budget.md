<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge budget`

Mostra estado do budget do case.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge budget show`](#sparkforge-budget-show) | Mostra budget do case. |

## `sparkforge budget show`

Mostra budget do case.

```bash
sparkforge budget show --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--template` | não | liga/desliga |  |  | Mostra os valores PADRAO do codigo, rotulados como template. Nao e o estado do case -- sem esta flag, budget nao declarado sai como unresolved. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
