<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws economy`

O que a execucao poe na janela de contexto: byte medido, nunca token estimado.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws economy provider-cost`](#sparkforge-aws-economy-provider-cost) | Calcula custo observado do transcript com pricing e cost_basis declarados. |
| [`sparkforge-aws economy report`](#sparkforge-aws-economy-report) | Agrupa os spans de um run e poe a superficie ao lado. |

## `sparkforge-aws economy provider-cost`

Calcula custo observado do transcript com pricing e cost_basis declarados.

```bash
sparkforge-aws economy provider-cost --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--host-transcript` | sim | texto |  |  |  |
| `--pricing` | sim | texto |  |  |  |
| `--out` | não | texto |  |  | Escreve o relatorio (JSON) neste arquivo. |

### Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.

## `sparkforge-aws economy report`

Agrupa os spans de um run e poe a superficie ao lado.

```bash
sparkforge-aws economy report --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--run-id` | sim | texto |  |  |  |
| `--host-transcript` | não | texto |  | `` | Transcript JSONL do host, quando houver. Sem ele o relatorio traz `tokens_unresolved` -- token de provider e do host, nao deste processo. |
| `--out` | não | texto |  |  | Escreve o relatorio (JSON) neste arquivo. |

### Tool MCP equivalente

[`sparkforge_economy_report`](../tools/sparkforge_economy_report.md)
