---
sdd: 1
feature: PLATFORM_INTELLIGENCE_EVALS
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Suite declarativa por domínio com casos sintéticos/realistas, gabarito de fatos e proibições, e métricas de economia observáveis."
    tradeoffs: ["reprodutível e offline", "casos reais precisam ser adicionados com governança"]
  - id: B
    summary: "Avaliar apenas resposta final de modelo."
    tradeoffs: ["mais simples", "perde evidência, unresolved, routing e custo de contexto"]
chosen: A
---

# PLATFORM_INTELLIGENCE_EVALS — exploração

O prompt exige centenas de casos reais e métricas de qualidade/economia. A
abordagem A entrega contrato e seed pack versionado agora, sem alegar que o
seed é corpus de produção nem converter bytes em tokens sem transcript.
