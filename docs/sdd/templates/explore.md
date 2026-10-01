---
sdd: 1
feature: EXEMPLO
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Gravar o resumo por execução num arquivo JSON ao lado do relatório."
    tradeoffs:
      - "simples e sem dependência nova"
      - "cada consumidor lê o arquivo por conta própria"
  - id: B
    summary: "Expor o resumo como verbo novo da CLI, com tool MCP."
    tradeoffs:
      - "um contrato só para CLI e MCP"
      - "move a superfície e o surface lock"
chosen: A
---

# EXEMPLO — exploração

> Template da skill `sdd-explore`. Copie para `docs/sdd/<FEATURE>/explore.md`,
> troque `feature: EXEMPLO` pelo nome da feature, os valores e o corpo, e ponha
> `status: draft` enquanto a conversa não fecha. `chosen` é um dos
> `approaches[].id`. `explore` é a única fase sem `upstream`, e é opcional:
> quando ela existe, o `define` passa a declarar `upstream` apontando para ela.

## Perfil

`dev`: a mudança é no próprio SparkForge. (`operator` quando a mudança é no job
de quem usa os agents; aí o build passa por `sparkforge change sandbox`.)

## Perguntas feitas, uma por vez

1. Quem lê o resumo? Resposta: o coordenador do case, depois de cada execução.
2. Precisa de CLI própria? Resposta: não nesta rodada.

## Abordagens

A (recomendada) resolve o pedido sem mexer na superfície. B fica registrada
para quando existir um segundo consumidor.

## Escolha

A, porque atende o único consumidor medido e não move o surface lock.
