---
sdd: 1
feature: FORGE_LAB_PRODUCT
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Construir um produto Lab CLI-first com contratos declarativos, backend Compose/Testcontainers compartilhado, captura de evidências e receipts assináveis."
    tradeoffs:
      - "Entrega superfície completa sem permitir execução implícita de infraestrutura."
      - "Exige vários contratos pequenos antes de existir uma suíte live."
  - id: B
    summary: "Criar somente um docker-compose grande e scripts por cenário."
    tradeoffs:
      - "Começo rápido para exploração manual."
      - "Duplica lógica, dificulta CI, receipts, oracle e reprodutibilidade."
  - id: C
    summary: "Começar por Testcontainers e esconder a topologia atrás de fixtures de teste."
    tradeoffs:
      - "Boa integração com pytest."
      - "Não atende uso interativo, CLI, shell, inspeção e promoção de runs."
chosen: A
---

# FORGE_LAB_PRODUCT — exploração

## Perfil

`dev`: a mudança evolui o próprio SparkForge.

## Perguntas e decisão

1. O prompt trata Forge Lab como produto interno e fábrica de evidências, não
   como pasta de scripts; resposta: sim.
2. A primeira entrega deve executar containers automaticamente; resposta: não,
   comandos mutáveis exigem `--execute --confirm` e o default é plano offline.
3. Compose e Testcontainers devem ter implementações independentes; resposta:
   não, ambos consomem o mesmo manifesto, registry, cenário e action plan.

## Escolha

A vence porque cobre o ciclo inteiro (`scenario → environment → workload →
fault → probes → capture → analyze/judge → oracle → receipt`) mantendo L0/L1/L2/L3,
sem transformar ambiente local em prova de comportamento AWS.
