---
sdd: 1
feature: AIRFLOW_DAG
phase: design
profile: dev
status: ready
upstream:
  path: docs/sdd/AIRFLOW_DAG/define.md
  sha256: "dfe531954bb5423c0becaddc6a6929acb53c295cf2be2d6c99143f8c3ec7d2ae"
files:
  - {path: sparkforge/facts/airflow_dag.py, action: create, reason: "extrator por AST (af.dag, af.task, af.dependency, af.unresolved, af.analyzed) e a derivacao pura af.glue_job_link (D1, D2, D5)"}
  - {path: tests/test_airflow_dag.py, action: create, reason: "AC1, AC2, AC6 e AC7"}
  - {path: sparkforge/facts/fusion.py, action: modify, reason: "fuse() chama build_af_glue_link, como ja chama build_sfn_glue_link (D5)"}
  - {path: sparkforge/adapters/_core.py, action: modify, reason: "funcao publica de analyze airflow-dag (D3)"}
  - {path: sparkforge/adapters/cli.py, action: modify, reason: "subcomando analyze airflow-dag --path (D3)"}
  - {path: sparkforge/adapters/tools.py, action: modify, reason: "tool sparkforge_analyze_airflow_dag, READ_ONLY (D3)"}
  - {path: rules/catalog/airflow.yaml, action: create, reason: "area SF-AIRFLOW, SF-AIRFLOW-001 a 004 (D4)"}
  - {path: rules/catalog/routing.yaml, action: modify, reason: "rota AGENT-087 por findings_area SF-AIRFLOW para glue-infra-reviewer (D6)"}
  - {path: agents/glue-infra-reviewer.md, action: modify, reason: "declara SF-AIRFLOW, cita a tool nova e ganha a description (D6)"}
  - {path: .claude/agents/glue-infra-reviewer.md, action: modify, reason: "espelho gerado por sync_skills"}
  - {path: .agents/agents/glue-infra-reviewer.md, action: modify, reason: "espelho gerado por sync_skills"}
  - {path: .github/agents/glue-infra-reviewer.agent.md, action: modify, reason: "espelho gerado por sync_skills"}
  - {path: .codex/agents/glue-infra-reviewer.toml, action: modify, reason: "espelho que o sync nao gera: a secao nova a mao"}
  - {path: knowledge/airflow/glue-operator.md, action: create, reason: "as frases citadas do provider e do core, e as lacunas (D7)"}
  - {path: knowledge/airflow-pipelines.md, action: modify, reason: "aponta para o documento novo, que traz os defaults com fonte"}
  - {path: knowledge/offline-manifest.json, action: modify, reason: "sha256 dos documentos de knowledge, por _content_sha256"}
  - {path: knowledge/sources.lock.json, action: modify, reason: "URLs novas, por refresh_knowledge.py --offline --update"}
  - {path: fixtures/airflow, action: create, reason: "corpus novo: uma fixture por regra, as negativas, o par DAG + Terraform e os casos de nao literal (D8)"}
  - {path: tests/test_fixtures_golden_airflow.py, action: create, reason: "golden do corpus, com a linha literal FIXTURES = ROOT / \"fixtures\" / \"airflow\""}
  - {path: scripts/regen_fixtures.py, action: modify, reason: "FIXTURES_AIRFLOW e regen_airflow"}
  - {path: tests/test_fixtures_kind_coverage.py, action: modify, reason: "extrator novo nas listas manuais"}
  - {path: tests/test_rules_catalog_reachability.py, action: modify, reason: "extrator novo na lista de imports"}
  - {path: tests/test_adapters_tools.py, action: modify, reason: "lista literal da superficie e argumento real da tool nova"}
  - {path: tests/test_harness_authorization.py, action: modify, reason: "contagem de tools que declaram caminho"}
  - {path: tests/test_fixtures_golden_mcp_parity.py, action: modify, reason: "tool nova depois do golden entra em NOVAS_DEPOIS_DO_GOLDEN"}
  - {path: tests/test_databricks_rule_audit.py, action: modify, reason: "airflow_dag entra em SO_AWS: o extrator le DAG que dispara job AWS, e as regras tem runtime_scope vazio (D4)"}
  - {path: sparkforge/agentic/executor/debate_evidence.py, action: modify, reason: "airflow-dag na allowlist de extratores de evidencia, como step-functions"}
  - {path: docs/agentic-evolution-report.md, action: modify, reason: "a contagem da allowlist de extratores"}
  - {path: parity.yaml, action: modify, reason: "capacidade com tools, cli e knowledge"}
  - {path: manifest.json, action: modify, reason: "tools e knowledge_base.rule_count"}
  - {path: docs/surface.lock.json, action: modify, reason: "tool e knowledge novos (regra 26, bytes no commit)"}
  - {path: docs/guia/referencia/tools/sparkforge_analyze_airflow_dag.md, action: create, reason: "pagina gerada da tool"}
  - {path: docs/guia/referencia/tools/README.md, action: modify, reason: "indice gerado"}
  - {path: docs/guia/referencia/cli/analyze.md, action: modify, reason: "pagina gerada do verbo"}
  - {path: docs/guia/referencia/agents/glue-infra-reviewer.md, action: modify, reason: "pagina gerada do coordenador"}
  - {path: docs/guia/usos/airflow.md, action: create, reason: "manual de uso: como coletar o DAG e o que as quatro regras dizem"}
  - {path: docs/guia/06-extrair-julgar-compor.md, action: modify, reason: "o verbo novo na tabela e as contagens"}
  - {path: docs/guia/07-conhecimento-e-catalogo.md, action: modify, reason: "contagem de regras e areas"}
  - {path: fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, action: modify, reason: "goldens de assessment carregam a contagem do catalogo (tres cenarios e dois holdout; este e o representante)"}
  - {path: docs/superpowers/STATUS.md, action: modify, reason: "regras, tools, extratores, rotas, fontes"}
  - {path: README.md, action: modify, reason: "contagem de regras, tools e extratores"}
  - {path: CLAUDE.md, action: modify, reason: "contagem de tools e de tools com detail_level"}
  - {path: AGENTS.md, action: modify, reason: "mesma contagem"}
  - {path: GUIA_DE_USO.md, action: modify, reason: "mesma contagem"}
  - {path: .devin/README.md, action: modify, reason: "mesma contagem"}
  - {path: docs/harness/CODEINTEL-GAP.md, action: modify, reason: "alegacoes de corpus e de tools"}
  - {path: docs/harness/AUTHORIZATION-CHAIN.md, action: modify, reason: "alegacoes de len(TOOLS)"}
  - {path: docs/harness/CURRENT-HARNESS-GAP.md, action: modify, reason: "alegacoes de contagem"}
  - {path: docs/harness/ICEBERG-GAP.md, action: modify, reason: "alegacao da contagem de fontes vigiadas"}
  - {path: docs/claims.lock.json, action: modify, reason: "arquivo .py novo e contagens movem alegacoes"}
