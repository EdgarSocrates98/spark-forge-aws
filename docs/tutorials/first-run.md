# Tutorial — primeira execução real (sparkforge-aws)

Task-first: do zero ao primeiro resultado em minutos. Todos os exemplos
abaixo são classificados — rode os `offline` sem credencial nenhuma.

## 1. Instalar (offline)

```bash
git clone <spark-forge-aws>
cd spark-forge-aws
./setup.sh        # Windows: .\setup.ps1
```

`setup.sh` cria a venv, constrói o wheel e publica o launcher — sem rede
além do download de dependências Python (uma vez).

## 2. Descobrir (offline)

```bash
sparkforge-aws
```

Sem argumentos o CLI mostra o resumo do produto e os comandos mais usados
— nunca um erro, nunca uma mutação. `sparkforge-aws --help` aprofunda.

## 3. Primeiro comando (offline)

```bash
sparkforge-aws analyze pyspark --path <arquivo-ou-dir>
```

extrai facts do código PySpark (offline).

## 4. Segundo passo (offline)

```bash
sparkforge-aws judge --show-skipped
```

julgamento dos findings contra o catálogo.

## 5. Instalar nos hosts (mutação confirmada)

```bash
sparkforge-aws install --dry-run     # plano: nada é escrito
sparkforge-aws install --yes         # aplica após aprovar o plano
```

instala skills, agents e MCP nos hosts. `--dry-run` antes de `--yes` é o padrão do ecossistema.

## 6. Verificar (offline)

```bash
sparkforge-aws mcp verify
```

Verificação real: handshake MCP → `tools/list` → `tools/call` segura →
saída limpa do processo. Um `FAIL` aqui vem com `stderr_tail` e
`process.exit_code` — é diagnóstico, não enfeite.

## 7. Próximo passo

```bash
sparkforge-aws playbook spark-performance-architect
```

decomposição de um coordenador — o piso em qualquer plataforma.

## Classificação dos exemplos

| Exemplo | Classe |
|---|---|
| setup.sh / clone | offline (precisa rede só p/ deps Python) |
| `sparkforge-aws` bare, help, capabilities | offline |
| analyze/scan/judge locais | offline — nunca toca credencial |
| install --dry-run/--yes | offline, mutação no disco local |
| mcp-verify | offline, spawna o servidor MCP local |
| collect */ chamadas de cloud | **credenciais de cloud necessárias** |
| uso via Claude/Devin/Codex | **requer host instalado** |

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `command not found: sparkforge-aws` | launcher fora do PATH ou shell velha | abra terminal novo; rode `./setup.sh` de novo |
| `FORGE-INSTALL-LOCKED` | instalação concorrente/interrompida | lock expira e é recuperado sozinho; repita |
| `FORGE-INSTALL-PLAN-NOT-APPROVED` | mutação sem `--yes` | rode `--dry-run`, depois `--yes` |
| MCP `FAIL` com stderr | dependência ausente (ex.: extra `mcp`) | instale o extra e repita `mcp-verify` |

Mais: [../installation/troubleshooting.md](../installation/troubleshooting.md).
