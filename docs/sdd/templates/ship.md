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

> Template da skill `sdd-ship`. Troque `feature: EXEMPLO` pelo nome da
> feature e ponha `status: draft` ao copiar. `registries` sai de
> `change_kinds` do define, pelo mapa de `sparkforge/sdd/change_kinds.yaml`:
> aqui `agent_or_skill` exige `sync_skills` e `agents_parity`, e cada um foi
> rodado pela seção de `docs/gates-por-mudanca.md`. `hypothesis_outcome` fecha
> a hipótese do define sem reescrevê-la (regra 21): `confirmed` só com a
> previsão inteira medida.

## Hipótese

Confirmada: o coordenador leu o resumo no case sintético e o teste passou.
Parte da previsão sem medida mantém o ship em `draft`, ou fecha como
`abandoned` dizendo onde será medida.

## Gates rodados

- `python scripts/sync_skills.py --check` (exit 0)
- `python -m pytest tests/test_agents_parity.py -q` (exit 0)
- Cada `verified_by` de `kind: command` do define, com o exit.

## Lições

- O que a próxima feature deve fazer diferente, com a evidência no relatório.
