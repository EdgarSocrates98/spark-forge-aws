---
sdd: 1
feature: STREAMING_ICEBERG_TEMPORAL
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Emitir um Fact por snapshot observado e compor uma janela temporal progresso→Iceberg sobre facts já extraídos."
    tradeoffs:
      - "preserva source_fact_ids granulares e permite pareamento determinístico"
      - "altera o corpus de facts do extrator Iceberg e exige regenerar goldens"
  - id: B
    summary: "Adicionar lista compacta de timestamps dentro de iceberg.snapshots_summary e parear o resumo agregado."
    tradeoffs:
      - "menor mudança de kinds e menos fixtures alteradas"
      - "perde âncora por snapshot e aumenta o payload de um fact agregado"
  - id: C
    summary: "Criar collector live para consultar snapshots e progresso em AWS/Spark durante a composição."
    tradeoffs:
      - "poderia observar janela real"
      - "introduz credencial, rede, custo e uma superfície que não cabe no core offline"
chosen: A
---

# STREAMING_ICEBERG_TEMPORAL — exploração

## Perfil

`dev`: mudança no próprio SparkForge, sem recurso AWS live ou benchmark externo.

## Perguntas feitas

1. Qual lacuna P0 permanece? A composição `mode=iceberg` só recebe um
   `iceberg.snapshots_summary` agregado; não há uma sequência de snapshots com
   timestamp e operação para correlacionar com batches observados.
2. Qual evidência o agente precisa reauditar? Facts individuais por snapshot,
   ids de origem, janela declarada e unresolved quando timestamp, identidade ou
   quantidade mínima faltarem.
3. Como preservar economia? Emitir diagnóstico agregado com ids de facts e
   `detail_level=summary`; não copiar todos os snapshots para o finding.

## Escolha

A foi escolhida porque mantém extração, composição e julgamento separados,
fecha a âncora factual que B perderia e continua offline. C fica fora: collector
live é uma feature de coleta e autorização independente, não requisito para
provar o contrato sobre dumps já coletados.
