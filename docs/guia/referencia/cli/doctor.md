<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge doctor`

Confere se o ambiente esta pronto: pacote, extras, MCP, catalogo, packs, knowledge, indice de codigo, artefatos, credencial AWS e a integracao de usuario de cada host. Sai 1 com alguma falha.

```bash
sparkforge doctor --help
```

## Opções

| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |
|---|---|---|---|---|---|
| `--repo` | não | texto |  | `.` | Raiz do repositorio (padrao: .). |
| `--online` | não | liga/desliga |  |  | Confirma a credencial na AWS (STS get_caller_identity). Unico modo com rede. |

## Tool MCP equivalente

[`sparkforge_doctor`](../tools/sparkforge_doctor.md)
