<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge decision`

Valida e observa decisões declarativas sem alterar o dispatch atual.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge decision benchmark`](#sparkforge-decision-benchmark) | Executa a suíte seed offline do Decision Plane. |
| [`sparkforge decision compare`](#sparkforge-decision-compare) | Compara uma decisão shadow persistida com uma rota atual. |
| [`sparkforge decision evaluate`](#sparkforge-decision-evaluate) | Avalia contrato bounded genérico em modo offline. |
| [`sparkforge decision receipt`](#sparkforge-decision-receipt) | Verifica receipt content-addressed de decisão shadow. |
| [`sparkforge decision shadow`](#sparkforge-decision-shadow) | Avalia estado normalizado e compara com a rota atual. |
| [`sparkforge decision validate`](#sparkforge-decision-validate) | Valida um contrato Decision Plane versionado. |

## `sparkforge decision benchmark`

Executa a suíte seed offline do Decision Plane.

```bash
sparkforge decision benchmark --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--fixture` | não | texto |  | `evals/token_efficient/fixtures/decision_plane_cases.yaml` |  |
| `--repo` | não | texto |  | `.` |  |
| `--out` | não | texto |  |  | Escreve o relatório neste arquivo. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge decision compare`

Compara uma decisão shadow persistida com uma rota atual.

```bash
sparkforge decision compare --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--shadow` | sim | texto |  |  | JSON de resultado shadow. |
| `--current-route` | sim | texto |  |  |  |
| `--out` | não | texto |  |  | Escreve a comparação neste arquivo. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge decision evaluate`

Avalia contrato bounded genérico em modo offline.

```bash
sparkforge decision evaluate --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--contract` | não | texto |  | `kernel.synthetic` |  |
| `--input` | sim | texto |  |  | JSON de estado declarado. |
| `--repo` | não | texto |  | `.` |  |
| `--now` | não | texto |  |  |  |
| `--out` | não | texto |  |  | Escreve o resultado completo neste arquivo. |

### Tool MCP equivalente

[`sparkforge_decision_evaluate`](../tools/sparkforge_decision_evaluate.md)

## `sparkforge decision receipt`

Verifica receipt content-addressed de decisão shadow.

```bash
sparkforge decision receipt --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge decision shadow`

Avalia estado normalizado e compara com a rota atual.

```bash
sparkforge decision shadow --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--contract` | não | texto |  | `routing.data_domain` |  |
| `--input` | sim | texto |  |  | JSON de DecisionInput. |
| `--repo` | não | texto |  | `.` |  |
| `--now` | não | texto |  |  |  |
| `--out` | não | texto |  |  | Escreve o resultado completo neste arquivo. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge decision validate`

Valida um contrato Decision Plane versionado.

```bash
sparkforge decision validate --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--contract` | não | texto |  | `routing.data_domain` |  |
| `--version` | não | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
