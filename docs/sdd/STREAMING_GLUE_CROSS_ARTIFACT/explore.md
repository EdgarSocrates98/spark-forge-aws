---
sdd: 1
feature: STREAMING_GLUE_CROSS_ARTIFACT
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Derivar link Glue efetivo→Terraform no fuse existente, com comparação declarada e unresolved por campo."
    tradeoffs: ["reutiliza pipeline Facts→fuse→judge", "não prova estado live nem execução do job"]
  - id: B
    summary: "Criar analyzer/verb dedicado para receber dois artefatos e correlacionar fora do fuse."
    tradeoffs: ["surface e payload novos", "duplica o contrato de fusão e quebra composição existente"]
  - id: C
    summary: "Consultar Glue/Terraform state live durante a análise."
    tradeoffs: ["poderia reduzir drift desconhecido", "viola core offline e exige credencial, endpoint e autorização"]
chosen: A
---

# STREAMING_GLUE_CROSS_ARTIFACT — exploração

## Lacuna observada

`glue.streaming.job` já descreve uma definição efetiva salva e `tf.resource`/`tf.attribute`
já descrevem `aws_glue_job` em Terraform, mas nenhum compositor cruza as duas
fontes. Assim, divergência de Glue version, modo RTM, linguagem ou workers não
chega ao juiz como um fato único e reauditable.

## Escolha

A mantém o contrato do repositório: extratores continuam somente observando,
`fuse` deriva fatos compostos, regras julgam fatos e o operador pode reextrair
cada origem pelos `source_fact_ids`. A identidade é declarada pelo nome literal
do job; ausência, ambiguidade ou valor Terraform não resolvido vira
`glue.streaming.cross.unresolved`, nunca correspondência presumida.

Collector AWS, Terraform state completo, execução funcional e validação live
ficam fora desta wave: exigem endpoint, credencial, janela e workload reais.
