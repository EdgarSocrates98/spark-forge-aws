<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws code`

Indice local de codigo: prepara, sincroniza, busca simbolo, monta contexto e diagnostica.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws code context`](#sparkforge-aws-code-context) | Monta o ContextPack de uma tarefa a partir do indice, dentro do orcamento. |
| [`sparkforge-aws code doctor`](#sparkforge-aws-code-doctor) | Diagnostico local do indice e da superficie. Sai 1 quando alguma checagem falha. Nao testa conectividade de internet. |
| [`sparkforge-aws code export`](#sparkforge-aws-code-export) | Exporta o grafo no formato de extracao que a fonte publica. |
| [`sparkforge-aws code index`](#sparkforge-aws-code-index) |  |
| [`sparkforge-aws code init`](#sparkforge-aws-code-init) | Prepara o indice sob --root: preflight de seguranca, diretorio, conferencia do .gitignore, banco, indexacao e integridade. `index` e o nome antigo do mesmo comando. |
| [`sparkforge-aws code path`](#sparkforge-aws-code-path) | O caminho mais curto de chamadas entre dois simbolos. Nunca o corpo. |
| [`sparkforge-aws code purge`](#sparkforge-aws-code-purge) | Apaga SOMENTE .sparkforge_aws/local/codeintel/. Qualquer outro diretorio e recusado. |
| [`sparkforge-aws code read`](#sparkforge-aws-code-read) | Le um trecho do repositorio, por --node-id OU por --file com faixa. Tetos duros: 250 linhas, 32 KiB, 4096 tokens. |
| [`sparkforge-aws code search`](#sparkforge-aws-code-search) | Busca simbolo por parte do nome. |
| [`sparkforge-aws code shape`](#sparkforge-aws-code-shape) | Comunidades e nos de maior grau. Nao e julgamento, e forma. |
| [`sparkforge-aws code status`](#sparkforge-aws-code-status) | Estado do indice: frescor, contagens, seguranca e o que mudou na arvore. |
| [`sparkforge-aws code symbol`](#sparkforge-aws-code-symbol) | Metadado, vizinhanca e raio de impacto de um simbolo. Nunca o corpo. |
| [`sparkforge-aws code sync`](#sparkforge-aws-code-sync) | Poe o indice em dia com a arvore. Unica escrita do verbo. |

## `sparkforge-aws code context`

Monta o ContextPack de uma tarefa a partir do indice, dentro do orcamento.

```bash
sparkforge-aws code context --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `task` (posicional) | sim | texto |  |  |  |
| `--max-tokens` | não | texto |  |  |  |
| `--include` | não | `symbols`, `relationships`, `lineage`, `rules`, `unresolved` | sim |  | Repetivel. Omitido, todas as secoes que este motor sabe preencher. |

### Tool MCP equivalente

[`sparkforge_code_context`](../tools/sparkforge_code_context.md)

## `sparkforge-aws code doctor`

Diagnostico local do indice e da superficie. Sai 1 quando alguma checagem falha. Nao testa conectividade de internet.

```bash
sparkforge-aws code doctor --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws code export`

Exporta o grafo no formato de extracao que a fonte publica.

```bash
sparkforge-aws code export --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--no-communities` | não | liga/desliga |  | `True` | Nao calcula comunidade. `algorithm` sai `null`, que diz 'nao calculei'. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para as contagens e a declaracao de compatibilidade; `normal` e `full` trazem nos e arestas. |

### Tool MCP equivalente

[`sparkforge_code_export`](../tools/sparkforge_code_export.md)

## `sparkforge-aws code index`

```bash
sparkforge-aws code index --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws code init`

Prepara o indice sob --root: preflight de seguranca, diretorio, conferencia do .gitignore, banco, indexacao e integridade. `index` e o nome antigo do mesmo comando.

```bash
sparkforge-aws code init --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws code path`

O caminho mais curto de chamadas entre dois simbolos. Nunca o corpo.

```bash
sparkforge-aws code path --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `origem` (posicional) | sim | texto |  |  |  |
| `destino` (posicional) | sim | texto |  |  |  |
| `--depth` | não | texto |  | `6` | Teto de saltos. Satura no maximo; atingi-lo sai como `depth_exhausted`. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para o veredito e as contagens do grafo; `normal` e `full` acrescentam os nos do caminho. |

### Tool MCP equivalente

[`sparkforge_code_path`](../tools/sparkforge_code_path.md)

## `sparkforge-aws code purge`

Apaga SOMENTE .sparkforge_aws/local/codeintel/. Qualquer outro diretorio e recusado.

```bash
sparkforge-aws code purge --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws code read`

Le um trecho do repositorio, por --node-id OU por --file com faixa. Tetos duros: 250 linhas, 32 KiB, 4096 tokens.

```bash
sparkforge-aws code read --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--node-id` | não | texto |  |  |  |
| `--file` | não | texto |  |  | Caminho RELATIVO a --root. |
| `--start-line` | não | texto |  |  |  |
| `--end-line` | não | texto |  |  |  |
| `--context-lines` | não | texto |  | `3` |  |
| `--max-tokens` | não | texto |  | `1200` |  |

### Tool MCP equivalente

[`sparkforge_code_read`](../tools/sparkforge_code_read.md), [`sparkforge_code_symbol`](../tools/sparkforge_code_symbol.md)

## `sparkforge-aws code search`

Busca simbolo por parte do nome.

```bash
sparkforge-aws code search --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `term` (posicional) | sim | texto |  |  |  |
| `--kind` | não | texto |  |  | Filtra por tipo de no: function, class, method. |
| `--path-prefix` | não | texto |  |  | Filtra por prefixo do caminho relativo. |
| `--limit` | não | texto |  | `20` |  |

### Tool MCP equivalente

[`sparkforge_code_search`](../tools/sparkforge_code_search.md)

## `sparkforge-aws code shape`

Comunidades e nos de maior grau. Nao e julgamento, e forma.

```bash
sparkforge-aws code shape --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--top` | não | texto |  | `20` | Quantas comunidades e quantos nos por grau. Satura no teto. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para as contagens e o metodo; `normal` e `full` acrescentam os membros e a lista por grau. |

### Tool MCP equivalente

[`sparkforge_code_shape`](../tools/sparkforge_code_shape.md)

## `sparkforge-aws code status`

Estado do indice: frescor, contagens, seguranca e o que mudou na arvore.

```bash
sparkforge-aws code status --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Mesmos niveis das tools de fact, conteudo proprio deste verbo: `full` acrescenta o bloco de seguranca (SPEC 67) e o de mudancas (SPEC 63); `normal` e `summary` param no estado do indice. |

### Tool MCP equivalente

[`sparkforge_code_status`](../tools/sparkforge_code_status.md), [`sparkforge_code_sync`](../tools/sparkforge_code_sync.md)

## `sparkforge-aws code symbol`

Metadado, vizinhanca e raio de impacto de um simbolo. Nunca o corpo.

```bash
sparkforge-aws code symbol --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |
| `node_id` (posicional) | sim | texto |  |  |  |
| `--depth` | não | texto |  | `1` |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | `summary` para no metadado; `normal` acrescenta vizinhanca direta; `full` acrescenta o raio de impacto e os testes nele. |

### Tool MCP equivalente

[`sparkforge_code_read`](../tools/sparkforge_code_read.md), [`sparkforge_code_symbol`](../tools/sparkforge_code_symbol.md)

## `sparkforge-aws code sync`

Poe o indice em dia com a arvore. Unica escrita do verbo.

```bash
sparkforge-aws code sync --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--root` | não | texto |  | `.` |  |
| `--db` | não | texto |  |  | Arquivo do indice. Default: `.sparkforge_aws/local/codeintel/graph.sqlite3` sob --root, que esta no `.gitignore` desde 715a657. Apontar para fora dali e escolha de quem chama, e o arquivo passa a ser candidato a commit. |

### Tool MCP equivalente

[`sparkforge_code_status`](../tools/sparkforge_code_status.md), [`sparkforge_code_sync`](../tools/sparkforge_code_sync.md)
