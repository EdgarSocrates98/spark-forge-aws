<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_doctor`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Confere se o ambiente esta pronto, em treze checagens com status ok, warn, fail ou skip e o comando que resolve: pacote, extras, mcp, catalogo, packs, knowledge, indice_de_codigo, artefatos, credencial_aws e uma por host da integracao de usuario (integracao_claude, integracao_devin, integracao_codex, integracao_copilot: presente, versao do pacote gravada e copia vendorizada em dobro no repositorio). A credencial e conferida so localmente (cadeia do boto3): esta tool nunca vai a rede; a confirmacao na AWS e `sparkforge doctor --online`, so na CLI.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | não | Raiz do repositorio (padrao: .). |

## Na CLI

[`sparkforge doctor`](../cli/doctor.md)

## Capacidade

check that the environment is ready

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
