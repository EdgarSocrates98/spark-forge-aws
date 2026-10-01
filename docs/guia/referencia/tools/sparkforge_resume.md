<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_resume`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Monta o payload de rehidratacao de um case: onde parou, runtime, baseline, achados principais, hipoteses abertas, gates, artefatos ausentes e proximo passo. `coverage.unresolved` e um sinal de ponto cego, nao de ausencia de problema -- um no nao resolvido nunca deve ser lido como 'sem achados'.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim |  |
| `findings` | array de object | não |  |
| `in_flight` | string | não |  |
| `unresolved` | integer | não |  |

## Na CLI

[`sparkforge handoff`](../cli/handoff.md), [`sparkforge resume`](../cli/resume.md)

## Capacidade

resume an investigation started in another tool

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
