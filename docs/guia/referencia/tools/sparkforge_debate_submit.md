<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_debate_submit`

**Efeito:** Grava em disco local e muda o estado a cada chamada (repetir não é igual a chamar uma vez).

## O que faz

Submete o turno do lado da vez, INLINE em `submission`, no schema que o brief publica. Valida TUDO antes de gravar QUALQUER coisa, e a recusa deixa o estado igual. RECUSA por nome: `debate_closed`, `invalid_schema` (inclusive chave desconhecida -- campo que o executor nao le nao e considerado), `out_of_turn`, `claim_without_evidence`, `dangling_evidence_ref` (fact_id fora da uniao congelada e dos reextraidos), `dangling_target_ref`, `duplicate_entity`, e as da reextracao: `extractor_not_allowed`, `artifact_outside_case`, `artifact_not_found`, `extractor_failed`. NAO aceita fact escrito pelo agente: evidencia nova entra por `evidence_artifacts` e e REEXTRAIDA pelo executor, com extrator de allowlist e caminho confinado a raiz do case. Aceita, grava `Claim`, `Objection` e `Rebuttal` no blackboard e devolve o passo seguinte em `next`. Nada aqui gera argumento nem chama provider: o texto da submissao e do HOST.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `debate_id` | string | sim |  |
| `repo` | string | sim | Raiz do case. |
| `submission` | object | sim | `{side, round, claims, objections, rebuttals, concede, evidence_artifacts}` -- o schema completo sai em `brief.submission_schema`. |

## Na CLI

[`sparkforge debate next`](../cli/debate.md), [`sparkforge debate start`](../cli/debate.md), [`sparkforge debate submit`](../cli/debate.md)

## Capacidade

run the debate protocol turn by turn and close it through the referee

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `false` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
