<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge policy`

Politica de seguranca do repositorio (.sparkforge/policy.yaml): validar, explicar uma decisao e gerar as regras ask do .claude/settings.json.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge policy check`](#sparkforge-policy-check) | Valida a policy e lista as regras; sai 2 se ela for invalida. |
| [`sparkforge policy explain`](#sparkforge-policy-explain) | Diz a decisao (allow, ask, deny), a regra que casou e qual porta a impoe. |
| [`sparkforge policy sync-settings`](#sparkforge-policy-sync-settings) | Gera permissions.ask no .claude/settings.json a partir das regras ask; --check so confere e sai 1 se divergir. |

## `sparkforge policy check`

Valida a policy e lista as regras; sai 2 se ela for invalida.

```bash
sparkforge policy check --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do repositorio (padrao: .). |

### Tool MCP equivalente

[`sparkforge_policy_explain`](../tools/sparkforge_policy_explain.md)

## `sparkforge policy explain`

Diz a decisao (allow, ask, deny), a regra que casou e qual porta a impoe.

```bash
sparkforge policy explain --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do repositorio (padrao: .). |
| `--bash` | não | texto |  |  | Comando de shell a conferir. |
| `--path` | não | texto |  |  | Caminho de escrita a conferir. |
| `--tool` | não | texto |  |  | Nome de tool MCP a conferir. |

### Tool MCP equivalente

[`sparkforge_policy_explain`](../tools/sparkforge_policy_explain.md)

## `sparkforge policy sync-settings`

Gera permissions.ask no .claude/settings.json a partir das regras ask; --check so confere e sai 1 se divergir.

```bash
sparkforge policy sync-settings --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do repositorio (padrao: .). |
| `--check` | não | liga/desliga |  |  | So confere; nao grava. Sai 1 se divergir. |

### Tool MCP equivalente

[`sparkforge_policy_explain`](../tools/sparkforge_policy_explain.md)
