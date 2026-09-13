<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge knowledge`

Localiza os arquivos de conhecimento versionado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge knowledge drift`](#sparkforge-knowledge-drift) | Knowledge Drift Radar: para cada fonte vigiada que mudou (changed_at no lock), as regras e documentos que a leram antes da mudanca e os goldens, evals e agentes dessas regras. Sem rede. |
| [`sparkforge knowledge path`](#sparkforge-knowledge-path) | Imprime a raiz de knowledge e, com --file, um arquivo dentro dela. |

## `sparkforge knowledge drift`

Knowledge Drift Radar: para cada fonte vigiada que mudou (changed_at no lock), as regras e documentos que a leram antes da mudanca e os goldens, evals e agentes dessas regras. Sem rede.

```bash
sparkforge knowledge drift --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--source` | não | texto |  |  | So esta fonte do lock (a chave do lock). |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_knowledge_drift`](../tools/sparkforge_knowledge_drift.md)

## `sparkforge knowledge path`

Imprime a raiz de knowledge e, com --file, um arquivo dentro dela.

```bash
sparkforge knowledge path --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--file` | não | texto |  |  |  |
| `--source-freshness` | não | liga/desliga |  |  | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_knowledge_path`](../tools/sparkforge_knowledge_path.md)
