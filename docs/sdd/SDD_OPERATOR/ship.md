---
sdd: 1
feature: SDD_OPERATOR
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_OPERATOR/build_report.md
  sha256: "1c06876ea4cf24ac861d83f84b321d7d20c8ff035a94e57068f1267c9aaf4dd6"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity]
deviations:
  - "T1: o teste de funcval_not_comparison tambem recusa arquivo que nao e JSON."
  - "T2: o teste cobre tambem a forma real do funcval.unresolved (subject.symbol e attrs.reason)."
  - "T3: o teste passou de primeira depois de T1/T2; o vermelho foi visto num git worktree em 2bed741a; a comparacao e sintetica e funcval compare nao roda no teste."
  - "T4: D2 revista. As sdd-* sao nao despachaveis (NON_DISPATCHABLE_SKILLS) e ficam fora do skills: dos coordenadores, que as citam na prosa; o teste de T4 inverteu a assercao, e design e plan foram recarimbados."
  - "T5 (acrescimo pedido no build, dentro do commit de T4): perfil operator concreto em sdd-define, sdd-plan e sdd-build; os tres arquivos entraram no manifesto do design e na T4."
  - "Registros fora do manifesto: docs/guia/referencia, surface lock, claims lock (VNX-640, VNX-674, VNX-726), CODEINTEL-GAP, ADR-010 e STATUS."
  - "Build num agente so, sem subagente por tarefa e sem a revisao em dois estagios."
---

# SDD_OPERATOR — entrega

## Hipótese

**Confirmada no que o experimento do define mede, com duas ressalvas.** O
experimento era um teste de ponta a ponta com `case_open` e `change_sandbox`
reais sobre um repositório sintético, e ele roda:
`tests/test_sdd_operator.py::test_fluxo_operator_ponta_a_ponta`.

A previsão tem duas partes, e as duas se confirmaram:

- **O fluxo operator passa no `sdd check`.** O case vem de `case_open`, o id de
  `change_sandbox` vira `change_id`, e há um arquivo de comparação. A feature
  sai `ok`, sem recusa e sem lacuna.
- **O gate recusa o mesmo fluxo sem o sandbox ou sem a comparação.**
  - Depois de `change sandbox` com `clean`, sai `change_missing`.
  - Com um arquivo de comparação sem `funcval.check_delta`, sai
    `funcval_not_comparison`.

As ressalvas, ditas em vez de caladas:

1. A comparação do teste é **sintética**, na forma de
   `sparkforge/facts/funcval.py::_check_delta`. `sparkforge funcval compare` não
   roda no teste, embora a previsão o cite entre parênteses. O experimento do
   define só nomeia `case_open` e `change_sandbox`.
2. Comparação **ausente** continua sendo lacuna (`funcval_not_run`), não
   recusa. O `check` sai com `ok` falso, mas o código é `unresolved`. A
   previsão fala em "recusa"; o que se prova como recusa é a comparação sem
   delta.

**Fica para `SDD_EVAL` (E):** a parte da afirmação que fala de quem usa os
agents, ou seja, um operador de verdade especificando e mudando o próprio job
com o SDD. Um teste sintético não mede isso.

`SC1`, medido em `tests/test_sdd_operator.py` e `tests/test_sdd.py`, lista os
códigos que o fluxo operator exercita:

- recusas: `change_missing` e `funcval_not_comparison`;
- lacuna: `funcval_blind_spot`, no teste do núcleo;
- no caso positivo, nenhum código.

## Registros

`change_kinds` do define: `agent_or_skill`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `sync_skills` | Alterar agent, skill ou seus espelhos | `python scripts/sync_skills.py` com `.claude/agents/README.md` fora da árvore, depois `--check`: OK |
| `agents_parity` | Alterar agent, skill ou seus espelhos | `python -m pytest tests/test_agents_parity.py tests/test_agent_coverage.py tests/test_sync_render.py -q`: verde, dentro da bateria abaixo |

Estes gates não vêm do mapa de `change_kinds`. Rodaram porque a entrega os move:

- `python scripts/gen_reference_docs.py`: 7 páginas regravadas; na última
  rodada, 0 regravadas.
- `python scripts/check_surface_lock.py --update`: +770 bytes em skills
  (528425 para 529195), declarados no commit `9f720e05`. Depois disso, 0
  divergências.
- `python scripts/check_vnext_claims.py`: 0 divergências. VNX-640, VNX-674 e
  VNX-726 foram remediados por id.
- `python scripts/check_status_numbers.py --strict`: 0 divergências.

A bateria final de testes rodou com 1594 passando e nenhuma falha:

```
python -m pytest tests/test_sdd.py tests/test_sdd_operator.py tests/test_sdd_skills.py tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_reference_docs.py tests/test_arvore_versionada.py tests/test_adapters_tools.py tests/test_harness_authorization.py -q
```

A suíte inteira em lotes (`tests/test_suite_batches.py`) não rodou nesta
entrega.

## Desvios

O detalhe está no `build_report.md`. O desvio que muda o desenho é o D2. Uma
skill não-despachável não entra no `skills:` de um coordenador, porque o
coordenador roda como subagente. O ponteiro para ela mora na prosa. Quem
desenhar a próxima feature que ligue agent a skill deve ler
`scripts/sync_skills.py::NON_DISPATCHABLE_SKILLS` antes.

## O que fica para depois

- `SDD_MIGRATION` (D): desativar os plugins e apontar `CLAUDE.md`/`AGENTS.md`
  para as skills.
- `SDD_EVAL` (E): um caso operator real, com `sparkforge funcval compare` de
  verdade, e a pergunta se o ciclo próprio rende melhor. Nenhuma afirmação de
  ganho é feita aqui.
- Comparação ausente como recusa: hoje é lacuna por desenho do núcleo
  (`funcval_not_run`). Mudar isso é decisão do núcleo, não desta feature.
