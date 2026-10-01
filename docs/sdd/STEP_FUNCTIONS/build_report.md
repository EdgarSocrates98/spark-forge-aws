---
sdd: 1
feature: STEP_FUNCTIONS
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/STEP_FUNCTIONS/plan.md
  sha256: "75e3472d8cd3a39dccc8ac566b949e15148c1a999e10e60f52edd83d65c3fa37"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_stepfunctions.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_stepfunctions.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_stepfunctions.py::test_cli_e_tool_devolvem_os_mesmos_facts -q", exit: 1}
    green: {command: "python -m pytest tests/test_stepfunctions.py::test_cli_e_tool_devolvem_os_mesmos_facts -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_stepfunctions.py::test_fuse_liga_task_ao_job_e_nomeia_o_que_nao_liga -q", exit: 1}
    green: {command: "python -m pytest tests/test_stepfunctions.py tests/test_fixtures_golden_stepfunctions.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest \"tests/test_refresh_knowledge.py::TestWatchlistIsDerivedFromBothOrigins::test_the_committed_lock_matches_the_watchlist\" -q", exit: 1}
    green: {command: "python -m pytest \"tests/test_refresh_knowledge.py::TestWatchlistIsDerivedFromBothOrigins::test_the_committed_lock_matches_the_watchlist\" -q", exit: 0}
claims:
  - text: "Um .asl.json vira sfn.task por estado Task, dentro de Parallel e Map (ItemProcessor e Iterator), com padrao de integracao, JobName literal ou dinamico, retry efetivo do primeiro retrier que casa (3 quando omitido, com a marca), Catch e TimeoutSeconds; sfn.unresolved nomeado para o que nao le."
    evidence_ref: "tests/test_stepfunctions.py::test_task_glue_vira_fact_com_retry_efetivo"
  - text: "describe-state-machine e lido igual, e o type sai undeclared quando ausente ou nao reconhecido."
    evidence_ref: "tests/test_stepfunctions.py::test_describe_state_machine_le_definition_e_tipo"
  - text: "fuse liga o Task Glue .sync ao aws_glue_job de mesmo nome e nomeia o que nao liga (job_name_dynamic, job_name_absent, job_definition_absent, job_definition_ambiguous, glue_max_retries_not_literal)."
    evidence_ref: "tests/test_stepfunctions.py::test_fuse_liga_task_ao_job_e_nomeia_o_que_nao_liga"
  - text: "CLI e tool MCP devolvem os mesmos facts."
    evidence_ref: "tests/test_stepfunctions.py::test_cli_e_tool_devolvem_os_mesmos_facts"
  - text: "Cada regra SF-SFN dispara na sua fixture e fica calada em glue_limpo, definicao_ilegivel, retry_so_no_glue, retry_duas_camadas_sem_sync e glue_polling_com_get_job_run."
    evidence_ref: "tests/test_fixtures_golden_stepfunctions.py::test_golden"
  - text: "A area SF-SFN passa pelo criterio de dominio."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"
  - text: "Nenhuma tool ficou orfa."
    evidence_ref: "tests/test_agent_coverage.py::TestEveryToolIsReachable::test_no_tool_is_orphan"
  - text: "Antes das correcoes da revisao, os goldens de fixture passaram sem regeneracao: 3238 passed, 4 skipped (3217 de antes mais o corpus novo)."
    evidence_ref: "python -m pytest tests/test_fixtures_golden*.py -q (2026-09-19, em 6f82c00c)"
  - text: "Na arvore final, os goldens de fixture passaram sem regeneracao: 3242 passed, 4 skipped e 1 error de teardown em tests/test_fixtures_golden_workload.py, causado por sparkforge sdd stamp/check rodado durante a suite (a CLI grava em .sparkforge/ e a guarda do conftest derruba o teste corrente); o arquivo rodado sozinho da 34 passed."
    evidence_ref: "python -m pytest tests/test_fixtures_golden*.py -q (2026-09-19, em 8c5a764d) e python -m pytest tests/test_fixtures_golden_workload.py -q"
change_id: null
---

# STEP_FUNCTIONS — relatório do build

## Commits

Hashes depois do rebase sobre a `main` com o #89 (`58a6fb4e`):

| tarefa | commit | o quê |
|---|---|---|
| T1 | `f7200553` | extrator `sfn.*` |
| T2 | `f5cc613f` | verbo `analyze step-functions` e tool `sparkforge_analyze_step_functions` |
| T3 | `a1146e60` | área SF-SFN, quatro regras, derivação em `fuse`, rota AGENT-086, corpus e golden |
| T4 | `6f82c00c` | documento de conhecimento, guia de uso, registros finais |
| revisão | `8c5a764d` | os achados da revisão final |

## Desvios do plano

- **T1:** o teste do plano esperava `state_count: 8`; a fixture `ASL_COM_PARALLEL_E_MAP`
  tem 7 estados, e o teste foi corrigido para 7. O `plan.md` ficou com o 8. O gate de
  lastro moveu sete alegações, entre elas VNX-675 e VNX-726, que o plano não previa.
- **T2:** o gerador de referência regravou cinco páginas, e não quatro. O gate moveu 22
  alegações em vez das de `len(TOOLS)` que o plano previa: bytes do corpus, `detail_level`
  e `READ_ONLY` também. `detail_level` publica 39 em CLAUDE e AGENTS (contagem por
  assinatura) e 41 em CODEINTEL-GAP (outra prova). Cada um publica o que a própria prova
  mede.
- **T3:**
  - o red registrado é o teste do `fuse` rodado sozinho. A coleta do lote conjunto
    falhou com `ImportError`, que interrompe a sessão;
  - sete alegações moveram, três delas por efeitos que o plano não listava: `routing.yaml`
    cresceu (VNX-430), o lock de fontes cresceu (VNX-767) e entrou um domínio de fixture
    novo (VNX-469).
- **T4:** os links relativos do guia de uso usavam `../../` e passaram a `../../../`. A
  VNX-767 moveu de novo (258 para 259).
- **Revisão final:** voltou ao build com sete achados importantes e doze menores, todos
  corrigidos em `8c5a764d`:
  - SF-SFN-004 passou a exigir `.sync`;
  - `MaxAttempts` ilegível sai nomeado;
  - JSON profundo e arquivo grande não derrubam o extrator;
  - SF-SFN-001 caiu para P2, respeita o polling por `getJobRun` e herda o `Next` do
    contêiner;
  - o texto de SF-SFN-002 e SF-SFN-003 ficou restrito às frases citadas;
  - a recusa de `EXPRESS` com `.sync` pela API é lacuna 4 do documento de conhecimento.

  Duas fixtures entraram (`retry_duas_camadas_sem_sync` e `glue_polling_com_get_job_run`).
  O golden `fixtures/debate/retomada/expected/brief.json` mudou numa linha, porque a
  allowlist de extratores de debate ganhou `step-functions`. Ele não é golden de achado.

## Revisão

- **Revisão final:** um revisor leu o diff inteiro contra o define e o design. Crítico:
  nenhum. Importante: sete. Menor: doze. Todos estão fechados.
- **Revisão por tarefa em dois estágios:** não rodou. O controlador conferiu cada relato e
  os gates que o plano nomeia.

## Medidas

| | antes (`0d7050c3`) | depois |
|---|---|---|
| regras | 157 | 161 |
| tools | 106 | 107 |
| extratores | 38 | 39 |
| rotas | 40 | 41 |
| fontes no lock | 254 | 262 |
