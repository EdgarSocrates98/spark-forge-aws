<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge lab`

Planeja e inspeciona experimentos Forge Lab; execução mutável exige confirmação explícita.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge lab analyze`](#sparkforge-lab-analyze) | Aponta artifacts capturados para análise posterior. |
| [`sparkforge lab compare`](#sparkforge-lab-compare) | Compara dois receipts/runs sem afirmar performance. |
| [`sparkforge lab describe`](#sparkforge-lab-describe) | Descreve um cenário |
| [`sparkforge lab doctor`](#sparkforge-lab-doctor) | Verifica host, registry e perfis sem iniciar serviços. |
| [`sparkforge lab down`](#sparkforge-lab-down) | Derruba projeto Compose |
| [`sparkforge lab gc`](#sparkforge-lab-gc) | Planeja coleta de runs |
| [`sparkforge lab inspect`](#sparkforge-lab-inspect) | Inspeciona run/receipt e verifica hash. |
| [`sparkforge lab plan`](#sparkforge-lab-plan) | Compila cenário em actions |
| [`sparkforge lab profiles`](#sparkforge-lab-profiles) | Lista profiles e requisitos declarados. |
| [`sparkforge lab promote-fixture`](#sparkforge-lab-promote-fixture) | Promove run revisado para fixture curated. |
| [`sparkforge lab reproduce`](#sparkforge-lab-reproduce) | Verifica receipt e devolve plano reproduzível. |
| [`sparkforge lab run`](#sparkforge-lab-run) | Planeja ou executa cenário |
| [`sparkforge lab scenarios`](#sparkforge-lab-scenarios) | Lista o Golden 20 e suas fidelidades. |
| [`sparkforge lab shell`](#sparkforge-lab-shell) | Planeja shell de serviço |
| [`sparkforge lab up`](#sparkforge-lab-up) | Sobe profile Compose |
| [`sparkforge lab verify`](#sparkforge-lab-verify) | Verifica registry, Golden 20, schemas e action plans offline. |

## `sparkforge lab analyze`

Aponta artifacts capturados para análise posterior.

```bash
sparkforge lab analyze --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab compare`

Compara dois receipts/runs sem afirmar performance.

```bash
sparkforge lab compare --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `before` (posicional) | sim | texto |  |  |  |
| `after` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab describe`

Descreve um cenário

```bash
sparkforge lab describe --help
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

## `sparkforge lab doctor`

Verifica host, registry e perfis sem iniciar serviços.

```bash
sparkforge lab doctor --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab down`

Derruba projeto Compose

```bash
sparkforge lab down --help
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

## `sparkforge lab gc`

Planeja coleta de runs

```bash
sparkforge lab gc --help
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

## `sparkforge lab inspect`

Inspeciona run/receipt e verifica hash.

```bash
sparkforge lab inspect --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab plan`

Compila cenário em actions

```bash
sparkforge lab plan --help
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

## `sparkforge lab profiles`

Lista profiles e requisitos declarados.

```bash
sparkforge lab profiles --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab promote-fixture`

Promove run revisado para fixture curated.

```bash
sparkforge lab promote-fixture --help
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

## `sparkforge lab reproduce`

Verifica receipt e devolve plano reproduzível.

```bash
sparkforge lab reproduce --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `receipt` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab run`

Planeja ou executa cenário

```bash
sparkforge lab run --help
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

## `sparkforge lab scenarios`

Lista o Golden 20 e suas fidelidades.

```bash
sparkforge lab scenarios --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |
| `--json` | não | liga/desliga |  |  | Mantido por compatibilidade; saída já é JSON. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge lab shell`

Planeja shell de serviço

```bash
sparkforge lab shell --help
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

## `sparkforge lab up`

Sobe profile Compose

```bash
sparkforge lab up --help
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

## `sparkforge lab verify`

Verifica registry, Golden 20, schemas e action plans offline.

```bash
sparkforge lab verify --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
