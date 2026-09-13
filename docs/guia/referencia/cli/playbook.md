<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge playbook`

Decomposicao de um coordenador em passos sequenciais -- o PISO de orquestracao das cinco plataformas: unico caminho em Codex e Copilot CI, e o caminho em Claude Code, Devin CLI e Devin Local agent quando o despacho de subagente esta desligado -- e, no Devin, tambem quando ele esta ligado, porque subagente nao gera subagente por default. Le agents/, nunca repete a lista de executores.

```bash
sparkforge playbook --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `coordinator` (posicional) | sim | texto |  |  |  |
| `--repo` | não | texto |  | `.` |  |
| `--findings` | não | texto |  |  | Arquivo de findings (JSON) usado para resolver o next_step embutido (AGENT-*). |

## Tool MCP equivalente

[`sparkforge_playbook`](../tools/sparkforge_playbook.md)
