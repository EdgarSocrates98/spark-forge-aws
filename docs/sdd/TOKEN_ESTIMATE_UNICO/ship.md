---
sdd: 1
feature: TOKEN_ESTIMATE_UNICO
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/TOKEN_ESTIMATE_UNICO/build_report.md
  sha256: "a81cd9ff7fc1d76648c1d6ba7352cfab87fab9039c14309329767bc728d1f09e"
hypothesis_outcome: confirmed
registries: [claims_gate]
deviations:
  - "A feature substituiu TOOLS_ORFAS, abandonada antes do explore: medida de novo, a premissa era falsa (o __init__ reexporta e o pyproject publica o console script sparkforge-tools)."
  - "A revisao achou regressao de API publica: o alias fazia sparkforge.tools.estimate_tokens levantar TypeError onde antes devolvia numero. Corrigido em 0839755c."
  - "A selecao do funnel muda em 20.553 de 59.040 casos pequenos medidos; o prefixo vale em todos. E o custo aceito pela abordagem A."
  - "Plano e build numa rodada so, por pressao de contexto."
  - "O scan Snyk nao concluiu: MCP sem conexao, CLI autenticado travando ate em 6 arquivos. Feita revisao manual da superficie."
---

# TOKEN_ESTIMATE_UNICO — entrega

## Hipotese

**Confirmada.** `tools/cost`, `context/funnel` e `providers/mock` usam a funcao de
`agents/budget` (identidade conferida); o funnel com teto escolhe sempre um prefixo do que
escolhia com piso (0 falhas em 59.040 casos); o mock nunca afirma 0; nenhum golden de achado
mudou (3299 passed, 4 skipped, sem regenerar).

## O custo, dito

O funnel encaixa **menos** chunks num orcamento apertado: a selecao mudou em 20.553 dos
59.040 casos medidos, e um chunk unico que cabia justo com o piso agora sai. Nunca encaixa
mais, nunca estoura o orcamento.

## Gates

| gate | resultado |
|---|---|
| testes da feature, funnel, codeintel, agent runtime, offline | 39 passed |
| `pytest tests/test_fixtures_golden*.py` (AC4) | 3299 passed, 4 skipped |
| `python scripts/check_vnext_claims.py` (AC5) | 0 divergencias |
| `ruff` | limpo |
| `sparkforge sdd check --feature TOKEN_ESTIMATE_UNICO` | ok |
| scan Snyk | **nao concluiu** |

## Pendencias

- `sparkforge/codeintel/budget.py` (`utf8_bytes / 3`) segue separado, de proposito.
- A docstring de `tools/cost.py` diz `is_estimate: True` "em todo retorno"; so
  `budget_report` devolve dict. Anterior a esta feature.
- Rodar o scan Snyk quando o motor do Snyk Code subir nesta maquina.

## Licoes

- **Alias preserva o nome, nao o comportamento.** A identidade provou que era a mesma
  funcao -- e por isso mesmo a API publica herdou o `TypeError` do dono.
- **"Sem leitor" exige varredura exaustiva**, que e por que esta feature existe no lugar
  da TOOLS_ORFAS.
