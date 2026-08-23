---
name: engineer-agent-context
description: Use quando for necessaria a capacidade de montar e comprimir contexto sem perder evidencia.
---
# Engineer Agent Context

Deduplicate mensagens, preserve kinds e envie contexto relevante.

## Protocolo
Use fatos locais, evidence_refs, confidence e unresolved. Entregue uma decisao estruturada ao coordenador. não executa manutencao destrutiva. Se houver mutacao, sobe a decisao ao coordenador e exige confirmacao explicita.

## Quando NÃO usar
Nao use quando uma ferramenta deterministica simples resolver o caso.

## Referência rápida
Entrada: pacote minimo. Saida: facts, riscos, lacunas e next_step. Parada: uma rodada.

## Red flags
Sem fonte, contexto inteiro retransmitido, afirmacao sem evidence_ref ou mutacao sem aprovacao.
