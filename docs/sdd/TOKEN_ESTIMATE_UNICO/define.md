---
sdd: 1
feature: TOKEN_ESTIMATE_UNICO
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/TOKEN_ESTIMATE_UNICO/explore.md
  sha256: "39bd3fce3c5094dae3fb9706c26141a86f20da2c93e8b1ee07a70d1b3d14169f"
hypothesis:
  claim: "Os quatro estimadores de token por caracteres podem virar um so, o de sparkforge/agents/budget.py (teto de len/4, minimo 1), sem que nenhum consumidor passe a gastar mais do que o orcamento dele: o teto e o lado conservador, entao o funnel encaixa no maximo os mesmos chunks, e o mock deixa de afirmar zero token."
  prediction: "Depois da mudanca: tools/cost, context/funnel e providers/mock chamam a mesma funcao, conferido por identidade; para qualquer entrada, o funnel com teto escolhe um PREFIXO da escolha que fazia com piso, nunca um conjunto maior; o mock nunca devolve 0; e nenhum golden de achado muda. Se algum sitio mantiver formula propria, se o funnel escolher um chunk que antes nao escolhia, ou se um golden de achado mudar, a afirmacao esta errada."
  experiment: "Testes de identidade e de prefixo sobre entradas sinteticas, os testes existentes de funnel e mock, e python -m pytest tests/test_fixtures_golden*.py -q sem regenerar."
acceptance:
  - id: AC1
    statement: "Existe uma definicao de estimativa de token por caracteres, em sparkforge/agents/budget.py, e tools/cost.py, context/funnel.py e providers/mock.py a usam -- conferido por identidade, nao por nome. sparkforge/codeintel/budget.py continua fora, com a razao na docstring dele."
    verified_by: {kind: test, ref: "tests/test_token_estimate_unico.py::test_uma_definicao_e_os_sitios_a_usam"}
  - id: AC2
    statement: "Com o teto, o funnel escolhe sempre um prefixo do que escolhia com o piso: nunca um chunk a mais, nunca acima do orcamento."
    verified_by: {kind: test, ref: "tests/test_token_estimate_unico.py::test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso"}
  - id: AC3
    statement: "O mock nunca devolve 0 token: texto vazio e texto de 1 a 3 caracteres dao 1."
    verified_by: {kind: test, ref: "tests/test_token_estimate_unico.py::test_mock_nunca_afirma_zero_token"}
  - id: AC4
    statement: "Nenhum golden de achado muda: a suite de goldens passa sem regeneracao."
    verified_by: {kind: command, ref: "python -m pytest tests/test_fixtures_golden*.py -q"}
  - id: AC5
    statement: "A alegacao auditada que dizia 'existe quatro vezes, e essas divergem' passa a descrever o que existe, e o gate de lastro fecha."
    verified_by: {kind: command, ref: "python scripts/check_vnext_claims.py"}
success:
  - id: SC1
    metric: "Definicoes de estimativa de token por caracteres, antes e depois"
    source: "varredura por len(...) // 4 e def estimate_tokens em sparkforge/"
  - id: SC2
    metric: "Testes existentes cuja expectativa numerica mudou, com o antes e o depois de cada um"
    source: "diff dos testes de funnel e mock no build"
  - id: SC3
    metric: "Goldens de achado que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
out_of_scope:
  - "sparkforge/codeintel/budget.py e a formula utf8_bytes / 3: outra unidade e outro papel, declarados na docstring dele."
  - "Trocar 4 caracteres por token por outra razao: a heuristica fica; so as quatro copias viram uma."
  - "Token de provider: regra 24 -- estimativa nunca se veste de token medido."
unknowns: []
change_kinds: [claims]
---

# TOKEN_ESTIMATE_UNICO — requisitos

## Problema

A mesma pergunta — quantos tokens tem este texto — tem quatro respostas no repositório, e
elas divergem: duas arredondam para cima, duas para baixo, e uma afirma zero token para
texto curto. `docs/claims.lock.json` já registrava isso; `sparkforge/codeintel/budget.py`
declarava a consolidação devida.

## O que muda, e por que é seguro para cima

O `funnel` e o `mock` passam do piso para o teto. O teto é o lado conservador: o funnel
passa a caber **no máximo** os mesmos chunks, nunca mais, e nenhum consumidor estoura o
orçamento. O AC2 trava isso como propriedade — prefixo da escolha antiga — em vez de
confiar no argumento.

## O custo, medido no build

Mudar o funnel muda **quantos** chunks cabem no limite. O SC2 obriga o build a listar cada
teste cuja expectativa numérica mudou, com o antes e o depois, para que a mudança de
comportamento seja lida e não descoberta.
