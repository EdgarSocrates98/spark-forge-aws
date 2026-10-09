<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws uninstall`

Remove so o que o manifesto declara como gerenciado.

```bash
sparkforge-aws uninstall --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--scope` | não | `project`, `workspace`, `user` |  | `project` |  |
| `--host` | não | `claude`, `devin`, `codex`, `copilot`, `all` |  | `all` |  |
| `--root` | não | texto |  |  |  |
| `--purge` | não | liga/desliga |  |  | Apaga tambem o state dir .sparkforge_aws/install. |
| `--dry-run` | não | liga/desliga |  |  |  |

## Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
