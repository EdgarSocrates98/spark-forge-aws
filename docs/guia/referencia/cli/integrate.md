<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge integrate`

Instala skills, agents e o MCP do SparkForge nos diretorios de USUARIO do host (Claude Code por marketplace local; Devin, Codex e Copilot CLI), a partir do pacote instalado. Nada e escrito no repositorio, exceto a remocao da copia vendorizada que o operador escolher.

```bash
sparkforge integrate --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `host` (posicional) | sim | `claude`, `devin`, `codex`, `copilot`, `all` |  |  | Host, ou all. |
| `--scope` | sim | `user` |  |  | Escopo da integracao; so user nesta versao. |
| `--dry-run` | não | liga/desliga |  |  | Lista o que seria escrito, sem escrever. |
| `--on-conflict` | não | `overwrite`, `merge`, `ignore` |  |  | Copia vendorizada em dobro no repositorio atual: overwrite apaga do repo, merge apaga so o identico, ignore nao toca. Sem a flag e sem terminal: ignore. |

## Tool MCP equivalente

Nenhuma: este verbo existe só na CLI.
