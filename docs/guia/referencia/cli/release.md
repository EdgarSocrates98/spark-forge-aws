<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge release`

O que uma release publica, e o que muda entre duas. Le matriz de versao; NAO avalia se algo quebra.

## Subcomandos

| Subcomando | O que faz |
|---|---|
| [`sparkforge release describe`](#sparkforge-release-describe) | O que a fonte daquela plataforma publica para uma release. Componente nao publicado sai em `unresolved` NOMEADO. |
| [`sparkforge release diff`](#sparkforge-release-diff) | O que muda entre duas releases, com o eixo (`release`, `platform` ou os dois) DECLARADO na saida. |

## `sparkforge release describe`

O que a fonte daquela plataforma publica para uma release. Componente nao publicado sai em `unresolved` NOMEADO.

```bash
sparkforge release describe --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--platform` | sim | texto |  |  | Uma das quatro: glue, emr_ec2, emr_serverless, emr_eks. |
| `--release` | sim | texto |  |  | O rotulo da release, com ou sem o prefixo `emr-` (ex.: 7.7.0, emr-7.7.0, 5.1). |

### Tool MCP equivalente

[`sparkforge_release_describe`](../tools/sparkforge_release_describe.md)

## `sparkforge release diff`

O que muda entre duas releases, com o eixo (`release`, `platform` ou os dois) DECLARADO na saida.

```bash
sparkforge release diff --help
```

### Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--left-platform` | sim | texto |  |  | Plataforma do lado de ONDE o operador sai. |
| `--left-release` | sim | texto |  |  | Release do lado de ONDE o operador sai. |
| `--right-platform` | sim | texto |  |  | Plataforma do lado PARA ONDE o operador vai. |
| `--right-release` | sim | texto |  |  | Release do lado PARA ONDE o operador vai. |

### Tool MCP equivalente

[`sparkforge_release_diff`](../tools/sparkforge_release_diff.md)
