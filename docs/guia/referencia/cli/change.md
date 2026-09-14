<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge change`

Autonomia L1-L2: gera o diff de um valor de configuracao (plan) e aplica um diff numa copia isolada para ver o que ele move nos achados (sandbox).

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge change plan`](#sparkforge-change-plan) | Diff e diff de rollback de um valor de configuracao, achado pela procedencia dos facts (Terraform --conf ou spark.conf.set). Nao aplica nada. |
| [`sparkforge change sandbox`](#sparkforge-change-sandbox) | Aplica um diff numa copia em .sparkforge/sandbox/<id>/, roda o scan antes e depois e compara os achados. A arvore principal nao muda. |

## `sparkforge change plan`

Diff e diff de rollback de um valor de configuracao, achado pela procedencia dos facts (Terraform --conf ou spark.conf.set). Nao aplica nada.

```bash
sparkforge change plan --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Facts do case (repetivel): a uniao que o judge recebeu. |
| `--repo` | não | texto |  | `.` | Raiz usada na extracao dos facts (padrao: .). |
| `--from-tune` | não | liga/desliga |  |  | Usa o valor que o tune deriva da medida. |
| `--set` | não | `CHAVE=VALOR` | sim |  | Valor a propor (repetivel), por exemplo spark.sql.shuffle.partitions=320. |
| `--out` | não | texto |  |  | Grava o diff neste arquivo .patch (so quando pedido). |

### Tool MCP equivalente

[`sparkforge_change_plan`](../tools/sparkforge_change_plan.md), [`sparkforge_change_sandbox`](../tools/sparkforge_change_sandbox.md)

## `sparkforge change sandbox`

Aplica um diff numa copia em .sparkforge/sandbox/<id>/, roda o scan antes e depois e compara os achados. A arvore principal nao muda.

```bash
sparkforge change sandbox --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do repositorio (padrao: .). |
| `--diff` | não | texto |  |  | Arquivo de diff unificado (de change plan --out ou de git diff). |
| `--clean` | não | liga/desliga |  |  | Apaga .sparkforge/sandbox/ e sai. |

### Tool MCP equivalente

[`sparkforge_change_plan`](../tools/sparkforge_change_plan.md), [`sparkforge_change_sandbox`](../tools/sparkforge_change_sandbox.md)
