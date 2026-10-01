<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge pack`

Forge Packs: regras, knowledge e fixtures de terceiro (SPARKFORGE_PACKS).

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge pack check`](#sparkforge-pack-check) | Roda cada fixture do pack pelo judge. Sai 1 quando uma regra do pack nao dispara no fixture que a declara, ou quando o pack e recusado. |
| [`sparkforge pack list`](#sparkforge-pack-list) | Packs ativos, recusados com o motivo, e o mapa prefixo -> pack. |

## `sparkforge pack check`

Roda cada fixture do pack pelo judge. Sai 1 quando uma regra do pack nao dispara no fixture que a declara, ou quando o pack e recusado.

```bash
sparkforge pack check --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `dir` (posicional) | sim | texto |  |  | Diretorio do pack (com pack.yaml). |

### Tool MCP equivalente

[`sparkforge_pack_list`](../tools/sparkforge_pack_list.md)

## `sparkforge pack list`

Packs ativos, recusados com o motivo, e o mapa prefixo -> pack.

```bash
sparkforge pack list --help
```

### Opções

Este comando não recebe opções.

### Tool MCP equivalente

[`sparkforge_pack_list`](../tools/sparkforge_pack_list.md)
