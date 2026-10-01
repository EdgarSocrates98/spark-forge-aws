<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge journal`

Journal de eventos do case (.sparkforge/journal.jsonl): um started e um finished por verbo que muda estado, encadeados por hash.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge journal verify`](#sparkforge-journal-verify) | Recalcula a cadeia: intact, broken (com o seq da quebra), torn_tail ou absent. Sai 1 em broken. |

## `sparkforge journal verify`

Recalcula a cadeia: intact, broken (com o seq da quebra), torn_tail ou absent. Sai 1 em broken.

```bash
sparkforge journal verify --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  |  |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
