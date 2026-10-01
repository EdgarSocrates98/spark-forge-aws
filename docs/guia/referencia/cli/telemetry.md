<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge telemetry`

Os spans de tool e o transcript do host em OTLP/JSON, para um OTLP Collector.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge telemetry export`](#sparkforge-telemetry-export) | Grava .sparkforge/telemetry/<run_id>.traces.jsonl e .metrics.jsonl (nomes fixos), com gen_ai.* e mcp.* da semconv GenAI (Development). O Collector le com o receiver otlp_json_file. Nao chama rede; token so com transcript do host. |

## `sparkforge telemetry export`

Grava .sparkforge/telemetry/<run_id>.traces.jsonl e .metrics.jsonl (nomes fixos), com gen_ai.* e mcp.* da semconv GenAI (Development). O Collector le com o receiver otlp_json_file. Nao chama rede; token so com transcript do host.

```bash
sparkforge telemetry export --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--run-id` | sim | texto |  |  |  |
| `--host-transcript` | não | texto |  | `` | Transcript JSONL do host, quando houver: vira o span invoke_agent com tokens. |
| `--provider` | não | texto |  |  | Provider do host (gen_ai.provider.name), DECLARADO: anthropic, aws.bedrock, gcp.vertex_ai. Sem ele o atributo fica em unresolved e a metrica de token nao sai. |
| `--repo` | não | texto |  | `.` | Raiz do repositorio. A saida vai para <repo>/.sparkforge/telemetry/. |

### Tool MCP equivalente

[`sparkforge_telemetry_export`](../tools/sparkforge_telemetry_export.md)
