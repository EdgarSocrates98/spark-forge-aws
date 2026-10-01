<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_report_sign`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Escreve, no fim do relatorio, o bloco que prova CORRESPONDENCIA entre o texto, a evidencia e o catalogo que o produziram -- nunca autoria: nao ha chave e nao ha segredo, e qualquer um com os mesmos findings produz a mesma assinatura. O limite vai escrito dentro do bloco, porque bloco que sugira autoridade mente por omissao. O corpo assinado e tudo que vem ANTES do delimitador de abertura, entao o bloco nunca entra no hash que carrega. Os quatro campos nao-corpo saem do arquivo de FINDINGS, e nao do de facts: so o finding carrega `evidence` (os fact_id citados), `rule_id`, `catalog_version` e `schema_version`. Reassinar e barato e idempotente.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `findings_path` | string | sim | Findings (JSON) gerados por `sparkforge judge --out`. |
| `report_path` | string | sim | Markdown do relatorio. E reescrito no lugar. |

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
| `readOnlyHint` | `false` |
