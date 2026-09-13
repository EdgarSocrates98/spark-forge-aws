<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge iceberg`

Comandos especificos de Apache Iceberg.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge iceberg assess-upgrade`](#sparkforge-iceberg-assess-upgrade) | Avalia subir o format version da tabela contra quem a consome. NAO executa. |

## `sparkforge iceberg assess-upgrade`

Avalia subir o format version da tabela contra quem a consome. NAO executa.

```bash
sparkforge iceberg assess-upgrade --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  | Diretorio do job, com o inventario em .sparkforge/consumers.yaml. |
| `--from` | sim | texto |  |  | Format version de origem. |
| `--to` | sim | texto |  |  | Format version alvo. |

### Tool MCP equivalente

[`sparkforge_iceberg_assess_upgrade`](../tools/sparkforge_iceberg_assess_upgrade.md)
