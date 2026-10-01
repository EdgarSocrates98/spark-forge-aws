# Payload Devin — SparkForge AWS

Este repositorio ja publica tudo o que o Devin CLI e o Devin Desktop precisam:

- **MCP stdio**: `.devin/mcp_config.json`
- **MCP HTTP**: `payloads/devin/mcp_config_desktop.json`
- **Permissoes de projeto**: `.devin/config.json`
- **Skills e agentes**: `.agents/skills/` e `.agents/agents/` (gerados por `scripts/sync_skills.py`)
- **Prompt de inicio**: `payloads/devin/PROMPT.md`

## Uso rapido

```bash
pip install "sparkforge-aws[mcp]"
python scripts/sync_skills.py
```

### Devin CLI

Copie os arquivos do payload para `.devin/` e inicie a sessao com o conteudo de `payloads/devin/PROMPT.md`:

```bash
cp payloads/devin/config.json .devin/config.json
cp payloads/devin/mcp_config.json .devin/mcp_config.json
devin
```

Verifique que as tools estao disponiveis:

```text
Liste as tools MCP do sparkforge e confirme que consegue chamar sparkforge_runtime_detect.
```

Ou, na CLI:

```bash
devin mcp list
```

### Devin Desktop

1. Suba o servidor MCP:

```bash
python -m sparkforge.adapters.mcp --transport http --host 127.0.0.1 --port 8765
```

2. No Devin Desktop, adicione o MCP em **Devin Settings > MCP** com a URL `http://127.0.0.1:8765/mcp`.
3. Habilite **Subagents (Preview)** em Devin Settings para usar os agentes de `.agents/agents/`.
4. Cole o conteudo de `payloads/devin/PROMPT.md` na sessao.

Para confirmar que o endpoint HTTP subiu:

```bash
curl -i http://127.0.0.1:8765/mcp
```

## Troubleshooting

| Sintoma | Causa provavel | Correcao |
|---|---|---|
| `CatalogError: .../${CLAUDE_PLUGIN_ROOT}/...` | `.mcp.json` sendo usado no Devin | Use `.devin/mcp_config.json` |
| `ModuleNotFoundError: mcp` | extra `[mcp]` nao instalado | `pip install "sparkforge-aws[mcp]"` |
| `devin mcp list` nao mostra `sparkforge` | escopo global em vez de projeto | confira `.devin/mcp_config.json` na raiz |
| Desktop nao conecta | servidor HTTP nao rodando | suba com o comando acima |

Veja `GUIA_DE_USO.md` secao 3.4, 3.5 e 3.6 para detalhes completos.

## Onde ler o passo a passo completo

- `payloads/devin/SESSION_CLI.md`
- `payloads/devin/SESSION_DESKTOP.md`
- `payloads/devin/README.md`

## Verificacao

```bash
python scripts/sync_skills.py --check
python -m sparkforge.adapters.cli --help
```
