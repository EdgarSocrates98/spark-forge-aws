---
sdd: 1
feature: STREAMING_ARCHITECTURE_DECISION
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Decision engine offline que separa requirements, assumptions e elimina candidatos por constraints declaradas."
    tradeoffs:
      - "não escolhe entre candidatos empatados"
      - "exige input explícito e validação posterior"
  - id: B
    summary: "Ranking por preferência de serviço, custo presumido ou popularidade."
    tradeoffs:
      - "resposta rápida"
      - "transforma hipótese em decisão e não deixa auditoria reproduzível"
chosen: A
---

# STREAMING_ARCHITECTURE_DECISION — exploração

O prompt pede requirements→facts→candidates→constraints→ADR. A plataforma já
tinha desenho genérico e Decision Plane para roteamento, mas não uma avaliação
streaming que recusasse um vencedor quando fatos não eliminassem alternativas.

Escopo: comando CLI offline, matriz pequena de candidatos de runtime/sink,
fixtures de empate, seleção factual e insuficiência. Sem benchmark, preço,
SLO, provisionamento ou collector live.
