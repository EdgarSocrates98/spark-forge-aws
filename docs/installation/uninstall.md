# Uninstall — spark-forge-aws

```bash
sparkforge-aws uninstall                # remove só arquivos gerenciados (todos os hosts)
sparkforge-aws uninstall --host devin   # remove só os assets daquele host
sparkforge-aws uninstall --purge        # + remove o estado local (.sparkforge_aws/)
```

`--host` aceita um nome (`devin`, `claude`, `codex`, `copilot`) e remove
só o que aquele host possui no ledger — os demais hosts ficam; a entrada
`sparkforge-aws` do `.mcp.json` compartilhado sai quando é o host dono
dela que sai. `--scope`/`--root` selecionam o alvo como no `install`;
`--dry-run` mostra o plano sem escrever (`status: planned`,
`lifecycle.state: planned`); `--yes` aprova sem perguntar.

O ledger SHA-256 decide ownership: arquivos que você criou ou modificou
depois da instalação ficam no lugar (reportados como `kept`/recusa
`editado_pelo_usuario`). Diretórios que esvaziam são podados; os seus
permanecem.
