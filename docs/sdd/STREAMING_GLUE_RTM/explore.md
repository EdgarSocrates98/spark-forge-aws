---
sdd: 1
feature: STREAMING_GLUE_RTM
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Analyzer offline de definição Glue Streaming/RTM com regras de restrição e capacidade observada."
    tradeoffs:
      - "reuso do envelope CLI/MCP e fatos ancorados"
      - "não substitui collector AWS, matriz completa ou validação funcional"
  - id: B
    summary: "Inferir suporte RTM a partir de código Spark e nome de worker."
    tradeoffs:
      - "menos artefatos"
      - "mistura configuração com comportamento e inventa capacidade"
chosen: A
---

# STREAMING_GLUE_RTM — exploração

## Problema

O prompt exige Glue Streaming e Real-Time Mode como domínios operacionais. O
repositório possui fatos de Structured Streaming, mas não consegue separar uma
definição Glue, as restrições do RTM e a capacidade de partições/task slots sem
preencher ausência com suposição.

## Escopo desta wave

Extrair dumps JSON/JSONL de jobs Glue, preservar runtime/modo/fonte/opções e
`unresolved`, julgar três incompatibilidades observáveis, publicar CLI/MCP,
skill, especialista, routing e SDD. Terraform cross-artifact, collector live,
matriz completa e validação funcional permanecem lacunas nomeadas.
