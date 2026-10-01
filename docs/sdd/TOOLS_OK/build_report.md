---
sdd: 1
feature: TOOLS_OK
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/TOOLS_OK/plan.md
  sha256: "de0ed77246b9a2185a713130df8fe2841c4f9e6a6aec4d5b27f11dcd49e07554"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_tools_ok_rule.py::test_claude_md_abre_com_a_regra_de_prova -q", exit: 1}
    green: {command: "python -m pytest tests/test_tools_ok_rule.py -k \"not baseline\" -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_tools_ok_rule.py::test_baseline_tools_ok_gravado -q", exit: 1}
    green: {command: "python -m pytest tests/test_tools_ok_rule.py::test_baseline_tools_ok_gravado -q", exit: 0}
claims:
  - text: "O CLAUDE.md abre, antes de 'Ao trabalhar em código PySpark', com o bloco '## Antes de responder sobre artefato, rode o verbo', citando fact_id, rule_id e ao menos uma tool sparkforge_*."
    evidence_ref: "tests/test_tools_ok_rule.py::test_claude_md_abre_com_a_regra_de_prova"
  - text: "O AGENTS.md carrega o bloco equivalente em inglês, antes de 'This repository contains', com o mesmo conjunto de tools que o bloco do CLAUDE.md."
    evidence_ref: "tests/test_tools_ok_rule.py::test_agents_md_carrega_a_mesma_regra"
  - text: "Toda tool sparkforge_* citada no bloco existe em sparkforge.adapters.tools.TOOLS, e o conjunto citado cobre required_tools de toda pergunta de evals/agentic/fase0/suite.yaml."
    evidence_ref: "tests/test_tools_ok_rule.py::test_verbos_da_regra_existem_e_cobrem_a_suite"
  - text: "CLAUDE.md (24 440 bytes) e AGENTS.md (23 043 bytes) continuam dentro do teto de 26 000 bytes de tests/test_bootstrap_budget.py depois do bloco novo."
    evidence_ref: "tests/test_bootstrap_budget.py"
  - text: "Uma rodada Haiku 4.5 da suíte fase0 (3 repetições) com o bloco novo está gravada em evals/agentic/fase0/baselines/2026-09-19-haiku-4-5-tools-ok/r1..r3.json, cada uma com tools_ok, correct e questions."
    evidence_ref: "tests/test_tools_ok_rule.py::test_baseline_tools_ok_gravado"
  - text: "Mediana de tools_ok subiu de 3 (baseline 2026-09-16: 3, 3, 1) para 9 (baseline novo: 9, 9, 8); nenhuma repetição do baseline novo ficou abaixo de 8. Acerto por repetição: 10, 10, 9, contra 9, 9, 10 antes. Bytes de Read por repetição: 214 828, 234 982, 292 235, contra 380 039 na primeira repetição do baseline anterior."
    evidence_ref: "evals/agentic/fase0/baselines/2026-09-19-haiku-4-5-tools-ok/r1..r3.json e evals/agentic/fase0/baselines/2026-09-16-haiku-4-5-lookup-busca/r1..r3.json"
  - text: "false_certainty ficou em 1 em cada repetição do baseline novo, igual ao baseline anterior: a regra não moveu esse sintoma."
    evidence_ref: "evals/agentic/fase0/baselines/2026-09-19-haiku-4-5-tools-ok/r1..r3.json (totals.false_certainty) e evals/agentic/fase0/baselines/2026-09-16-haiku-4-5-lookup-busca/r1..r3.json (totals.false_certainty)"
change_id: null
---

# TOOLS_OK — relatório do build

## Desvios do plano

- **T1, gate de lastro.** O arquivo `.py` novo (`tests/test_tools_ok_rule.py`)
  moveu duas alegações do gate de lastro: VNX-640 (750 -> 751) e VNX-726 (89,7 ->
  89,6). Remedidas por id em `docs/claims.lock.json`, com o número em negrito
  espelhado em `docs/harness/CODEINTEL-GAP.md` e no ADR-010, sem mudar o texto
  ao redor.
- **T1, import sem uso entre commits.** O `import json` do teste, previsto pelo
  plano para a T2, ficou sem uso até a T2 existir e reprovava o `ruff`. Removido
  no commit `c418b834` (`style(tests): drop the json import until the baseline
  test needs it`) e devolvido junto com `test_baseline_tools_ok_gravado` no
  commit `4ff3a2a5`. T1 e T2, no plano, previam um teste só desde o início;
  ficaram três commits para chegar ao mesmo arquivo, sem mudar o conteúdo dos
  testes de T1.
