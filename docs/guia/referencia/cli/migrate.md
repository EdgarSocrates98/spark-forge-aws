<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge migrate`

Avalia migracao entre versoes de runtime com o catalogo.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge migrate controlm`](#sparkforge-migrate-controlm) | Julga a migracao de um job Control-M entre um par de versoes, degrau a degrau, por CAPACIDADE e nao por runtime. |
| [`sparkforge migrate emr`](#sparkforge-migrate-emr) | Julga a migracao de um job EMR entre um par de releases, degrau a degrau, na matriz da plataforma escolhida. |
| [`sparkforge migrate glue`](#sparkforge-migrate-glue) | Julga a migracao de um job Glue entre um par de versoes, degrau a degrau. |

## `sparkforge migrate controlm`

Julga a migracao de um job Control-M entre um par de versoes, degrau a degrau, por CAPACIDADE e nao por runtime.

```bash
sparkforge migrate controlm --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  | Diretorio com as definicoes de `Jobs-as-Code` (`*.json`), ou um arquivo sozinho. E o mesmo artefato que o `ctm build` valida. |
| `--from` | sim | texto |  |  | Versao de Control-M de origem, na grafia da matriz (`9.0.21.300`). |
| `--to` | sim | texto |  |  | Versao alvo. Pode ser ANTERIOR a origem: descer e caso legitimo. |
| `--out` | não | texto |  |  | Escreve o assessment completo (JSON) neste arquivo. |

### Tool MCP equivalente

[`sparkforge_migration_assess`](../tools/sparkforge_migration_assess.md)

## `sparkforge migrate emr`

Julga a migracao de um job EMR entre um par de releases, degrau a degrau, na matriz da plataforma escolhida.

```bash
sparkforge migrate emr --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  | Diretorio do job -- codigo, requirements*.txt, .jar, os .tf quando existem e o inventario de consumidores em .sparkforge/consumers.yaml --, ou um .py sozinho. |
| `--platform` | sim | `emr_ec2`, `emr_serverless`, `emr_eks` |  |  | Qual matriz de EMR ordena o caminho e da o runtime de cada degrau. |
| `--from` | sim | texto |  |  | Release de origem, com ou sem o prefixo `emr-`. |
| `--to` | sim | texto |  |  | Release alvo, com ou sem o prefixo `emr-`. |
| `--out` | não | texto |  |  | Escreve o assessment completo (JSON) neste arquivo. |

### Tool MCP equivalente

[`sparkforge_migration_assess`](../tools/sparkforge_migration_assess.md)

## `sparkforge migrate glue`

Julga a migracao de um job Glue entre um par de versoes, degrau a degrau.

```bash
sparkforge migrate glue --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  | Diretorio do job -- codigo, requirements*.txt, .jar, os .tf quando existem e o inventario de consumidores em .sparkforge/consumers.yaml --, ou um .py sozinho. |
| `--from` | sim | texto |  |  | Versao de Glue de origem. |
| `--to` | sim | texto |  |  | Versao de Glue alvo. |
| `--out` | não | texto |  |  | Escreve o assessment completo (JSON) neste arquivo. |

### Tool MCP equivalente

[`sparkforge_migration_assess`](../tools/sparkforge_migration_assess.md)
