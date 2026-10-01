---
sdd: 1
feature: AIRFLOW_DAG
phase: ship
profile: dev
status: done
upstream:
  path: docs/sdd/AIRFLOW_DAG/build_report.md
  sha256: "abe91a91b76eb9e3d7ffc3a78989af62c22ad678a0c7c4a4b7a0a3782be26c94"
hypothesis_outcome: confirmed
registries: [reachability_lists, fixture_kind_coverage, snippet_measure, rules_catalog_gates, manifest_rule_count, runtime_scope_gates, routing_yaml, coordinator_rule_areas, fixture_corpus_gates, offline_manifest, sources_lock, surface_lock, generated_reference, sync_skills, agents_parity, router_gates, status_numbers_gate, claims_gate]
deviations:
  - "Design emendado no plano: execution_timeout separa declaracao de valor (timedelta(hours=2) e ast.Call, e exigir literal mataria a regra em todo DAG real), razao multiplos_dags, e onze fixtures em vez de dez."
  - "A revisao final voltou ao build com um achado critico e quatro importantes, corrigidos em 9223f037: SF-AIRFLOW-002 afirmava que o job continua cobrando (o que U3 proibe) e nao exigia que a task esperasse o job; a description do coordenador nao citava Airflow; o operations-guide dizia que Airflow e Step Functions nao tinham coordenador; as datas da feature estavam um dia a frente. Mais nove menores. Uma fixture negativa entrou (timeout_sem_espera): doze no corpus."
  - "O AC4 do define foi reescrito na correcao (ele repetia a afirmacao proibida), e a cascata do SDD foi recarimbada. A hipotese nao foi tocada."
  - "O golden fixtures/debate/retomada/expected/brief.json mudou numa linha: a allowlist de extratores de evidencia ganhou airflow-dag. Nao e golden de achado."
  - "Armadilha nova: description de agente nao pode conter `: `, porque quebra o frontmatter YAML e derruba 29 parametrizacoes de tests/test_router_agents.py."
  - "Revisao em dois estagios por tarefa nao rodou; a revisao final do diff inteiro rodou."
---

# AIRFLOW_DAG — entrega

## Hipótese

**Confirmada.** A previsão podia falhar de três jeitos, e nenhum aconteceu:

- **Cada regra dispara na sua fixture e fica calada nas negativas.** SF-AIRFLOW-001 em
  `sem_espera`, 002 em `timeout_sem_stop`, 003 em `espera_sincrona`, 004 em
  `retry_duas_camadas`. Ficam caladas `dag_limpo`, `retry_so_no_glue`,
  `retry_so_no_airflow`, `job_name_nao_literal`, `dag_dinamico`, `python_invalido`,
  `taskflow_decorador` e `timeout_sem_espera`.
- **A área passa pelo critério de domínio:** `tests/test_criterio_de_dominio.py`, 7 passed.
- **Nenhum golden de achado existente mudou.** Na árvore final,
  `python -m pytest tests/test_fixtures_golden*.py -q` deu 3268 passed e 4 skipped, sem
  regeneração e com a árvore limpa. Os cinco goldens de assessment mudaram só na contagem
  do catálogo, e o `brief.json` do debate numa linha que não é achado.

## O que o domínio entrega

- **Extrator.** `sparkforge analyze airflow-dag --path` e a tool
  `sparkforge_analyze_airflow_dag` leem o `.py` do DAG por `ast.parse`, e **nunca** o
  importam nem executam. Sai `af.dag`, `af.task`, `af.dependency`, `af.unresolved` com
  razão própria e `af.analyzed`.
- **Derivação em `fuse`.** Liga o `GlueJobOperator` ao `aws_glue_job` de mesmo nome.
- **Regras.** Quatro na área SF-AIRFLOW, coordenada pelo `glue-infra-reviewer` pela rota
  AGENT-087:
  - **001, P2:** `wait_for_completion=False` com tarefa a jusante.
  - **002, P1:** `execution_timeout` declarado, espera do job, e `stop_job_run_on_kill`
    ausente ou `False`. O operador não para o JobRun; o que acontece com ele depois é
    lacuna nomeada.
  - **003, P3:** espera síncrona sem `deferrable`, que segura um slot de worker.
  - **004, P2:** duas camadas de retry sobre o mesmo job, sem afirmar contagem.
- **Conhecimento.** `knowledge/airflow/glue-operator.md`, com as frases citadas e seis
  lacunas.

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

## Gates rodados

| gate | resultado |
|---|---|
| regra, área, roteamento, escopo (12 arquivos) | 1521 passed |
| domínio, extrator, fusão, cenários, SDD (12 arquivos) | 388 passed |
| agent, superfície, tool, números (14 arquivos) | 1469 passed |
| `python scripts/sync_skills.py --check`, com o README fora | exit 0 |
| `python scripts/gen_reference_docs.py` | 0 regravadas |
| `python scripts/check_surface_lock.py` | 0 divergências |
| `python scripts/verify_offline_bundle.py` (AC9) | exit 0 |
| `python scripts/check_status_numbers.py --strict` (AC10) | 0 divergências |
| `python scripts/check_vnext_claims.py` | 0 divergências |
| `python -m pytest tests/test_fixtures_golden*.py -q` | 3268 passed, 4 skipped |
| `python -m ruff check sparkforge scripts tests` | limpo |

## Pendências

- **U1:** a composição do retry do Airflow com o `MaxRetries` do Glue. É a mesma lacuna do
  Step Functions, e destrava com histórico de execução real.
- **U2:** nenhum DAG real foi observado.
- **U3 e lacuna 6:** o que acontece com o JobRun quando a task morre, e qual ação de IAM o
  operador chama para pará-lo.
- **Módulo compartilhado:** `_glue_jobs_por_nome` e `_max_retries` estão duplicados entre
  `airflow_dag.py` e `stepfunctions.py`, de propósito. Um
  `sparkforge/facts/glue_terraform.py` é incremento separado, e a revisão conferiu que as
  cópias não divergiram.
- **Fora de escopo:** dependência entre DAGs, DAG dinâmico, metadados de execução, e
  operadores que não são o `GlueJobOperator`.

## Lições

- A revisão final pegou um crítico que os testes não pegam: a regra afirmava, em prosa, o
  que a própria lacuna do define proíbe. Texto de regra precisa ser lido contra as frases
  citadas, uma a uma.
- Uma regra com condição incompleta fica verde no golden: a SF-AIRFLOW-002 não exigia
  espera, e só a fixture negativa nova mostrou o achado falso. Toda condição nova merece a
  negativa correspondente.
- Registro que uma feature cria, a seguinte precisa manter: o golden do debate mudou nas
  duas, e na segunda ninguém regenerou até a suíte acusar.
