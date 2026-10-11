<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_aws_ai`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Estado observado dos hosts de IA no repo: binario detectado (caminho), versao lida por `<bin> --version`, autenticacao pelo subcomando oficial de status (so o booleano `logged_in` entra na resposta — a saida pode listar credenciais) e estado da integracao lido do manifesto do install. `host: all` mede os quatro. So le: nunca lanca processo — abrir o host e `sparkforge-aws ai <host> --launch`, so na CLI, com TTY e aprovacao humana.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `host` | string: `claude`, `devin`, `codex`, `copilot`, `all` | não | Host a medir (padrao: all). |
| `repo` | string | não | Raiz do repositorio (padrao: .). |

## Na CLI

[`sparkforge-aws ai`](../cli/ai.md)

## Capacidade

open the AI host in the repository

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
