---
sdd: 1
feature: SDD_EVAL
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/SDD_EVAL/build_report.md
  sha256: "3afd2a5fba9667f2eeac383c82cd8da84a8d001ae2bedf1fd60e1dc9d7aee538"
hypothesis_outcome: confirmed
registries: [fixture_corpus_gates]
deviations:
  - "Modulo golden tests/test_fixtures_golden_sdd.py fora do manifesto, exigido por test_fixtures_kind_coverage para o dominio novo."
  - "Caso operador com profile operator sob docs/sdd/ (como feature_limpa em tests/test_sdd.py), nao sob .sparkforge/sdd/."
  - "Fixtures geradas por script de scratchpad com o stamp real; nao entrou em scripts/regen_fixtures.py."
  - "--runs entrou no runner como sinonimo de --repeat, para o comando de AC5 rodar como o define o escreve."
  - "T4: o teste do plano passaria de primeira; ganhou a conferencia do baseline gravado, que deu o vermelho. T4 tocou tambem tests/test_sdd_eval_suite.py e evals/agentic/sdd/README.md."
  - "O rerun do comando de AC5 no ship entrou como r2.json do mesmo baseline (commit 6f569393): o plano pedia uma execucao, o baseline tem duas."
  - "Registros fora do manifesto: docs/claims.lock.json, docs/harness/CODEINTEL-GAP.md, docs/harness/CURRENT-HARNESS-GAP.md, docs/harness/RUNTIME-VS-EVALUATION.md e docs/superpowers/STATUS.md."
  - "python scripts/verify_wheel.py nao concluiu: morto pelo timeout de 15 minutos com os modulos golden em 37% e nenhuma falha no log."
  - "Build num agente so: sem subagente por tarefa, sem revisao em dois estagios e sem revisor novo na revisao final."
---

# SDD_EVAL — entrega

## Hipótese

**Confirmada no que a previsão pede; a afirmação não vale em 100% dos casos.**

A previsão tinha duas partes, e as duas foram medidas:

1. **O baseline registra k/N de acerto e de uso das tools exigidas.**
   `evals/agentic/sdd/baselines/2026-09-17-haiku-4-5/` tem `r1.json` e
   `r2.json` (N=2), pontuados contra o sha256 da suite
   (`test_suite_carrega_e_exige_as_tools`). `python -m sparkforge.evals
   compare` dá acerto 2/2 nas seis perguntas e tools 2/2 em cinco delas.
2. **A comparação com superpowers e AgentSpec sai recusada por nome.**
   `evals/agentic/sdd/README.md`, seção *O que ela NÃO mede*, com o que a
   destravaria (regra 30).

A afirmação ("usa `sdd_check`/`sdd_status`, e não lê o YAML no olho") foi
observada em 11 de 12 respostas. Em `r2`, `sdd-03` respondeu certo **lendo o
YAML**, depois de tentar `python -m sparkforge.cli`. A previsão não fixou
limiar, então o desfecho não esconde esse caso: ele está aqui e no README da
suite. Nenhuma chamada foi pelo MCP; todas as que contaram foram pela CLI.

`SC1` (acerto e uso das tools no baseline Haiku): acerto 12/12, tools 11/12,
fonte nos dois scorecards.

`U1` (claude autenticado) foi destravado nesta máquina: as duas execuções
saíram com exit 0.

## Registros

`change_kinds` do define: `fixture_corpus`.

| registro | seção de `docs/gates-por-mudanca.md` | rodado |
|---|---|---|
| `fixture_corpus_gates` | Acrescentar um CORPUS de fixture novo (`fixtures/<dominio>/`) | `python -m pytest tests/test_fixtures_kind_coverage.py tests/test_verify_wheel.py -q`: verdes (com `tests/test_fixtures_golden_sdd.py` reivindicando `fixtures/sdd/`) |

Critérios de `kind: command`, rodados agora:

- `AC5`: `python scripts/run_agentic_eval.py --suite sdd --model haiku --runs 1`
  — exit 0 (execução `sdd-2026-09-17T08-14-52Z-r1`, guardada como `r2.json`).

Fora do mapa, rodados porque a entrega os move:
`python scripts/sync_skills.py --check` (OK),
`python scripts/gen_reference_docs.py` (0 páginas),
`python scripts/check_surface_lock.py --update` (sem mudança),
`python scripts/check_vnext_claims.py` (0 divergências depois de VNX-640,
VNX-357, VNX-358 e VNX-469), `python scripts/check_status_numbers.py --strict`
(0 depois de *Fixtures golden*) e `python scripts/check_evals.py` (10
respostas reproduzem). `python scripts/verify_wheel.py` não concluiu (ver
desvios).

Bateria de 19 arquivos: 1453 verdes. A suíte inteira em lotes não rodou.

## A parte pendente de SDD_SKILLS

`SDD_SKILLS/ship.md` fechou `confirmed` com "as features seguintes fecham sem
recusa" ainda por medir. Medido agora: `SDD_OPERATOR`, `SDD_OPERATOR_DURAVEL`,
`SDD_SKILLS_REVISAO`, `SDD_MIGRATION` e esta feature fecham com
`sparkforge sdd check` em zero recusa e zero lacuna. O caso operator real
continua sem medida: as fixtures são sintéticas.

## Lições

- Pergunta sobre spec pode ser respondida lendo o YAML; só a conferência de
  tool do grader separa os dois caminhos, e com N=1 o desvio de `sdd-03` não
  teria aparecido.
- O define citou uma flag que o runner não tinha (`--runs`); comando de
  `kind: command` deve ser conferido contra o parser já no define.
- O gate de wheel não cabe em 15 minutos nesta máquina; rode-o sem limite ou
  deixe-o para o CI e diga isso.

## O que fica para depois

- `--repeat 3` na suite sdd, e um braço `--surface suite`.
- Um caso operator real, com `.sparkforge/sdd/` e sandbox.
- A comparação com outros processos, quando existir o caso bem posto do
  README da suite.
