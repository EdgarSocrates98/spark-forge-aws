# MCP — spark-forge-aws

Servidor MCP: `python -m sparkforge_aws.adapters.mcp --transport stdio`

A instalação registra uma entrada gerenciada em `.mcp.json`:

```json
{
  "mcpServers": {
    "sparkforge-aws": {
      "command": "<venv>/python",
      "args": ["-m", "sparkforge_aws.adapters.mcp", "--transport", "stdio"]
    }
  }
}
```

`command` aponta para o Python do ambiente onde o SparkForge está
instalado — recriar o venv pede `sparkforge-aws install --update` para
regravar o caminho. A entrada é a forma universal `command`/`args`: um só
`.mcp.json` serve todos os hosts que o leem. O arquivo fica visível no
drift do `status`: apagado ou editado fora do install degrada o estado
até `repair` restaurar.

Verificar de verdade:

```bash
sparkforge-aws status --scope project --root .
sparkforge-aws install doctor --scope project --root .
```

`status` responde `healthy|degraded` sobre manifesto + config; `install
doctor` aprofunda por host. `install` grava, `status` lê, `repair`
corrige — os três dividem o mesmo manifesto, então o que um mede o outro
restaura.

## O que cada host lê (verificado nativamente)

| Host | Onde consome |
|---|---|
| Devin | `.mcp.json` do projeto — `devin mcp list` lista o server na hora |
| Claude Code | `.mcp.json` do projeto — **pede aprovação na sessão**; `claude mcp list` mostra os aprovados |
| Codex | `~/.codex/config.toml` — **não lê `.mcp.json` de projeto**; use `install --scope user --host codex` ou `codex mcp add` |
| Copilot | `mcp-config.json` do usuário |

Em `--scope user` o registro vai para o config do usuário de cada host
(`~/.codex/config.toml`, `~/.config/devin/mcp_config.json`, …), nunca um
arquivo compartilhado.

Handshake real, observado neste repositório: o server sobe por stdio,
responde `tools/list` com as 146 tools e invoca
`sparkforge_aws_runtime_detect` com saída estruturada.
