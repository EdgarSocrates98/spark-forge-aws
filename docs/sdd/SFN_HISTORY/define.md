---
sdd: 1
feature: SFN_HISTORY
phase: define
profile: dev
status: ready
upstream:
  path: docs/sdd/SFN_HISTORY/explore.md
  sha256: "0f75d8a242b3cd05deb1d2f64f141d8c3248310fd4ef664dc9d7c54857ff4076"
hypothesis:
  claim: "O JSON salvo de get-execution-history basta para medir o que a definicao so declara: quantas vezes um Task foi agendado, quantos JobRun do Glue cada tentativa produziu, quanto durou cada uma e como a execucao terminou; e confrontado com o sfn.task do ASL do mesmo state machine, ele mostra divergencia entre o retry declarado e o observado."
  prediction: "Sobre fixtures sinteticas construidas a partir da forma de evento publicada, o extrator conta as tentativas por estado e le o JobRunId de cada TaskSubmitted; a regra de divergencia dispara quando as tentativas observadas nao cabem no retry declarado, e fica calada quando cabem; historico sem includeExecutionData sai sfn.unresolved nomeado, nunca com JobRun inventado; e nenhum golden de achado existente muda. Se a contagem de tentativas sair errada numa fixture, se a regra disparar no caso que cabe, ou se algum golden de achado existente mudar, a afirmacao esta errada."
  experiment: "Rodar sparkforge analyze sfn-history e judge sobre as fixtures novas, fuse sobre a fixture pareada ASL + historico, e python -m pytest tests/test_fixtures_golden*.py -q sem regenerar."
acceptance:
  - id: AC1
    statement: "Um JSON de get-execution-history vira sfn.execution (arn quando presente, status pelo evento terminal, duracao entre o primeiro e o ultimo evento, contagem de eventos) e um sfn.attempt por tentativa de Task (nome do estado, ordem da tentativa, resource, resourceType, resultado, duracao, error e cause quando houver); mais sfn.analyzed sempre."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_historico_vira_execucao_e_tentativas"}
  - id: AC2
    statement: "O JobRunId do Glue e lido do output do TaskSubmitted e vira sfn.job_run ligado a tentativa; historico gravado sem includeExecutionData (sem output) sai sfn.unresolved com razao propria, e nenhum sfn.job_run e afirmado."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_job_run_vem_do_output_e_a_ausencia_sai_nomeada"}
  - id: AC3
    statement: "Historico truncado (nextToken presente na saida salva), paginacao incompleta, evento de tipo desconhecido e JSON invalido saem sfn.unresolved nomeado, e o que foi lido continua valendo."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_historico_incompleto_sai_nomeado_sem_perder_o_que_leu"}
  - id: AC4
    statement: "SF-SFNX-001 dispara quando as tentativas observadas de um estado excedem o que o retry declarado no ASL permite (1 + MaxAttempts efetivo), pelo confronto derivado em fuse entre sfn.attempt e sfn.task do mesmo nome de estado; sem o ASL no case, nao dispara e a lacuna sai nomeada."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"}
  - id: AC5
    statement: "SF-SFNX-002 dispara quando uma tentativa terminou em TaskTimedOut num Task .sync: o Task expirou e o historico nao registra o fim do JobRun que ele acompanhava."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"}
  - id: AC6
    statement: "SF-SFNX-003 dispara quando uma execucao terminou em ExecutionAborted ou ExecutionTimedOut com um Task .sync agendado e sem evento terminal proprio: a execucao parou com o job possivelmente em voo."
    verified_by: {kind: test, ref: "tests/test_fixtures_golden_sfn_history.py::test_golden"}
  - id: AC7
    statement: "sparkforge analyze sfn-history --path le arquivo ou diretorio e devolve os facts, e a tool MCP sparkforge_analyze_sfn_history faz o mesmo."
    verified_by: {kind: test, ref: "tests/test_sfn_history.py::test_cli_e_tool_devolvem_os_mesmos_facts"}
  - id: AC8
    statement: "A area SF-SFNX passa pelo criterio de dominio: regra que julga, coordenador que a declara e rota por findings_area."
    verified_by: {kind: test, ref: "tests/test_criterio_de_dominio.py::test_todo_coordenador_tem_rota_por_artefato"}
  - id: AC9
    statement: "knowledge/stepfunctions/execution-history.md registra as frases citadas da pagina da API lida em 2026-09-19, o que cada evento sustenta, e as lacunas; o bundle offline continua integro."
    verified_by: {kind: command, ref: "python scripts/verify_offline_bundle.py"}
  - id: AC10
    statement: "Os registros que extrator, regra, area, tool e documento de knowledge movem estao em dia."
    verified_by: {kind: command, ref: "python scripts/check_status_numbers.py --strict"}
success:
  - id: SC1
    metric: "Tentativas contadas por estado e JobRun distintos lidos, por fixture"
    source: "goldens de fixtures/sfn_history"
  - id: SC2
    metric: "Goldens de achado existentes que mudaram"
    source: "python -m pytest tests/test_fixtures_golden*.py -q sem regeneracao"
  - id: SC3
    metric: "Regras, tools, extratores e rotas antes e depois"
    source: "load_catalog(), TOOLS, sparkforge/facts/*.py e routing.yaml"
out_of_scope:
  - "Coletor que chama a API com credencial: o operador salva a saida de aws stepfunctions get-execution-history e o analyze le."
  - "EXPRESS: a API nao suporta, e o historico dele vai para o CloudWatch Logs."
  - "Fechar a lacuna U1 com numero: o mecanismo fica pronto, mas a resposta exige um historico REAL de execucao com falha; fixture sintetica prova o extrator, nao a composicao dos retries."
  - "Custo em dolar de tentativa: exige cost_basis (regra 25)."
  - "Map Run distribuido (mapRunArn) alem de nomear o que nao le."
unknowns:
  - id: U1
    blocks: [AC2]
    unlock: "A forma exata do output do TaskSubmitted do Glue (se traz JobRunId e JobName, e com que chaves) nao esta na pagina da API; a pagina de integracao diz que o JobName e inserido na resposta. Destrava um historico real, ou a pagina de integracao lida de novo com esse foco."
  - id: U2
    blocks: [AC4]
    unlock: "Nenhum historico real foi observado. As fixtures sao sinteticas a partir da forma de evento publicada, e por isso a feature entrega o mecanismo, nao a resposta da composicao dos retries."
change_kinds: [extractor, rule, rule_runtime_scope, rule_area, fixture_corpus, knowledge_doc, tool_or_verb, agent_or_skill, routing, status_numbers, claims]
---

# SFN_HISTORY — requisitos

## Problema

O SparkForge lê a definição da state machine e do DAG, e as duas dizem o que **deveria**
acontecer. Quantas vezes o Task foi agendado de verdade, quantos `JobRun` isso produziu e
como a execução terminou só existem no histórico de execução. É esse artefato que separa
retry declarado de retry observado, e é ele que a lacuna U1 das duas features pede.

## Fontes citadas

`docs/sdd/SFN_HISTORY/explore.md`, seção *Fontes lidas*.

## Critérios

- AC1 a AC3 e AC7 são o extrator e a porta pública.
- AC4 a AC6 são as três regras, uma delas derivada do confronto com o ASL.
- AC8 é o critério de domínio.
- AC9 e AC10 são os registros.
