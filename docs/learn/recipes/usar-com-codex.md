# Receita — usar com o Codex CLI

**O quê:** o install escreve `.codex/agents/*.toml` (14 coordenadores),
skills em `.codex/skills/`, e — **só em `--scope user`** — o bloco MCP em
`~/.codex/config.toml`.
**Por que:** no Codex o `playbook` é o piso de orquestração: é o único
caminho que decompõe o coordenador em passos sem despacho de subagente.
**Quando:** investigação agêntica no Codex sobre um repo com o Forge.
**Quando não:** quando o objetivo é despachar coordenadores como
subagentes — Codex não tem esse mecanismo; o playbook cobre.

## Problema

"Como faço o Codex CLI usar o SparkForge?"

## Pré-requisitos

`sparkforge-aws install` no repo (project para agents/skills) **e**
`--scope user --host codex` se quiser MCP no Codex. Codex CLI presente
(`codex --version`; verificado em 0.160.0).

## Passo a passo

```bash
# agents + skills no projeto
sparkforge-aws install --scope project --root . --host codex --profile full

# MCP — o Codex só lê config de usuário
sparkforge-aws install --scope user --host codex

codex mcp list
# sparkforge-aws: enabled
```

Na sessão, o caminho determinístico:

```bash
sparkforge-aws playbook spark-performance-architect --repo .
```

## Saída esperada / interpretação

Verificado nativamente em Codex 0.160.0: `codex mcp list` mostra
`sparkforge-aws` `enabled` com o comando
`python -m sparkforge_aws.adapters.mcp --transport stdio` — vindo de
`~/.codex/config.toml` (bloco gerenciado `>>> sparkforge`).

## Verificação

```bash
codex mcp list                          # enabled
ls .codex/agents                        # 14 .toml de coordenadores
```

## Limitações

- **Codex não lê `.mcp.json` nem `.codex/config.toml` de projeto**
  (observado em 0.160.0). MCP em escopo projeto sai como
  `mcp-scope:codex → NOT_APPLICABLE` no recibo — declarado, nunca escondido.
- Executores não viram `.toml` (o schema exige `description`, que eles não
  carregam) — por isso 14 agents e não 19; o `playbook` os sequencia.
- Sem despacho de subagente: `playbook` é o caminho, não um fallback.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `codex mcp list` sem o server | install só em escopo project | `install --scope user --host codex` ou `codex mcp add` |
| esperando subagentes | plataforma sem o mecanismo | `playbook <coordenador>` |

## Uso por agentes

Os `.toml` de `.codex/agents/` são os mesmos 14 coordenadores do canônico
`agents/*.md`, na sintaxe que o Codex consome.

## Leitura seguinte

- [usar-agents](usar-agents.md)
- `GUIA_DE_USO.md` §3 — walkthrough Codex
