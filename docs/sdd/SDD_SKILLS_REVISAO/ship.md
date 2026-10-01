---
sdd: 1
feature: SDD_SKILLS_REVISAO
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_SKILLS_REVISAO/build_report.md
  sha256: "76e173f66bef8aee0a795e97dc51010e357a80df60c1400b7c967fd2cf0c716e"
hypothesis_outcome: confirmed
registries: [sync_skills, agents_parity]
deviations:
  - "SDD_SKILLS/ship.md marcou hypothesis_outcome confirmed com metade da previsao pendente (as features seguintes fecharem sem recusa). Pela regra 21 o arquivo nao e reescrito (AC8, git diff --exit-code 480181a6 com exit 0): o desfecho foi prematuro, e a parte pendente e verificada por SDD_EVAL."
  - "T4: a frase sobre quem escreve red e green foi reescrita numa linha so para casar com a assercao, no mesmo commit."
  - "Tamanho: os seis SKILL.md cairam 254 bytes no total, mas sdd-build (+318) e sdd-ship (+1203) cresceram com os itens novos; o README cresceu com as tres secoes."
  - "Registros fora do manifesto: docs/guia/referencia/skills/README.md."
  - "Build num agente so: sem subagente por tarefa, sem revisao em dois estagios e sem revisor novo na revisao final."
---

# SDD_SKILLS_REVISAO — entrega

## Hipótese

**Confirmada: as três partes da previsão foram medidas.**

1. Os testes novos passam sobre o texto revisado
   (`tests/test_sdd_skills.py`, 12 testes) e falharam sobre o texto anterior —
   cada vermelho está no `build_report.md`, visto na hora, tarefa por tarefa.
2. O teste de comandos recusa flag inventada
   (`test_o_detector_recusa_flag_inventada`) e aceita todas as flags que as
   skills citam (`test_comandos_citados_existem`).
3. A soma das skills no surface lock ficou em 532007 bytes, menor que 532261
   (−254).

`SC2`, bytes de cada `SKILL.md` (antes → depois): `sdd-build` 10317 → 10635,
`sdd-define` 7644 → 7229, `sdd-design` 6490 → 5608, `sdd-explore` 5873 → 5608,
`sdd-plan` 6381 → 6168, `sdd-ship` 6959 → 8162.

## Registros

`change_kinds` do define: `agent_or_skill`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `sync_skills` | Alterar agent, skill ou seus espelhos | `python scripts/sync_skills.py` (README de `.claude/agents/` fora), depois `--check`: OK |
| `agents_parity` | Alterar agent, skill ou seus espelhos | `tests/test_agents_parity.py`, `tests/test_agent_coverage.py`, `tests/test_sync_render.py`: verdes na bateria abaixo |

Critérios de `kind: command`, rodados agora:

- `AC7`: `python scripts/sync_skills.py --check` — exit 0.
- `AC8`: `git diff --exit-code 480181a6 -- docs/sdd/SDD_SKILLS/ship.md` — exit 0.

Fora do mapa, rodados porque a entrega os move:
`python scripts/gen_reference_docs.py` (7 páginas),
`python scripts/check_surface_lock.py --update` (−254 bytes em skills, no
commit), `python scripts/check_vnext_claims.py` (0 divergências) e
`python scripts/check_status_numbers.py --strict` (0 divergências).

Bateria de 13 arquivos (a mesma de `SDD_OPERATOR_DURAVEL`): 1611 testes
verdes, nenhuma falha. A suíte inteira em lotes não rodou.

## Desfecho anterior de SDD_SKILLS

`docs/sdd/SDD_SKILLS/ship.md` fechou `confirmed` com a parte "as features
seguintes fecham sem recusa" ainda por medir. Pela regra do `sdd-ship` revista
aqui, aquilo seria `draft` ou `abandoned`. O arquivo fica como está (regra 21).
Até agora, `SDD_OPERATOR`, `SDD_OPERATOR_DURAVEL` e esta feature fecham com
`sparkforge sdd check` sem recusa; `SDD_MIGRATION` e `SDD_EVAL` ainda não
existem, e é `SDD_EVAL` que consolida a verificação.

## Lições

- Skill com fluxo inteiro na `description` paga o custo em toda sessão; o
  gatilho basta para a seleção.
- Teste de texto que só confere o verbo deixa passar a flag errada — o
  `funcval compare` sem `--out` passou por ele.
- Mover bloco para o README economiza pouco se a revisão acrescenta regra nova
  na mesma entrega; o número do lock é o que decide.

## O que fica para depois

- `SDD_EVAL`: a parte pendente de `SDD_SKILLS` e um caso operator real.
