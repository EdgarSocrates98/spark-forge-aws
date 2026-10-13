<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws mcp`

Operacoes do servidor MCP.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws mcp serve`](#sparkforge-aws-mcp-serve) | Sobe servidor MCP no transporte selecionado (default: stdio). |
| [`sparkforge-aws mcp verify`](#sparkforge-aws-mcp-verify) | Handshake JSON-RPC real: initialize + tools/list contra o server. |

## `sparkforge-aws mcp serve`

Sobe servidor MCP no transporte selecionado (default: stdio).

```bash
sparkforge-aws mcp serve --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--transport` | não | `stdio`, `http` |  | `stdio` |  |
| `--mode` | não | `full`, `compact` |  | `full` |  |
| `--host` | não | texto |  | `127.0.0.1` |  |
| `--port` | não | texto |  | `8765` |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws mcp verify`

Handshake JSON-RPC real: initialize + tools/list contra o server.

```bash
sparkforge-aws mcp verify --help
```

### Opções

Este comando não recebe opções.

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
