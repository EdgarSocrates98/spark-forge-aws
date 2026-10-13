<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws graph`

Grafo do indice de codigo: status, ForgeGraphView e Graph Studio local.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws graph status`](#sparkforge-aws-graph-status) | Estado do grafo: contagens e origem do indice. |
| [`sparkforge-aws graph ui`](#sparkforge-aws-graph-ui) | Abre o Graph Studio local (read-only, 127.0.0.1). |
| [`sparkforge-aws graph view`](#sparkforge-aws-graph-view) | Emite o documento ForgeGraphView/v1 (contrato do Graph Studio). |

## `sparkforge-aws graph status`

Estado do grafo: contagens e origem do indice.

```bash
sparkforge-aws graph status --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |

### Tool MCP equivalente

[`sparkforge_aws_graph_status`](../tools/sparkforge_aws_graph_status.md), [`sparkforge_aws_graph_view`](../tools/sparkforge_aws_graph_view.md)

## `sparkforge-aws graph ui`

Abre o Graph Studio local (read-only, 127.0.0.1).

```bash
sparkforge-aws graph ui --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--limit` | não | texto |  | `5000` |  |
| `--no-browser` | não | liga/desliga |  |  | Serve sem abrir navegador (SSH). |
| `--port` | não | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws graph view`

Emite o documento ForgeGraphView/v1 (contrato do Graph Studio).

```bash
sparkforge-aws graph view --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--limit` | não | texto |  | `5000` | Teto de nos exportados (o restante fica em limitations). |

### Tool MCP equivalente

[`sparkforge_aws_graph_status`](../tools/sparkforge_aws_graph_status.md), [`sparkforge_aws_graph_view`](../tools/sparkforge_aws_graph_view.md)
