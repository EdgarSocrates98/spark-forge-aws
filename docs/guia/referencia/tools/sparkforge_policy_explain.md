<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_policy_explain`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Diz o que a policy de seguranca do repositorio (`.sparkforge/policy.yaml`) decide para UM comando de shell (`bash_text`, so comparado como texto, nunca executado), UM caminho de escrita (`file_path`) ou UMA tool MCP (`tool`): allow, ask ou deny, a regra que casou e a porta que impoe (hook PreToolUse para deny de shell e escrita, permissions.ask do `.claude/settings.json` para ask, servidor MCP para deny de tool). So le. Regra de shell casa o texto do comando, nao o programa: nao e fronteira de seguranca. Sem arquivo de policy, `active: false` e allow.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `bash_text` | string | não | Texto do comando de shell a conferir (nunca executado). |
| `file_path` | string | não | Caminho de escrita a conferir. |
| `repo` | string | não | Raiz do repositorio (padrao: .). |
| `tool` | string | não | Nome de tool MCP a conferir. |

## Na CLI

[`sparkforge policy check`](../cli/policy.md), [`sparkforge policy explain`](../cli/policy.md), [`sparkforge policy sync-settings`](../cli/policy.md)

## Capacidade

declare and explain the repository security policy

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
