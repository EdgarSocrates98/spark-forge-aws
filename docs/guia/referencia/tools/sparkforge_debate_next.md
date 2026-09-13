<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_debate_next`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

O proximo passo do debate, derivado SO dos arquivos do case: o brief do lado da vez (`status: brief`) ou o fechamento (`status: done`). O brief traz a regra defendida e a adversaria, os `fact_id` citaveis, as objecoes abertas contra o lado e o schema da submissao; as submissoes anteriores vem rotuladas `untrusted_content: true`, porque sao texto de agente. E MUTACAO, embora leia: quando a ultima rodada completa nao traz objecao nova (consenso) ou o teto de rodadas se esgota, ele passa o candidato pelo `referee` e grava a `Decision` no blackboard. Vencedor so existe quando EXATAMENTE um lado concedeu e o `referee` aceitou -- nunca por contagem de claim, evidencia ou rodada; fora disso a decisao e `unresolved`. Depois do fechamento devolve sempre o mesmo `done`. Recusa `debate_not_found` para id que nao existe (o id nunca vira caminho arbitrario). Nao gera argumento e nao chama provider: a geracao e do host. Autonomia L0 -- `applied_changes` sai sempre `false`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `debate_id` | string | sim | O id que `sparkforge_debate_start` devolveu (`dbt_` + 8 hex). |
| `repo` | string | sim | Raiz do case. |

## Na CLI

[`sparkforge debate next`](../cli/debate.md), [`sparkforge debate start`](../cli/debate.md), [`sparkforge debate submit`](../cli/debate.md)

## Capacidade

run the debate protocol turn by turn and close it through the referee

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `true` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
