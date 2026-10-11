# Receita — usar com o Claude Code

**O quê:** o install escreve `.claude/skills/`, `.claude/agents/` (perfil
`full`) e `.mcp.json`; o Claude Code ativa as skills por linguagem natural
e despacha coordenadores como subagentes.
**Por que:** é o host com o mapeamento mais completo — os 14 coordenadores
viram perfis de subagente, e o `next-step` diz qual chamar.
**Quando:** investigação agêntica no Claude Code sobre um repo com o Forge
instalado.
**Quando não:** execução headless em pipeline — use a CLI/MCP direto.

## Problema

"Como faço o Claude Code usar o SparkForge neste projeto?"

## Pré-requisitos

`sparkforge-aws install --scope project --root . --profile full` (agents
só aterrissam no `full`) e Claude Code instalado.

## Passo a passo

```bash
claude mcp list   # o server do projeto aparece após aprovação de sessão
```

Na sessão:

```text
Use the emr-infra-reviewer profile as a subagent to review this EMR cluster.
Use the review-emr-cluster skill on this cluster dump.
```

## Saída esperada / interpretação

Nomes de skill e de perfil acionam a superfície: a skill chama os verbos
determinísticos via MCP e devolve findings com `rule_id` + `fact_id` de
evidência.

## Verificação

```bash
ls .claude/skills | wc -l      # 61 entradas = 60 skills + `_shared/`
ls .claude/agents              # 14 coordenadores + executors/
```

## Limitações

- **`.mcp.json` de projeto pede aprovação por sessão** — `claude mcp list`
  mostra os servers aprovados/globais; a do projeto entra depois que a
  sessão a aprova. Não é instalação quebrada: é o modelo de trust do host.
- `.claude/` e `.agents/` são espelhos gerados do canônico `agents/` +
  `skills/` — edite a fonte, nunca o espelho.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| MCP do projeto não lista | aprovação pendente | aprove na sessão; `claude mcp list` confirma |
| coordenador sem efeito | install `recommended` | reinstall `--profile full` |

## Uso por agentes

`CLAUDE.md` recebe o bloco gerenciado `sparkforge-aws:managed` com o estado
do install — o host sabe que o Forge existe sem ninguém contar.

## Leitura seguinte

- [usar-agents](usar-agents.md)
- `GUIA_DE_USO.md` §2 — walkthrough Claude Code
- `AGENT_PROTOCOL.md` — as regras que os coordenadores seguem
