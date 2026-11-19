# Troubleshooting — spark-forge-aws

| Sintoma | Ação |
|---|---|
| `command not found: sparkforge-aws` | rode `./setup.sh` de novo; abra terminal novo (launcher no PATH) |
| `FORGE-INSTALL-LOCKED` | outra instalação em curso; se foi interrompida, o lock expira/recupera sozinho |
| `FORGE-INSTALL-PLAN-NOT-APPROVED` | mutações exigem `--yes` (após o `--dry-run`) — recibo sai `lifecycle.state: blocked` |
| `FORGE-INSTALL-NOT-A-REPO` | escopo project precisa de `.git` ou `--root` |
| `lifecycle.state: unverified` | sem evidência no alvo — nada instalado (ou nada medido) naquele escopo |
| `lifecycle.state: partially_applied` | drift parcial — `sparkforge-aws repair` restaura o que o ledger declara |
| `lifecycle.state: applied` | escrito, verificação pendente — **não** é prova de prontidão |
| doctor FAIL em mcp-handshake | `sparkforge-aws mcp verify` mostra stderr_tail — geralmente dependência ausente |
| arquivo seu sumiu? | não deveria — instalação nunca sobrescreve conteúdo do usuário; backups em `<state_dir>/backups/` |
| drift detectado | `sparkforge-aws repair` restaura regiões gerenciadas mantendo o resto |
