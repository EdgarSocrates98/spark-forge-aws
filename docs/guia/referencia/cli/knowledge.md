<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws knowledge`

Localiza os arquivos de conhecimento versionado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws knowledge drift`](#sparkforge-aws-knowledge-drift) | Knowledge Drift Radar: para cada fonte vigiada que mudou (changed_at no lock), as regras e documentos que a leram antes da mudanca e os goldens, evals e agentes dessas regras. Sem rede. |
| [`sparkforge-aws knowledge list`](#sparkforge-aws-knowledge-list) | Enumera os documentos de knowledge (e dos packs ativos). |
| [`sparkforge-aws knowledge path`](#sparkforge-aws-knowledge-path) | Imprime a raiz de knowledge e, com --file, um arquivo dentro dela. |
| [`sparkforge-aws knowledge search`](#sparkforge-aws-knowledge-search) | Busca textual offline sobre os documentos de knowledge. |

## `sparkforge-aws knowledge drift`

Knowledge Drift Radar: para cada fonte vigiada que mudou (changed_at no lock), as regras e documentos que a leram antes da mudanca e os goldens, evals e agentes dessas regras. Sem rede.

```bash
sparkforge-aws knowledge drift --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--source` | não | texto |  |  | So esta fonte do lock (a chave do lock). |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_aws_knowledge_drift`](../tools/sparkforge_aws_knowledge_drift.md)

## `sparkforge-aws knowledge list`

Enumera os documentos de knowledge (e dos packs ativos).

```bash
sparkforge-aws knowledge list --help
```

### Opções

Este comando não recebe opções.

### Tool MCP equivalente

[`sparkforge_aws_knowledge_list`](../tools/sparkforge_aws_knowledge_list.md), [`sparkforge_aws_knowledge_search`](../tools/sparkforge_aws_knowledge_search.md)

## `sparkforge-aws knowledge path`

Imprime a raiz de knowledge e, com --file, um arquivo dentro dela.

```bash
sparkforge-aws knowledge path --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--file` | não | texto |  |  |  |
| `--source-freshness` | não | liga/desliga |  |  | Acrescenta o estado das fontes citadas (fixed, unverified, stale, aging, fresh), calculado sobre knowledge/sources.lock.json. Depende do lock e do dia. |
| `--as-of` | não | texto |  |  | Dia de referencia do estado das fontes (AAAA-MM-DD). |

### Tool MCP equivalente

[`sparkforge_aws_knowledge_path`](../tools/sparkforge_aws_knowledge_path.md)

## `sparkforge-aws knowledge search`

Busca textual offline sobre os documentos de knowledge.

```bash
sparkforge-aws knowledge search --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `term` (posicional) | sim | texto |  |  |  |
| `--limit` | não | texto |  | `20` |  |
| `--domain` | não | texto |  |  | So documentos cujo primeiro segmento de caminho (ou nome na raiz) e este dominio ou um sub-dominio `<dominio>-`: glue, spark, emr, ... |
| `--cursor` | não | texto |  |  | Offset da pagina anterior (`next_cursor` da resposta). |

### Tool MCP equivalente

[`sparkforge_aws_knowledge_list`](../tools/sparkforge_aws_knowledge_list.md), [`sparkforge_aws_knowledge_search`](../tools/sparkforge_aws_knowledge_search.md)
