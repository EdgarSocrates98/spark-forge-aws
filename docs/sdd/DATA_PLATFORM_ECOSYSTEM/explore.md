---
sdd: 1
feature: DATA_PLATFORM_ECOSYSTEM
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Inventário declarativo de serving, ingestion, AI data e integrações radar com Connector Reliability Model."
    tradeoffs: ["um contrato transversal", "cada tecnologia ainda precisa de evidence própria"]
  - id: B
    summary: "Adicionar um agente e um conector dedicado por produto."
    tradeoffs: ["especialização", "explosão de superfície antes de evidência"]
chosen: A
---

# DATA_PLATFORM_ECOSYSTEM — exploração

O prompt pede muitos produtos e deixa Beam/DataHub/OpenMetadata como radar, não
dependências. O inventário A registra categoria, tecnologia, owner, lineage e
confiabilidade sem instalar ou conectar qualquer produto.
