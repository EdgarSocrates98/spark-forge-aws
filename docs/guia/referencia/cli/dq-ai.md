<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws dq-ai`

Avalia governanca Glue DQ ADVANCED sobre facts e artefatos observados.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws dq-ai assess`](#sparkforge-aws-dq-ai-assess) | Compõe facts, julga regras e renderiza o relatório canônico. |

## `sparkforge-aws dq-ai assess`

Compõe facts, julga regras e renderiza o relatório canônico.

```bash
sparkforge-aws dq-ai assess --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  |  |
| `--dqdl` | não | texto |  | `` | DQDL externo a validar por sintaxe. |
| `--review` | não | texto |  | `` | Manifesto externo de revisão humana. |
| `--cost-facts` | não | texto |  | `` | Medição observada de custo Athena em JSON. |
| `--glue` | não | texto |  | `` |  |
| `--spark` | não | texto |  | `` |  |
| `--python` | não | texto |  | `` |  |
| `--view` | não | `all`, `maintainer`, `operator`, `security_compliance` |  | `all` |  |
| `--out` | não | texto |  |  | Escreve o relatório completo (JSON). |

### Tool MCP equivalente

[`sparkforge_aws_analyze_dq_ai`](../tools/sparkforge_aws_analyze_dq_ai.md), [`sparkforge_aws_dq_ai_assess`](../tools/sparkforge_aws_dq_ai_assess.md)
