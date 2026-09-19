---
sdd: 1
feature: TOOLS_OK
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/TOOLS_OK/build_report.md
  sha256: "671249ba3be01bc8919aecf81653525d3d4fad38c8e3a83866265a9f42d0734e"
hypothesis_outcome: confirmed
registries: [claims_gate]
deviations:
  - "Commit 9f2caa40 saiu com a linha de co-autoria 'Claude Sonnet 5' em vez de 'Claude Opus 5 (1M context)', usada nos outros dois commits da feature (c418b834, 4ff3a2a5); não corrigido por reescrita de histórico."
  - "O arquivo .py novo (tests/test_tools_ok_rule.py) moveu VNX-640 (750 -> 751) e VNX-726 (89,7 -> 89,6) no gate de lastro; remediado por id em docs/claims.lock.json, com o número em negrito espelhado em docs/harness/CODEINTEL-GAP.md e no ADR-010."
  - "O import json do teste ficou sem uso entre T1 e T2 e reprovava o ruff; removido no commit c418b834 e devolvido junto com o teste da T2 no commit 4ff3a2a5, sem mudar o conteúdo dos testes de T1."
  - "T1 e T2 sem subagente revisor próprio: revisão feita pelo controlador sobre o diff e os gates, por serem tarefas pequenas e mecânicas."
  - "AC5 não foi reexecutado neste fechamento: a rodada paga já rodou uma vez (2026-09-19, OK do operador para o custo e a máquina livre), e repetir custa dinheiro sem mover a hipótese, já medida."
---

# TOOLS_OK — entrega

## Hipótese

Confirmada. A previsão do define tinha dois limiares explícitos, contra o
baseline `2026-09-16-haiku-4-5-lookup-busca` (`tools_ok` 3, 3, 1; `correct`
9, 9, 10): mediana de `tools_ok` subindo para 7 ou mais, e nenhuma repetição
com `correct` abaixo de 9 (o mínimo do baseline anterior).

A rodada `2026-09-19-haiku-4-5-tools-ok` (Haiku 4.5, `claude-haiku-4-5-20251001`,
fase0, 3 repetições) mediu:

| repetição | tools_ok | correct | bytes de `Read` |
|---|---|---|---|
| r1 | 9 | 10 | 214 828 |
| r2 | 9 | 10 | 234 982 |
| r3 | 8 | 9 | 292 235 |

Mediana de `tools_ok`: 9, acima do limiar de 7. Mínimo de `correct`: 9, não
abaixo de 9 — o critério de refutação do define ("mediana em 3 ou menos, ou
acerto abaixo de 9 em qualquer repetição") não se cumpriu. `false_certainty`
ficou em 1 em toda repetição, nos dois baselines: a regra não moveu esse
sintoma, e isto não afirma que moveria — fica fora do escopo do define.

Isto é um experimento: um modelo (Haiku 4.5), uma suíte (fase0, 13 perguntas),
uma regra injetada em `CLAUDE.md`/`AGENTS.md`. A regra 30 do `CLAUDE.md`
continua valendo — não há benchmark da camada agêntica, e nada aqui afirma
causa além deste experimento, nem generaliza para outro modelo ou suíte
(fora de escopo, define §`out_of_scope`).

## Comandos de aceite (`kind: command`)

| critério | comando | exit |
|---|---|---|
| AC4 | `python -m pytest tests/test_bootstrap_budget.py -q` | 0 (3 passed) |
| AC5 | `python scripts/run_agentic_eval.py --suite fase0 --model haiku --runs 3` | 0, rodada de 2026-09-19 (conjunto `fase0-2026-09-19T03-09-37Z`); **não reexecutado neste ship** — rodada paga, autorizada uma vez pelo operador; repetir gasta dinheiro sem mover a hipótese já medida |

`AC1`, `AC2` e `AC3` são `kind: test` (`tests/test_tools_ok_rule.py`), já
verificados no build (`build_report.md`, T1, `status: done`).

## Gates rodados

| registro | comando | resultado |
|---|---|---|
| `claims_gate` | `python scripts/check_vnext_claims.py` | 0 divergências |
| `claims_gate` | `python -m pytest tests/test_vnext_claims.py tests/test_docs_coverage.py tests/test_installed_provenance.py -q` | 174 passed, 5 skipped |
| números correntes | `python scripts/check_status_numbers.py --strict` | 0 divergências |
| lint | `python -m ruff check sparkforge scripts tests` | sem achados |

Nenhum `change_kinds` de `tool_or_verb` ou `agent_or_skill`: a feature não
acrescenta tool, skill nem verbo — só o bloco em `CLAUDE.md`/`AGENTS.md`, o
teste que o trava e o baseline novo. `surface_lock` e `generated_reference`
não se aplicam.

## Pendências

- **Limiar de sucesso de `tools_ok` além desta rodada (explore, "em aberto").**
  Uma rodada de 3 repetições não separa ruído de efeito num limiar fino; o
  define aceitou isso ao fixar mediana >= 7 como refutação, não como prova de
  causa.
- **Grader não confere citação de `fact_id`/`rule_id`.** Fora de escopo por
  decisão do define: o grader atual confere tools, não se a resposta cita o
  fact ou a regra que a sustenta. Mudança própria em `sparkforge/evals`.
- **Abordagens B e C do explore seguem registradas, não descartadas.** Se um
  limiar mais alto de `tools_ok` for exigido depois, ou se outro modelo não
  repetir o efeito, C (hook `PreToolUse` que recusa `Read` de artefato com
  verbo) é a feature seguinte, com esta rodada como baseline.

## Lições

- A regra curta no canal injetado (`CLAUDE.md`/`AGENTS.md`) moveu `tools_ok`
  de mediana 3 para 9 numa suíte onde o próprio `answer_protocol` já pedia o
  mesmo comportamento em texto e era ignorado — o canal importa mais que o
  conteúdo da instrução, ao menos neste experimento.
- O teste de T1 lendo a própria suíte (`suite.yaml`) em vez de uma lista
  escrita à mão no teste evitou que a trava envelhecesse silenciosamente; é o
  padrão a repetir quando um teste precisa cobrir um conjunto que já existe em
  outro arquivo.
- A rodada paga do AC5 deveria ter sido citada no plano como um passo que
  "roda uma vez, se autorizado" — ficou implícito nos `unknowns` do define
  (U1) e quase foi reexecutada por engano ao fechar o ship; registrar isso
  explicitamente no plano da próxima feature com `kind: command` caro evita a
  ambiguidade.