- **T1, linha de atribuição divergente.** O commit `9f2caa40` saiu com
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` em vez da atribuição
  usada no resto da feature (`Claude Opus 5 (1M context)`, presente em
  `c418b834` e `4ff3a2a5`). Não foi corrigido por reescrita de histórico
  (regra do repositório: nunca `--amend` fora de pedido explícito); registrado
  aqui como desvio.
- **T1 e T2, sem subagente revisor próprio.** As duas tarefas foram pequenas e
  mecânicas (bloco de texto travado por teste; cópia de artefato de eval para
  `evals/agentic/fase0/baselines/`); a revisão foi feita pelo controlador sobre
  o diff e os gates vizinhos, sem despachar um subagente de spec e outro de
  qualidade.
- **T2, custo pago e não repetido nesta sessão de fechamento.** A rodada
  `python scripts/run_agentic_eval.py --suite fase0 --model haiku --runs 3` já
  rodou uma vez, com o OK do operador para o custo (U1 do define) e a máquina
  livre (U2). Fechar a feature (este relatório e o ship) não reexecuta a
  rodada — repetir custa dinheiro sem mover a hipótese, que já está medida.

## Revisão

Por tarefa, pelo controlador sobre o diff e os gates (sem subagente revisor
próprio nas duas, conforme o desvio acima):

- **T1.** O bloco entra sem número, entre o título e "Ao trabalhar em código
  PySpark" no `CLAUDE.md`, e entre o título e "This repository contains" no
  `AGENTS.md`, como o design (D1) pedia. A tabela do design (D2) foi levada
  ao texto sem cortes: sete linhas de tipo de pergunta para tool. O teste de
  T1 confere id-a-id (D3): tools citadas dentro de `TOOLS`, e o conjunto citado
  cobre `required_tools` de cada pergunta da suíte, lendo a própria suíte em
  vez de uma lista escrita à mão no teste. Gates vizinhos:
  `python -m pytest tests/test_bootstrap_budget.py tests/test_docs_coverage.py -q`
  (AC4) e `python scripts/check_vnext_claims.py`,
  `python scripts/check_status_numbers.py --strict`,
  `python -m ruff check sparkforge scripts tests` — todos verdes depois da
  remediação por id em `docs/claims.lock.json`.
- **T2.** O teste (D4) confere que existe um diretório
  `evals/agentic/fase0/baselines/*-tools-ok` com três ou mais `r*.json`, cada
  um com `tools_ok`, `correct` e `questions` em `totals` — sem comparar valor
  contra limiar, porque o limiar é do define (SC1/SC2), não do teste. Os três
  `r*.json` copiados batem, campo a campo, com os números do commit
  `4ff3a2a5` e com os lidos agora: `tools_ok` 9, 9, 8; `correct` 10, 10, 9;
  bytes de `Read` por repetição 214 828, 234 982, 292 235 (somados por
  `tool_result_bytes_by_tool.Read` de cada pergunta, já que o schema do
  scorecard não traz esse total pronto em `totals`).

## Medida (AC5, SC1–SC3)

| repetição | tools_ok (antes 3, 3, 1) | correct (antes 9, 9, 10) | bytes de Read (antes 380 039 na r1) |
|---|---|---|---|
| r1 | 9 | 10 | 214 828 |
| r2 | 9 | 10 | 234 982 |
| r3 | 8 | 9 | 292 235 |

Mediana de `tools_ok`: 9 (antes: 3). Nenhuma repetição ficou abaixo de 8 —
perto do piso "nenhuma abaixo de 9" da previsão do define, com a terceira
repetição em 8. `false_certainty` ficou em 1 em toda repetição, nos dois
baselines: o bloco não moveu esse sintoma, e o relatório não afirma que
moveria (fora do escopo do define). A comparação usa a suíte fase0 e o
`answer_protocol` constantes, como o define exigiu; é um experimento, um
modelo (Haiku 4.5, `claude-haiku-4-5-20251001`) e uma suíte — a regra 30 do
`CLAUDE.md` (sem benchmark da camada agêntica, sem afirmação de ganho fora do
medido) continua valendo, e nada aqui afirma causa além deste experimento.
