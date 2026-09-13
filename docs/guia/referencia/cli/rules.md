<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge rules`

Consulta o catalogo de regras versionado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge rules lookup`](#sparkforge-rules-lookup) | Busca regras por id ou categoria (thresholds, fontes, severidade). |

## `sparkforge rules lookup`

Busca regras por id ou categoria (thresholds, fontes, severidade).

```bash
sparkforge rules lookup --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--id` | não | texto | sim |  |  |
| `--category` | não | texto |  |  |  |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--source-freshness` | não | liga/desliga |  |  | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_rules_lookup`](../tools/sparkforge_rules_lookup.md)
