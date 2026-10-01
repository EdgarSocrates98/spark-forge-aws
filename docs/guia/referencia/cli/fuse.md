<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge fuse`

Correlaciona facts de SQL com schema do catalogo (sparkforge.facts.fusion), antes de judge.

```bash
sparkforge fuse --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--facts` | sim | texto | sim |  | Arquivo de facts (JSON) gerado por `analyze`. Repetivel: fusao precisa ver as fontes que quer correlacionar na mesma chamada. |
| `--out` | não | texto |  |  | Escreve a lista completa de facts fundidos (JSON) neste arquivo. |
| `--kind` | não | texto | sim |  | Filtra por kind. Repetivel. |
| `--limit` | não | texto |  | `50` |  |
| `--cursor` | não | texto |  |  |  |
| `--detail-level` | não | `summary`, `normal`, `full` |  | `full` | Verbosidade da saida. `full` (default) devolve o fato inteiro, com a procedencia dentro de cada item -- e o modo de reauditoria. `normal` declara procedencia e schema_version UMA VEZ no envelope e referencia a procedencia por `provenance_ref`. `summary` reduz cada item a id, kind, medidas, arquivo:linha e simbolo. NAO existe subcomando que busque um fato por id: para ter o fato inteiro de volta, reexecute em `full` e pague o payload inteiro outra vez. |

## Tool MCP equivalente

[`sparkforge_fuse`](../tools/sparkforge_fuse.md)
