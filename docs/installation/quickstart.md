# Quickstart — spark-forge-aws

Três comandos:

```bash
git clone <spark-forge-aws repo>
cd spark-forge-aws
./setup.sh        # Windows: .\setup.ps1
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
sparkforge-aws doctor
```

Problemas? → [troubleshooting.md](troubleshooting.md)
