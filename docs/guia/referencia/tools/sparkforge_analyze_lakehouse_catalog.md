<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_analyze_lakehouse_catalog`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Analisa topologia declarada de Glue, Iceberg REST, Polaris, S3 Tables, Lake Formation e integrações futuras, relacionando engines, tabelas e bindings com evidence. Não negocia protocolo, não consulta catálogos e não cria recursos. Recusa campos de segredo e mantém referências ou compatibilidade não resolvidas em unresolved.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | sim | Arquivo JSON ou YAML da topologia de catalog. |

## Na CLI

[`sparkforge analyze lakehouse-catalog`](../cli/analyze.md)

## Capacidade

analyze open lakehouse catalog and multi-engine bindings

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
