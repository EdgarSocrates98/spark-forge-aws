<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws ai`

Abre o host de IA no repositorio: detecta o binario, le a versao, confere autenticacao pelo subcomando oficial de status e o estado da integracao. Com `--launch` e TTY, executa o CLI do host no diretorio; sem eles, o recibo traz `launch_command` para o operador. Host deslogado nao e lancado — `login_hint` aponta o login oficial.

```bash
sparkforge-aws ai --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `host` (posicional) | sim | `claude`, `devin`, `codex`, `copilot`, `all` |  | `all` | Host a abrir (padrao: all — mede os quatro, sem lancar). |
| `--launch` | não | liga/desliga |  |  | Executa o CLI do host no diretorio do repo (so com TTY e um host escolhido). |
| `--repo` | não | texto |  |  | Raiz do repositorio onde o host abre (padrao: diretorio corrente). |

## Tool MCP equivalente

[`sparkforge_aws_ai`](../tools/sparkforge_aws_ai.md)
