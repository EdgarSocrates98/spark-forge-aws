---
sdd: 1
feature: EXEMPLO
phase: ship
profile: dev
status: ready
upstream:
  path: docs/sdd/EXEMPLO/build_report.md
  sha256: ""
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity]
deviations:
  - "Nenhum desvio do plano."
---

# EXEMPLO — entrega

> Template da skill `sdd-ship`. `registries` sai de `change_kinds` do define,
> pelo mapa de `sparkforge/sdd/change_kinds.yaml`: aqui `agent_or_skill` exige
> `sync_skills` e `agents_parity`, e cada um foi rodado pela secao de
> `docs/gates-por-mudanca.md`. `hypothesis_outcome` fecha a hipotese do define
> sem reescreve-la (`confirmed`, `refuted` ou `abandoned`).

## Hipotese

Confirmada: o coordenador leu o resumo no case sintetico e o teste passou.
Se alguma parte da previsao so pode ser medida depois, diga qual e onde.

## Gates rodados

- `python scripts/sync_skills.py --check`
- `python -m pytest tests/test_agents_parity.py -q`
