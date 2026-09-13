<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge blackboard`

Lê o shared blackboard (.sparkforge/blackboard/).

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge blackboard list`](#sparkforge-blackboard-list) | Lista entidades de um tipo. |
| [`sparkforge blackboard summary`](#sparkforge-blackboard-summary) | Resumo contável do blackboard. |

## `sparkforge blackboard list`

Lista entidades de um tipo.

```bash
sparkforge blackboard list --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--type` | sim | `claims`, `evidence`, `hypotheses`, `objections`, `rebuttals`, `contradictions`, `experiments`, `decisions`, `unknowns` |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge blackboard summary`

Resumo contável do blackboard.

```bash
sparkforge blackboard summary --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
