<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws agentops`

Inspeciona runs locais, compara baseline e atribui desperdicio observado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws agentops baseline`](#sparkforge-aws-agentops-baseline) | Salva ou compara baseline local. |
| [`sparkforge-aws agentops compare`](#sparkforge-aws-agentops-compare) | Compara dois runs locais. |
| [`sparkforge-aws agentops critical-path`](#sparkforge-aws-agentops-critical-path) | Maiores duracoes, retries e waiting medidos do run. |
| [`sparkforge-aws agentops inspect`](#sparkforge-aws-agentops-inspect) | Inspeciona um run local. |
| [`sparkforge-aws agentops timeline`](#sparkforge-aws-agentops-timeline) | Linha do tempo do run, por lane de componente. |

## `sparkforge-aws agentops baseline`

Salva ou compara baseline local.

```bash
sparkforge-aws agentops baseline --help
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

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge-aws agentops compare`

Compara dois runs locais.

```bash
sparkforge-aws agentops compare --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_a` (posicional) | sim | texto |  |  |  |
| `run_b` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge-aws agentops critical-path`

Maiores duracoes, retries e waiting medidos do run.

```bash
sparkforge-aws agentops critical-path --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_id` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge-aws agentops inspect`

Inspeciona um run local.

```bash
sparkforge-aws agentops inspect --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_id` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge-aws agentops timeline`

Linha do tempo do run, por lane de componente.

```bash
sparkforge-aws agentops timeline --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `run_id` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)
