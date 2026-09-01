# Sessao no Devin Desktop

## 1. Instalacao

```bash
pip install "sparkforge-aws[mcp]"
```

## 2. Sincronize os espelhos (se ainda nao estiverem gerados)

```bash
cd <raiz-do-repositorio-spark-forge-aws>
python scripts/sync_skills.py
```

## 3. Sobe o servidor MCP (HTTP)

```bash
python -m sparkforge.adapters.mcp --transport http --host 127.0.0.1 --port 8765
```

Deixe esse processo rodando. O endpoint do Desktop e:

```text
http://127.0.0.1:8765/mcp
```

## 4. Configure o Devin Desktop

Va em **Devin Settings > MCP** e adicione um servidor com a URL acima. Use o conteudo de `mcp_config_desktop.json`:

```json
{
  "mcpServers": {
    "sparkforge": {
      "serverUrl": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

No Desktop, nao e possivel versionar `mcpServers` por arquivo. A configuracao fica nas settings da sessao.

## 5. Habilite Subagents (se quiser usar agentes especializados)

Va em **Devin Settings > Subagents (Preview)** e ligue o toggle. Isso permite que o Devin Local agent despache os perfis em `.agents/agents/` e `.claude/agents/`.

## 6. Inicie a sessao

Abra um novo chat no Devin Desktop e cole o conteudo de `PROMPT.md`.

## 7. Verifique que as tools estao disponiveis

Pergunte ao agente:

```text
Liste as tools MCP do sparkforge que estao disponiveis e confirme que consegue chamar sparkforge_runtime_detect.
```

## 8. Workflow tipico

1. Abra o case: `sparkforge case open --repo . --case-id <id> --now <ISO-8601> --glue <versao>`
2. Detecte runtime: `sparkforge runtime detect --glue <versao>`
3. Analise codigo: `sparkforge analyze pyspark --path <lib> --out .sparkforge/facts.json`
4. Julgue: `sparkforge judge --facts .sparkforge/facts.json --out .sparkforge/findings.json`
5. Proximo passo: `sparkforge next-step --repo . --findings .sparkforge/findings.json`
6. Siga a rota indicada, usando skills, subagentes ou `sparkforge playbook <coordenador>`.

## 9. Subagentes no Desktop

Com **Subagents (Preview)** ativado, diga:

```text
Use o agente glue-incremental-performance-architect como subagente para investigar este job.
```

Fora do Devin Local agent com subagentes ativados, a coordenacao e feita por `sparkforge playbook`:

```bash
sparkforge playbook glue-incremental-performance-architect --repo .
```
