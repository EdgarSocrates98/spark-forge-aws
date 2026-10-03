---
sdd: 1
feature: STREAMING_GLUE_CROSS_ARTIFACT
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/STREAMING_GLUE_CROSS_ARTIFACT/define.md
  sha256: "b8dccade56fc7b8290a394926ed60ae0ca8edbb25cbc92336d2d84f532c719f0"
files:
  - {path: sparkforge/facts/streaming_glue_cross.py, action: create, reason: "correlacionar fatos Glue efetivos e Terraform sem reler artefatos"}
  - {path: sparkforge/facts/fusion.py, action: modify, reason: "invocar derivação somente quando os kinds fonte existirem"}
  - {path: rules/catalog/glue-streaming.yaml, action: modify, reason: "julgar drift e blind spot cross-artifact"}
  - {path: fixtures/streaming_glue_cross_artifact, action: create, reason: "goldens de match, drift e identidade/valor unresolved"}
  - {path: tests/test_streaming_glue_cross_artifact.py, action: create, reason: "contrato, regra, guarda e idempotência"}
  - {path: knowledge/glue-streaming-rtm.md, action: modify, reason: "explicar comparação efetiva→IaC e limites"}
  - {path: skills/review-glue-streaming/SKILL.md, action: modify, reason: "orientar reextração e leitura do link"}
  - {path: docs/streaming/prompt-coverage.md, action: modify, reason: "registrar fechamento parcial da lacuna Glue cross-artifact"}
decisions:
  - id: D1
    choice: "Usar fuse como ponto de composição e publicar um resumo content-addressed com ids das fontes."
    rejected: ["novo analyzer que duplica envelope", "regra que combina dois facts diretamente"]
    rollback: "Remover a chamada do fuse e preservar apenas os extratores atuais."
  - id: D2
    choice: "Casar exclusivamente por name literal único; resource_name não substitui name."
    rejected: ["casar pelo sufixo do resource", "casar o único job do pool sem identidade declarada"]
    rollback: "Retornar unresolved para toda identidade não literal ou ambígua."
  - id: D3
    choice: "Comparar quatro eixos observáveis: Glue version, RTM enabled, language e worker count."
    rejected: ["inferir fonte/sink do nome do script", "tratar ausência como igualdade", "atribuir capacidade suficiente"]
    rollback: "Reduzir o link aos eixos com evidência e manter os demais em unresolved."
  - id: D4
    choice: "Não criar tool MCP: `fuse` existente já é a superfície comum e evita crescimento de payload."
    rejected: ["mais uma tool somente para Glue", "transportar os artefatos crus ao compositor"]
    rollback: "Se o fluxo comum não expuser o contrato, criar verbo separado em SDD posterior."
covers:
  - {part: "cross-artifact extractor and identity", acceptance: [AC1, AC2]}
  - {part: "fusion and rules", acceptance: [AC3, AC4]}
  - {part: "fixtures, skill and documentation", acceptance: [AC5]}
---

# STREAMING_GLUE_CROSS_ARTIFACT — desenho

Fluxo: `analyze glue-streaming + analyze terraform → fuse → judge`.
O compositor não acessa disco nem rede. O link preserva poucos atributos
comparáveis, `source_fact_ids`, divergências e campos não resolvidos; o payload
de detalhe pode expandir as fontes originais por referência.