decisions:
  - id: D1
    choice: "Modulo sparkforge/facts/airflow_dag.py, prefixo de kind af. (nenhum kind existente comeca com af). Le .py por ast.parse, NUNCA executa o arquivo. Kinds: af.dag (dag_id, schedule literal ou marca, default_args com retries e execution_timeout literais), af.task (operator_class, task_id, os argumentos literais que a regra julga, has_downstream efetivo), af.dependency (upstream, downstream, forma declarada), af.unresolved (reason: invalid_python, read_error, size_above_limit, dag_dinamico, arg_nao_literal, dependencia_dinamica, task_id_nao_literal), af.analyzed (sempre). Molde de leitura: sparkforge/facts/pyspark_ast.py; molde de dominio: sparkforge/facts/stepfunctions.py."
    rejected: ["importar o DAG e usar DagBag: executa codigo do operador, e o repositorio nao executa artefato", "ler o DAG serializado do banco do Airflow: exige acesso, e o define poe fora de escopo"]
    rollback: "git revert dos commits da feature"
  - id: D2
    choice: "Os defaults publicados moram no extrator como constantes com a URL ao lado: wait_for_completion True, deferrable False, stop_job_run_on_kill False, job_poll_interval 6 (provider Amazon) e core.default_task_retries 0 (referencia de configuracao). O fact grava o efetivo e a marca de omitido. Argumento que nao e literal (Name, f-string, Call, JinjaTemplate em string com {{ }}) vira af.unresolved nomeado, e o atributo correspondente sai ausente, nunca com o default."
    rejected: ["assumir o default quando o argumento nao e literal: seria afirmar o que nao se leu"]
    rollback: "git revert do commit"
  - id: D3
    choice: "Verbo sparkforge analyze airflow-dag --path <arquivo|diretorio> e tool MCP sparkforge_analyze_airflow_dag (path, detail_level), READ_ONLY, no molde de analyze step-functions. Teto de tamanho pelo mesmo _teto_para do scan."
    rejected: ["reaproveitar analyze pyspark: o extrator de PySpark julga transformacao, e um DAG nao e job"]
    rollback: "git revert do commit"
  - id: D4
    choice: "Area SF-AIRFLOW em rules/catalog/airflow.yaml, runtime_scope {} nas quatro (o DAG sozinho nao detecta runtime Glue; o mesmo motivo de SF-SFN), e airflow_dag em SO_AWS na auditoria de texto AWS. SF-AIRFLOW-001 (P2, structural): GlueJobOperator com wait_for_completion False e has_downstream. SF-AIRFLOW-002 (P1, structural): execution_timeout declarado e stop_job_run_on_kill ausente ou False. SF-AIRFLOW-003 (P3, structural): espera sincrona sem deferrable. SF-AIRFLOW-004 (P2, structural): af.glue_job_link com retries efetivo > 0 e max_retries > 0. Cada regra cita a frase que a sustenta em sources, e nenhuma afirma contagem de tentativas (U1)."
    rejected: ["regra sobre codigo pesado no top-level do DAG: o que e pesado nao se mede por AST sem heuristica, e heuristica nao e fact", "regra sobre retries sem escrita idempotente: e a SF-GLUE-004, que ja existe pelo lado do job"]
    rollback: "git revert do commit, e regen dos goldens de assessment"
  - id: D5
    choice: "Derivacao pura build_af_glue_link(facts) em airflow_dag.py, chamada por fusion.fuse(): para cada af.task GlueJobOperator com job_name literal, procura tf.attribute key name com o mesmo valor num recurso aws_glue_job e le o max_retries do mesmo recurso; emite af.glue_job_link com job_name, resource, glue_max_retries, airflow_retries_effective e derived_from com os tres ids. job_name nao literal, job ausente, dois jobs com o mesmo nome ou max_retries nao literal saem af.unresolved nomeado."
    rejected: ["casar pelo task_id: o task_id e do Airflow, nao do Glue"]
    rollback: "git revert do commit"
  - id: D6
    choice: "glue-infra-reviewer declara SF-AIRFLOW e ganha a rota AGENT-087 por findings_area, com uma secao curta citando a tool nova. Coordenador novo nao entra."
    rejected: ["ressuscitar sf-airflow-specialist: foi removido no SF_STUBS por ser nome sem artefato, e uma area so nao justifica coordenador proprio"]
    rollback: "git revert do commit, depois python scripts/sync_skills.py"
  - id: D7
    choice: "knowledge/airflow/glue-operator.md com as frases citadas (provider Amazon e referencia de configuracao do core), a data de leitura e as lacunas: composicao dos retries, JobRun quando a task morre com stop_job_run_on_kill False, DAG dinamico fora do alcance da leitura estatica. knowledge/airflow-pipelines.md ganha um ponteiro para ele."
    rejected: ["escrever os defaults so na regra: knowledge e o que o agente consulta offline"]
    rollback: "git revert do commit"
  - id: D8
    choice: "Corpus fixtures/airflow/<caso>/input e expected, sintetico a partir dos exemplos do provider: sem_espera (001), timeout_sem_stop (002), espera_sincrona (003), retry_duas_camadas (004, DAG + main.tf), dag_limpo (negativa: espera com deferrable, sem timeout, sem retries), retry_so_no_glue (negativa), job_name_nao_literal, dag_dinamico (laco), python_invalido e taskflow_decorador (reconhece e nomeia o que nao le)."
    rejected: ["DAG real: nenhum foi observado, e caso real nunca entra no repositorio"]
    rollback: "git rm do corpus"
