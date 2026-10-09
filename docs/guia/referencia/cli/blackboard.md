<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws blackboard`

Lê o shared blackboard (.sparkforge_aws/blackboard/).

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws blackboard list`](#sparkforge-aws-blackboard-list) | Lista entidades de um tipo. |
| [`sparkforge-aws blackboard summary`](#sparkforge-aws-blackboard-summary) | Resumo contável do blackboard. |

## `sparkforge-aws blackboard list`

Lista entidades de um tipo.

```bash
sparkforge-aws blackboard list --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--type` | sim | `claims`, `evidence`, `hypotheses`, `objections`, `rebuttals`, `contradictions`, `experiments`, `decisions`, `unknowns` |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws blackboard summary`

Resumo contável do blackboard.

```bash
sparkforge-aws blackboard summary --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
