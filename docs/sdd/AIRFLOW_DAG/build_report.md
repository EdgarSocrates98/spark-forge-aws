---
sdd: 1
feature: AIRFLOW_DAG
phase: build_report
profile: dev
status: done
upstream:
  path: docs/sdd/AIRFLOW_DAG/plan.md
  sha256: "1b508a8c532493de22224776dca9fc34763b82cb54627ef5658e7cfd255e58b1"
tasks:
  - id: T1
    status: done
    red: {command: "python -m pytest tests/test_airflow_dag.py -q", exit: 2}
    green: {command: "python -m pytest tests/test_airflow_dag.py -q", exit: 0}
  - id: T2
    status: done
    red: {command: "python -m pytest tests/test_airflow_dag.py::test_cli_e_tool_devolvem_os_mesmos_facts -q", exit: 1}
    green: {command: "python -m pytest tests/test_airflow_dag.py::test_cli_e_tool_devolvem_os_mesmos_facts -q", exit: 0}
  - id: T3
    status: done
    red: {command: "python -m pytest tests/test_airflow_dag.py::test_fuse_liga_a_task_ao_job_e_nomeia_o_que_nao_liga -q", exit: 1}
    green: {command: "python -m pytest tests/test_airflow_dag.py tests/test_fixtures_golden_airflow.py -q", exit: 0}
  - id: T4
    status: done
    red: {command: "python -m pytest \"tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches\" -q", exit: 1}
    green: {command: "python -m pytest \"tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches\" -q", exit: 0}
claims:
  - text: "Um DAG .py vira af.dag e af.task com os argumentos literais que a regra julga, a marca do que nao e literal e schedule_literal; DAG em laco, operador dentro de def, dois DAGs no arquivo e dependencia dinamica saem af.unresolved com razao propria."
    evidence_ref: "tests/test_airflow_dag.py::test_dag_vira_fact_com_operador_e_argumentos_literais"
  - text: "As dependencias por >>, <<, set_downstream, set_upstream e chain viram af.dependency ou af.unresolved nomeado, e o af.task sabe se tem tarefa a jusante."
    evidence_ref: "tests/test_airflow_dag.py::test_dependencias_viram_fact_e_o_que_nao_le_sai_nomeado"
  - text: "fuse liga o GlueJobOperator ao aws_glue_job de mesmo nome e nomeia job_name nao literal, job ausente, job ambiguo e max_retries nao literal."
    evidence_ref: "tests/test_airflow_dag.py::test_fuse_liga_a_task_ao_job_e_nomeia_o_que_nao_liga"
  - text: "CLI e tool MCP devolvem os mesmos facts."
    evidence_ref: "tests/test_airflow_dag.py::test_cli_e_tool_devolvem_os_mesmos_facts"
  - text: "Cada regra SF-AIRFLOW dispara na sua fixture e fica calada nas oito negativas, inclusive timeout_sem_espera."
    evidence_ref: "tests/test_fixtures_golden_airflow.py::test_golden"
  - text: "A area SF-AIRFLOW passa pelo criterio de dominio."
    evidence_ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"
  - text: "O documento de knowledge novo entrou na superficie declarada: knowledge de 54 para 55 documentos."
    evidence_ref: "tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches"
  - text: "Na arvore final os goldens de fixture passam sem regeneracao: 3268 passed, 4 skipped, arvore limpa."
    evidence_ref: "python -m pytest tests/test_fixtures_golden*.py -q (2026-09-19, em 9223f037)"
change_id: null
---

# AIRFLOW_DAG — relatório do build

## Commits

| tarefa | commit | o quê |
|---|---|---|
| T1 | `9f7df85f` | extrator `af.*` por AST, que nunca importa o DAG |
| T2 | `7431cdad` | verbo `analyze airflow-dag` e tool `sparkforge_analyze_airflow_dag` |
| T3 | `b7e7788c` | área SF-AIRFLOW, quatro regras, derivação em `fuse`, rota AGENT-087, corpus e golden |
| T4 | `e3b09a53` | documento de conhecimento, guia de uso, registros |
| revisão | `9223f037` | os achados da revisão final |

## Desvios do plano

- **T1:** três erros de lint no código do plano (um `zip` sem `strict`, duas linhas longas)
  e a lista de ids do gate de lastro defasada: o gate acusou oito, e dois dos citados não
  estavam entre eles.
- **T2:** o gate de lastro acusou 22 alegações, não as sete que o plano listava. Duas delas
  são o tamanho em KB de `tools.py` e `_core.py`. E `docs/claims.lock.json` compara
  `expect.value` por tipo: valor de `kind: number` precisa ser `int`, não string.
- **T3:**
  - o `STATUS.md` publica uma linha que o plano não previa, o gold set de recuperação, que
    é derivado das regras e cresceu sozinho (29 para 33 perguntas);
  - o gate de lastro acusou onze alegações;
  - `CURRENT-HARNESS-GAP.md` tem duas alegações na mesma linha.
- **T4:** o comando de `sdd stamp` escrito no plano não existe na CLI (`--feature`,
  `--phase`); a sintaxe real é `sdd stamp --repo . <artefato>`.
- **Revisão final:** um achado crítico e quatro importantes voltaram ao build, corrigidos
  em `9223f037`:
  - SF-AIRFLOW-002 afirmava que o job Glue continua cobrando, o que a lacuna U3 proíbe. O
    título, a explicação e o AC4 do define foram reescritos, e a cascata do SDD
    recarimbada;
  - a regra passou a exigir que a task espere o job, com fixture negativa nova
    (`timeout_sem_espera`);
  - a `description` do coordenador passou a citar Airflow;
  - o `operations-guide` deixou de dizer que Airflow e Step Functions não têm coordenador;
  - as datas da feature passaram de 2026-09-20 para 2026-09-19 em quinze arquivos.

  Menores corrigidos: `chain` como atributo saía em silêncio, operador dentro de função
  ganhou razão própria, `schedule_literal` passou a existir sempre, o nome de uma permissão
  IAM sem fonte saiu da regra, o `knowledge/INDEX.md` ganhou a seção de orquestração, e as
  `reason` das rotas AGENT-086 e AGENT-087 deixaram de afirmar contagem de tentativas.

  **Armadilha nova, que vale para toda feature:** `description` de agente não pode conter
  `: `, porque quebra o frontmatter YAML. Isso derrubou 29 parametrizações de
  `tests/test_router_agents.py`.

- **Golden de outro domínio:** `fixtures/debate/retomada/expected/brief.json` mudou numa
  linha, a allowlist de extratores de evidência. Foi o mesmo efeito do STEP_FUNCTIONS, e
  desta vez a T3 não o regenerou; a rodada de goldens acusou, e a correção o regenerou pelo
  caminho do próprio teste.

## Revisão

- **Revisão final:** um revisor leu o diff inteiro contra o define e o design. Crítico:
  um. Importante: quatro. Menor: nove. Todos fechados.
- **Revisão por tarefa em dois estágios:** não rodou. O controlador conferiu cada relato e
  os gates que o plano nomeia.

## Medidas

| | antes (`b324aa3b`) | depois |
|---|---|---|
| regras | 161 | 165 |
| áreas | 29 | 30 |
| tools | 107 | 108 |
| extratores | 39 | 40 |
| kinds | 233 | 239 |
| rotas | 41 | 42 |
| fixtures | 528 em 57 domínios | 540 em 58 |
| fontes vigiadas | 262 | 265 |
