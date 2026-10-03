---
sdd: 1
feature: PLATFORM_INTELLIGENCE_GRAPH
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Estender o compositor federado existente com um contrato explícito de entidades, linhagem e impacto da plataforma de dados."
    tradeoffs:
      - "Reutiliza limites, frescor, proveniência e unresolved já existentes."
      - "Exige um novo contrato de entrada e uma nova superfície de análise."
  - id: B
    summary: "Criar um grafo paralelo isolado para streaming e lakehouse."
    tradeoffs:
      - "Permite evolução independente."
      - "Duplica composição, segurança e semântica de impacto."
  - id: C
    summary: "Inferir relações diretamente de nomes, código e serviços descobertos."
    tradeoffs:
      - "Menos configuração inicial."
      - "Viola evidência explícita e produz falsos vínculos sem contrato."
chosen: A
---

# PLATFORM_INTELLIGENCE_GRAPH — exploração

## Perfil

`dev`: a mudança evolui o próprio SparkForge.

## Perguntas feitas

1. O prompt pede um Control Plane de Metadata Graph, Lineage e Impact Analysis;
   resposta: sim, como fundação P0 para as demais fases.
2. A relação deve ser inferida por nome ou declarada com evidência;
   resposta: declarada, com pontos cegos explícitos.

## Escolha

A vence porque transforma o compositor federado existente no núcleo comum para
datasets, jobs, runs, contratos, owners, SLOs, consumidores e serviços sem
permitir que conectores futuros inventem lineage.
