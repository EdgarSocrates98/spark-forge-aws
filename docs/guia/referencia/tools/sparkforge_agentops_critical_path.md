<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_agentops_critical_path`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Caminho critico medido do run: maiores duracoes, retries e waiting entre spans consecutivos.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `run_id` | string | sim |  |
| `db_path` | string | não |  |
| `repo` | string | não |  |

## Na CLI

Sem verbo de CLI declarado para esta tool.

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
