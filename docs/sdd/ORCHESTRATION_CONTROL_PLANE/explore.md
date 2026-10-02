---
sdd: 1
feature: ORCHESTRATION_CONTROL_PLANE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Contrato normalizado de orquestradores e workflows, preservando configuração de origem."
    tradeoffs: ["compara plataformas sem perder detalhes", "precisa de export declarado"]
  - id: B
    summary: "Executar cada API de orquestração no analisador."
    tradeoffs: ["dados frescos", "credencial/rede e semântica live fora do core"]
chosen: A
---

# ORCHESTRATION_CONTROL_PLANE — exploração

O prompt pede Airflow, Dagster, Step Functions e Control-M com confiabilidade
operacional. A abordagem A cria um inventário canônico e pode receber fragments
dos analisadores existentes sem duplicar conectores.
