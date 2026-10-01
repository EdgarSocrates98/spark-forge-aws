<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_knowledge_path`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Resolve a raiz dos arquivos de conhecimento versionado e, opcionalmente, um arquivo dentro dela. Use antes de tentar LER knowledge: num pacote instalado por pip o caminho fica dentro do site-packages e nao e adivinhavel.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `as_of` | string | não | Dia de referencia do estado das fontes (AAAA-MM-DD). Default: hoje, UTC. |
| `file` | string | não | Caminho relativo, ex.: glue/runtime-matrix.md |
| `source_freshness` | boolean | não | Acrescenta `source_freshness` (estado de cada fonte citada: fixed, unverified, stale, aging, fresh ou unresolved, com o motivo e as datas) e `freshness_policy` (limiar declarado, `as_of` e contagem por estado). Calculado sobre knowledge/sources.lock.json: depende do lock e do dia. stale = a fonte mudou depois da data em que a regra a validou. |

## Na CLI

[`sparkforge knowledge path`](../cli/knowledge.md)

## Capacidade

locate the version-controlled knowledge files

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
