---
sdd: 1
feature: DATA_OBSERVABILITY_SRE
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Avaliar SLOs e incidentes sobre dumps métricos declarados, preservando unidades e lacunas."
    tradeoffs: ["offline e auditável", "não substitui OTel/Prometheus live"]
  - id: B
    summary: "Consultar observabilidade ao vivo pelo analisador."
    tradeoffs: ["frescor", "acoplamento de credencial, janela e custo"]
chosen: A
---

# DATA_OBSERVABILITY_SRE — exploração

O prompt requer Data Observability/Data SRE e OpenTelemetry. A abordagem A
avalia evidência exportada em arquivo e integra depois com collectors como
fragments, mantendo ausência de métrica como unresolved.
