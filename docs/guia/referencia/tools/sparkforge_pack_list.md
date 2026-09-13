<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_pack_list`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Forge Packs ativos: pacotes de DADO (regras YAML, knowledge e fixtures) de terceiro, carregados junto do core pela variavel SPARKFORGE_PACKS. Devolve os packs ativos (id, versao, prefixo, faixa de core aceita, regras, knowledge), os RECUSADOS com o motivo -- manifesto_invalido, prefixo_reservado (SF e do core), pack_duplicado (id ou prefixo repetido), core_incompativel, regra_invalida, id_fora_do_prefixo, id_duplicado -- e o mapa prefixo -> pack, que e como se sabe de onde veio um finding `ACME-GOV-001`. Pack recusado sai inteiro: nenhuma regra dele entra em judge. O QUE ELA NAO FAZ: nao instala nem baixa pack, nao executa codigo de pack (pack e so dado), nao sobrescreve regra do core. Checar um pack contra os fixtures dele e da CLI: `sparkforge pack check <dir>`.

## Parâmetros

Esta tool não recebe parâmetros.

## Na CLI

[`sparkforge pack check`](../cli/pack.md), [`sparkforge pack list`](../cli/pack.md)

## Capacidade

load third-party rule packs alongside the core

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
