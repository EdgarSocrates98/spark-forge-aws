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
| `--severity` | não | `P0`, `P1`, `P2`, `P3`, `P4` |  |  | Filtra por severity_default. |
| `--runtime` | não | texto |  |  | Filtra pelas regras cujo runtime_scope tem esta CHAVE (glue, spark, ...). Nao compara versao: o escopo vem na resposta para voce ler. |
| `--index` | não | liga/desliga |  |  | Forma compacta em rules_index (id, category, title, severity_default, runtime_scope), com rules vazia. Para procurar regra por atributo sem baixar o catalogo inteiro. |
| `--source-freshness` | não | liga/desliga |  |  | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_rules_lookup`](../tools/sparkforge_rules_lookup.md)
