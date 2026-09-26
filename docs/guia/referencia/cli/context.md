<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge context`

Descobre capabilities e empacota contexto deterministico sob limite explicito.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge context expand`](#sparkforge-context-expand) | Expande uma referencia ctx://v1 sob budget. |
| [`sparkforge context start`](#sparkforge-context-start) | Inicia descoberta, selecao, reducao e materializacao de contexto. |

## `sparkforge context expand`

Expande uma referencia ctx://v1 sob budget.

```bash
sparkforge context expand --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--ref` | sim | texto |  |  |  |
| `--max-bytes` | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

[`sparkforge_context_expand`](../tools/sparkforge_context_expand.md), [`sparkforge_context_start`](../tools/sparkforge_context_start.md)

## `sparkforge context start`

Inicia descoberta, selecao, reducao e materializacao de contexto.

```bash
sparkforge context start --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--intent` | sim | texto |  |  |  |
| `--profile` | não | `economy`, `balanced`, `deep` |  | `balanced` |  |
| `--max-bytes` | sim | texto |  |  |  |
| `--items` | não | texto |  |  | JSON com lista de facts/findings/knowledge/codigo ja extraidos. |
| `--repo` | não | texto |  | `.` |  |
| `--case-id` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_context_expand`](../tools/sparkforge_context_expand.md), [`sparkforge_context_start`](../tools/sparkforge_context_start.md)
