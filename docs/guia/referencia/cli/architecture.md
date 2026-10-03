<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge architecture`

Avalia arquitetura declarada sem escolher por preferência ou custo inventado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge architecture streaming`](#sparkforge-architecture-streaming) | Compara candidatos streaming por constraints factuais declaradas. |

## `sparkforge architecture streaming`

Compara candidatos streaming por constraints factuais declaradas.

```bash
sparkforge architecture streaming --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--path` | sim | texto |  |  | JSON com requirements e assumptions separados. |
| `--out` | não | texto |  |  | Escreve o ADR e a matriz completa neste arquivo. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
