<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_knowledge_drift`

**Efeito:** Só leitura: não grava nada e não acessa a rede.

## O que faz

Knowledge Drift Radar: para cada fonte oficial vigiada cujo hash mudou (`changed_at` em knowledge/sources.lock.json), o que ela arrasta. As citacoes (regras e documentos de knowledge/) com o `retrieved` declarado e o estado; as lidas ANTES da mudanca sao `stale` e entram no impacto -- regras e documentos a reler, os goldens que provam essas regras, os evals que as citam e os agentes que declaram a area ou citam a regra --, e as lidas depois saem em `revalidated`. So por ligacao que existe em arquivo; nada inferido. Sem checkout do repositorio (instalado por pip), goldens, evals e agentes saem `unresolved` com `sem_repositorio`. Fonte fixa por versao nunca entra. O QUE ELA NAO FAZ: nao acessa a rede (quem confere o hash e o refresh semanal), nao diz se a mudanca tocou o trecho que a regra cita (`refused`), nao roda os goldens nem os evals.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `as_of` | string | não | Dia de referencia (AAAA-MM-DD). |
| `source` | string | não | So esta fonte do lock (a chave, igual a do lock). |

## Na CLI

[`sparkforge knowledge drift`](../cli/knowledge.md)

## Capacidade

show what a changed official source drags along

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `true` |
