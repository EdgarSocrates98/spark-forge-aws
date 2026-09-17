---
sdd: 1
feature: EXEMPLO
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Gravar o resumo por execucao num arquivo JSON ao lado do relatorio."
    tradeoffs:
      - "simples e sem dependencia nova"
      - "cada consumidor le o arquivo por conta propria"
  - id: B
    summary: "Expor o resumo como verbo novo da CLI, com tool MCP."
    tradeoffs:
      - "um contrato so para CLI e MCP"
      - "move a superficie e o surface lock"
chosen: A
---

# EXEMPLO — exploracao

> Template da skill `sdd-explore`. Copie para `docs/sdd/<FEATURE>/explore.md`,
> troque `feature`, os valores e o corpo, e ponha `status: draft` enquanto a
> conversa nao fecha. `explore` e a unica fase sem `upstream`, e e opcional:
> quando ela existe, o `define` passa a declarar `upstream` apontando para ela.

## Perfil

`dev`: a mudanca e no proprio SparkForge. (`operator` quando a mudanca e no job
de quem usa os agents; ai o build passa por `sparkforge change sandbox`.)

## Perguntas feitas, uma por vez

1. Quem le o resumo? Resposta: o coordenador do case, depois de cada execucao.
2. Precisa de CLI propria? Resposta: nao nesta rodada.

## Abordagens

A (recomendada) resolve o pedido sem mexer na superficie. B fica registrada
para quando existir um segundo consumidor.

## Escolha

A, porque atende o unico consumidor medido e nao move o surface lock.
