<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws portal`

Abre o portal web local do SparkForge (127.0.0.1, sessão por token): dashboard de instalação, hosts de IA, MCP, skills, agents, tarefas, grafo e docs — os mesmos serviços e receipts do CLI. Opcional: o ecossistema inteiro funciona sem ele. --no-browser só imprime a URL.

```bash
sparkforge-aws portal --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--no-browser` | não | liga/desliga |  |  | Só imprime a URL de sessão — útil em SSH/headless ou quando você quer abrir manualmente. |
| `--port` | não | texto |  |  | Porta fixa (default: porta livre do sistema — evita conflito entre instâncias). |
| `--root` | não | texto |  |  | Workspace a inspecionar (default: cwd). |

## Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
