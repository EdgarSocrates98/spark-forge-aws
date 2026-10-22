<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws evals`

Inventario classificado e execucao das suites de avaliacao (§7.1/§7.2): developer, runtime-decision, output-verification, host-conformance. Gabaritos selados nunca sao emitidos.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws evals describe`](#sparkforge-aws-evals-describe) | evals.describe (§7.2): categoria, ambiente, selagem e sha256 da suite. |
| [`sparkforge-aws evals list`](#sparkforge-aws-evals-list) | evals.list (§7.2): suites classificadas por categoria. |
| [`sparkforge-aws evals result`](#sparkforge-aws-evals-result) | evals.result (§7.2): scorecard de uma execucao de host gravada. |
| [`sparkforge-aws evals run`](#sparkforge-aws-evals-run) | evals.run (§7.2): executa o runner deterministico da suite; suites de host recusam EVALS-REQUIRES-HOST. |

## `sparkforge-aws evals describe`

evals.describe (§7.2): categoria, ambiente, selagem e sha256 da suite.

```bash
sparkforge-aws evals describe --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--suite` | sim | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws evals list`

evals.list (§7.2): suites classificadas por categoria.

```bash
sparkforge-aws evals list --help
```

### Opções

Este comando não recebe opções.

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws evals result`

evals.result (§7.2): scorecard de uma execucao de host gravada.

```bash
sparkforge-aws evals result --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--suite` | sim | texto |  |  |  |
| `--run` | sim | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws evals run`

evals.run (§7.2): executa o runner deterministico da suite; suites de host recusam EVALS-REQUIRES-HOST.

```bash
sparkforge-aws evals run --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--suite` | sim | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
