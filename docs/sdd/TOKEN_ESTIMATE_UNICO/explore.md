---
sdd: 1
feature: TOKEN_ESTIMATE_UNICO
phase: explore
profile: dev
status: ready
approaches:
  - id: A
    summary: "Uma funcao so, a de sparkforge/agents/budget.py (teto de len/4, minimo 1, JSON ordenado para nao-string), e sparkforge/tools/cost.py, sparkforge/context/funnel.py e sparkforge/providers/mock.py passam a chama-la. O funnel e o mock mudam de comportamento (piso vira teto; o mock deixa de devolver 0), e o define mede e declara esse custo antes do build."
    tradeoffs:
      - "e a consolidacao que a propria base declara devida, na docstring de sparkforge/codeintel/budget.py"
      - "teto e o lado conservador: o funnel passa a encaixar no maximo os mesmos chunks, nunca mais"
      - "muda resultado: registros diferentes podem ser escolhidos com o mesmo orcamento; exige medida e aprovacao"
  - id: B
    summary: "Consolidar so agents/budget e tools/cost, que ja tem a mesma regra; funnel e mock ficam, documentados como divergentes."
    tradeoffs:
      - "zero mudanca de comportamento"
      - "resolve metade: a pergunta continua com duas respostas"
  - id: C
    summary: "Consolidar no piso."
    tradeoffs:
      - "muda agents/budget e tools/cost para baixo, que e o lado menos conservador, e agents/budget decide o corte das memorias de agente"
chosen: A
---

# TOKEN_ESTIMATE_UNICO — exploração

## Origem

A feature TOOLS_ORFAS foi abandonada antes do explore: medida de novo, a premissa ("cost
sem leitor") era falsa — o `__init__.py` do pacote reexporta e o `pyproject.toml` publica o
console script `sparkforge-tools`. A medida achou, no lugar, este defeito, já registrado em
`docs/claims.lock.json`: a mesma pergunta com quatro respostas. Pedido do operador em
2026-09-21.

## Perfil

`dev`.

## Medido (2026-09-21, `main` em `ed90f77f`)

| onde | fórmula | mínimo |
|---|---|---|
| `sparkforge/agents/budget.py::estimate_tokens` | teto de `len/4`; não-string vira JSON ordenado | 1 |
| `sparkforge/tools/cost.py::estimate_tokens` | teto de `len(str(x))/4` | 1 |
| `sparkforge/context/funnel.py` (em linha) | **piso** de `len/4` | 1 |
| `sparkforge/providers/mock.py` (em linha) | **piso** de `len/4` | **0** |

**Uma quinta fica fora, de propósito.** `sparkforge/codeintel/budget.py` mede
`utf8_bytes / 3`, e a docstring dele explica: *"a unidade é outra e o papel é outro: lá a
estimativa DECIDE o corte, aqui o byte decide e a estimativa acompanha"*. A mesma docstring
declara a consolidação dos quatro **devida**, *"com esse custo medido e declarado"*.

**O custo.** Trocar a fórmula de quem decide corte muda que registros são escolhidos com o
mesmo orçamento. A memória do projeto manda preservar semântica; por isso o define mede a
mudança e o operador a aprova com o número na mão.

## Perguntas feitas

1. Qual caminho? Resposta (2026-09-21): A, consolidar no teto com o custo medido.

## Escolha

A. O teto é o lado conservador: nenhum consumidor passa a gastar mais do que o orçamento.