covers:
  - {part: "extrator", acceptance: [AC1, AC2]}
  - {part: "verbo e tool", acceptance: [AC7]}
  - {part: "regras e area", acceptance: [AC3, AC4, AC5, AC8]}
  - {part: "derivacao", acceptance: [AC6]}
  - {part: "knowledge e registros", acceptance: [AC9, AC10]}
---

# AIRFLOW_DAG — desenho

## Partes

| parte | arquivos | critério |
|---|---|---|
| extrator | `sparkforge/facts/airflow_dag.py`, `tests/test_airflow_dag.py` | AC1, AC2 |
| verbo e tool | `_core.py`, `cli.py`, `tools.py`, `parity.yaml`, testes de superfície | AC7 |
| regras e área | `rules/catalog/airflow.yaml`, `routing.yaml`, `glue-infra-reviewer`, corpus e golden | AC3–AC5, AC8 |
| derivação | `build_af_glue_link` e `fusion.py` | AC6 |
| knowledge e registros | documento, manifesto offline, lock de fontes, superfície, referência, números | AC9, AC10 |

## Medidas que sustentam o desenho

- Precedente inteiro: `docs/sdd/STEP_FUNCTIONS/` (extrator, verbo, tool, área com quatro
  regras, derivação em `fuse`, corpus). O CI do #90 passou com ele.
- Precedente de leitura de Python: `sparkforge/facts/pyspark_ast.py`
  (`extract_source`, `extract_path`, `extract_tree`).
- `SF-AIRFLOW` é nome de área que já existiu vazio e saiu no #88; volta com regra que
  julga.
- O lado do Glue já é fact: `tf.attribute` com `key: name` e `key: max_retries` no mesmo
  recurso.
