---
sdd: 1
feature: FORGE_PORTAL
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Adapter fino dentro do pacote mapeando forge/PortalApi/1 para os serviços reais (install.lifecycle, integrate.open_host, registry, graphview); servidor stdlib vendored byte-identical do forge-portal."
    tradeoffs:
      - "Zero duplicação de lógica de domínio; receipts e recusas idênticos ao CLI."
      - "O adapter fica acoplado aos contratos internos do pacote — que são estáveis e testados."
  - id: B
    summary: "Servidor portal chamando a CLI por subprocess e parseando stdout."
    tradeoffs:
      - "Desacoplado do pacote."
      - "Frágil (parsing de saída humana), lento, e quebra o contrato de receipts estruturados."
  - id: C
    summary: "Reimplementar os serviços no portal."
    tradeoffs:
      - "Controle total do shape."
      - "Duplica o motor e viola a regra de misturar/divergir lógica de negócio entre forjas."
chosen: A
---

# FORGE_PORTAL — exploração

## Perfil

`dev`: a mudança evolui o próprio SparkForge — um verbo novo `portal`, um
adapter `sparkforge_aws/portal_adapter.py` e os assets vendored.

## Abordagem escolhida

A — adapter fino sobre os serviços reais. O portal é uma superfície, não um
motor: toda resposta vem de `lifecycle.*`, `open_host.ai_flow`,
`CanonicalRegistry` e `graphview.build_view`, preservando receipts
`forge/*` e recusas nomeadas. O servidor HTTP é o vendored canônico
`_forge_portal.py` (sessão por token, CSRF, plan tokens, loopback-only),
idêntico em bytes ao fonte em `forge-portal/portal_core`.
