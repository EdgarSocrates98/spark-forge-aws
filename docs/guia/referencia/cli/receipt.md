<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge receipt`

Recibo content-addressed da execucao do case: prova CORRESPONDENCIA entre o recibo e os artefatos, nunca autoria.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge receipt emit`](#sparkforge-receipt-emit) | Grava .sparkforge/receipts/<receipt_id>.json com caminho e sha256 do case, dos facts, dos findings, do report, do blackboard, dos ADRs e dos debates, os spans do run declarado e o host declarado. Sem conteudo de caso. |
| [`sparkforge receipt verify`](#sparkforge-receipt-verify) | Recalcula cada parte contra o disco e diz qual divergiu. Sai com codigo 1 quando o recibo nao corresponde. |

## `sparkforge receipt emit`

Grava .sparkforge/receipts/<receipt_id>.json com caminho e sha256 do case, dos facts, dos findings, do report, do blackboard, dos ADRs e dos debates, os spans do run declarado e o host declarado. Sem conteudo de caso.

```bash
sparkforge receipt emit --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Arquivo de facts. Repetivel, e a repeticao e o contrato: a UNIAO do case. |
| `--findings` | sim | texto |  |  | Findings (JSON) gerados por `judge --out`. |
| `--now` | sim | texto |  |  | Instante ISO 8601 da emissao. Entra no hash. |
| `--report` | não | texto |  |  | Relatorio assinado, se houver. |
| `--run-id` | não | texto |  |  | Run cujos spans de tool entram. Sem ele, a parte tools sai em unresolved. |
| `--host-transcript` | não | texto |  | `` | Transcript JSONL do host. So o sha256 entra; modelo e agente saem dele. |
| `--provider` | não | texto |  |  | Provider do host, DECLARADO (anthropic). |
| `--repo` | não | texto |  | `.` | Raiz do case. Caminhos relativos resolvem contra ela. |

### Tool MCP equivalente

[`sparkforge_receipt_emit`](../tools/sparkforge_receipt_emit.md), [`sparkforge_receipt_verify`](../tools/sparkforge_receipt_verify.md)

## `sparkforge receipt verify`

Recalcula cada parte contra o disco e diz qual divergiu. Sai com codigo 1 quando o recibo nao corresponde.

```bash
sparkforge receipt verify --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--receipt` | sim | texto |  |  |  |
| `--host-transcript` | não | texto |  | `` | O mesmo transcript da emissao; sem ele a parte host sai not_rechecked. |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

[`sparkforge_receipt_emit`](../tools/sparkforge_receipt_emit.md), [`sparkforge_receipt_verify`](../tools/sparkforge_receipt_verify.md)
