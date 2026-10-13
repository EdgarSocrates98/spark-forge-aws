---
sdd: 1
feature: STREAMING_RUNTIME_MATRIX
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Matriz local versionada, com fontes oficiais, estados e limites explícitos."
    tradeoffs: ["não substitui dump regional/managed nem runtime observado"]
  - id: B
    summary: "Copiar versões upstream para runtime_scope e tratar managed como equivalente."
    tradeoffs: ["fabricaria compatibilidade e perderia divergências de serviço"]
chosen: A
---

# STREAMING_RUNTIME_MATRIX — exploração

O prompt exige matriz de versões para P0, mas o SparkForge não deve transformar
release upstream em capacidade de Glue, MSK ou Managed Flink. A abordagem A
registra somente fatos revalidados, `UNRESOLVED` quando a fonte managed/regional
não está no corpus e `N/A + motivo` quando o conceito de release não se aplica.

Fora do escopo: consultar AWS live, alterar `runtime_scope` de regras existentes
sem uma fonte e afirmar throughput, custo ou compatibilidade funcional.
