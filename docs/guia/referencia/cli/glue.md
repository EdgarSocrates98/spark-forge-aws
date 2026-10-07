<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws glue`

Comandos especificos do runtime AWS Glue.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws glue dependency-audit`](#sparkforge-aws-glue-dependency-audit) | Audita dependencia Python e binario Scala do job contra um runtime. |

## `sparkforge-aws glue dependency-audit`

Audita dependencia Python e binario Scala do job contra um runtime.

```bash
sparkforge-aws glue dependency-audit --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `path` (posicional) | sim | texto |  |  | Diretorio do job (requirements*.txt e .jar). |
| `--glue` | sim | texto |  |  | Versao de Glue a auditar. |

### Tool MCP equivalente

[`sparkforge_aws_glue_dependency_audit`](../tools/sparkforge_aws_glue_dependency_audit.md)
