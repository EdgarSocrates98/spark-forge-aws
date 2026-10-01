---
sdd: 1
feature: STEP_FUNCTIONS
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/STEP_FUNCTIONS/explore.md
  sha256: "adc835e18b46752535bedbe1864d14298eac8d10dbb70b950bba83ab6b491507"
hypothesis:
  claim: "A definicao ASL de uma state machine basta para julgar como ela chama o Glue (padrao de integracao, retry efetivo com os defaults publicados, tipo de workflow), e cruzada com a definicao Terraform do job pelo JobName literal ela mostra as duas camadas de retry sobre o mesmo job; o dominio entra pelas tres portas do criterio sem mudar nenhum achado existente."
  prediction: "Sobre fixtures sinteticas, cada uma das quatro regras novas dispara na fixture que reproduz o seu caso e fica calada na fixture limpa (Glue .sync com Retry explicito em erro nomeado, sem MaxRetries no job); JobName dinamico sai como sfn.unresolved nomeado, nunca como link; tests/test_criterio_de_dominio.py passa com a area nova; e os goldens de fixture existentes passam sem regeneracao, com excecao dos assessment que carregam a contagem do catalogo. Se alguma regra ficar calada na sua fixture, disparar na limpa, ou se algum golden de achado existente mudar, a afirmacao esta errada."
  experiment: "Rodar sparkforge analyze step-functions e judge sobre as fixtures novas, fuse sobre a fixture pareada ASL + Terraform, os testes do criterio de dominio, e python -m pytest tests/test_fixtures_golden*.py -q."
acceptance:
  - id: AC1
    statement: "Um .asl.json vira um fact sfn.task por estado Task, inclusive dentro de Parallel e Map, com servico, API, padrao de integracao (request_response, sync, callback), JobName literal ou a marca de dinamico, os retriers com MaxAttempts efetivo (3 quando omitido, e a marca de omitido), a presenca de Catch e o TimeoutSeconds declarado ou ausente; mais um sfn.analyzed sempre, e sfn.unresolved nomeado para o que nao le."
    verified_by: {kind: test, ref: "tests/test_stepfunctions.py::test_task_glue_vira_fact_com_retry_efetivo"}
  - id: AC2
    statement: "A saida de describe-state-machine (definition como string JSON dentro do objeto) e lida igual ao .asl.json, e o type (STANDARD ou EXPRESS) vira atributo da state machine; sem type, o atributo sai undeclared, nunca STANDARD por suposicao."
    verified_by: {kind: test, ref: "tests/test_stepfunctions.py::test_describe_state_machine_le_definition_e_tipo"}
  - id: AC3
    statement: "SF-SFN-001 dispara quando um Task glue:startJobRun sem .sync tem Next: o proximo estado roda com o job ainda em execucao."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_stepfunctions.py::test_golden"}
  - id: AC4
    statement: "SF-SFN-002 dispara quando um Task glue:startJobRun.sync tem retrier em States.ALL ou States.TaskFailed com MaxAttempts efetivo maior que zero: cada tentativa roda o job batch inteiro, e com MaxAttempts omitido sao tres a mais."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_stepfunctions.py::test_golden"}
  - id: AC5
    statement: "SF-SFN-003 dispara quando um Task com .sync esta numa state machine de type EXPRESS, que so suporta Request Response; com type undeclared, a regra nao dispara."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_stepfunctions.py::test_golden"}
  - id: AC6
    statement: "Com o ASL e o Terraform do job no mesmo case, fuse deriva um fact que liga o Task Glue ao aws_glue_job de mesmo nome, e SF-SFN-004 dispara quando o Task tem retrier efetivo e o job tem max_retries maior que zero, dizendo que as duas camadas de retry existem e que a composicao delas nao e documentada; JobName dinamico ou job ausente saem nomeados em sfn.unresolved."
    verified_by: {kind: test, ref: "tests/test_stepfunctions.py::test_fuse_liga_task_ao_job_e_nomeia_o_que_nao_liga"}
  - id: AC7
    statement: "sparkforge analyze step-functions --path le arquivo ou diretorio e devolve os facts, e a tool MCP sparkforge_analyze_step_functions faz o mesmo."
    verified_by: {kind: test, ref: "tests/test_stepfunctions.py::test_cli_e_tool_devolvem_os_mesmos_facts"}
  - id: AC8
    statement: "A area SF-SFN passa pelo criterio de dominio: regra que julga, coordenador que a declara e rota por findings_area."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"}
  - id: AC9
    statement: "knowledge/stepfunctions/glue-integration.md registra as frases citadas das seis paginas oficiais lidas em 2026-09-19, e a lacuna da composicao dos retries."
    verified_by: {kind: command, ref: "python scripts/verify_offline_bundle.py"}
  - id: AC10
    statement: "Os registros que extrator, regra, area, tool e documento de knowledge movem estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Regras SF-SFN que disparam na propria fixture e ficam caladas na limpa"
    source: "goldens de fixtures/stepfunctions"
  - id: SC2
    metric: "Goldens de achado existentes que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
  - id: SC3
    metric: "Regras, tools, coordenadores e rotas antes e depois"
    source: "load_catalog(), TOOLS, agents/*.md e routing.yaml"
