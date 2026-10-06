<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge agentops`

Inspeciona runs locais, compara baseline e atribui desperdicio observado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge agentops baseline`](#sparkforge-agentops-baseline) | Salva ou compara baseline local. |
| [`sparkforge agentops compare`](#sparkforge-agentops-compare) | Compara dois runs locais. |
| [`sparkforge agentops critical-path`](#sparkforge-agentops-critical-path) | Maiores duracoes, retries e waiting medidos do run. |
| [`sparkforge agentops inspect`](#sparkforge-agentops-inspect) | Inspeciona um run local. |
| [`sparkforge agentops timeline`](#sparkforge-agentops-timeline) | Linha do tempo do run, por lane de componente. |

## `sparkforge agentops baseline`

Salva ou compara baseline local.

```bash
sparkforge agentops baseline --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `action` (posicional) | sim | `save`, `compare` |  |  |  |
| `run_id` (posicional) | sim | texto |  |  |  |
| `--path` | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge agentops compare`

Compara dois runs locais.

```bash
sparkforge agentops compare --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_a` (posicional) | sim | texto |  |  |  |
| `run_b` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge agentops critical-path`

Maiores duracoes, retries e waiting medidos do run.

```bash
sparkforge agentops critical-path --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_id` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge agentops inspect`

Inspeciona um run local.

```bash
sparkforge agentops inspect --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_id` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge agentops timeline`

Linha do tempo do run, por lane de componente.

```bash
sparkforge agentops timeline --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_id` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
