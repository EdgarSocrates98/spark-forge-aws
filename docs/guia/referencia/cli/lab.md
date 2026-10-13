<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws lab`

Planeja e inspeciona experimentos Forge Lab; execução mutável exige confirmação explícita.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws lab analyze`](#sparkforge-aws-lab-analyze) | Aponta artifacts capturados para análise posterior. |
| [`sparkforge-aws lab compare`](#sparkforge-aws-lab-compare) | Compara dois receipts/runs sem afirmar performance. |
| [`sparkforge-aws lab describe`](#sparkforge-aws-lab-describe) | Descreve um cenário |
| [`sparkforge-aws lab doctor`](#sparkforge-aws-lab-doctor) | Verifica host, registry e perfis sem iniciar serviços. |
| [`sparkforge-aws lab down`](#sparkforge-aws-lab-down) | Derruba projeto Compose |
| [`sparkforge-aws lab gc`](#sparkforge-aws-lab-gc) | Planeja coleta de runs |
| [`sparkforge-aws lab inspect`](#sparkforge-aws-lab-inspect) | Inspeciona run/receipt e verifica hash. |
| [`sparkforge-aws lab plan`](#sparkforge-aws-lab-plan) | Compila cenário em actions |
| [`sparkforge-aws lab profiles`](#sparkforge-aws-lab-profiles) | Lista profiles e requisitos declarados. |
| [`sparkforge-aws lab promote-fixture`](#sparkforge-aws-lab-promote-fixture) | Promove run revisado para fixture curated. |
| [`sparkforge-aws lab reproduce`](#sparkforge-aws-lab-reproduce) | Verifica receipt e devolve plano reproduzível. |
| [`sparkforge-aws lab run`](#sparkforge-aws-lab-run) | Planeja ou executa cenário |
| [`sparkforge-aws lab scenarios`](#sparkforge-aws-lab-scenarios) | Lista o Golden 20 e suas fidelidades. |
| [`sparkforge-aws lab shell`](#sparkforge-aws-lab-shell) | Planeja shell de serviço |
| [`sparkforge-aws lab up`](#sparkforge-aws-lab-up) | Sobe profile Compose |
| [`sparkforge-aws lab verify`](#sparkforge-aws-lab-verify) | Verifica registry, Golden 20, schemas e action plans offline. |

## `sparkforge-aws lab analyze`

Aponta artifacts capturados para análise posterior.

```bash
sparkforge-aws lab analyze --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab compare`

Compara dois receipts/runs sem afirmar performance.

```bash
sparkforge-aws lab compare --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `before` (posicional) | sim | texto |  |  |  |
| `after` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab describe`

Descreve um cenário

```bash
sparkforge-aws lab describe --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `scenario` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--backend` | não | `compose`, `testcontainers` |  | `compose` |  |
| `--seed` | não | texto |  |  |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab doctor`

Verifica host, registry e perfis sem iniciar serviços.

```bash
sparkforge-aws lab doctor --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab down`

Derruba projeto Compose

```bash
sparkforge-aws lab down --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--project` | não | texto |  | `forge-lab` |  |
| `--profile` | não | texto |  | `core` |  |
| `--service` | não | texto |  | `` |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab gc`

Planeja coleta de runs

```bash
sparkforge-aws lab gc --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--project` | não | texto |  | `forge-lab` |  |
| `--profile` | não | texto |  | `core` |  |
| `--service` | não | texto |  | `` |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab inspect`

Inspeciona run/receipt e verifica hash.

```bash
sparkforge-aws lab inspect --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab plan`

Compila cenário em actions

```bash
sparkforge-aws lab plan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `scenario` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--backend` | não | `compose`, `testcontainers` |  | `compose` |  |
| `--seed` | não | texto |  |  |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab profiles`

Lista profiles e requisitos declarados.

```bash
sparkforge-aws lab profiles --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab promote-fixture`

Promove run revisado para fixture curated.

```bash
sparkforge-aws lab promote-fixture --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run` (posicional) | sim | texto |  |  |  |
| `destination` (posicional) | sim | texto |  |  |  |
| `--reviewed` | não | liga/desliga |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab reproduce`

Verifica receipt e devolve plano reproduzível.

```bash
sparkforge-aws lab reproduce --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `receipt` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab run`

Planeja ou executa cenário

```bash
sparkforge-aws lab run --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `scenario` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--backend` | não | `compose`, `testcontainers` |  | `compose` |  |
| `--seed` | não | texto |  |  |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab scenarios`

Lista o Golden 20 e suas fidelidades.

```bash
sparkforge-aws lab scenarios --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--json` | não | liga/desliga |  |  | Mantido por compatibilidade; saída já é JSON. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab shell`

Planeja shell de serviço

```bash
sparkforge-aws lab shell --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--project` | não | texto |  | `forge-lab` |  |
| `--profile` | não | texto |  | `core` |  |
| `--service` | não | texto |  | `` |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab up`

Sobe profile Compose

```bash
sparkforge-aws lab up --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--project` | não | texto |  | `forge-lab` |  |
| `--profile` | não | texto |  | `core` |  |
| `--service` | não | texto |  | `` |  |
| `--execute` | não | liga/desliga |  |  |  |
| `--confirm` | não | liga/desliga |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws lab verify`

Verifica registry, Golden 20, schemas e action plans offline.

```bash
sparkforge-aws lab verify --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
