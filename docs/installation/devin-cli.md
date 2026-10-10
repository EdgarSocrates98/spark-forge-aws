# spark-forge-aws + Devin CLI

```bash
cd ~/meu-projeto
sparkforge-aws install
```

Assets vão para `.devin/skills/` e `.agents/` (Devin lê ambos). Abra
`devin` no diretório do projeto.

MCP: a entrada `mcpServers["sparkforge-aws"]` em `.mcp.json` é consumida pelo
host — `devin mcp list` na raiz do projeto lista o server na hora (verificado
nativamente).
