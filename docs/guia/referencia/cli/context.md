<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge context`

Descobre capabilities e empacota contexto deterministico sob limite explicito.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge context expand`](#sparkforge-context-expand) | Expande uma referencia ctx://v1 sob budget. |
| [`sparkforge context inspect`](#sparkforge-context-inspect) | Inspeciona qualidade de contexto sem inferir tokens por bytes. |
| [`sparkforge context start`](#sparkforge-context-start) | Inicia descoberta, selecao, reducao e materializacao de contexto. |

## `sparkforge context expand`

Expande uma referencia ctx://v1 sob budget.

```bash
sparkforge context expand --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--ref` | sim | texto |  |  |  |
| `--max-bytes` | não | texto |  |  | Teto de bytes serializados; omitido usa default economy. |
| `--repo` | não | texto |  | `.` |  |

### Tool MCP equivalente

[`sparkforge_context_expand`](../tools/sparkforge_context_expand.md), [`sparkforge_context_start`](../tools/sparkforge_context_start.md)

## `sparkforge context inspect`

Inspeciona qualidade de contexto sem inferir tokens por bytes.

```bash
sparkforge context inspect --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--input` | sim | texto |  |  | JSON com itens e refs de evidencia. |
| `--observed-provider-tokens` | não | texto |  |  | Tokens observados no transcript do host; omitido permanece unresolved. |

### Tool MCP equivalente

[`sparkforge_agentops_baseline`](../tools/sparkforge_agentops_baseline.md), [`sparkforge_agentops_compare`](../tools/sparkforge_agentops_compare.md), [`sparkforge_agentops_critical_path`](../tools/sparkforge_agentops_critical_path.md), [`sparkforge_agentops_inspect`](../tools/sparkforge_agentops_inspect.md), [`sparkforge_agentops_timeline`](../tools/sparkforge_agentops_timeline.md), [`sparkforge_context_inspect`](../tools/sparkforge_context_inspect.md), [`sparkforge_doctor_agentic`](../tools/sparkforge_doctor_agentic.md)

## `sparkforge context start`

Inicia descoberta, selecao, reducao e materializacao de contexto.

```bash
sparkforge context start --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--intent` | sim | texto |  |  |  |
| `--profile` | não | `economy`, `balanced`, `deep` |  | `balanced` |  |
| `--max-bytes` | não | texto |  |  | Teto de bytes serializados; omitido usa default do profile. |
| `--items` | não | texto |  |  | JSON com lista de facts/findings/knowledge/codigo ja extraidos. |
| `--role` | não | texto |  |  | Role com plano declarado (sf-inventory/sf-extractor/sf-judge/sf-verifier/sf-synthesizer); desconhecida nega contexto. |
| `--role-plan` | não | texto |  |  | Arquivo JSON com RoleContextPlan serializado (vence --role). |
| `--repo` | não | texto |  | `.` |  |
| `--case-id` | não | texto |  |  |  |

### Tool MCP equivalente

[`sparkforge_context_expand`](../tools/sparkforge_context_expand.md), [`sparkforge_context_start`](../tools/sparkforge_context_start.md)
