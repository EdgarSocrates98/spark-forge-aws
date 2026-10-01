<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_report_verify`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Confere a assinatura de um relatorio e diz QUAL das tres partes divergiu -- evidencia, catalogo ou corpo --, em vez de devolver apenas 'invalido'. Cobre tambem bloco ausente e bloco malformado, que sao estados diferentes de 'nao corresponde': relatorio sem bloco nao e relatorio adulterado, e confundir os dois faria o leitor desconfiar do texto errado.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `findings_path` | string | sim | O mesmo arquivo de findings contra o qual o relatorio foi assinado. |
| `report_path` | string | sim |  |

## Na CLI

[`sparkforge report sign`](../cli/report.md), [`sparkforge report verify`](../cli/report.md)

## Capacidade

prove a report corresponds to its evidence and catalog

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
