---
sdd: 1
feature: AIRFLOW_DAG
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/AIRFLOW_DAG/explore.md
  sha256: "ff72cb42c4a1088421f9ec859d2850b2b4a4fb4c5d40ef84ad3cf8b94d9cfc88"
hypothesis:
  claim: "O arquivo .py de um DAG basta, lido por AST, para julgar como ele dispara um job Glue: se espera o job, se o mata junto com a task, se segura o worker enquanto espera, e, cruzado com a definicao Terraform do job pelo job_name literal, se ha duas camadas de retry sobre o mesmo job."
  prediction: "Sobre fixtures sinteticas, cada uma das quatro regras novas dispara na fixture que a reproduz e fica calada nas negativas (DAG com wait_for_completion default e sem retry, e DAG que so o Glue retenta); argumento nao literal (variavel, f-string, chamada) e DAG gerado em laco saem af.unresolved nomeado, nunca como fact afirmado; o criterio de dominio passa com a area SF-AIRFLOW; e nenhum golden de achado existente muda. Se alguma regra ficar calada na sua fixture, disparar numa negativa, ou se algum golden de achado existente mudar, a afirmacao esta errada."
  experiment: "Rodar sparkforge analyze airflow-dag e judge sobre as fixtures novas, fuse sobre a fixture pareada DAG + Terraform, tests/test_criterio_de_dominio.py, e python -m pytest tests/test_fixtures_golden*.py -q sem regenerar."
acceptance:
  - id: AC1
    statement: "Um DAG .py vira af.dag (dag_id, schedule quando literal, default_args com retries e execution_timeout quando literais) e um af.task por operador instanciado, com classe, task_id, os argumentos literais que a regra julga (job_name, wait_for_completion, deferrable, stop_job_run_on_kill, retries, execution_timeout) e a marca do que nao e literal; mais af.analyzed sempre."
    verified_by: {kind: test, ref: "tests/test_airflow_dag.py::test_dag_vira_fact_com_operador_e_argumentos_literais"}
  - id: AC2
    statement: "As dependencias declaradas por >> , << , set_downstream e set_upstream viram af.dependency, e o af.task sabe se tem tarefa a jusante; dependencia montada em laco ou por lista dinamica sai af.unresolved nomeado."
    verified_by: {kind: test, ref: "tests/test_airflow_dag.py::test_dependencias_viram_fact_e_o_que_nao_le_sai_nomeado"}
  - id: AC3
    statement: "SF-AIRFLOW-001 dispara quando um GlueJobOperator declara wait_for_completion=False e tem tarefa a jusante: a proxima task roda com o job ainda em execucao."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_airflow.py::test_golden"}
  - id: AC4
    statement: "SF-AIRFLOW-002 dispara quando um GlueJobOperator tem execution_timeout declarado (na task ou em default_args) e stop_job_run_on_kill ausente ou False: o Airflow mata a task e o job Glue continua rodando e cobrando."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_airflow.py::test_golden"}
  - id: AC5
    statement: "SF-AIRFLOW-003 dispara quando um GlueJobOperator espera o job (wait_for_completion ausente ou True) com deferrable ausente ou False: a espera segura um slot de worker pelo tempo do job."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_airflow.py::test_golden"}
  - id: AC6
    statement: "Com o DAG e o Terraform do job no mesmo case, fuse deriva o link do GlueJobOperator com o aws_glue_job de mesmo nome, e SF-AIRFLOW-004 dispara quando retries efetivo do Airflow e max_retries do job sao ambos maiores que zero; job_name nao literal, job ausente ou ambiguo saem nomeados em af.unresolved."
    verified_by: {kind: test, ref: "tests/test_airflow_dag.py::test_fuse_liga_a_task_ao_job_e_nomeia_o_que_nao_liga"}
  - id: AC7
    statement: "sparkforge analyze airflow-dag --path le arquivo ou diretorio e devolve os facts, e a tool MCP sparkforge_analyze_airflow_dag faz o mesmo."
    verified_by: {kind: test, ref: "tests/test_airflow_dag.py::test_cli_e_tool_devolvem_os_mesmos_facts"}
  - id: AC8
    statement: "A area SF-AIRFLOW passa pelo criterio de dominio: regra que julga, coordenador que a declara e rota por findings_area."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"}
  - id: AC9
    statement: "knowledge/airflow/glue-operator.md registra as frases citadas das paginas oficiais lidas em 2026-09-20 e as lacunas nomeadas, e o bundle offline continua integro."
    verified_by: {kind: command, ref: "python scripts/verify_offline_bundle.py"}
  - id: AC10
    statement: "Os registros que extrator, regra, area, tool e documento de knowledge movem estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Regras SF-AIRFLOW que disparam na propria fixture e ficam caladas nas negativas"
    source: "goldens de fixtures/airflow"
  - id: SC2
    metric: "Goldens de achado existentes que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
  - id: SC3
    metric: "Regras, tools, extratores e rotas antes e depois"
    source: "load_catalog(), TOOLS, sparkforge/facts/*.py e routing.yaml"
out_of_scope:
  - "Dependencia entre DAGs (ExternalTaskSensor, TriggerDagRunOperator): abordagem C do explore."
  - "DAG gerado dinamicamente (laco, factory, import): sai af.unresolved, nao se tenta executar o arquivo."
  - "Metadados do Airflow em execucao (task instances, duracao, retries que aconteceram): exige acesso ao banco ou a API."
  - "TaskFlow API (@task, @dag) alem de reconhecer o decorador e nomear o que nao le como unresolved."
  - "Operadores de EMR, Athena e afins: o extrator registra o operador, as regras julgam so GlueJobOperator."
unknowns:
  - id: U1
    blocks: [AC6]
    unlock: "Como o retry do Airflow compoe com o MaxRetries do Glue nao esta documentado, pelo mesmo motivo do Step Functions (U1 daquela feature): o operador chama StartJobRun de novo, e o Glue retenta por conta propria. A regra afirma so que as duas camadas existem."
  - id: U2
    blocks: [AC1, AC2]
    unlock: "Nenhum DAG real foi observado; as fixtures sao sinteticas a partir dos exemplos da documentacao do provider. Destrava um DAG real do operador, lido na conversa, nunca commitado."
  - id: U3
    blocks: [AC4]
    unlock: "A documentacao do provider diz o que stop_job_run_on_kill faz quando True, e nao descreve o que acontece com o JobRun quando a task e morta com ele False. A regra afirma o que a documentacao sustenta (o operador nao para o job) e nomeia o resto como lacuna."
change_kinds: [extractor, rule, rule_runtime_scope, rule_area, fixture_corpus, knowledge_doc, tool_or_verb, agent_or_skill, routing, status_numbers, claims]
---

# AIRFLOW_DAG — requisitos

## Problema

O Airflow dispara boa parte dos jobs Glue, e o SparkForge não lê o DAG. Três defaults do
`GlueJobOperator` decidem o que acontece com o job, e nenhum aparece no código PySpark nem
no event log: `wait_for_completion`, `deferrable` e `stop_job_run_on_kill`. O `retries` do
Airflow ainda soma com o `MaxRetries` do job.

## Fontes citadas

As de `docs/sdd/AIRFLOW_DAG/explore.md`, seção *Fontes lidas*, mais as do lado do Glue já
citadas em `docs/sdd/STEP_FUNCTIONS/explore.md`.

## Critérios

- AC1, AC2 e AC7 são o extrator e a porta pública.
- AC3 a AC6 são as quatro regras.
- AC8 é o critério de domínio.
- AC9 e AC10 são os registros.
