# Receita — verificar o MCP

**O quê:** confirma que o server `sparkforge-aws` está configurado,
subindo e expondo as 145 tools — pelo lado do arquivo, do host e do
handshake.
**Por que:** "o agente não acha o Forge" quase sempre é MCP não
consumido — e cada host lê o config num lugar diferente.
**Quando:** depois do install; quando o host não vê as tools; depois de
mover o repo ou o venv.
**Quando não:** o problema é skill/agent, não MCP — `status` cobre os
três e diz qual camada falta.

## Problema

"Como sei que o MCP do SparkForge está funcionando neste host?"

## Pré-requisitos

`sparkforge-aws install` executado no escopo que o host lê.

## Passo a passo

```bash
# 1) o arquivo existe e aponta para um python válido
cat .mcp.json
# → mcpServers["sparkforge-aws"].command = <venv>/python
#   args = ["-m", "sparkforge_aws.adapters.mcp", "--transport", "stdio"]

# 2) a instalação reconhece o config como gerenciado
sparkforge-aws status --scope project --root .
# status: healthy (o .mcp.json entra no drift: sumiu/editou → degraded)

# 3) o host consome — varia por host
devin mcp list      # Devin lê .mcp.json de projeto direto
codex mcp list      # Codex: só ~/.codex/config.toml (escopo user)
# Claude: .mcp.json de projeto entra após aprovação na sessão
```

## Saída esperada / interpretação

Handshake verificado nesta sessão: o server sobe por stdio, lista as
145 tools e invoca `sparkforge_aws_runtime_detect` com saída estruturada.
`status` marca o `.mcp.json` como config gerenciado — removê-lo degrada
o estado até `repair` restaurar.

## Verificação

```bash
sparkforge-aws status --scope project --root .   # healthy
sparkforge-aws install doctor --scope project --root .
```

## Limitações

- **`command` aponta para o venv do clone** — mover o repo ou recriar o
  venv exige `install --update` ou novo install para regravar o path.
- Codex em escopo `project` sai como `mcp-scope:codex → NOT_APPLICABLE`
  no recibo: o host não lê `.mcp.json` de projeto (verificado em
  0.160.0); MCP exige `--scope user` ou `codex mcp add`.
- A entrada é a forma universal `command`/`args` — um único `.mcp.json`
  serve todos os hosts que o leem.

## Erros comuns

| Sintoma | Causa | Ação |
|---|---|---|
| `status: degraded` sem arquivo mexido | `.mcp.json` apagado/editado | `sparkforge-aws repair --root .` restaura a entrada gravada |
| Codex não lista o server | escopo project | `--scope user --host codex` |
| comando do MCP quebrado | venv recriado | `sparkforge-aws install --update` |

## Uso por agentes

O server expõe as mesmas tools para qualquer host — `python -m
sparkforge_aws.adapters.mcp --transport stdio` é o contrato único.

## Leitura seguinte

- [instalar-e-comecar](instalar-e-comecar.md)
- [../../installation/mcp.md](../../installation/mcp.md)
- [usar-com-codex](usar-com-codex.md) — a limitação de escopo do Codex
