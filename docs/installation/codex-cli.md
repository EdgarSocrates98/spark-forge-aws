# spark-forge-aws + Codex CLI

```bash
cd ~/meu-projeto
sparkforge-aws install --host codex
```

Assets vão para `.codex/agents/*.toml` (14 coordenadores — os executores
não viram TOML porque o schema do Codex exige `description`, que eles não
têm) e `.codex/skills/` + `.agents/skills/`. Abra `codex` no diretório.

MCP: **o Codex não lê `.mcp.json` nem `.codex/config.toml` de projeto**
(verificado em 0.160.0). Em escopo projeto o recibo declara
`mcp-scope:codex` como `NOT_APPLICABLE` — nunca como sucesso falso. Para
MCP de verdade:

```bash
sparkforge-aws install --scope user --host codex
codex mcp list   # sparkforge-aws: enabled
```

Isso grava o bloco gerenciado `>>> sparkforge` em `~/.codex/config.toml`
apontando para `python -m sparkforge_aws.adapters.mcp --transport stdio`.
Alternativa manual: `codex mcp add`.

Sem despacho de subagente no Codex — a orquestração é o `playbook`:

```bash
sparkforge-aws playbook spark-performance-architect --repo .
```
