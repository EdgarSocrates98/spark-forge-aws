---
name: tool-specialist-routing
description: Use quando for necessario escolher, validar ou autorizar ferramentas por especializacao, risco e contrato.
---

# Especializacao e Roteamento de Ferramentas

Escolha poucas ferramentas por agent, valide argumentos, registre fingerprints e autorize mutacoes somente com aprovacao e rollback.

## Contrato

Toda ferramenta devolve status, facts, warnings, evidence_refs, next_step e rollback.
## Quando NÃO usar

Nao use esta skill quando uma ferramenta deterministica simples resolver a tarefa sem cooperacao adicional.

## Referência rápida

Entrada: objetivo, escopo, evidencias e restricoes. Saida: handoff estruturado, referencias e proximo passo.

## Red flags

Contexto inteiro retransmitido, fan-out sem ganho, ausencia de evidencias, retry de contrato invalido ou mutacao sem aprovacao.

## Protocolo

Entregue fatos, decisoes, riscos, validacao, rollback e proxima acao em handoff compacto.
