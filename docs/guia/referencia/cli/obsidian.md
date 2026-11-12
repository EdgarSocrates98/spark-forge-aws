<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws obsidian`

Authorized Obsidian vault operations

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws obsidian export`](#sparkforge-aws-obsidian-export) | Apply a reviewed sync plan. |
| [`sparkforge-aws obsidian export-note`](#sparkforge-aws-obsidian-export-note) | Export FILE as forges/<forge-id>/<name>.md |
| [`sparkforge-aws obsidian history`](#sparkforge-aws-obsidian-history) | List Forge sync receipts (body-free). |
| [`sparkforge-aws obsidian preview`](#sparkforge-aws-obsidian-preview) | Metadata + projection, never the body. |
| [`sparkforge-aws obsidian scan`](#sparkforge-aws-obsidian-scan) | List Markdown paths without reading bodies. |
| [`sparkforge-aws obsidian status`](#sparkforge-aws-obsidian-status) | Report configured/detected vault state. |
| [`sparkforge-aws obsidian sync-plan`](#sparkforge-aws-obsidian-sync-plan) | Dry-run a sync of FILE into PATH. |

## `sparkforge-aws obsidian export`

Apply a reviewed sync plan.

```bash
sparkforge-aws obsidian export --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |
| `file` (posicional) | sim | texto |  |  |  |
| `--baseline-hash` | não | texto |  |  |  |
| `--classification` | não | texto |  | `internal` |  |
| `--yes` | não | liga/desliga |  |  | Confirm the reviewed plan |
| `--no-moc` | não | liga/desliga |  | `True` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws obsidian export-note`

Export FILE as forges/<forge-id>/<name>.md

```bash
sparkforge-aws obsidian export-note --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `name` (posicional) | sim | texto |  |  |  |
| `file` (posicional) | sim | texto |  |  |  |
| `--baseline-hash` | não | texto |  |  |  |
| `--classification` | não | texto |  | `internal` |  |
| `--yes` | não | liga/desliga |  |  |  |
| `--no-moc` | não | liga/desliga |  | `True` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws obsidian history`

List Forge sync receipts (body-free).

```bash
sparkforge-aws obsidian history --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--limit` | não | texto |  | `50` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws obsidian preview`

Metadata + projection, never the body.

```bash
sparkforge-aws obsidian preview --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws obsidian scan`

List Markdown paths without reading bodies.

```bash
sparkforge-aws obsidian scan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--prefix` | não | texto |  | `` |  |
| `--limit` | não | texto |  | `200` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws obsidian status`

Report configured/detected vault state.

```bash
sparkforge-aws obsidian status --help
```

### Opções

Este comando não recebe opções.

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws obsidian sync-plan`

Dry-run a sync of FILE into PATH.

```bash
sparkforge-aws obsidian sync-plan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  |  |
| `file` (posicional) | sim | texto |  |  |  |
| `--baseline-hash` | não | texto |  |  |  |
| `--classification` | não | texto |  | `internal` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
