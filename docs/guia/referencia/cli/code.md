<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge code`

Indice local de codigo: prepara, sincroniza, busca simbolo, monta contexto e diagnostica.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge code context`](#sparkforge-code-context) | Monta o ContextPack de uma tarefa a partir do indice, dentro do orcamento. |
| [`sparkforge code doctor`](#sparkforge-code-doctor) | Diagnostico local do indice e da superficie. Sai 1 quando alguma checagem falha. Nao testa conectividade de internet. |
| [`sparkforge code export`](#sparkforge-code-export) | Exporta o grafo no formato de extracao que a fonte publica. |
| [`sparkforge code index`](#sparkforge-code-index) |  |
| [`sparkforge code init`](#sparkforge-code-init) | Prepara o indice sob --root: preflight de seguranca, diretorio, conferencia do .gitignore, banco, indexacao e integridade. `index` e o nome antigo do mesmo comando. |
| [`sparkforge code path`](#sparkforge-code-path) | O caminho mais curto de chamadas entre dois simbolos. Nunca o corpo. |
| [`sparkforge code purge`](#sparkforge-code-purge) | Apaga SOMENTE .sparkforge/local/codeintel/. Qualquer outro diretorio e recusado. |
| [`sparkforge code read`](#sparkforge-code-read) | Le um trecho do repositorio, por --node-id OU por --file com faixa. Tetos duros: 250 linhas, 32 KiB, 4096 tokens. |
| [`sparkforge code search`](#sparkforge-code-search) | Busca simbolo por parte do nome. |
| [`sparkforge code shape`](#sparkforge-code-shape) | Comunidades e nos de maior grau. Nao e julgamento, e forma. |
| [`sparkforge code status`](#sparkforge-code-status) | Estado do indice: frescor, contagens, seguranca e o que mudou na arvore. |
| [`sparkforge code symbol`](#sparkforge-code-symbol) | Metadado, vizinhanca e raio de impacto de um simbolo. Nunca o corpo. |
| [`sparkforge code sync`](#sparkforge-code-sync) | Poe o indice em dia com a arvore. Unica escrita do verbo. |

## `sparkforge code context`

Monta o ContextPack de uma tarefa a partir do indice, dentro do orcamento.

```bash
sparkforge code context --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `task` (posicional) | sim | texto |  |  |  |
| `--max-tokens` | não | texto |  |  |  |
| `--include` | não | `symbols`, `relationships`, `lineage`, `rules`, `unresolved` | sim |  | Repetivel. Omitido, todas as secoes que este motor sabe preencher. |

### Tool MCP equivalente

[`sparkforge_code_context`](../tools/sparkforge_code_context.md)

## `sparkforge code doctor`

Diagnostico local do indice e da superficie. Sai 1 quando alguma checagem falha. Nao testa conectividade de internet.

```bash
sparkforge code doctor --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge code export`

Exporta o grafo no formato de extracao que a fonte publica.

```bash
sparkforge code export --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--no-communities` | não | liga/desliga |  | `True` | Nao calcula comunidade. `algorithm` sai `null`, que diz 'nao calculei'. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para as contagens e a declaracao de compatibilidade; `normal` e `full` trazem nos e arestas. |

### Tool MCP equivalente

[`sparkforge_code_export`](../tools/sparkforge_code_export.md)

## `sparkforge code index`

```bash
sparkforge code index --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge code init`

Prepara o indice sob --root: preflight de seguranca, diretorio, conferencia do .gitignore, banco, indexacao e integridade. `index` e o nome antigo do mesmo comando.

```bash
sparkforge code init --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge code path`

O caminho mais curto de chamadas entre dois simbolos. Nunca o corpo.

```bash
sparkforge code path --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `origem` (posicional) | sim | texto |  |  |  |
| `destino` (posicional) | sim | texto |  |  |  |
| `--depth` | não | texto |  | `6` | Teto de saltos. Satura no maximo; atingi-lo sai como `depth_exhausted`. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para o veredito e as contagens do grafo; `normal` e `full` acrescentam os nos do caminho. |

### Tool MCP equivalente

[`sparkforge_code_path`](../tools/sparkforge_code_path.md)

## `sparkforge code purge`

Apaga SOMENTE .sparkforge/local/codeintel/. Qualquer outro diretorio e recusado.

```bash
sparkforge code purge --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge code read`

Le um trecho do repositorio, por --node-id OU por --file com faixa. Tetos duros: 250 linhas, 32 KiB, 4096 tokens.

```bash
sparkforge code read --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--node-id` | não | texto |  |  |  |
| `--file` | não | texto |  |  | Caminho RELATIVO a --root. |
| `--start-line` | não | texto |  |  |  |
| `--end-line` | não | texto |  |  |  |
| `--context-lines` | não | texto |  | `3` |  |
| `--max-tokens` | não | texto |  | `1200` |  |

### Tool MCP equivalente

[`sparkforge_code_read`](../tools/sparkforge_code_read.md), [`sparkforge_code_symbol`](../tools/sparkforge_code_symbol.md)

## `sparkforge code search`

Busca simbolo por parte do nome.

```bash
sparkforge code search --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `term` (posicional) | sim | texto |  |  |  |
| `--kind` | não | texto |  |  | Filtra por tipo de no: function, class, method. |
| `--path-prefix` | não | texto |  |  | Filtra por prefixo do caminho relativo. |
| `--limit` | não | texto |  | `20` |  |

### Tool MCP equivalente

[`sparkforge_code_search`](../tools/sparkforge_code_search.md)

## `sparkforge code shape`

Comunidades e nos de maior grau. Nao e julgamento, e forma.

```bash
sparkforge code shape --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--top` | não | texto |  | `20` | Quantas comunidades e quantos nos por grau. Satura no teto. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para as contagens e o metodo; `normal` e `full` acrescentam os membros e a lista por grau. |

### Tool MCP equivalente

[`sparkforge_code_shape`](../tools/sparkforge_code_shape.md)

## `sparkforge code status`

Estado do indice: frescor, contagens, seguranca e o que mudou na arvore.

```bash
sparkforge code status --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Mesmos niveis das tools de fact, conteudo proprio deste verbo: `full` acrescenta o bloco de seguranca (SPEC 67) e o de mudancas (SPEC 63); `normal` e `summary` param no estado do indice. |

### Tool MCP equivalente

[`sparkforge_code_status`](../tools/sparkforge_code_status.md), [`sparkforge_code_sync`](../tools/sparkforge_code_sync.md)

## `sparkforge code symbol`

Metadado, vizinhanca e raio de impacto de um simbolo. Nunca o corpo.

```bash
sparkforge code symbol --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `node_id` (posicional) | sim | texto |  |  |  |
| `--depth` | não | texto |  | `1` |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para no metadado; `normal` acrescenta vizinhanca direta; `full` acrescenta o raio de impacto e os testes nele. |

### Tool MCP equivalente

[`sparkforge_code_read`](../tools/sparkforge_code_read.md), [`sparkforge_code_symbol`](../tools/sparkforge_code_symbol.md)

## `sparkforge code sync`

Poe o indice em dia com a arvore. Unica escrita do verbo.

```bash
sparkforge code sync --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

[`sparkforge_code_status`](../tools/sparkforge_code_status.md), [`sparkforge_code_sync`](../tools/sparkforge_code_sync.md)
