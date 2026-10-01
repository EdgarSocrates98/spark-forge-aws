<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: rode `python scripts/gen_reference_docs.py`. -->

# `sparkforge_case_update`

**Efeito:** Grava em disco local e muda o estado a cada chamada (repetir não é igual a chamar uma vez).

## O que faz

Atualiza a fase, um gate booleano, ou registra o uso de uma skill no case atual. Cada mutacao e uma transicao de estado explicita e validada contra o dominio conhecido (PHASES, GATES) -- nunca um valor livre. Num case aberto com `strict_gates`, `gate_value` NAO destrava a transicao de fase: destrava o fact produtor (informe `facts_path`) ou um `override_gate` com `reason`.

## Parâmetros

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `repo` | string | sim |  |
| `close_hypothesis` | string | não | Id da hipotese a fechar (`h1`, `h2`, ...). Exige `hypothesis_outcome`. O registro e ACRESCIMO: a afirmacao, a previsao e o experimento originais ficam onde estao, e reescreve-los para casar com o resultado e o vies que a hipotese escrita existe para impedir. |
| `evidence` | string | não | Onde ler o que fechou a hipotese (stage, run, arquivo de facts). |
| `experiment` | string | não | Como medir a previsao. |
| `facts_path` | string ou array de string | não | Facts que comprovam os gates da fase pedida. Num case estrito, e daqui que sai a evidencia que destrava `phase`. |
| `gate` | string | não |  |
| `gate_value` | boolean | não |  |
| `hypothesis` | string | não | Afirmacao testavel a registrar. Exige `prediction` e `experiment`: afirmacao sem previsao nao e testavel, e previsao sem experimento nao diz quem a testa. As tres juntas viram uma entrada em `hypotheses`, com id sequencial e status `open`. |
| `hypothesis_outcome` | string: `confirmed`, `refuted`, `abandoned` | não | Desfecho do experimento. `confirmed` e `refuted` sao os dois lados dele; `abandoned` existe porque a terceira coisa que acontece de verdade e o experimento nunca rodar -- job descontinuado, ambiente que sumiu. |
| `now` | string | não |  |
| `outcome` | string | não |  |
| `override_gate` | string: `baseline_captured`, `dominant_bottleneck_identified`, `functional_validation_defined`, `flows_mapped` | não | Passa por cima deste gate num case estrito, quando o dado genuinamente nao existe (job descontinuado, ambiente que sumiu). Exige `reason`. |
| `phase` | string | não |  |
| `prediction` | string | não | O que muda no numero se a hipotese valer. |
| `reason` | string | não | Motivo do `override_gate`. Sem ele o override e recusado -- override anonimo nao se distingue de gate esquecido. |
| `skill` | string | não |  |

## Na CLI

[`sparkforge case get`](../cli/case.md), [`sparkforge case open`](../cli/case.md), [`sparkforge case update`](../cli/case.md)

## Capacidade

maintain investigation state

## Anotações MCP

| Anotação | Valor |
|---|---|
| `destructiveHint` | `false` |
| `idempotentHint` | `false` |
| `openWorldHint` | `false` |
| `readOnlyHint` | `false` |
