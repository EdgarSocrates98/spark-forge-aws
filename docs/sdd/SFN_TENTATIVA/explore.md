---
sdd: 1
feature: SFN_TENTATIVA
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Recusa nomeada onde a contagem de tentativas nao e comparavel. Os tres tipos publicados que faltam entram em _TIPOS_CONHECIDOS, mas ExecutionRedriven ganha razao propria (sfn.unresolved: execution_redriven) e faz build_sfn_retry_observado RECUSAR o confronto daquele artefato, porque um teto declarado no ASL nao se compara com uma contagem que atravessa um redrive; EvaluationFailed e MapRunRedriven entram como conhecidos sem fact, como os demais MapRun*. Estados de mesmo nome cuja entrada pende de ancestrais de ramo diferentes deixam de ser numerados: saem em sfn.unresolved nomeado, e nenhum sfn.attempt e emitido para eles."
    tradeoffs:
      - "nao depende de nenhuma medida que ninguem tem: decide pela forma publicada e pela regra 20"
      - "promove ExecutionRedriven de 'palavra que o extrator nao conhece' para 'palavra que ele conhece, e que diz que a contagem nao e comparavel' -- a recusa passa a ter causa, nao so nome"
      - "SF-SFNX-002 e SF-SFNX-003 deixam de ancorar nos casos de Parallel com estados homonimos; hoje elas ancoram num attempt_index ERRADO, entao a troca e recusa no lugar de afirmacao falsa"
      - "nao resolve a reentrada por Choice, que continua contada como tentativa e continua so na prosa"
  - id: B
    summary: "Numerar as tentativas por ENTRADA de estado: ordem_por_estado passa a ser chaveado pelo id do TaskStateEntered em vez do nome."
    tradeoffs:
      - "resolveria Parallel com estados homonimos E a reentrada por Choice de uma vez"
      - "o trade-off que pode mata-la nao esta medido: se o Retry do Step Functions emitir um NOVO TaskStateEntered a cada tentativa, todo retry vira indice 1 e a SF-SFNX-001 perde exatamente a medida que ela existe para fazer"
      - "nenhuma das quatro paginas ja citadas em knowledge/stepfunctions/execution-history.md decide isso; e lacuna, e a abordagem depende de fecha-la"
  - id: C
    summary: "So acrescentar os tres tipos publicados a _TIPOS_CONHECIDOS, sem consequencia."
    tradeoffs:
      - "o menor diff possivel"
      - "apaga a recusa sem por nada no lugar: a contagem passa a atravessar um redrive CALADA, que e o defeito critico corrigido no #92 entrando por outra porta"
chosen: A
---

# SFN_TENTATIVA — exploração

## Origem

As revisões finais de #90, #91 e #92 deixaram três itens de consolidação. O operador
pediu a consolidação em 2026-09-20 e escolheu decompor em **duas** features: esta, sobre
o que é uma tentativa e quando o extrator não sabe dizer, e `GLUE_TERRAFORM`, sobre o
módulo compartilhado. As duas são assuntos diferentes e ciclos diferentes.

## Perfil

`dev`. A mudança é no próprio SparkForge.

## O que o repositório já diz sobre isto

`knowledge/stepfunctions/execution-history.md` §5, relido em 2026-09-20, **já nomeia os
dois casos** e já argumenta contra a forma óbvia:

- **Lacuna 9:** "os `Valid Values` do campo `type` do `HistoryEvent` trazem 62 tipos, e
  `_TIPOS_CONHECIDOS` tem 59 — faltam `EvaluationFailed`, `ExecutionRedriven` e
  `MapRunRedriven`". E, decisivo: "**`ExecutionRedriven` é a execução RETOMADA**, e ele
  muda o que 'quantas vezes o Task foi agendado' significa — um redrive reagenda o Task
  dentro da MESMA execução, e nada aqui hoje separa as tentativas de antes do redrive das
  de depois."
- **Lacuna 8:** "Nas duas páginas da API relidas em 2026-09-20, o `previousEventId` tem
  uma descrição e só uma: 'The id of the previous event.' Nada ali diz que, dentro de um
  `Parallel` ou de um `Map`, o anterior é o do **mesmo ramo**."

O defeito medido hoje, no código: `ordem_por_estado`
(`sparkforge/facts/sfn_history.py`, laço que resolve cada `TaskScheduled`) é chaveado
**só pelo nome do estado**. Dois ramos de um `Parallel` com um estado de mesmo nome
compartilham o contador, e a primeira tentativa do segundo ramo sai com índice 2. Esse
índice é o `subject.symbol` do `sfn.attempt`, e é por ele que SF-SFNX-002 e SF-SFNX-003
apontam o achado.

A revisão de #92 registrou os dois como menores 14 e 18, e o `ship.md` daquela feature os
levou para as pendências.

## Perguntas feitas

1. Como decompor os três itens de consolidação? Resposta (2026-09-20): duas features,
   com a semântica da tentativa primeiro.
2. Qual abordagem? Resposta (2026-09-20): A.

## Abordagens

A é a recomendada por um motivo só: **ela não depende de medida que ninguém tem**. B
resolveria mais, e por isso foi levada ao operador — mas ela pende de uma frase que
nenhuma das páginas já lidas publica, e adotá-la sem essa frase é trocar um índice errado
por outro. C é o mínimo, e é o pior: apaga a recusa e deixa a contagem atravessar o
redrive em silêncio.

O que A **não** faz, e fica declarado: a reentrada de estado por `Choice` continua contada
como tentativa. Ela é o caso em que B ganharia, e volta quando a lacuna do `Retry`
fechar — com um histórico real, ou com a página que a decida.

## Escolha

A, escolhida pelo operador.
