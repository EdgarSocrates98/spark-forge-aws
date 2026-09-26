<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge detach`

Remove a integracao de usuario do host: so o que o manifesto ~/.sparkforge/integrations.json registrou e ainda tem o sha256 gravado.

```bash
sparkforge detach --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `host` (posicional) | sim | `claude`, `devin`, `codex`, `copilot`, `all` |  |  | Host, ou all. |
| `--scope` | não | `user` |  | `user` | Escopo da integracao; so user nesta versao. |
| `--dry-run` | não | liga/desliga |  |  | Lista o que seria removido, sem remover. |

## Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
