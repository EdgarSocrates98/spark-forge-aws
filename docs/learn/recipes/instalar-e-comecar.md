# Receita — instalar e começar

**O quê:** `sparkforge-aws install` escreve a superfície agentic do Forge no
seu projeto: `.mcp.json`, skills e — no perfil `full` — agents, com manifesto
e recibo auditáveis.
**Por que:** a experiência é agent-first: depois do install, o host de IA é a
interface; a CLI fica como caminho determinístico e de CI.
**Quando:** primeiro uso num repositório; onboarding de um projeto novo.
**Quando não:** contribuir no próprio SparkForge — o repo se autodescreve,
não precisa de install.

## Problema

"Quero o SparkForge respondendo no meu host de IA sobre este repositório."

## Pré-requisitos

Python 3.10+ e `sparkforge-aws` instalado (`pip install -e .` no clone, ou o
pacote). Um diretório de projeto onde o host vai trabalhar.

## Passo a passo

```bash
# skills + MCP (perfil padrão)
sparkforge-aws install --scope project --root . --host all

# com a equipe de coordenadores (14) + executores (5)
sparkforge-aws install --scope project --root . --host all --profile full

# conferir o que aterrissou
sparkforge-aws status --scope project --root .
```

## Saída esperada / interpretação

`status: healthy` e o recibo lista por host o que foi `written`,
`managed_file` e `config`. `.mcp.json` na raiz com o server
`sparkforge-aws`; skills sob `.claude/skills/`, `.agents/skills/` e os
espelhos de cada host. Verificado em sessão real: 1393 arquivos gerenciados
num `full`, `status` healthy, e `uninstall` removendo tudo e preservando o
estado do case.

## Verificação

```bash
sparkforge-aws status --scope project --root .   # healthy
devin mcp list                                  # o server sparkforge-aws aparece
```

## Limitações

- `recommended` não instala agents — o time de coordenadores pede
  `--profile full` (deliberado: skills já cobrem o workflow).
- Codex em escopo `project` não lê `.mcp.json` — MCP exige
  `--scope user` ou `codex mcp add` (o recibo registra `mcp-scope:codex`
  como `NOT_APPLICABLE`, nunca como sucesso falso).
- Claude lê `.mcp.json` de projeto com aprovação por sessão.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `status: degraded` | arquivo gerenciado apagado/editado | `sparkforge-aws repair --root .` |
| recibo `failed` com `refused` | config já existente e não gerenciada | revise o path apontado; o instalador preserva arquivo do usuário |

## Uso por agentes

O bloco gerenciado `sparkforge-aws:managed` em `AGENTS.md`/`CLAUDE.md` diz ao
host que o Forge está instalado e onde está o MCP. Depois do install, peça em
linguagem natural — as skills ativam pelo pedido.

Para medir e abrir o host sem sair do terminal:

```bash
sparkforge-aws ai            # painel: binário, versão, login, integração dos 4 hosts
sparkforge-aws ai devin --launch   # abre o CLI do host aqui (só TTY; deslogado não lança)
```

## Leitura seguinte

- [quickstart](../../installation/quickstart.md) — caminho rápido ponta a ponta
- [first-run](../../tutorials/first-run.md) — primeira análise guiada
- [usar-com-devin](usar-com-devin.md) · [usar-com-claude](usar-com-claude.md) · [usar-com-codex](usar-com-codex.md)
- [verificar-mcp](verificar-mcp.md)
