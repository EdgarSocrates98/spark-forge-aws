# Troubleshooting — Spark Forge AWS (EN)

| Symptom | Action |
|---|---|
| `command not found: sparkforge-aws` | run `./setup.sh` again; open a **new** terminal (launcher lands on PATH) |
| `FORGE-INSTALL-LOCKED` | another install is running or was interrupted; the lock expires and is recovered automatically — retry |
| `FORGE-INSTALL-PLAN-NOT-APPROVED` | mutations require `--yes` after reviewing `--dry-run` — receipt exits `lifecycle.state: blocked` |
| `FORGE-INSTALL-NOT-A-REPO` | project scope needs a `.git` root or `--root` |
| `FORGE-INSTALL-DRIFT-UNREPAIRABLE` | managed files changed on disk beyond repair — check `status`, reinstall if intended |
| `lifecycle.state: unverified` | no evidence at the target — nothing installed (or measured) at that scope |
| `lifecycle.state: partially_applied` | partial drift — `sparkforge-aws repair` restores what the ledger declares |
| `lifecycle.state: applied` | written, verification pending — **not** proof of readiness |
| MCP `FAIL` + `stderr_tail` | missing dependency (e.g. the `mcp` extra) — install it and re-run `mcp verify` |
| stale/partial install | `uninstall` removes only ledger-owned files; `status`/`install doctor` show the truth |

Português: [troubleshooting.md](troubleshooting.md).
