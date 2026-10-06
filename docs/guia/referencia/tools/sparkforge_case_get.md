<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_case_get`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Le o estado atual do case (.sparkforge_aws/case.yaml): fase, gates, runtime detectado, indices de facts e findings. Falha com um erro que nomeia `sparkforge-aws case open` quando nenhum case existe ainda no repositorio.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim |  |

## Na CLI

[`sparkforge-aws case get`](../cli/case.md), [`sparkforge-aws case open`](../cli/case.md), [`sparkforge-aws case update`](../cli/case.md)

## Capacidade

maintain investigation state

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
