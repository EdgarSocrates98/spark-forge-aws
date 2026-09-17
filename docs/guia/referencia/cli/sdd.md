<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge sdd`

Confere os artefatos de spec em docs/sdd/<FEATURE>/<fase>.md: recusa por nome o que nao fecha, sem julgar a prosa.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge sdd check`](#sparkforge-sdd-check) | Roda os gates. Sai 1 se houver recusa; lacuna sozinha sai 0. |
| [`sparkforge sdd stamp`](#sparkforge-sdd-stamp) | Grava upstream.sha256 do artefato. Escreve so a linha do hash. |
| [`sparkforge sdd status`](#sparkforge-sdd-status) | Fase atual de cada feature e o que a impede de avancar. |

## `sparkforge sdd check`

Roda os gates. Sai 1 se houver recusa; lacuna sozinha sai 0.

```bash
sparkforge sdd check --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  | Raiz do repositorio. |
| `--root` | não | texto |  | `docs/sdd` | Pasta dos artefatos, relativa a --repo. |
| `--feature` | não | texto |  |  | Confere so esta feature. |

### Tool MCP equivalente

[`sparkforge_sdd_check`](../tools/sparkforge_sdd_check.md), [`sparkforge_sdd_status`](../tools/sparkforge_sdd_status.md)

## `sparkforge sdd stamp`

Grava upstream.sha256 do artefato. Escreve so a linha do hash.

```bash
sparkforge sdd stamp --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  | Raiz do repositorio. |
| `--root` | não | texto |  | `docs/sdd` | Pasta dos artefatos, relativa a --repo. |
| `path` (posicional) | sim | texto |  |  | Artefato, relativo a --repo. |

### Tool MCP equivalente

[`sparkforge_sdd_stamp`](../tools/sparkforge_sdd_stamp.md)

## `sparkforge sdd status`

Fase atual de cada feature e o que a impede de avancar.

```bash
sparkforge sdd status --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | sim | texto |  |  | Raiz do repositorio. |
| `--root` | não | texto |  | `docs/sdd` | Pasta dos artefatos, relativa a --repo. |

### Tool MCP equivalente

[`sparkforge_sdd_check`](../tools/sparkforge_sdd_check.md), [`sparkforge_sdd_status`](../tools/sparkforge_sdd_status.md)
