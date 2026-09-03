# Payload Devin — SparkForge AWS

Este diretorio contem tudo o que voce precisa para usar o projeto **SparkForge AWS** inteiro no **Devin CLI** e no **Devin Desktop**, sem depender de configuracoes manuais ou de memoria.

## O que esta aqui

| Arquivo | Para que serve |
|---|---|
| `PROMPT.md` | Prompt mestre otimizado para colar no inicio de uma sessao Devin |
| `mcp_config.json` | Configuracao MCP por **stdio** — usada no Devin CLI |
| `mcp_config_desktop.json` | Configuracao MCP por **HTTP** — usada no Devin Desktop (serverUrl) |
| `config.json` | Permissoes de projeto para os verbos `sparkforge` de leitura |
| `SESSION_CLI.md` | Passo a passo para iniciar no Devin CLI |
| `SESSION_DESKTOP.md` | Passo a passo para iniciar no Devin Desktop |

## Diferenca entre CLI e Desktop

- **Devin CLI**: usa MCP por `stdio`. Basta copiar `mcp_config.json` para `.devin/mcp_config.json` e colar o `PROMPT.md`.
- **Devin Desktop**: usa MCP por `serverUrl` (HTTP). Voce sobe o servidor localmente e aponta o `mcp_config_desktop.json`.

Em ambos, os **perfis de subagente** sao descobertos automaticamente em `.agents/agents/` e `.claude/agents/`, e as **skills** em `.agents/skills/`, desde que voce tenha rodado `python scripts/sync_skills.py` para gerar os espelhos.

## Pre-requisito

```bash
pip install "sparkforge-aws[mcp]"
```

## Ordem de uso

1. Instale o pacote.
2. Copie o `config.json` e o `mcp_config.json` adequado para `.devin/`.
3. Rode `python scripts/sync_skills.py` para garantir que `.agents/` e `.claude/` estejam atualizados.
4. Copie e cole o conteudo de `PROMPT.md` no inicio da sessao Devin.

## Importante

- Nao use o `.mcp.json` da raiz no Devin: ele e do plugin do Claude Code e usa `${CLAUDE_PLUGIN_ROOT}`, que o Devin nao expande.
- `subagents_enabled` e chave de usuario. O repositorio nao liga subagentes; o payload so publica os perfis e a configuracao MCP.
- Para manutencao destrutiva (expirar snapshots, remover arquivos, resetar bookmark), o agente deve pedir confirmacao explicita antes de executar.
- **Skills AWS complementares**: 11 skills de procedimento operacional AWS (`provision-s3-tables-table`, `harden-s3-bucket`, `aws-storage`, `aws-database`, `aws-serverless`, `aws-iam`, `aws-observability`, `aws-billing-and-cost-management`, `aws-messaging-and-streaming`, `aws-security`, `aws-sdk-python-usage`) sao nao-despachaveis. Use quando a pergunta for sobre o servico AWS em si (qual storage escolher, como configurar IAM), nao sobre diagnostico de job PySpark. Cada uma exige confirmacao explicita do operador para comandos de escrita. As 15 skills AWS restantes (Bedrock, SageMaker, CDK, etc) estao fora do dominio SparkForge e permanecem no nivel usuario (`~/.agents/skills/`).
