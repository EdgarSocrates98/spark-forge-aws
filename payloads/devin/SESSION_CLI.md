# Sessao no Devin CLI

## 1. Instalacao

```bash
pip install "sparkforge-aws[mcp]"
```

## 2. Sincronize os espelhos (se ainda nao estiverem gerados)

```bash
cd <raiz-do-repositorio-spark-forge-aws>
python scripts/sync_skills.py
```

## 3. Configure o Devin CLI

Copie os arquivos deste payload para `.devin/` no repositorio de trabalho:

```bash
cp payloads/devin/config.json .devin/config.json
cp payloads/devin/mcp_config.json .devin/mcp_config.json
```

Ou adicione o MCP pela CLI do Devin:

```bash
devin mcp add -s project sparkforge -- python -m sparkforge.adapters.mcp --transport stdio
devin mcp list
```

## 4. Inicie a sessao

```bash
devin
```

No prompt de abertura, cole o conteudo de `PROMPT.md`.

## 5. Verifique que as tools estao disponiveis

Pergunte ao agente:

```text
Liste as tools MCP do sparkforge que estao disponiveis e confirme que consegue chamar sparkforge_runtime_detect.
```

## 6. Workflow tipico

1. Abra o case: `sparkforge case open --repo . --case-id <id> --now <ISO-8601> --glue <versao>`
2. Detecte runtime: `sparkforge runtime detect --glue <versao>`
3. Analise codigo: `sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json`
4. Julgue: `sparkforge judge --facts .sparkforge/facts.json --out .sparkforge/findings.json`
5. Proximo passo: `sparkforge next-step --repo . --findings .sparkforge/findings.json`
6. Siga a rota indicada, usando skills, subagentes ou `sparkforge playbook <coordenador>`.

## 7. Subagentes

Se `subagents_enabled` estiver `true` na sua conta, voce pode dizer:

```text
Use o agente glue-incremental-performance-architect como subagente para investigar este job.
```

Se nao estiver ativo, use:

```bash
sparkforge playbook glue-incremental-performance-architect --repo .
```
