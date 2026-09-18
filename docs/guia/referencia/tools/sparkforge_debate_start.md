<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_debate_start`

**Efeito:** Grava em disco local (repetir a chamada dá o mesmo resultado).

## O que faz

Abre o debate que `sparkforge_arbitrate` deixou em `debate.unresolved`: recalcula os planos pelo MESMO caminho do `arbitrate`, sobre os MESMOS insumos (findings, a UNIAO dos facts do case, runtime), e congela o plano do par `rules` em `<repo>/.sparkforge/debate/<debate_id>/plan.json`. O `debate_id` e o hash do plano: o mesmo `start` e idempotente e devolve `created: false`. RECUSA por nome, sem gravar nada: `budget_undeclared` quando o `case.yaml` nao declara `budget.max_rounds` (o default do codigo nunca vira teto), `no_open_debate_for_rules` quando o par nao se contradiz ou a arbitragem ja fechou, `debate_exists_with_other_plan` quando o par ja tem debate congelado com outros facts ou outro budget, e `invalid_rules`. Antes do budget, o `debate_gate` do plano: `gate_experimentar_antes`, `gate_nao_debater` e `gate_unresolved` recusam o par cujo veredito nao e `debater`, nomeando a medida, as duas acoes com rollback, ou o sinal que falta. NAO gera argumento: nada neste projeto chama provider. Quem escreve cada submissao e o HOST (subagente ou `claude -p`), fora de `sparkforge/`. Nao estima ganho sobre a arbitragem deterministica e nao aplica mudanca (autonomia L0).

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim | Raiz do case. O estado do debate fica em `<repo>/.sparkforge/debate/`, e o budget e lido do `case.yaml`. |
| `rules` | array de string | sim | O par em contradicao. O lado A defende `rules[0]`. |
| `athena` | string | não |  |
| `databricks` | string | não | Versao do Databricks Runtime ('15.4' ou '15.4.x-scala2.12'). DECLARACAO, nao observacao: perde para o event log, e discordar vira divergencia reportada em `runtime.divergences`. |
| `emr` | string | não | Release do EMR on EC2, nas duas grafias ('emr-7.5.0' ou '7.5.0'). DECLARACAO, nao observacao: perde para o event log e para um dump de describe-cluster, e discordar de um deles vira divergencia reportada em `runtime.divergences`, nunca valor substituido em silencio. |
| `facts` | array de object | não |  |
| `facts_path` | string ou array de string | não | Um caminho, ou varios: a UNIAO dos facts do case, o mesmo conjunto do `arbitrate`. Subconjunto fabrica claim desancorada. |
| `findings` | array de object | não |  |
| `findings_path` | string | não | Arquivo gerado por `sparkforge judge --out` -- o do `arbitrate`. |
| `glue` | string | não |  |
| `iceberg` | string | não |  |
| `photon` | string: `on`, `off` | não | Photon ligado ou desligado no Databricks. Com 'on', regra de plano sai em skipped com databricks.photon.unresolved, exceto a que so exige plan.python_udf ou plan.aqe. Plano com operador Photon (plan.photon) faz o mesmo sem declaracao e vence 'off', que vira divergencia 'photon:'. Sem databricks, vira divergencia 'photon:'. |
| `python` | string | não |  |
| `spark` | string | não |  |

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