out_of_scope:
  - "Historico de execucao (get-execution-history) e coletor com credencial AWS: incremento seguinte."
  - "Definicao dentro de aws_sfn_state_machine do Terraform (templatefile, jsonencode): so o ASL em arquivo ou a saida de describe-state-machine."
  - "Servicos alem do Glue como alvo de regra (Lambda, Batch, EMR): o extrator os registra, as regras julgam so o Glue."
  - "Timeout do Task contra o Timeout do job Glue: a documentacao nao diz o que acontece com o JobRun quando o Task expira por States.Timeout (a lista de abort nao inclui timeout); fica como lacuna nomeada no documento de knowledge."
  - "JSONata alem de reconhecer expressao {% %} como valor dinamico."
unknowns:
  - id: U1
    blocks: [AC6]
    unlock: "Como o retry do Step Functions compoe com o MaxRetries do Glue (o .sync acompanha o JobRunId devolvido; o retry do Glue e outro JobRun) nao esta documentado. A regra afirma so que as duas camadas existem; destrava afirmar a contagem de tentativas um historico de execucao real com falha, ou documentacao oficial."
  - id: U2
    blocks: [AC1, AC2]
    unlock: "Nenhuma definicao ASL real foi observada nesta sessao; as fixtures sao sinteticas a partir dos exemplos oficiais. Destrava: um .asl.json ou describe-state-machine real do operador, lido na conversa, nunca commitado."
change_kinds: [extractor, rule, rule_runtime_scope, rule_area, fixture_corpus, knowledge_doc, tool_or_verb, agent_or_skill, routing, status_numbers, claims]
---

# STEP_FUNCTIONS — requisitos

## Problema

O SparkForge lê o job Glue, o plano e a execução, e não lê quem dispara o job. Uma
state machine que chama `glue:startJobRun` sem `.sync` segue adiante com o job rodando;
um retrier sem `MaxAttempts` reexecuta o job inteiro três vezes; e o retry do Step
Functions soma ao `MaxRetries` do job sem que nenhuma das duas documentações diga como.
Nada disso aparece no código PySpark nem no event log.

## Fontes citadas

Em `docs/sdd/STEP_FUNCTIONS/explore.md`, com as frases:
- `connect-glue`, `connect-to-resource`, `concepts-error-handling` e `state-task`, do guia
  do Step Functions;
- `aws-glue-api-jobs-job` e `aws-glue-api-jobs-runs`, da API do Glue.

## Critérios

- AC1, AC2 e AC7 são o extrator e a porta pública.
- AC3 a AC6 são as quatro regras.
- AC8 é o critério de domínio.
- AC9 e AC10 são os registros.
