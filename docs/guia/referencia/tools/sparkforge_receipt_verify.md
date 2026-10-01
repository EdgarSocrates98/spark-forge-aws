<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_receipt_verify`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Confere um recibo de execucao e diz QUAL parte divergiu -- `version`, `integrity`, `case`, `evidence`, `judgment`, `decision`, `proof`, `tools`, `host` --, em vez de devolver so 'invalido'. Arquivo apagado sai em `missing`, nunca em `diverged`. Fonte que nao esta aqui (`traces.db` de outra maquina, transcript nao informado) sai em `not_rechecked` e nao derruba `valid`. Os spans sao reconferidos pelos `span_id` do recibo: os que o run ganhou depois da emissao contam em `spans_after_emit` e ficam fora da comparacao.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `receipt_path` | string | sim | `.sparkforge/receipts/<receipt_id>.json`, dentro do repo. |
| `repo` | string | sim |  |
| `host_transcript_path` | string | não | O mesmo transcript da emissao, para reconferir `host`. |

## Na CLI

[`sparkforge receipt emit`](../cli/receipt.md), [`sparkforge receipt verify`](../cli/receipt.md)

## Capacidade

prove what an execution used and decided

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
