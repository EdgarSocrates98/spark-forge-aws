<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge benchmark`

Compara duas execucoes a partir dos facts de event log de cada uma. Nao executa nada e nao mede relogio.

```bash
sparkforge benchmark --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--before` | sim | texto |  |  | Arquivo de facts gerado por `analyze event-log --out` da execucao ANTES. |
| `--after` | sim | texto |  |  | Arquivo de facts gerado por `analyze event-log --out` da execucao DEPOIS. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts (JSON) neste arquivo. |
| `--before-runtime` | não | texto |  | `` | Versao de runtime em que a execucao ANTES rodou (ex.: 5.1). |
| `--after-runtime` | não | texto |  | `` | Versao de runtime em que a execucao DEPOIS rodou (ex.: 6.0). |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

## Tool MCP equivalente

[`sparkforge_benchmark`](../tools/sparkforge_benchmark.md)
