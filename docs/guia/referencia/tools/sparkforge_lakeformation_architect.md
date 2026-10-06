<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_lakeformation_architect`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Avalia uma arquitetura declarada de Lake Formation de forma offline e determinística. Separa engine/runtime, FGAC/FTA, formato, operação, ownership de catálogo, cross-account e credential vending; devolve consistent, unresolved ou blocked. A seção review compõe revisão de PySpark/Terraform, configuração tardia, explain-access, autorização, root-cause, preflight, migração, cross-review e progressive disclosure. Não chama AWS, não sugere bypass por S3 e não estima custo ou ganho.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `payload` | object | sim | Declaração JSON da arquitetura; inclua engine, runtime, source_catalog, target_catalog e evidence quando disponíveis. |

## Na CLI

[`sparkforge-aws lakeformation architect`](../cli/lakeformation.md)

## Capacidade

evaluate a version-aware Lake Formation architecture without AWS mutation

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
