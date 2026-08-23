---
name: agentic-orchestration
description: Use quando for necessario coordenar multiplos agents em fases limitadas, com handoffs, revisao e criterios de parada.
---

# Orquestracao Agentica

Coordene agents por fases, handoffs e criterios de parada. Abra ou retome o caso, classifique risco e complexidade, use ferramentas deterministicas antes do LLM e amplie o fan-out somente quando houver contradicao ou lacuna.

## Protocolo

O handoff minimo contem goal, status, evidence_refs, hypotheses, uncertainties, recommended_next_step e rollback.
## Quando NÃO usar

Nao use esta skill quando uma ferramenta deterministica simples resolver a tarefa sem cooperacao adicional.

## Referência rápida

Entrada: objetivo, escopo, evidencias e restricoes. Saida: handoff estruturado, referencias e proximo passo.

## Red flags

Contexto inteiro retransmitido, fan-out sem ganho, ausencia de evidencias, retry de contrato invalido ou mutacao sem aprovacao.
