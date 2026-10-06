<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge-aws doctor`

Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, knowledge, indice de codigo, artefatos, credencial AWS e a integracao de usuario de cada host. Sai 1 com alguma falha.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge-aws doctor agentic`](#sparkforge-aws-doctor-agentic) | Confere readiness local do plano agêntico, sem rede. |

## `sparkforge-aws doctor agentic`

Confere readiness local do plano agêntico, sem rede.

```bash
sparkforge-aws doctor agentic --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)
