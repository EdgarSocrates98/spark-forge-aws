# Quickstart — spark-forge-aws

Três comandos:

```bash
git clone <spark-forge-aws repo>
cd spark-forge-aws
./install.sh      # Windows: .\install.ps1 — account runtime + editable CLI
```

Depois, dentro de qualquer projeto:

```bash
cd ~/meu-projeto
sparkforge-aws install
```

Pronto. Abra seu AI host (Devin, Claude, Codex ou Copilot) — as skills do
spark-forge-aws já estão instaladas. Ou peça ao Forge para medir e abrir:

```bash
sparkforge-aws ai            # estado dos quatro hosts: binário, versão, login, integração
sparkforge-aws ai devin      # o mesmo para um host
sparkforge-aws ai devin --launch   # abre o CLI do host neste diretório (TTY)
```

`ai` nunca lança host deslogado nem sem TTY — nesses casos o recibo traz
`launch_command` e `login_hint` com o comando oficial.

## Verificar

```bash
sparkforge-aws status
sparkforge-aws install doctor
```

Todo recibo (`install`, `repair`, `update`, `uninstall`) e todo health doc
(`status`, `install doctor`) carrega um bloco `lifecycle`
(`forge/InstallLifecycle/v1`) com o estado derivado da evidência — o CLI
nunca declara sucesso, só anexa o que o recibo provou:

| `lifecycle.state` | Significado | exit |
|---|---|---|
| `planned` | `--dry-run`: plano emitido, nada escrito | 0 |
| `verified` | escrito + verificação do recibo PASS | 0 |
| `ready` | `verified` + health/ledger verde (`status` healthy) | 0 |
| `applied` | escrito; verificação ausente/pendente — **não é prova** | 0 |
| `unverified` | sem evidência no alvo (ex.: projeto sem instalação) | 0 |
| `partially_applied` | subconjunto íntegro (drift parcial — `status` degraded) | 1 |
| `blocked` | gate recusou tudo (aprovação, superfície) | 1 |
| `failed` | operação rodou e errou | 1 |
| `certified` | `ready` + certificação externa vinculada a SHA | 0 |

Só `verified`, `ready` e `certified` sustentam afirmação de sucesso —
`applied`/`unverified` são honestidade, não prontidão. O `status` grosso
do recibo continua `planned|completed|failed|rolled-back` por
compatibilidade; `--dry-run` nunca reporta `completed`.

Detalhes do ambiente de conta: [account-installation.md](account-installation.md).

Problemas? → [troubleshooting.md](troubleshooting.md)
