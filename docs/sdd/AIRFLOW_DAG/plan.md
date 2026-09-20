---
sdd: 1
feature: AIRFLOW_DAG
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/AIRFLOW_DAG/design.md
  sha256: "cab63e877c117ac89954b53077f1fdb212bb12555e135ca62d4de9761cedca0e"
tasks:
  - id: T1
    files: [sparkforge/facts/airflow_dag.py, tests/test_airflow_dag.py, docs/superpowers/STATUS.md, README.md, docs/guia/06-extrair-julgar-compor.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC1, AC2]
    test: {path: tests/test_airflow_dag.py, name: test_dag_vira_fact_com_operador_e_argumentos_literais}
  - id: T2
    files: [tests/test_airflow_dag.py, sparkforge/adapters/_core.py, sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, tests/test_adapters_tools.py, tests/test_harness_authorization.py, tests/test_fixtures_golden_mcp_parity.py, parity.yaml, manifest.json, agents/glue-infra-reviewer.md, .claude/agents/glue-infra-reviewer.md, .agents/agents/glue-infra-reviewer.md, .github/agents/glue-infra-reviewer.agent.md, .codex/agents/glue-infra-reviewer.toml, docs/surface.lock.json, docs/guia/referencia/tools/README.md, docs/guia/referencia/tools/sparkforge_analyze_airflow_dag.md, docs/guia/referencia/cli/analyze.md, docs/guia/referencia/agents/glue-infra-reviewer.md, docs/guia/06-extrair-julgar-compor.md, docs/superpowers/STATUS.md, README.md, CLAUDE.md, AGENTS.md, GUIA_DE_USO.md, .devin/README.md, docs/harness/AUTHORIZATION-CHAIN.md, docs/harness/CURRENT-HARNESS-GAP.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC7]
    test: {path: tests/test_airflow_dag.py, name: test_cli_e_tool_devolvem_os_mesmos_facts}
  - id: T3
    files: [tests/test_airflow_dag.py, sparkforge/facts/airflow_dag.py, sparkforge/facts/fusion.py, rules/catalog/airflow.yaml, rules/catalog/routing.yaml, agents/glue-infra-reviewer.md, .claude/agents/glue-infra-reviewer.md, .agents/agents/glue-infra-reviewer.md, .github/agents/glue-infra-reviewer.agent.md, .codex/agents/glue-infra-reviewer.toml, fixtures/airflow, tests/test_fixtures_golden_airflow.py, scripts/regen_fixtures.py, tests/test_fixtures_kind_coverage.py, tests/test_rules_catalog_reachability.py, tests/test_databricks_rule_audit.py, sparkforge/agentic/executor/debate_evidence.py, docs/agentic-evolution-report.md, manifest.json, knowledge/sources.lock.json, docs/guia/referencia/agents/glue-infra-reviewer.md, fixtures/scenarios/glue_40_para_60_salto_longo/expected/assessment.json, fixtures/scenarios/glue_51_para_60_iceberg_ansi/expected/assessment.json, fixtures/scenarios/glue_60_fgac_com_jar/expected/assessment.json, evals/holdout/config_por_caminho_indireto/expected/assessment.json, evals/holdout/lote_misto_iceberg_parquet/expected/assessment.json, docs/superpowers/STATUS.md, README.md, docs/guia/06-extrair-julgar-compor.md, docs/guia/07-conhecimento-e-catalogo.md, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC3, AC4, AC5, AC6, AC8]
    test: {path: tests/test_fixtures_golden_airflow.py, name: test_golden}
  - id: T4
    files: [knowledge/airflow/glue-operator.md, knowledge/airflow-pipelines.md, knowledge/offline-manifest.json, knowledge/sources.lock.json, docs/guia/usos/airflow.md, docs/gates-por-mudanca.md, parity.yaml, docs/surface.lock.json, docs/claims.lock.json]
    covers: [AC9, AC10]
    test: {path: tests/test_surface_lock.py, name: "TestOLockBateComAMedida::test_the_knowledge_matches"}
---

# AIRFLOW_DAG — plano

> Branch `sdd/airflow-dag`, empilhada sobre `main` depois do #90 (STEP_FUNCTIONS).
> O precedente inteiro — extrator, verbo, tool, área com quatro regras, derivação em
> `fuse`, corpus, golden e os registros — é `docs/sdd/STEP_FUNCTIONS/plan.md`, e o CI
> passou com ele. Este plano o espelha tarefa a tarefa, trocando Step Functions por
> Airflow. Onde ele se afasta do precedente, a razão está escrita no lugar.

## Regras de execução

- Pouca memória: **um comando por vez**, nunca a suíte inteira nem os lotes de
  `tests/test_suite_batches.py` em paralelo com edição.
- Edição por ferramenta (Edit/Write), fim de linha LF. `rules/catalog/routing.yaml` tem
  BOM: edite com Edit, nunca reescreva o arquivo inteiro.
- Arquivo `.py` novo do pacote entra no índice (`git add <arquivo>`) **antes** de
  qualquer teste: `tests/test_arvore_versionada.py` reprova `.py` de `sparkforge/**`
  fora do git.
- **`python scripts/sync_skills.py` e `tests/test_agents_parity.py` apagam o
  `.claude/agents/README.md` não rastreado.** Antes de cada um:
  `cp .claude/agents/README.md "$TEMP/claude_agents_README.bak.md"`; depois:
  `cp "$TEMP/claude_agents_README.bak.md" .claude/agents/README.md`. O README nunca
  entra no `git add`.
- Agente se edita na fonte `agents/<nome>.md`; `.claude/`, `.agents/` e `.github/` saem
  do `sync_skills.py`. **`.codex/agents/<nome>.toml` o sync NÃO gera**: é espelho à mão,
  e a seção nova vai nele no mesmo commit.
- Commit por tarefa com `git commit -F <arquivo no scratchpad>`, mensagem conventional
  em inglês, terminando com as duas linhas de atribuição da sessão.
- `python scripts/check_vnext_claims.py` antes de todo commit que acrescenta `.py` ou
  move `len(TOOLS)`. Remedie **pela lista de ids da saída do gate**, nunca por varredura;
  `--seed` reescreve o lock inteiro — se precisar dele, guarde só a entrada nova e
  devolva o resto com `git checkout docs/claims.lock.json`.

## Medidas desta árvore, tiradas antes de começar

Com os produtores de `scripts/check_status_numbers.py` (`0 divergencia(s)` na hora,
2026-09-20, já sobre o #90), e `python scripts/check_vnext_claims.py` com `exit 0`:

| medida | antes | depois desta feature |
|---|---|---|
| Regras de diagnóstico | **161** (98 `confirmed`, 63 `structural`, 26 com `runtime_scope` não-vazio) | **165** (98 `confirmed`, **67** `structural`, 26 com `runtime_scope` não-vazio) |
| Áreas (`area_of`) | **29** | **30** |
| Tools MCP | **107** (99 declaram caminho, 39 com `detail_level`) | **108** (**100** com caminho, **40** com `detail_level`) |
| Extratores de facts | **39** | **40** |
| Fact kinds distintos | **233** | **239** |
| Rotas determinísticas | **41** | **42** |
| Coordenadores | **12** | **12** (nenhum novo) |
| Fixtures golden | **528** em **57** domínios | **539** em **58** domínios |
| Fontes oficiais vigiadas | **262** (247 móveis, 15 fixas) | **265** (250 móveis, 15 fixas) |
| Documentos de `knowledge/` no `surface.lock` | **54** | **55** |
| `manifest.json` `rule_count` | **161** | **165** |
| Goldens de assessment: `catalog_rules` / `unguarded_rules` | **161** / **135** | **165** / **139** |
| Allowlist de extratores de evidência do debate | **23** | **24** |
| Arquivos `.py` que `iter_source_files` entrega | **756** | **~769** (3 módulos + 10 DAGs de fixture; **meça**) |

**Publique o que o gate medir na hora, não o número escrito aqui.** Se alguma linha
divergir ao executar, a medida do gate é que vale — este plano é a previsão, e a
previsão pode estar errada.

Duas medidas que decidem desenho e ficam registradas aqui:

- `runtime.wall_clock` é o maior grupo de eixo de `action.moves`, com **12**, e
  `tests/test_agentic_executor_ordering.py` afirma `maior == 12` e
  `no_topo == {"runtime.wall_clock"}`. **Nenhuma regra `SF-AIRFLOW` pode declarar
  `runtime.wall_clock`** — os eixos escolhidos são `cost.dpu_seconds` (3 → 5),
  `cost.provisioned_capacity_time` (6 → 7) e `correctness.write_result` (`nature: risk`,
  fora da restrição).
- O único outro `action.target` do catálogo com `max_retries` é `SF-SFN-004`
  (`glue.max_retries`, `decrease`). A `SF-AIRFLOW-004` usa o mesmo alvo e a mesma
  direção: mesma direção não é contradição para `tests/test_rules_action_field.py`.

## Por que quatro tarefas, e não cinco

Pelo mesmo motivo medido no STEP_FUNCTIONS: a contagem do catálogo move seis registros
(`manifest.json`, `STATUS.md`, `README.md`, `docs/guia/07`, os cinco goldens de
assessment e o lastro), e separar as regras em duas tarefas moveria os seis duas vezes.
A área precisa entrar inteira com rota e coordenador (`test_router_agents`,
`test_agent_coverage`). Então T3 leva as quatro regras, a derivação, a área, a rota, o
corpus e o golden; e a derivação fica em T3 e não em T1 porque o teste dela (AC6) só
fecha com a `SF-AIRFLOW-004` julgando.

`af.glue_job_link` entra em `EMITTED_KINDS` só em T3: declarado em T1 sem golden, ele
deixaria `test_every_kind_of_every_extractor_appears_in_some_golden[airflow_dag]`
vermelho assim que o módulo entrasse nas listas manuais.

## O que este plano refina do desenho (e por quê)

Três pontos, todos repetidos na seção **Dúvidas** no fim:

1. **`execution_timeout` é DECLARAÇÃO, não valor.** D2 manda transformar argumento não
   literal em `af.unresolved` com o atributo ausente. Aplicado ao pé da letra,
   `execution_timeout=timedelta(hours=2)` — um `ast.Call`, a única forma que a
   documentação do Airflow ensina — deixaria a `SF-AIRFLOW-002` calada em 100% dos DAGs
   reais. A refinação: a **presença** da palavra-chave é lida do AST com exatidão e vira
   `attrs.execution_timeout_declared`; o **valor** vira `measures.execution_timeout_seconds`
   só quando é `timedelta(**literais)`, e quando não é, a medida fica ausente sem
   `af.unresolved` — porque nada do que a regra lê deixou de ser lido.
2. **Uma razão de `af.unresolved` a mais que a lista de D1: `multiplos_dags`.** Com dois
   ou mais `DAG(...)` no mesmo arquivo, não há como dizer de qual DAG vem o
   `default_args` de uma task. A leitura adotada é recusar: `default_args` fica ilegível
   para o arquivo inteiro e a lacuna sai nomeada.
3. **Uma fixture a mais que a lista de D8: `retry_so_no_airflow`.**
   `tests/test_rules_threshold_mutation.py` compara `FRONTEIRA_SEM_GOLDEN` por
   **igualdade exata**, e a `expr` da `SF-AIRFLOW-004` tem duas comparações `> 0`. D8
   traz o golden que mata `airflow_retries_effective >= 0` (`retry_so_no_glue`) e não
   traz o que mata `glue_max_retries >= 0`. São 11 fixtures, não 10.

## T1 — o extrator do DAG

### 1. Teste que falha

`tests/test_airflow_dag.py` (arquivo novo):

```python
"""O extrator do arquivo .py de um DAG do Airflow: o que ele diz sobre o job Glue.

DAGs sinteticos, montados a partir dos exemplos da documentacao do provider: nenhum
DAG real foi observado (U2 de `docs/sdd/AIRFLOW_DAG/define.md`).
"""
import json

from sparkforge.facts.airflow_dag import (
    DEFAULT_DEFERRABLE,
    DEFAULT_STOP_JOB_RUN_ON_KILL,
    DEFAULT_TASK_RETRIES,
    DEFAULT_WAIT_FOR_COMPLETION,
    extract_airflow_dag,
    extract_airflow_dag_path,
    extract_airflow_dag_tree,
)

DAG_COM_TRES_TASKS = '''
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

DEFAULT_ARGS = {"retries": 2, "execution_timeout": timedelta(minutes=90)}

with DAG(
    dag_id="carga_diaria",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        wait_for_completion=False,
    )
    enriquecer = GlueJobOperator(
        task_id="enriquecer",
        job_name=NOME_DO_JOB,
        deferrable=True,
        stop_job_run_on_kill=True,
        retries=0,
    )
    publicar = EmptyOperator(task_id="publicar")

    carga >> enriquecer >> publicar
'''


def _por_kind(facts, kind):
    return {f.subject["symbol"]: f for f in facts if f.kind == kind}


def test_dag_vira_fact_com_operador_e_argumentos_literais():
    facts = extract_airflow_dag(DAG_COM_TRES_TASKS, "dags/carga_diaria.py")

    [dag] = [f for f in facts if f.kind == "af.dag"]
    assert dag.attrs["dag_id"] == "carga_diaria"
    assert dag.attrs["dag_id_literal"] is True
    assert dag.attrs["schedule"] == "0 3 * * *"
    assert dag.attrs["schedule_source"] == "schedule"
    assert dag.attrs["default_args_source"] == "module_name"
    assert dag.attrs["default_retries_declared"] is True
    assert dag.attrs["default_execution_timeout_declared"] is True
    assert dag.measures == {"default_retries": 2, "default_execution_timeout_seconds": 5400}

    tasks = _por_kind(facts, "af.task")
    assert set(tasks) == {"carga", "enriquecer", "publicar"}

    carga = tasks["carga"]
    assert carga.attrs["operator_class"] == "GlueJobOperator"
    assert carga.attrs["operator_family"] == "glue_job"
    assert carga.attrs["task_id"] == "carga"
    assert carga.attrs["var_name"] == "carga"
    assert carga.attrs["job_name"] == "carga-diaria"
    assert carga.attrs["job_name_source"] == "literal"
    assert carga.attrs["wait_for_completion_effective"] is False
    assert carga.attrs["wait_for_completion_defaulted"] is False
    # Omitidos: o default PUBLICADO, com a marca de omitido (D2).
    assert carga.attrs["deferrable_effective"] is DEFAULT_DEFERRABLE
    assert carga.attrs["deferrable_defaulted"] is True
    assert carga.attrs["stop_job_run_on_kill_effective"] is DEFAULT_STOP_JOB_RUN_ON_KILL
    assert carga.attrs["stop_job_run_on_kill_defaulted"] is True
    # `execution_timeout` vem de `default_args`: a DECLARACAO e o que a regra le.
    assert carga.attrs["execution_timeout_declared"] is True
    assert carga.attrs["execution_timeout_source"] == "default_args"
    assert carga.attrs["retries_source"] == "default_args"
    assert carga.attrs["retries_defaulted"] is False
    assert carga.attrs["has_downstream"] is True
    assert carga.measures == {"retries_effective": 2, "execution_timeout_seconds": 5400}

    enriquecer = tasks["enriquecer"]
    assert enriquecer.attrs["wait_for_completion_effective"] is DEFAULT_WAIT_FOR_COMPLETION
    assert enriquecer.attrs["wait_for_completion_defaulted"] is True
    assert enriquecer.attrs["deferrable_effective"] is True
    assert enriquecer.attrs["stop_job_run_on_kill_effective"] is True
    assert enriquecer.attrs["retries_source"] == "task"
    assert enriquecer.measures["retries_effective"] == 0
    # `job_name=NOME_DO_JOB` nao e literal: o atributo SAI AUSENTE, nunca o default.
    assert "job_name" not in enriquecer.attrs
    assert enriquecer.attrs["job_name_source"] == "nao_literal"
    assert enriquecer.attrs["has_downstream"] is True

    publicar = tasks["publicar"]
    assert publicar.attrs["operator_class"] == "EmptyOperator"
    assert publicar.attrs["operator_family"] == ""
    assert publicar.attrs["has_downstream"] is False
    assert "wait_for_completion_effective" not in publicar.attrs
    assert publicar.measures["retries_effective"] == 2

    nao_literais = [
        (f.attrs["arg"], f.subject["symbol"])
        for f in facts
        if f.kind == "af.unresolved" and f.attrs["reason"] == "arg_nao_literal"
    ]
    assert nao_literais == [("job_name", "enriquecer")]

    [sentinela] = [f for f in facts if f.kind == "af.analyzed"]
    assert sentinela.measures == {
        "dag_count": 1,
        "task_count": 3,
        "dependency_count": 2,
        "unresolved_count": 1,
    }


def test_dependencias_viram_fact_e_o_que_nao_le_sai_nomeado(tmp_path):
    fonte = '''
from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(dag_id="cargas", schedule="@daily", start_date=datetime(2026, 1, 1)) as dag:
    abrir = EmptyOperator(task_id="abrir")
    clientes = GlueJobOperator(task_id="clientes", job_name="carga-clientes")
    pedidos = GlueJobOperator(task_id="pedidos", job_name="carga-pedidos")
    fechar = EmptyOperator(task_id="fechar")

    abrir >> [clientes, pedidos]
    fechar.set_upstream(clientes)
    for tarefa in [clientes, pedidos]:
        tarefa >> fechar
'''
    facts = extract_airflow_dag(fonte, "dags/cargas.py")
    elos = sorted(
        (f.attrs["upstream"], f.attrs["downstream"], f.attrs["form"])
        for f in facts
        if f.kind == "af.dependency"
    )
    assert elos == [
        ("abrir", "clientes", "rshift"),
        ("abrir", "pedidos", "rshift"),
        ("clientes", "fechar", "set_upstream"),
    ]
    dinamicas = [
        f.attrs["form"]
        for f in facts
        if f.kind == "af.unresolved" and f.attrs["reason"] == "dependencia_dinamica"
    ]
    assert dinamicas == ["rshift"]

    tasks = _por_kind(facts, "af.task")
    assert tasks["abrir"].attrs["has_downstream"] is True
    assert tasks["clientes"].attrs["has_downstream"] is True
    # `pedidos >> fechar` so existe dentro do laco: nao foi lido, e o fact nao mente.
    assert tasks["pedidos"].attrs["has_downstream"] is False
    assert tasks["fechar"].attrs["has_downstream"] is False

    # DAG montado em laco, TaskFlow, e Python que nao parseia: cada um nomeado.
    (tmp_path / "em_laco.py").write_text(
        "from airflow import DAG\n"
        "from airflow.providers.amazon.aws.operators.glue import GlueJobOperator\n"
        "for dominio in ('clientes', 'pedidos'):\n"
        "    with DAG(dag_id=f'carga_{dominio}') as dag:\n"
        "        GlueJobOperator(task_id='carga', job_name=f'carga-{dominio}')\n",
        encoding="utf-8",
    )
    (tmp_path / "taskflow.py").write_text(
        "from airflow.decorators import dag, task\n"
        "@dag(schedule='@daily')\n"
        "def fluxo():\n"
        "    @task\n"
        "    def extrair():\n"
        "        return 1\n"
        "    extrair()\n",
        encoding="utf-8",
    )
    (tmp_path / "quebrado.py").write_text("with DAG(dag_id='x',\n", encoding="utf-8")
    facts = extract_airflow_dag_tree(tmp_path, repo_root=tmp_path)
    motivos = sorted(
        (f.subject["file"], f.attrs["reason"])
        for f in facts
        if f.kind == "af.unresolved"
    )
    assert motivos == [
        ("em_laco.py", "dag_dinamico"),
        ("em_laco.py", "dag_dinamico"),
        ("quebrado.py", "invalid_python"),
        ("taskflow.py", "taskflow_decorador"),
        ("taskflow.py", "taskflow_decorador"),
    ]
    assert not [f for f in facts if f.kind in ("af.dag", "af.task")]
    assert len([f for f in facts if f.kind == "af.analyzed"]) == 3

    # Dois DAGs no mesmo arquivo: `default_args` fica ilegivel para o arquivo inteiro.
    dois = '''
from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

primeiro = DAG(dag_id="um", default_args={"retries": 3})
segundo = DAG(dag_id="dois", default_args={"retries": 0})
carga = GlueJobOperator(task_id="carga", job_name="carga-diaria", dag=primeiro)
'''
    facts = extract_airflow_dag(dois, "dags/dois.py")
    assert sorted(f.attrs["reason"] for f in facts if f.kind == "af.unresolved") == [
        "arg_nao_literal",
        "arg_nao_literal",
        "multiplos_dags",
    ]
    [carga] = [f for f in facts if f.kind == "af.task"]
    assert "retries_effective" not in carga.measures
    assert "execution_timeout_declared" not in carga.attrs
    assert DEFAULT_TASK_RETRIES == 0


def test_o_teto_de_tamanho_e_o_erro_de_leitura_saem_nomeados(tmp_path):
    from sparkforge.facts import scan

    grande = tmp_path / "gigante.py"
    teto = scan._teto_para(grande)
    grande.write_text("# " + ("x" * teto) + "\n", encoding="utf-8")
    facts = extract_airflow_dag_path(grande, repo_root=tmp_path)
    assert [f.attrs["reason"] for f in facts if f.kind == "af.unresolved"] == [
        "size_above_limit"
    ]
    assert [f.kind for f in facts if f.kind == "af.analyzed"] == ["af.analyzed"]

    ilegivel = tmp_path / "bytes.py"
    ilegivel.write_bytes(b"\xff\xfe\x00 nao e utf-8 \x80")
    facts = extract_airflow_dag_path(ilegivel, repo_root=tmp_path)
    assert [f.attrs["reason"] for f in facts if f.kind == "af.unresolved"] == ["read_error"]

    assert json.loads(json.dumps([f.to_dict() for f in facts]))
```

### 2. Rodar e ver falhar

```bash
git add tests/test_airflow_dag.py
python -m pytest tests/test_airflow_dag.py -q
```

Falha esperada: `ModuleNotFoundError: No module named 'sparkforge.facts.airflow_dag'` na
coleta — o módulo ausente é a unidade sob teste.

### 3. Código mínimo

`sparkforge/facts/airflow_dag.py` (arquivo novo, inteiro):

```python
"""Extrator de Facts a partir do arquivo `.py` de um DAG do Apache Airflow.

Le o DAG com `ast.parse` e NUNCA o importa nem o executa: importar um modulo de DAG
executa o codigo do operador e do que ele importa, e este repositorio nao executa
artefato analisado (D1 de `docs/sdd/AIRFLOW_DAG/design.md`). Molde de leitura de
Python: `sparkforge/facts/pyspark_ast.py`. Molde de dominio novo inteiro:
`sparkforge/facts/stepfunctions.py`.

Como `stepfunctions.py`, NAO coleta nada e NUNCA levanta excecao por arquivo
malformado: o que nao consegue ler vira `af.unresolved` com `attrs.reason`, e a
sentinela `af.analyzed` sai sempre, uma por arquivo.

## Por que `af.`

E o prefixo curto de Airflow, e nenhum kind existente comeca com ele (D1).

## O que sai

- `af.dag` -- um por chamada `DAG(...)` lida. `attrs.dag_id` e `attrs.schedule` so
  aparecem quando sao literais; `measures.default_retries` e
  `measures.default_execution_timeout_seconds`, quando `default_args` e legivel.
- `af.task` -- um por operador instanciado. `subject.symbol` e o `task_id` literal
  quando ha um, senao o nome da variavel; `attrs.var_name` traz sempre o nome da
  variavel, que e por onde as dependencias se referem a task.
- `af.dependency` -- um por elo declarado por `>>`, `<<`, `set_downstream` ou
  `set_upstream`, com `attrs.form` dizendo qual das quatro formas o declarou.
- `af.unresolved` -- o que nao deu para ler. Razoes: `invalid_python`, `read_error`,
  `size_above_limit`, `dag_dinamico`, `multiplos_dags`, `arg_nao_literal`,
  `dependencia_dinamica` e `task_id_nao_literal`.
- `af.analyzed` -- a sentinela, com as contagens.
- `af.glue_job_link` -- DERIVADO, nunca lido de arquivo: `build_af_glue_link` liga a
  task do `GlueJobOperator` ao `aws_glue_job` de mesmo `name` quando os dois estao no
  pool, e `fusion.fuse` a chama (D5). Ela entra em `EMITTED_KINDS` na T3, junto com o
  golden que a cobre.

Nenhum fact deste modulo carrega `subject.snippet`: `tests/test_harness_untrusted.py`
mede quais extratores produzem snippet, e este nao entra em `EXTRATORES_COM_SNIPPET`.

## O que e "operador", e como se sabe

A leitura adotada, escrita aqui porque e uma escolha: chamada cujo nome termina em
`Operator` ou em `Sensor`. E estrutural (nao executa nada, nao resolve import) e casa
a convencao que o Airflow publica e que todo provider segue. O que ela NAO alcanca e
a TaskFlow API (`@task`, `@dag`), e por isso o decorador nao e lido como operador: ele
sai em `af.unresolved` com `taskflow_decorador`, nomeado em vez de adivinhado (a
TaskFlow esta fora de escopo no `define`).

`GlueJobOperator` e o legado `AwsGlueJobOperator` recebem `attrs.operator_family:
glue_job`; qualquer outro operador entra com familia vazia. A familia e o predicado
que as regras leem -- derivar aqui e o que a regra 33 exige, porque
`sparkforge/rules/expr.py` nao tem funcao e `where` so compara por igualdade.

## Os defaults publicados moram AQUI, com a fonte ao lado

A regra nao sabe o default. O fact grava o valor EFETIVO e a marca de que ele foi
omitido (D2), e argumento que NAO e literal deixa o atributo AUSENTE -- nunca o
default para o que ninguem leu.

## `execution_timeout` e a excecao declarada a essa frase

A regra `SF-AIRFLOW-002` julga a DECLARACAO de `execution_timeout`, nao o valor dele.
A presenca da palavra-chave e lida do AST com exatidao, e vira
`attrs.execution_timeout_declared`. O valor so vira `measures.execution_timeout_seconds`
quando e `timedelta(**literais)` -- a forma que a documentacao ensina --, e quando nao
e, a medida fica ausente SEM `af.unresolved`, porque nada do que a regra le deixou de
ser lido. Tratar `timedelta(...)` como nao literal deixaria a regra calada em todo DAG
real, que e o modo de falha que esta escolha evita.
"""
from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkforge.facts import scan
from sparkforge.facts.scan import iter_source_files
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "airflow_dag@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "af.dag",
        "af.task",
        "af.dependency",
        "af.unresolved",
        "af.analyzed",
    }
)

# https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html
# wait_for_completion (default True): "Whether to wait for job run completion".
DEFAULT_WAIT_FOR_COMPLETION = True
# deferrable (default False): "If True, the operator will wait asynchronously for the
# job to complete".
DEFAULT_DEFERRABLE = False
# stop_job_run_on_kill (default False): "If True, Operator will stop the job run when
# task is killed".
DEFAULT_STOP_JOB_RUN_ON_KILL = False
# job_poll_interval (default 6). Nenhuma regra o julga; fica declarado porque o default
# publicado tem que morar ao lado da fonte que o publica.
DEFAULT_JOB_POLL_INTERVAL = 6
# https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html
# core.default_task_retries (default 0): "The number of retries each task is going to
# have by default".
DEFAULT_TASK_RETRIES = 0

_GLUE_OPERATORS = frozenset({"GlueJobOperator", "AwsGlueJobOperator"})
_TASKFLOW_DECORADORES = frozenset({"task", "dag", "task_group"})
_METODOS_DE_DEPENDENCIA = frozenset({"set_downstream", "set_upstream"})
_FUNCOES_DE_DEPENDENCIA = frozenset({"chain", "chain_linear", "cross_downstream"})
_BOOLEANOS_DO_GLUE = (
    ("wait_for_completion", DEFAULT_WAIT_FOR_COMPLETION),
    ("deferrable", DEFAULT_DEFERRABLE),
    ("stop_job_run_on_kill", DEFAULT_STOP_JOB_RUN_ON_KILL),
)
_SEGUNDOS_POR_UNIDADE = {
    "weeks": 604800,
    "days": 86400,
    "hours": 3600,
    "minutes": 60,
    "seconds": 1,
}

# Sentinela de "nao e literal". `None` nao serve: `x=None` e um valor que o DAG pode
# escrever, e confundir os dois faria o extrator afirmar leitura que nao houve.
_AUSENTE = object()


@dataclass
class _Tarefa:
    """O que se leu de UMA instanciacao de operador, antes de virar Fact.

    `has_downstream` so e conhecido depois de ler as dependencias, e por isso a
    tarefa espera aqui em vez de sair Fact na hora.
    """

    symbol: str
    var_name: str
    node: ast.AST
    attrs: dict[str, Any]
    measures: dict[str, Any]


@dataclass
class _Leitura:
    """O estado de UM arquivo sendo lido: onde, com que `default_args`, e o que saiu."""

    path: str
    provenance: dict[str, Any]
    facts: list[Fact] = field(default_factory=list)
    tarefas: list[_Tarefa] = field(default_factory=list)
    com_downstream: set[str] = field(default_factory=set)
    default_args: ast.Dict | None = None
    default_args_legivel: bool = True


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _node_subject(path: str, node: ast.AST, symbol: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": getattr(node, "lineno", 0),
        "col": getattr(node, "col_offset", 0),
        "symbol": symbol,
        "snippet": "",
    }


def _provenance(path: str, sha: str) -> dict[str, Any]:
    return {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}


def _unresolved(
    subject: dict[str, Any], reason: str, provenance: dict[str, Any], **extra: Any
) -> Fact:
    return Fact(
        kind="af.unresolved",
        subject=subject,
        attrs={"reason": reason, **extra},
        provenance=provenance,
    )


def _nome_chamado(node: ast.Call) -> str:
    """`GlueJobOperator(...)` e `glue.GlueJobOperator(...)` dao o mesmo nome curto."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _nome_decorador(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _nome_chamado(node)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _e_operador(nome: str) -> bool:
    return nome.endswith("Operator") or nome.endswith("Sensor")


def _literal(node: ast.AST | None) -> Any:
    """Valor quando o no e constante simples; `_AUSENTE` caso contrario."""
    if isinstance(node, ast.Constant) and isinstance(node.value, bool | int | float | str):
        return node.value
    return _AUSENTE


def _e_jinja(valor: Any) -> bool:
    """String com `{{ }}` e template do Airflow, resolvido em execucao -- nao e nome."""
    return isinstance(valor, str) and "{{" in valor and "}}" in valor


def _kwarg(node: ast.Call, nome: str) -> ast.AST | None:
    for kw in node.keywords:
        if kw.arg == nome:
            return kw.value
    return None


def _do_dict(no_dict: ast.Dict, chave: str) -> ast.AST | None:
    """Valor de uma chave literal num `ast.Dict`. Chave de `**spread` e `None`, e cai fora."""
    for chave_no, valor_no in zip(no_dict.keys, no_dict.values):
        if isinstance(chave_no, ast.Constant) and chave_no.value == chave:
            return valor_no
    return None


def _timedelta_segundos(node: ast.AST | None) -> int | None:
    """Segundos de `timedelta(**literais)`; `None` para qualquer outra forma.

    So palavras-chave, e so as unidades inteiras: `timedelta(2)` posicional e
    `milliseconds=...` ficam de fora de proposito -- a medida so existe quando e exata.
    """
    if not isinstance(node, ast.Call) or _nome_chamado(node) != "timedelta" or node.args:
        return None
    total = 0
    for kw in node.keywords:
        if kw.arg not in _SEGUNDOS_POR_UNIDADE:
            return None
        valor = _literal(kw.value)
        if isinstance(valor, bool) or not isinstance(valor, int):
            return None
        total += valor * _SEGUNDOS_POR_UNIDADE[kw.arg]
    return total


class _Escopo:
    """No -> profundidade de laco e se esta dentro de `def`.

    Pilha explicita e nao recursao, pelo mesmo motivo de `pyspark_ast._Context`: um
    modulo com expressao profunda estouraria o limite de pilha do interpretador.
    """

    def __init__(self, tree: ast.AST) -> None:
        self.loop_depth: dict[int, int] = {}
        self.in_function: dict[int, bool] = {}
        pilha: list[tuple[ast.AST, int, bool]] = [(tree, 0, False)]
        while pilha:
            node, profundidade, dentro = pilha.pop()
            self.loop_depth[id(node)] = profundidade
            self.in_function[id(node)] = dentro
            proxima = profundidade
            if isinstance(
                node,
                ast.For
                | ast.AsyncFor
                | ast.While
                | ast.ListComp
                | ast.SetComp
                | ast.DictComp
                | ast.GeneratorExp,
            ):
                proxima = profundidade + 1
            interna = dentro or isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            for filho in ast.iter_child_nodes(node):
                pilha.append((filho, proxima, interna))

    def dinamico(self, node: ast.AST) -> bool:
        """DAG ou operador montado em laco, comprehension ou funcao: fora do alcance."""
        return self.loop_depth.get(id(node), 0) > 0 or self.in_function.get(id(node), False)


def _alvos_de_atribuicao(tree: ast.AST) -> dict[int, str]:
    """`id` da chamada -> nome da variavel a que ela foi atribuida.

    As dependencias se referem as tasks pelo nome da VARIAVEL, nao pelo `task_id`.
    Cobre `x = Op(...)`, `x: T = Op(...)` e `with DAG(...) as x:`.
    """
    alvos: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if isinstance(node.value, ast.Call):
                    alvos[id(node.value)] = node.targets[0].id
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and isinstance(node.value, ast.Call):
                alvos[id(node.value)] = node.target.id
        elif isinstance(node, ast.withitem):
            if isinstance(node.context_expr, ast.Call) and isinstance(
                node.optional_vars, ast.Name
            ):
                alvos[id(node.context_expr)] = node.optional_vars.id
    return alvos


def _dicts_de_modulo(tree: ast.Module) -> dict[str, ast.Dict]:
    """Nome -> dicionario literal, para `NOME = {...}` no nivel de modulo.

    `default_args=DEFAULT_ARGS` e a forma comum, e ela e legivel por AST sem executar
    nada. So entra o nome atribuido UMA vez: reatribuido, nao se sabe qual valor vale.
    """
    contagem: dict[str, int] = {}
    valores: dict[str, ast.Dict] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        alvo = node.targets[0]
        if not isinstance(alvo, ast.Name):
            continue
        contagem[alvo.id] = contagem.get(alvo.id, 0) + 1
        if isinstance(node.value, ast.Dict):
            valores[alvo.id] = node.value
    return {nome: no for nome, no in valores.items() if contagem.get(nome) == 1}
```

Continuação do **mesmo arquivo** (a leitura do DAG, do operador e das dependências):

```python
def _le_dags(tree: ast.AST, leitura: _Leitura, escopo: _Escopo, alvos: dict[int, str],
             dicts: dict[str, ast.Dict]) -> None:
    """Emite um `af.dag` por chamada `DAG(...)` lida, e fixa o `default_args` do arquivo.

    Com DOIS ou mais DAGs no arquivo nao ha como dizer de qual deles vem o
    `default_args` de uma task: `default_args` fica ILEGIVEL para o arquivo inteiro e a
    lacuna sai como `multiplos_dags`. Adivinhar o primeiro seria afirmar heranca que
    ninguem leu.
    """
    blocos: list[ast.Dict | None] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _nome_chamado(node) != "DAG":
            continue
        var = alvos.get(id(node), "")
        if escopo.dinamico(node):
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, var),
                    "dag_dinamico",
                    leitura.provenance,
                    at="DAG",
                    unblocked_by="DAG declarado no nivel de modulo, fora de laco e de funcao",
                )
            )
            continue
        dag_id = _literal(_kwarg(node, "dag_id"))
        attrs: dict[str, Any] = {"dag_id_literal": isinstance(dag_id, str)}
        if isinstance(dag_id, str):
            attrs["dag_id"] = dag_id
        agenda_no, origem = _kwarg(node, "schedule"), "schedule"
        if agenda_no is None:
            agenda_no, origem = _kwarg(node, "schedule_interval"), "schedule_interval"
        agenda = _literal(agenda_no)
        attrs["schedule_declared"] = agenda_no is not None
        attrs["schedule_source"] = origem if agenda_no is not None else "absent"
        if isinstance(agenda, str):
            attrs["schedule"] = agenda
        bruto = _kwarg(node, "default_args")
        bloco: ast.Dict | None = None
        if bruto is None:
            attrs["default_args_source"] = "absent"
        elif isinstance(bruto, ast.Dict):
            bloco, attrs["default_args_source"] = bruto, "inline"
        elif isinstance(bruto, ast.Name) and bruto.id in dicts:
            bloco, attrs["default_args_source"] = dicts[bruto.id], "module_name"
        else:
            attrs["default_args_source"] = "unreadable"
        measures: dict[str, Any] = {}
        retries = _literal(_do_dict(bloco, "retries")) if bloco is not None else _AUSENTE
        attrs["default_retries_declared"] = isinstance(retries, int) and not isinstance(
            retries, bool
        )
        if attrs["default_retries_declared"]:
            measures["default_retries"] = retries
        prazo = _do_dict(bloco, "execution_timeout") if bloco is not None else None
        attrs["default_execution_timeout_declared"] = prazo is not None
        segundos = _timedelta_segundos(prazo)
        if segundos is not None:
            measures["default_execution_timeout_seconds"] = segundos
        leitura.facts.append(
            Fact(
                kind="af.dag",
                subject=_node_subject(
                    leitura.path, node, dag_id if isinstance(dag_id, str) else var
                ),
                measures=measures,
                attrs=attrs,
                provenance=leitura.provenance,
            )
        )
        blocos.append(bloco if attrs["default_args_source"] != "unreadable" else None)
        if attrs["default_args_source"] == "unreadable":
            leitura.default_args_legivel = False
    if len(blocos) > 1:
        leitura.default_args, leitura.default_args_legivel = None, False
        leitura.facts.append(
            _unresolved(
                _file_subject(leitura.path),
                "multiplos_dags",
                leitura.provenance,
                dag_count=len(blocos),
                unblocked_by="um DAG por arquivo, ou `default_args` declarado na propria task",
            )
        )
    elif blocos:
        leitura.default_args = blocos[0]


def _le_decoradores(tree: ast.AST, leitura: _Leitura) -> None:
    """`@dag`, `@task` e `@task_group`: reconhecidos e NOMEADOS, nunca lidos."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        nomes = sorted({_nome_decorador(d) for d in node.decorator_list})
        usados = [n for n in nomes if n in _TASKFLOW_DECORADORES]
        if not usados:
            continue
        leitura.facts.append(
            _unresolved(
                _node_subject(leitura.path, node, node.name),
                "taskflow_decorador",
                leitura.provenance,
                decorators=usados,
                unblocked_by="operador instanciado como classe, fora da TaskFlow API",
            )
        )


def _le_bool(chamada: ast.Call, nome: str, default: bool, attrs: dict[str, Any],
             leitura: _Leitura, subject: dict[str, Any]) -> None:
    """`<nome>_effective` mais `<nome>_defaulted`, ou o nao literal nomeado (D2)."""
    valor_no = _kwarg(chamada, nome)
    if valor_no is None:
        attrs[f"{nome}_effective"] = default
        attrs[f"{nome}_defaulted"] = True
        return
    valor = _literal(valor_no)
    if not isinstance(valor, bool):
        leitura.facts.append(
            _unresolved(
                subject,
                "arg_nao_literal",
                leitura.provenance,
                arg=nome,
                unblocked_by=f"`{nome}` escrito como `True` ou `False` literal na task",
            )
        )
        return
    attrs[f"{nome}_effective"] = valor
    attrs[f"{nome}_defaulted"] = False


def _le_job_name(chamada: ast.Call, attrs: dict[str, Any], leitura: _Leitura,
                 subject: dict[str, Any]) -> None:
    """So o literal liga a task ao `aws_glue_job` de mesmo nome (D5)."""
    valor_no = _kwarg(chamada, "job_name")
    if valor_no is None:
        attrs["job_name_source"] = "absent"
        return
    valor = _literal(valor_no)
    if isinstance(valor, str) and valor.strip() and not _e_jinja(valor):
        attrs["job_name"] = valor
        attrs["job_name_source"] = "literal"
        return
    attrs["job_name_source"] = "jinja" if _e_jinja(valor) else "nao_literal"
    leitura.facts.append(
        _unresolved(
            subject,
            "arg_nao_literal",
            leitura.provenance,
            arg="job_name",
            job_name_source=attrs["job_name_source"],
            unblocked_by="`job_name` escrito como string literal na task",
        )
    )


def _le_retries(chamada: ast.Call, attrs: dict[str, Any], measures: dict[str, Any],
                leitura: _Leitura, subject: dict[str, Any]) -> None:
    """`retries` da task, senao de `default_args`, senao o default publicado (0)."""
    valor_no, origem = _kwarg(chamada, "retries"), "task"
    if valor_no is None and leitura.default_args is not None:
        valor_no, origem = _do_dict(leitura.default_args, "retries"), "default_args"
    if valor_no is None:
        if not leitura.default_args_legivel:
            leitura.facts.append(
                _unresolved(
                    subject,
                    "arg_nao_literal",
                    leitura.provenance,
                    arg="retries",
                    at="default_args",
                    unblocked_by="`default_args` legivel: um DAG por arquivo, dicionario literal",
                )
            )
            return
        measures["retries_effective"] = DEFAULT_TASK_RETRIES
        attrs["retries_source"] = "default_publicado"
        attrs["retries_defaulted"] = True
        return
    valor = _literal(valor_no)
    if isinstance(valor, bool) or not isinstance(valor, int):
        leitura.facts.append(
            _unresolved(
                subject,
                "arg_nao_literal",
                leitura.provenance,
                arg="retries",
                at=origem,
                unblocked_by="`retries` escrito como inteiro literal",
            )
        )
        return
    measures["retries_effective"] = valor
    attrs["retries_source"] = origem
    attrs["retries_defaulted"] = False


def _le_execution_timeout(chamada: ast.Call, attrs: dict[str, Any],
                          measures: dict[str, Any], leitura: _Leitura,
                          subject: dict[str, Any]) -> None:
    """A DECLARACAO e o que a regra le; o valor so vira medida quando e exato."""
    valor_no, origem = _kwarg(chamada, "execution_timeout"), "task"
    if valor_no is None and leitura.default_args is not None:
        valor_no = _do_dict(leitura.default_args, "execution_timeout")
        origem = "default_args"
    if isinstance(valor_no, ast.Constant) and valor_no.value is None:
        valor_no = None  # `execution_timeout=None` e a AUSENCIA declarada de prazo
    if valor_no is None:
        if not leitura.default_args_legivel:
            leitura.facts.append(
                _unresolved(
                    subject,
                    "arg_nao_literal",
                    leitura.provenance,
                    arg="execution_timeout",
                    at="default_args",
                    unblocked_by="`default_args` legivel: um DAG por arquivo, dicionario literal",
                )
            )
            return
        attrs["execution_timeout_declared"] = False
        attrs["execution_timeout_source"] = "absent"
        return
    attrs["execution_timeout_declared"] = True
    attrs["execution_timeout_source"] = origem
    segundos = _timedelta_segundos(valor_no)
    if segundos is not None:
        measures["execution_timeout_seconds"] = segundos


def _le_operadores(tree: ast.AST, leitura: _Leitura, escopo: _Escopo,
                   alvos: dict[int, str]) -> None:
    """Uma `_Tarefa` por operador instanciado. O Fact so sai depois das dependencias."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        classe = _nome_chamado(node)
        if not _e_operador(classe):
            continue
        var = alvos.get(id(node), "")
        if escopo.dinamico(node):
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, var),
                    "dag_dinamico",
                    leitura.provenance,
                    at=classe,
                    unblocked_by="operador instanciado no nivel de modulo, fora de laco e de funcao",
                )
            )
            continue
        task_id = _literal(_kwarg(node, "task_id"))
        simbolo = task_id if isinstance(task_id, str) and task_id.strip() else var
        subject = _node_subject(leitura.path, node, simbolo)
        attrs: dict[str, Any] = {
            "operator_class": classe,
            "operator_family": "glue_job" if classe in _GLUE_OPERATORS else "",
            "task_id_literal": isinstance(task_id, str),
            "var_name": var,
        }
        if isinstance(task_id, str):
            attrs["task_id"] = task_id
        else:
            leitura.facts.append(
                _unresolved(
                    subject,
                    "task_id_nao_literal",
                    leitura.provenance,
                    operator_class=classe,
                    unblocked_by="`task_id` escrito como string literal",
                )
            )
        measures: dict[str, Any] = {}
        _le_retries(node, attrs, measures, leitura, subject)
        _le_execution_timeout(node, attrs, measures, leitura, subject)
        if attrs["operator_family"] == "glue_job":
            _le_job_name(node, attrs, leitura, subject)
            for nome, default in _BOOLEANOS_DO_GLUE:
                _le_bool(node, nome, default, attrs, leitura, subject)
            espera = _literal(_kwarg(node, "job_poll_interval"))
            if isinstance(espera, int) and not isinstance(espera, bool):
                measures["job_poll_interval"] = espera
        leitura.tarefas.append(
            _Tarefa(symbol=simbolo, var_name=var, node=node, attrs=attrs, measures=measures)
        )


def _elos(node: ast.BinOp, tipo: type[ast.AST]) -> list[ast.AST]:
    """`a >> b >> c` e `BinOp(BinOp(a,b),c)`: devolve [a, b, c], com `while`, nao recursao."""
    saida: list[ast.AST] = []
    atual: ast.AST = node
    while isinstance(atual, ast.BinOp) and isinstance(atual.op, tipo):
        saida.append(atual.right)
        atual = atual.left
    saida.append(atual)
    saida.reverse()
    return saida


def _nomes_do_lado(node: ast.AST) -> list[str] | None:
    """Nomes de variavel de um lado do elo, ou `None` quando nao e legivel."""
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.List | ast.Tuple):
        nomes: list[str] = []
        for elemento in node.elts:
            if not isinstance(elemento, ast.Name):
                return None
            nomes.append(elemento.id)
        return nomes
    return None


def _emite_elo(leitura: _Leitura, mapa: dict[str, str], acima: ast.AST, abaixo: ast.AST,
               forma: str, node: ast.AST) -> None:
    ups, downs = _nomes_do_lado(acima), _nomes_do_lado(abaixo)
    if ups is None or downs is None:
        leitura.facts.append(
            _unresolved(
                _node_subject(leitura.path, node, ""),
                "dependencia_dinamica",
                leitura.provenance,
                form=forma,
                unblocked_by="elo entre variaveis de task, nao montado em laco nem por lista dinamica",
            )
        )
        return
    for acima_var in ups:
        for abaixo_var in downs:
            resolvido = acima_var in mapa and abaixo_var in mapa
            um = mapa.get(acima_var, acima_var)
            outro = mapa.get(abaixo_var, abaixo_var)
            leitura.facts.append(
                Fact(
                    kind="af.dependency",
                    subject=_node_subject(leitura.path, node, f"{um} >> {outro}"),
                    attrs={
                        "upstream": um,
                        "downstream": outro,
                        "upstream_var": acima_var,
                        "downstream_var": abaixo_var,
                        "form": forma,
                        "resolved": resolvido,
                    },
                    provenance=leitura.provenance,
                )
            )
            if resolvido:
                leitura.com_downstream.add(um)


def _le_dependencias(tree: ast.AST, leitura: _Leitura, escopo: _Escopo) -> None:
    """As quatro formas declaradas, mais o que nao se le, nomeado.

    So `>>` e `<<` no NIVEL DE INSTRUCAO (`ast.Expr`): um `>>` dentro de outra
    expressao nao e declaracao de dependencia, e o de dentro de um laco cai em
    `dependencia_dinamica` pelo escopo.
    """
    mapa = {t.var_name: t.symbol for t in leitura.tarefas if t.var_name}
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.BinOp):
            operacao = node.value.op
            if not isinstance(operacao, ast.RShift | ast.LShift):
                continue
            if escopo.dinamico(node):
                leitura.facts.append(
                    _unresolved(
                        _node_subject(leitura.path, node, ""),
                        "dependencia_dinamica",
                        leitura.provenance,
                        form="rshift" if isinstance(operacao, ast.RShift) else "lshift",
                        unblocked_by="elo declarado fora de laco, entre variaveis de task",
                    )
                )
                continue
            direita = isinstance(operacao, ast.RShift)
            elos = _elos(node.value, ast.RShift if direita else ast.LShift)
            forma = "rshift" if direita else "lshift"
            for indice in range(len(elos) - 1):
                primeiro, segundo = elos[indice], elos[indice + 1]
                acima, abaixo = (primeiro, segundo) if direita else (segundo, primeiro)
                _emite_elo(leitura, mapa, acima, abaixo, forma, node)
            continue
        if not isinstance(node, ast.Call):
            continue
        nome = _nome_chamado(node)
        if nome in _FUNCOES_DE_DEPENDENCIA and not isinstance(node.func, ast.Attribute):
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, ""),
                    "dependencia_dinamica",
                    leitura.provenance,
                    form=nome,
                    unblocked_by="elo declarado por `>>`, `<<`, `set_downstream` ou `set_upstream`",
                )
            )
            continue
        if nome not in _METODOS_DE_DEPENDENCIA or not isinstance(node.func, ast.Attribute):
            continue
        if escopo.dinamico(node) or len(node.args) != 1:
            leitura.facts.append(
                _unresolved(
                    _node_subject(leitura.path, node, ""),
                    "dependencia_dinamica",
                    leitura.provenance,
                    form=nome,
                    unblocked_by="chamada com um argumento so, fora de laco",
                )
            )
            continue
        alvo, outro = node.func.value, node.args[0]
        acima, abaixo = (alvo, outro) if nome == "set_downstream" else (outro, alvo)
        _emite_elo(leitura, mapa, acima, abaixo, nome, node)


def _emite_tarefas(leitura: _Leitura) -> None:
    """Agora que as dependencias foram lidas, `has_downstream` e conhecido."""
    for tarefa in leitura.tarefas:
        attrs = {**tarefa.attrs, "has_downstream": tarefa.symbol in leitura.com_downstream}
        leitura.facts.append(
            Fact(
                kind="af.task",
                subject=_node_subject(leitura.path, tarefa.node, tarefa.symbol),
                measures=dict(tarefa.measures),
                attrs=attrs,
                provenance=leitura.provenance,
            )
        )


def _finish(facts: list[Fact], path: str, provenance: dict[str, Any]) -> list[Fact]:
    """Sentinela, guarda de namespace e ordenacao -- o mesmo fecho em todo caminho."""
    facts.append(
        Fact(
            kind="af.analyzed",
            subject=_file_subject(path),
            measures={
                "dag_count": sum(1 for f in facts if f.kind == "af.dag"),
                "task_count": sum(1 for f in facts if f.kind == "af.task"),
                "dependency_count": sum(1 for f in facts if f.kind == "af.dependency"),
                "unresolved_count": sum(1 for f in facts if f.kind == "af.unresolved"),
            },
            provenance=provenance,
        )
    )
    desconhecidos = {f.kind for f in facts} - EMITTED_KINDS
    if desconhecidos:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(desconhecidos)}")
    return sort_facts(facts)


def extract_airflow_dag(source: str, path: str, artifact_sha256: str = "") -> list[Fact]:
    """Extrai Facts do TEXTO de um DAG. `path` e ancora e procedencia.

    `ast.parse` levanta `SyntaxError` para Python invalido, `ValueError` para fonte com
    byte nulo e `RecursionError`/`MemoryError` para aninhamento extremo -- o parser do
    CPython usa "Parser stack overflowed" em vez de `RecursionError` conforme a versao,
    e os dois significam a mesma coisa para o operador. Os quatro viram
    `af.unresolved`, nunca excecao que derruba quem chamou.
    """
    provenance = _provenance(path, artifact_sha256)
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        falha = _unresolved(
            {
                "type": "source_location",
                "file": path,
                "line": exc.lineno or 0,
                "col": exc.offset or 0,
                "symbol": "",
                "snippet": "",
            },
            "invalid_python",
            provenance,
            detail=str(exc.msg),
        )
        return _finish([falha], path, provenance)
    except (ValueError, RecursionError, MemoryError) as exc:
        falha = _unresolved(
            _file_subject(path), "invalid_python", provenance, detail=str(exc)
        )
        return _finish([falha], path, provenance)
    leitura = _Leitura(path=path, provenance=provenance)
    try:
        escopo = _Escopo(tree)
        alvos = _alvos_de_atribuicao(tree)
        _le_dags(tree, leitura, escopo, alvos, _dicts_de_modulo(tree))
        _le_decoradores(tree, leitura)
        _le_operadores(tree, leitura, escopo, alvos)
        _le_dependencias(tree, leitura, escopo)
        _emite_tarefas(leitura)
    except (RecursionError, MemoryError) as exc:
        falha = _unresolved(_file_subject(path), "read_error", provenance, detail=str(exc))
        return _finish([falha], path, provenance)
    return _finish(leitura.facts, path, provenance)


def extract_airflow_dag_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um arquivo `.py`, ancorando o caminho relativo a `repo_root`.

    Arquivo acima do teto de `scan._teto_para` -- o MESMO que a varredura aplica -- sai
    `size_above_limit`; falha ao abrir ou a decodificar, `read_error`. Le com
    `utf-8-sig`: sem isso um DAG salvo com BOM falharia o parse e seria reportado como
    ponto cego por engano.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    vazio = _provenance(anchor, "")
    try:
        tamanho, teto = path.stat().st_size, scan._teto_para(path)
        if tamanho > teto:
            falha = _unresolved(
                _file_subject(anchor), "size_above_limit", vazio, size=tamanho, limit=teto
            )
            return _finish([falha], anchor, vazio)
        texto = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
        return _finish([falha], anchor, vazio)
    sha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    return extract_airflow_dag(texto, anchor, artifact_sha256=sha)


def extract_airflow_dag_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todo `*.py` sob `root`, em ordem deterministica de caminho.

    Falha por arquivo nao e fatal: vira `af.unresolved` daquele arquivo e a travessia
    continua.
    """
    facts: list[Fact] = []
    for arquivo in iter_source_files(root, "*.py"):
        rel = str(arquivo.relative_to(repo_root)) if repo_root else str(arquivo)
        anchor = rel.replace("\\", "/")
        try:
            facts.extend(extract_airflow_dag_path(arquivo, repo_root))
        except Exception as exc:  # qualquer falha por arquivo vira Fact, nunca propaga
            vazio = _provenance(anchor, "")
            falha = _unresolved(_file_subject(anchor), "read_error", vazio, detail=str(exc))
            facts.extend(_finish([falha], anchor, vazio))
    return sort_facts(facts)


__all__ = [
    "DEFAULT_DEFERRABLE",
    "DEFAULT_JOB_POLL_INTERVAL",
    "DEFAULT_STOP_JOB_RUN_ON_KILL",
    "DEFAULT_TASK_RETRIES",
    "DEFAULT_WAIT_FOR_COMPLETION",
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "extract_airflow_dag",
    "extract_airflow_dag_path",
    "extract_airflow_dag_tree",
]
```

Sem função aninhada (duas `def` de mesmo nome no mesmo escopo quebram
`tests/test_codeintel_security.py::TestInv001`), sem `Path.glob`/`rglob` (é
`tests/test_facts_scan.py`), sem API de Python 3.11+ (o CI roda 3.10) — `X | Y` dentro
de `isinstance` existe desde a 3.10, e `datetime.UTC` não aparece aqui.

### 4. Rodar e ver passar

```bash
git add sparkforge/facts/airflow_dag.py
python -m pytest tests/test_airflow_dag.py -q
```

Três testes verdes. Os dois primeiros são o `verified_by` de AC1 e AC2.

### 5. Gates vizinhos

Extrator (`docs/gates-por-mudanca.md`, "Acrescentar ou alterar um EXTRATOR de facts") —
o módulo ainda **não** entra nas duas listas manuais: entra em T3, no mesmo commit do
golden e da área. Um comando por vez:

```bash
python -m ruff check sparkforge/facts/airflow_dag.py tests/test_airflow_dag.py
python -m pytest tests/test_rules_catalog_reachability.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_facts_scan.py tests/test_harness_untrusted.py tests/test_databricks_rule_audit.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py -q
```

`test_harness_untrusted.py` roda `extract_airflow_dag_tree` sobre todo domínio de
`fixtures/` (a medida de snippet): o módulo tem `*_tree`, então é exercitado sem entrada
em `_derivados_de_facts`, e nenhum fact dele carrega `snippet` — `EXTRATORES_COM_SNIPPET`
não muda.

Números (tabela *Números correntes* e prosa auditada). `docs/superpowers/STATUS.md`,
duas trocas de prefixo de linha (o resto de cada linha fica como está). Antes → depois:

```text
| Extratores de facts | **39** —
| Extratores de facts | **40** — `airflow_dag.py` é o quadragésimo (2026-09-20, feature `docs/sdd/AIRFLOW_DAG/`): o segundo que lê quem DISPARA o job Glue, e o primeiro que lê um artefato que não é da AWS — o arquivo `.py` do DAG do Apache Airflow, por AST e sem nunca executá-lo. Leitura anterior de **39** —
```

```text
| Fact kinds distintos emitidos | **233** —
| Fact kinds distintos emitidos | **238** — os cinco `af.*` do extrator de DAG (2026-09-20, feature `docs/sdd/AIRFLOW_DAG/`): `af.dag`, `af.task`, `af.dependency`, `af.unresolved` e `af.analyzed`. Leitura anterior de **233** —
```

- `README.md` linha 45: `Os 39 extratores emitem 233 kinds distintos` →
  `Os 40 extratores emitem 238 kinds distintos`.
- `docs/guia/06-extrair-julgar-compor.md`: linha 86,
  `Os 39 extratores emitem 233 kinds distintos de fact (recontado em 2026-09-19),` →
  `Os 40 extratores emitem 238 kinds distintos de fact (recontado em 2026-09-20),`;
  linha 232, `nenhum dos 233 kinds a nomeia` → `nenhum dos 238 kinds a nomeia`.

(São **238** e não 239 nesta tarefa: `af.glue_job_link` entra em T3. Confira com o gate.)

```bash
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

O gate de lastro reprova as alegações de corpus de `.py` — **dois arquivos novos aqui**,
e mais dez em T3 (os DAGs de fixture). Medido nesta árvore antes de começar:
`iter_source_files(raiz, "*.py")` entrega **756** arquivos, e as alegações que dependem
disso estão em `docs/harness/CODEINTEL-GAP.md` (`VNX-640` traz o 756; `VNX-666`,
`VNX-671`, `VNX-674` e `VNX-737` trazem os bytes derivados dele). **Remedie pelos ids que
a saída do gate listar**, número no documento e em `docs/claims.lock.json`, e rode o gate
de novo até `exit 0`. Nunca por varredura.

### 6. Commit

`feat(facts): read Airflow DAG files into af.* facts, by AST and never by import`

Arquivos: `sparkforge/facts/airflow_dag.py`, `tests/test_airflow_dag.py`,
`docs/superpowers/STATUS.md`, `README.md`, `docs/guia/06-extrair-julgar-compor.md`,
`docs/harness/CODEINTEL-GAP.md`, `docs/claims.lock.json`.

## T2 — verbo `analyze airflow-dag` e tool `sparkforge_analyze_airflow_dag`

### 1. Teste que falha

Acrescente ao fim de `tests/test_airflow_dag.py`:

```python
def test_cli_e_tool_devolvem_os_mesmos_facts(tmp_path, capsys):
    from sparkforge.adapters.cli import main
    from sparkforge.adapters.tools import call_tool

    entrada = tmp_path / "dags"
    entrada.mkdir()
    (entrada / "carga_diaria.py").write_text(DAG_COM_TRES_TASKS, encoding="utf-8")
    saida = tmp_path / "facts.json"

    codigo = main(["analyze", "airflow-dag", "--path", str(entrada), "--out", str(saida)])
    capsys.readouterr()
    assert codigo == 0
    pela_cli = json.loads(saida.read_text(encoding="utf-8"))

    pela_tool = call_tool("sparkforge_analyze_airflow_dag", {"path": str(entrada), "limit": 1000})
    assert "error" not in pela_tool, pela_tool
    assert pela_tool["total_count"] == len(pela_cli)
    assert pela_tool["items"] == pela_cli
    assert pela_tool["by_kind"]["af.task"] == 3
    assert pela_tool["by_kind"]["af.dependency"] == 2
    assert pela_tool["unresolved"] == 1

    erro = call_tool("sparkforge_analyze_airflow_dag", {"path": str(tmp_path / "nao-existe")})
    assert "sparkforge analyze airflow-dag" in erro["error"]
```

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_airflow_dag.py::test_cli_e_tool_devolvem_os_mesmos_facts -q
```

Falha esperada: `SystemExit: 2` do argparse (`invalid choice: 'airflow-dag'`).

### 3. Código mínimo

**`sparkforge/adapters/_core.py`** — import. Troque

```python
from sparkforge.facts import lakeformation_matrix as _lf_matrix
from sparkforge.facts.athena_workgroup import (
```

por

```python
from sparkforge.facts import lakeformation_matrix as _lf_matrix
from sparkforge.facts.airflow_dag import (
    extract_airflow_dag_path,
    extract_airflow_dag_tree,
)
from sparkforge.facts.athena_workgroup import (
```

E a função pública, logo depois de `analyze_step_functions`. Troque

```python
    facts = _extract_step_functions_facts(path)
    return _facts_page(facts, "sfn.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# benchmark
```

por

```python
    facts = _extract_step_functions_facts(path)
    return _facts_page(facts, "sfn.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# analyze airflow-dag
# --------------------------------------------------------------------------- #
#
# Le o ARQUIVO `.py` do DAG, por AST, e NUNCA o importa nem o executa (D1 de
# `docs/sdd/AIRFLOW_DAG/design.md`). Nao ha `collect` par e a ausencia e decidida: o
# metadado do Airflow em execucao (task instances, duracao, retentativas que
# aconteceram) exige acesso ao banco ou a API, e esta fora de escopo no `define`.


def _extract_airflow_dag_facts(path: str) -> list[Fact]:
    target = Path(path)
    if not target.exists():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para o arquivo .py do DAG ou para a pasta de DAGs:\n"
            f"    sparkforge analyze airflow-dag --path dags/ "
            f"--out .sparkforge/facts_airflow.json",
            exit_code=2,
        )
    if target.is_dir():
        return extract_airflow_dag_tree(target, repo_root=target)
    return extract_airflow_dag_path(target, repo_root=target.parent)


def analyze_airflow_dag(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    facts = _extract_airflow_dag_facts(path)
    return _facts_page(facts, "af.unresolved", kind, limit, cursor, detail_level)


# --------------------------------------------------------------------------- #
# benchmark
```

**`sparkforge/adapters/cli.py`** — subcomando. Troque

```python
    _add_detail_level(sfn_analyze_p)

    dq_p = analyze_sub.add_parser(
```

por

```python
    _add_detail_level(sfn_analyze_p)

    af_analyze_p = analyze_sub.add_parser(
        "airflow-dag",
        help="Extrai facts do arquivo .py de um DAG do Apache Airflow, lido por AST e "
        "NUNCA executado: um fact por operador instanciado, com classe, task_id, os "
        "argumentos literais que as regras julgam (job_name, wait_for_completion, "
        "deferrable, stop_job_run_on_kill, retries, execution_timeout), as dependencias "
        "declaradas, e a marca do que nao e literal.",
    )
    af_analyze_p.add_argument(
        "--path",
        required=True,
        help="Arquivo .py do DAG ou diretorio com eles (a pasta de DAGs).",
    )
    af_analyze_p.add_argument(
        "--out", help="Escreve a lista completa de facts (JSON) neste arquivo."
    )
    af_analyze_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    af_analyze_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    af_analyze_p.add_argument("--cursor")
    _add_detail_level(af_analyze_p)

    dq_p = analyze_sub.add_parser(
```

Handler: troque

```python
def _cmd_analyze_step_functions(args: argparse.Namespace) -> int:
```

por

```python
def _cmd_analyze_airflow_dag(args: argparse.Namespace) -> int:
    full = _core.analyze_airflow_dag(args.path, kind=args.kind, limit=None)
    return _emit_facts_page(full, args)


def _cmd_analyze_step_functions(args: argparse.Namespace) -> int:
```

Despacho: troque

```python
    ("analyze", "step-functions"): _cmd_analyze_step_functions,
```

por

```python
    ("analyze", "step-functions"): _cmd_analyze_step_functions,
    ("analyze", "airflow-dag"): _cmd_analyze_airflow_dag,
```

**`sparkforge/adapters/tools.py`** — declaração. Troque

```python
    "sparkforge_analyze_data_quality": {
        "description": (
```

por

```python
    "sparkforge_analyze_airflow_dag": {
        "description": (
            "Extrai facts do arquivo `.py` de um DAG do Apache Airflow. Le por AST e "
            "NUNCA importa nem executa o DAG. Emite `af.dag` (dag_id e schedule quando "
            "literais, e o `default_args` com `retries` e `execution_timeout`), um "
            "`af.task` por operador instanciado (classe, `task_id`, e para o "
            "`GlueJobOperator` o `job_name` literal, o EFETIVO de "
            "`wait_for_completion`/`deferrable`/`stop_job_run_on_kill` com a marca de "
            "omitido -- os defaults publicados sao True, False e False --, o `retries` "
            "efetivo e se `execution_timeout` esta declarado), `af.dependency` por elo "
            "declarado com `>>`, `<<`, `set_downstream` ou `set_upstream`, "
            "`af.unresolved` com a razao do que nao deu para ler (argumento nao literal, "
            "DAG montado em laco, TaskFlow, Python invalido), e a sentinela "
            "`af.analyzed`. Argumento que nao e literal NAO vira o default: o atributo "
            "sai ausente e a lacuna sai nomeada. Com o Terraform do job no mesmo pool, "
            "`sparkforge_fuse` liga a task ao `aws_glue_job` de mesmo nome."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Arquivo .py do DAG ou diretorio com eles.",
                },
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "detail_level": {
                    "type": "string",
                    "enum": list(_core.NIVEIS_DE_DETALHE),
                    "description": _DETAIL_LEVEL_DESC,
                },
            },
        },
        "outputSchema": _may_fail(
            _ANALYZE_FACTS_SCHEMA,
            "Facts extraidos, ou erro se o path nao existe.",
        ),
        "annotations": _READ_ONLY,
    },
    "sparkforge_analyze_data_quality": {
        "description": (
```

Handler: troque

```python
def _h_analyze_data_quality(args: dict[str, Any]) -> dict[str, Any]:
```

por

```python
def _h_analyze_airflow_dag(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_airflow_dag(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit", _core.DEFAULT_LIMIT),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )


def _h_analyze_data_quality(args: dict[str, Any]) -> dict[str, Any]:
```

Despacho: troque

```python
    "sparkforge_analyze_step_functions": _h_analyze_step_functions,
```

por

```python
    "sparkforge_analyze_step_functions": _h_analyze_step_functions,
    "sparkforge_analyze_airflow_dag": _h_analyze_airflow_dag,
```

**Registros da superfície, no mesmo commit:**

`tests/test_adapters_tools.py`:

- lista literal de `TestToolSurface`: troque

```python
            "sparkforge_analyze_step_functions",
            "sparkforge_analyze_data_quality",
```

por

```python
            "sparkforge_analyze_step_functions",
            "sparkforge_analyze_airflow_dag",
            "sparkforge_analyze_data_quality",
```

- amostra real: troque `_CONSUMER_INVENTORY = """consumers:` por

```python
# DAG com um GlueJobOperator: rende `af.task` com os campos que as regras SF-AIRFLOW
# leem, e nao so a sentinela que sai de qualquer `.py`.
_AIRFLOW_DAG_SOURCE = '''from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(dag_id="carga", schedule="@daily", start_date=datetime(2026, 1, 1)) as dag:
    carga = GlueJobOperator(task_id="carga", job_name="carga-diaria")
'''

_CONSUMER_INVENTORY = """consumers:
```

- construtor de `_real_output_for`: troque `    if name == "sparkforge_analyze_data_quality":` por

```python
    if name == "sparkforge_analyze_airflow_dag":
        dag_path = tmp_path / "carga_diaria.py"
        dag_path.write_text(_AIRFLOW_DAG_SOURCE, encoding="utf-8")
        resultado = call_tool("sparkforge_analyze_airflow_dag", {"path": str(dag_path)})
        assert resultado["by_kind"].get("af.task") == 1, resultado["by_kind"]
        return resultado

    if name == "sparkforge_analyze_data_quality":
```

- `FAILABLE`: troque

```python
        ("sparkforge_analyze_step_functions", {"path": "<tmp>/inexistente"}),
```

por

```python
        ("sparkforge_analyze_step_functions", {"path": "<tmp>/inexistente"}),
        ("sparkforge_analyze_airflow_dag", {"path": "<tmp>/inexistente"}),
```

`tests/test_harness_authorization.py`: troque

```python
        # 98 -> 99 com `analyze_step_functions` (2026-09-19, `docs/sdd/STEP_FUNCTIONS/`):
        # `_READ_ONLY`, le a definicao ASL em disco e declara `path`.
        assert len(TOOLS) - len(sem_caminho) == 99
```

por

```python
        # 98 -> 99 com `analyze_step_functions` (2026-09-19, `docs/sdd/STEP_FUNCTIONS/`):
        # `_READ_ONLY`, le a definicao ASL em disco e declara `path`.
        # 99 -> 100 com `analyze_airflow_dag` (2026-09-20, `docs/sdd/AIRFLOW_DAG/`):
        # `_READ_ONLY`, le o arquivo .py do DAG em disco e declara `path`.
        assert len(TOOLS) - len(sem_caminho) == 100
```

`parity.yaml`: logo depois do bloco `- name: extract facts from an AWS Step Functions
state machine definition` (termina em `copilot_ci: [cli, files]`, antes de
`- name: diff component versions between two runtime releases`), acrescente:

```yaml
  # O arquivo `.py` do DAG e codigo-fonte, como a definicao ASL da capacidade acima.
  # NAO HA `collect` PAR, e a ausencia e decidida (D1 de `docs/sdd/AIRFLOW_DAG/design.md`):
  # o metadado do Airflow em execucao exige acesso ao banco ou a API, e o `define` o poe
  # fora de escopo. O bloco `knowledge:` entra na T4, com o documento.
  - name: extract facts from an Apache Airflow DAG file
    tools: [sparkforge_analyze_airflow_dag]
    cli: [analyze airflow-dag]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]

```

`manifest.json`: troque

```json
    "sparkforge_analyze_step_functions",
```

por

```json
    "sparkforge_analyze_step_functions",
    "sparkforge_analyze_airflow_dag",
```

`agents/glue-infra-reviewer.md` (senão `test_no_tool_is_orphan` reprova): troque

```markdown
## Três armadilhas que a infraestrutura esconde
```

por

```markdown
## Quem dispara o job: Airflow

Quando quem chama o job é um DAG do Apache Airflow, `sparkforge_analyze_airflow_dag` lê
o arquivo `.py` por AST — **nunca o importa nem o executa** — e devolve um `af.task` por
operador instanciado. Para o `GlueJobOperator`, três defaults decidem o que acontece com
o job e nenhum aparece no código PySpark nem no event log: `wait_for_completion` (default
`True`), `deferrable` (default `False`) e `stop_job_run_on_kill` (default `False`). O
fact traz o valor efetivo e a marca de omitido; argumento que não é literal (variável,
f-string, `{{ jinja }}`) sai ausente e a lacuna sai nomeada em `af.unresolved`, nunca
como o default.

## Três armadilhas que a infraestrutura esconde
```

Espelhos: backup do `.claude/agents/README.md`, `python scripts/sync_skills.py`, devolva
o README. E **à mão**, `.codex/agents/glue-infra-reviewer.toml`: a mesma seção, no mesmo
lugar do `developer_instructions` (antes da linha
`## Três armadilhas que a infraestrutura esconde`).

`docs/guia/06-extrair-julgar-compor.md`, tabela de verbos: depois da linha que começa com
`| **Definição ASL do AWS Step Functions** | \`analyze step-functions\` |`, acrescente:

```markdown
| **Arquivo `.py` de um DAG do Apache Airflow** | `analyze airflow-dag` | o DAG lido por AST e nunca executado: um fact por operador instanciado, com os argumentos literais que decidem se o fluxo espera o job, se o mata junto com a task e se segura o worker, mais as dependências declaradas. Com o Terraform do job no mesmo pool, `fuse` liga a task ao `aws_glue_job` |
```

`tests/test_fixtures_golden_mcp_parity.py`: o SDK `mcp` está instalado nesta máquina,
então `test_toda_tool_nova_esta_declarada` roda. Troque

```python
    "sparkforge_analyze_step_functions": "2026-09-19: definicao ASL do AWS Step Functions",
}
```

por

```python
    "sparkforge_analyze_step_functions": "2026-09-19: definicao ASL do AWS Step Functions",
    "sparkforge_analyze_airflow_dag": "2026-09-20: arquivo .py de um DAG do Apache Airflow",
}
```

Referência e superfície:

```bash
python scripts/gen_reference_docs.py
python scripts/check_surface_lock.py --update
```

O primeiro reescreve `docs/guia/referencia/tools/README.md`, cria
`docs/guia/referencia/tools/sparkforge_analyze_airflow_dag.md`, e reescreve também
`docs/guia/referencia/cli/analyze.md` e
`docs/guia/referencia/agents/glue-infra-reviewer.md`. O segundo imprime o crescimento em
bytes: copie-o para o corpo do commit (regra 26).

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_airflow_dag.py -q
python -m pytest tests/test_adapters_tools.py -q
```

### 5. Gates vizinhos

"Acrescentar ou alterar tool, verbo de CLI, agent ou skill: a referência gerada" e
"Alterar agent, skill ou seus espelhos", um comando por vez:

```bash
python -m pytest tests/test_reference_docs.py tests/test_surface_lock.py -q
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_agent_coverage.py tests/test_docs_coverage.py -q
python -m pytest tests/test_harness_authorization.py tests/test_capability_parity.py tests/test_adapters_code_surface.py tests/test_mcp_modern_era.py -q
python -m pytest tests/test_fixtures_golden_mcp_parity.py -q
python -m ruff check sparkforge/adapters tests/test_airflow_dag.py tests/test_adapters_tools.py tests/test_harness_authorization.py
```

(backup e devolução do `.claude/agents/README.md` em volta do sync e de
`test_agents_parity.py`.)

Números. `docs/superpowers/STATUS.md`, antes → depois:

```text
| Tools MCP | **107** —
| Tools MCP | **108** — a **108ª** é `sparkforge_analyze_airflow_dag` (2026-09-20, feature `docs/sdd/AIRFLOW_DAG/`): lê o arquivo `.py` de um DAG do Apache Airflow por AST, é `_READ_ONLY` e declara `path`. Leitura anterior de **107** —
```

`README.md` linha 111: `**107 tools MCP**` → `**108 tools MCP**`.

Prosa que `check_status_numbers.py` audita:

- `GUIA_DE_USO.md` linha 237: `as 107 tools fazem (recontado em 2026-09-19)` →
  `as 108 tools fazem (recontado em 2026-09-20)`;
- `.devin/README.md` linha 31: `**107 tools** por stdio (recontado em 2026-09-19)` →
  `**108 tools** por stdio (recontado em 2026-09-20)`;
- `AGENTS.md` linha 143: ``**107 tools, 39 with `detail_level`** (recounted 2026-09-19)``
  → ``**108 tools, 40 with `detail_level`** (recounted 2026-09-20)``;
- `CLAUDE.md` linha 144: ``**107 tools, 39 com `detail_level`** (recontado em 2026-09-19)``
  → ``**108 tools, 40 com `detail_level`** (recontado em 2026-09-20)``. A tool nova aceita
  `detail_level`, e a medida é por assinatura (`_tools_com_detail_level`).

```bash
python scripts/check_status_numbers.py --strict
python -m pytest tests/test_status_numbers_gate.py tests/test_bootstrap_budget.py -q
python scripts/check_vnext_claims.py
```

`len(TOOLS)` move alegações de `docs/harness/`, lidas nesta árvore:
`AUTHORIZATION-CHAIN.md` (linhas 80, 196, 278 e 324: "107 tools" e "**99** de 107"),
`CURRENT-HARNESS-GAP.md` (linhas 42 e 107) e `CODEINTEL-GAP.md` (linha 305,
`detail_level` em 41 das 107). Remedie **pelos ids da saída do gate** — número no
documento e no `docs/claims.lock.json` — até `exit 0`.

### 6. Commit

`feat(cli,mcp): add the analyze airflow-dag verb and its MCP tool`, com o crescimento da
superfície em bytes no corpo.

## T3 — a área `SF-AIRFLOW`: quatro regras, a derivação em `fuse`, a rota, o corpus e o golden

### 1. Testes que falham, e o corpus

**1a.** Acrescente ao fim de `tests/test_airflow_dag.py`:

```python
TF_CARGA_DIARIA = """resource "aws_glue_job" "carga_diaria" {
  name        = "carga-diaria"
  role_arn    = aws_iam_role.glue_role.arn
  max_retries = 2
}
"""

RUNTIME_GLUE = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}

DAG_PAREADO = '''
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="cargas",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    default_args={"retries": 2},
) as dag:
    ligada = GlueJobOperator(
        task_id="ligada", job_name="carga-diaria", deferrable=True
    )
    dinamica = GlueJobOperator(
        task_id="dinamica", job_name="{{ var.value.job }}", deferrable=True
    )
    sem_definicao = GlueJobOperator(
        task_id="sem_definicao", job_name="job-que-nao-esta-no-terraform", deferrable=True
    )
'''


def test_fuse_liga_a_task_ao_job_e_nomeia_o_que_nao_liga(tmp_path):
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.terraform import extract_terraform_tree
    from sparkforge.rules.engine import judge
    from sparkforge.rules.loader import load_catalog

    (tmp_path / "cargas.py").write_text(DAG_PAREADO, encoding="utf-8")
    (tmp_path / "main.tf").write_text(TF_CARGA_DIARIA, encoding="utf-8")
    so_dag = extract_airflow_dag_tree(tmp_path, repo_root=tmp_path)
    so_tf = extract_terraform_tree(tmp_path, repo_root=tmp_path)

    fundidos = fuse(so_dag + so_tf)

    [link] = [f for f in fundidos if f.kind == "af.glue_job_link"]
    assert link.subject["symbol"] == "ligada"
    assert link.attrs["resource"] == "aws_glue_job.carga_diaria"
    assert link.attrs["job_name"] == "carga-diaria"
    assert link.attrs["glue_max_retries_source"] == "literal"
    assert link.measures == {"airflow_retries_effective": 2, "glue_max_retries": 2}
    assert len(link.provenance["derived_from"]) == 3

    motivos = {
        f.subject["symbol"]: f.attrs["reason"]
        for f in fundidos
        if f.kind == "af.unresolved" and f.attrs["reason"] != "arg_nao_literal"
    }
    assert motivos == {
        "dinamica": "job_name_dynamic",
        "sem_definicao": "job_definition_absent",
    }

    achados = judge(fundidos, load_catalog(), RUNTIME_GLUE)
    quatro = [a.subject["symbol"] for a in achados if a.rule_id == "SF-AIRFLOW-004"]
    assert quatro == ["ligada"]

    # fuse sem Terraform no pool nao inventa vinculo
    assert not [f for f in fuse(so_dag) if f.kind == "af.glue_job_link"]
    # e pool sem Airflow sai do fuse sem nenhum af.*
    assert not [f for f in fuse(so_tf) if f.kind.startswith("af.")]
```

**1b.** `tests/test_fixtures_golden_airflow.py` (arquivo novo, com a linha **literal**
que `tests/test_fixtures_kind_coverage.py` casa por regex):

```python
"""Golden do corpus de DAG do Apache Airflow (`fixtures/airflow/`).

Cada fixture e sintetica, montada a partir dos exemplos da documentacao do provider
Amazon: nenhum DAG real foi observado (U2 de `docs/sdd/AIRFLOW_DAG/define.md`).

A EXTRACAO SEGUE O CAMINHO DO PRODUTO. Fixture so com `.py` e o que
`analyze airflow-dag` seguido de `judge` ve. Fixture com `main.tf` ao lado e o que
`fuse` ve com os dois lados no pool: extrai o Terraform e deriva `af.glue_job_link`
com `build_af_glue_link`, a mesma funcao que `fusion.fuse` chama.
`scripts/regen_fixtures.py::regen_airflow` e o par deste `_extract`: se um deriva e o
outro nao, o golden nunca fecha.

Este modulo NAO e opcional: `test_fixtures_kind_coverage.py` casa o dominio pela linha
literal `FIXTURES = ...` abaixo, e `scripts/verify_wheel.py` roda os modulos
`test_fixtures_*.py` contra o pacote instalado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.airflow_dag import build_af_glue_link, extract_airflow_dag_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.models import sort_facts
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "airflow"

# Lista escrita a mao de proposito: fixture removida em silencio some do `parametrize`
# sem que nada reclame, e o corpus encolhe sem deixar rastro.
REQUIRED_FIXTURES = {
    # SF-AIRFLOW-001: wait_for_completion=False com tarefa a jusante.
    "sem_espera",
    # SF-AIRFLOW-002: execution_timeout declarado e stop_job_run_on_kill ausente.
    "timeout_sem_stop",
    # SF-AIRFLOW-003: espera o job sem deferrable.
    "espera_sincrona",
    # SF-AIRFLOW-004: DAG + o aws_glue_job com max_retries 2.
    "retry_duas_camadas",
    # O negativo da area: espera com deferrable, sem timeout, retries 0.
    "dag_limpo",
    # As duas fronteiras da SF-AIRFLOW-004: liga, mas uma das camadas e zero.
    "retry_so_no_glue",
    "retry_so_no_airflow",
    # `job_name` em Jinja nao liga: af.unresolved, SF-AIRFLOW-004 calada.
    "job_name_nao_literal",
    # O que a leitura estatica nao alcanca, contado em vez de adivinhado.
    "dag_dinamico",
    "python_invalido",
    "taskflow_decorador",
}


def fixture_dirs() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = list(extract_airflow_dag_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
        facts.extend(build_af_glue_link(facts))
    return sort_facts(facts)


def run_fixture(directory: Path):
    meta = _meta(directory)
    facts = _extract(directory)
    return meta, facts, judge(facts, load_catalog(), meta["runtime"])


def _esperado(directory: Path, nome: str):
    return json.loads((directory / "expected" / nome).read_text(encoding="utf-8"))


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio vazio o pytest 8.x
# chama o callable sobre o sentinela NOTSET e aborta a sessao inteira.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
def test_golden(directory):
    meta, facts, findings = run_fixture(directory)
    assert [f.to_dict() for f in facts] == _esperado(directory, "facts.json")
    assert [f.to_dict() for f in findings] == _esperado(directory, "findings.json")
    assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))
    assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))
    for fact in facts:
        validate_fact(fact.to_dict())
    for finding in findings:
        validate_finding(finding.to_dict())


@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
def test_uma_sentinela_por_arquivo_e_ela_conta_o_que_diz(directory):
    _, facts, _ = run_fixture(directory)
    sentinelas = [f for f in facts if f.kind == "af.analyzed"]
    assert len(sentinelas) == len(list((directory / "input").glob("*.py")))
    for campo, kind in (("dag_count", "af.dag"), ("task_count", "af.task")):
        esperado = sum(1 for f in facts if f.kind == kind)
        assert sum(s.measures[campo] for s in sentinelas) == esperado, campo


def test_nenhum_fact_do_dominio_carrega_snippet():
    """O DAG e codigo de terceiro: `subject.snippet` sairia com texto nao confiavel.

    `tests/test_harness_untrusted.py` mede o conjunto de extratores que produzem
    snippet, e `airflow_dag` nao entra nele -- este teste trava a decisao no dominio.
    """
    for directory in fixture_dirs():
        _, facts, _ = run_fixture(directory)
        for fact in facts:
            if fact.kind.startswith("af."):
                assert not fact.subject.get("snippet"), (directory.name, fact.kind)
```

**1c.** O corpus `fixtures/airflow/<caso>/{meta.yaml,input/}`. Todas as fixtures usam o
mesmo `runtime`. Ele é inerte para as `SF-AIRFLOW` (`runtime_scope: {}`), e existe
porque o `judge` exige um e porque o `aws_glue_job` das fixtures pareadas declara
`glue_version = "5.0"`:

```yaml
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
```

**O `main.tf` das quatro fixtures pareadas é o mesmo**, e é cópia literal de
`fixtures/stepfunctions/retry_duas_camadas/input/main.tf` — medido naquela entrega:
esse `aws_glue_job` sozinho, julgado com o `runtime` acima, **não dispara regra
nenhuma**, então o golden só pode mudar por causa do DAG. Só o `max_retries` varia:

```hcl
resource "aws_glue_job" "carga_diaria" {
  name              = "carga-diaria"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 2
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://bucket-exemplo/scripts/carga_diaria.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://bucket-exemplo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://bucket-exemplo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
```

| fixture pareada | `max_retries` do `main.tf` |
|---|---|
| `retry_duas_camadas` | `2` |
| `retry_so_no_glue` | `2` |
| `retry_so_no_airflow` | `0` |
| `job_name_nao_literal` | `2` |

Os quatro `expects_kinds` das pareadas trazem os mesmos kinds de Terraform que o corpus
de Step Functions mediu: `tf.attribute`, `tf.module_analyzed`, `tf.observability.spark_ui`
e `tf.resource`.

---

`fixtures/airflow/sem_espera/input/carga_diaria.py`:

```python
"""Fixture sintetica: o Glue e disparado sem esperar, e a task seguinte depende dele."""
from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_diaria",
    schedule="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        wait_for_completion=False,
    )
    publicar = EmptyOperator(task_id="publicar")

    carga >> publicar
```

`fixtures/airflow/sem_espera/meta.yaml`:

```yaml
name: sem_espera
proves: >
  O POSITIVO de SF-AIRFLOW-001. `wait_for_completion=False` e uma tarefa a jusante: a
  task termina quando o Glue aceita o pedido, e `publicar` roda com o job ainda em
  execucao. O EmptyOperator e registrado e nao julgado -- as regras julgam so o
  GlueJobOperator. SF-AIRFLOW-003 fica calada porque a task NAO espera o job.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.dag, af.dependency, af.task]
expects_rules: [SF-AIRFLOW-001]
```

---

`fixtures/airflow/timeout_sem_stop/input/carga_com_timeout.py`:

```python
"""Fixture sintetica: o Airflow mata a task no prazo, e o JobRun continua."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_com_timeout",
    schedule="0 4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        execution_timeout=timedelta(hours=2),
        deferrable=True,
    )
```

`fixtures/airflow/timeout_sem_stop/meta.yaml`:

```yaml
name: timeout_sem_stop
proves: >
  O POSITIVO de SF-AIRFLOW-002. `execution_timeout` declarado e `stop_job_run_on_kill`
  omitido -- o default publicado e False. Esta fixture tambem e a que prova a refinacao
  de D2 escrita no plano: `timedelta(hours=2)` e um `ast.Call`, e mesmo assim a
  DECLARACAO e lida (`execution_timeout_declared: true`) e o valor vira medida
  (`execution_timeout_seconds: 7200`). `deferrable=True` mantem SF-AIRFLOW-003 calada.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.dag, af.task]
expects_rules: [SF-AIRFLOW-002]
```

---

`fixtures/airflow/espera_sincrona/input/carga_sincrona.py`:

```python
"""Fixture sintetica: tudo no default -- a espera segura um slot de worker."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_sincrona",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(task_id="carga", job_name="carga-diaria")
```

`fixtures/airflow/espera_sincrona/meta.yaml`:

```yaml
name: espera_sincrona
proves: >
  O POSITIVO de SF-AIRFLOW-003, e o caso em que NENHUM dos tres argumentos foi escrito:
  `wait_for_completion` efetivo True e `deferrable` efetivo False, os dois pelo default
  publicado e os dois com `_defaulted: true`. Sem `execution_timeout` e sem tarefa a
  jusante, as outras duas regras do DAG ficam caladas.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.dag, af.task]
expects_rules: [SF-AIRFLOW-003]
```

---

`fixtures/airflow/retry_duas_camadas/input/carga_com_retry.py` (usa o `main.tf` com
`max_retries = 2`):

```python
"""Fixture sintetica: o mesmo job com retry no Airflow e no proprio Glue."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

DEFAULT_ARGS = {"retries": 2}

with DAG(
    dag_id="carga_com_retry",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        deferrable=True,
    )
```

`fixtures/airflow/retry_duas_camadas/meta.yaml`:

```yaml
name: retry_duas_camadas
proves: >
  O POSITIVO de SF-AIRFLOW-004. A task liga ao `aws_glue_job.carga_diaria` pelo
  `job_name` literal igual ao `name`; o `retries` efetivo do Airflow vem de
  `default_args` e vale 2, e o job declara `max_retries = 2`. As duas camadas existem
  sobre o mesmo job, e a composicao delas nao e documentada (U1). Esta fixture tambem e
  a que exercita `default_args=DEFAULT_ARGS` pelo nome de modulo.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - af.analyzed
  - af.dag
  - af.glue_job_link
  - af.task
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: [SF-AIRFLOW-004]
```

---

`fixtures/airflow/dag_limpo/input/carga_limpa.py`:

```python
"""Fixture sintetica: o negativo da area -- os tres argumentos escritos, e nenhum achado."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_limpa",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        wait_for_completion=True,
        deferrable=True,
        stop_job_run_on_kill=True,
    )
```

`fixtures/airflow/dag_limpo/meta.yaml`:

```yaml
name: dag_limpo
proves: >
  O NEGATIVO da area. Espera o job, espera de forma diferida, e mata o JobRun junto com
  a task: os tres argumentos escritos a mao, com `_defaulted: false` nos tres. Nenhuma
  das quatro regras dispara.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.dag, af.task]
expects_rules: []
```

---

`fixtures/airflow/retry_so_no_glue/input/carga.py` (usa o `main.tf` com
`max_retries = 2`):

```python
"""Fixture sintetica: o Airflow nao retenta; o job Glue retenta."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_sem_retry",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 0},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        deferrable=True,
    )
```

`fixtures/airflow/retry_so_no_glue/meta.yaml`:

```yaml
name: retry_so_no_glue
proves: >
  Uma fronteira de SF-AIRFLOW-004: o vinculo existe, o job declara `max_retries = 2` e
  o `retries` do Airflow e 0. Uma camada so, e a regra calada. E o golden que muda se
  alguem trocar `measures.airflow_retries_effective > 0` por `>= 0`.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - af.analyzed
  - af.dag
  - af.glue_job_link
  - af.task
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: []
```

---

`fixtures/airflow/retry_so_no_airflow/input/carga.py` (usa o `main.tf` com
`max_retries = 0`):

```python
"""Fixture sintetica: o Airflow retenta; o job Glue nao."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_com_retry_no_airflow",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        deferrable=True,
    )
```

`fixtures/airflow/retry_so_no_airflow/meta.yaml`:

```yaml
name: retry_so_no_airflow
proves: >
  A outra fronteira de SF-AIRFLOW-004: o vinculo existe, o `retries` do Airflow e 2 e o
  job declara `max_retries = 0`. Uma camada so, e a regra calada. E o golden que muda se
  alguem trocar `measures.glue_max_retries > 0` por `>= 0`. Esta fixture NAO esta na
  lista de D8 do desenho, e a razao e medida: `tests/test_rules_threshold_mutation.py`
  compara `FRONTEIRA_SEM_GOLDEN` por igualdade exata, e sem ela a troca sobreviveria.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - af.analyzed
  - af.dag
  - af.glue_job_link
  - af.task
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: []
```

---

`fixtures/airflow/job_name_nao_literal/input/carga.py` (usa o `main.tf` com
`max_retries = 2`):

```python
"""Fixture sintetica: o nome do job vem de uma Variable, resolvida em execucao."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

with DAG(
    dag_id="carga_parametrizada",
    schedule="0 5 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args={"retries": 2},
) as dag:
    carga = GlueJobOperator(
        task_id="carga",
        job_name="{{ var.value.glue_job }}",
        deferrable=True,
    )
```

`fixtures/airflow/job_name_nao_literal/meta.yaml`:

```yaml
name: job_name_nao_literal
proves: >
  O NEGATIVO de SF-AIRFLOW-004 por nome nao literal. O `retries` do Airflow e 2 e o
  Terraform tem `max_retries = 2`, mas `{{ var.value.glue_job }}` e template do Jinja,
  resolvido em execucao: nao ha vinculo, saem dois `af.unresolved` -- `arg_nao_literal`
  do extrator e `job_name_dynamic` da derivacao --, e SF-AIRFLOW-004 fica calada em vez
  de adivinhar o job.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds:
  - af.analyzed
  - af.dag
  - af.task
  - af.unresolved
  - tf.attribute
  - tf.module_analyzed
  - tf.observability.spark_ui
  - tf.resource
expects_rules: []
```

---

`fixtures/airflow/dag_dinamico/input/cargas_por_dominio.py`:

```python
"""Fixture sintetica: DAG montado em laco -- fora do alcance da leitura estatica."""
from datetime import datetime

from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

for dominio in ("clientes", "pedidos"):
    with DAG(
        dag_id=f"carga_{dominio}",
        schedule="0 7 * * *",
        start_date=datetime(2026, 1, 1),
        catchup=False,
    ) as dag:
        GlueJobOperator(task_id="carga", job_name=f"carga-{dominio}")
```

`fixtures/airflow/dag_dinamico/meta.yaml`:

```yaml
name: dag_dinamico
proves: >
  O ponto cego contado. O DAG e o operador nascem dentro de um `for`, e o extrator NAO
  executa o arquivo para descobrir quantos saem: os dois viram `af.unresolved` com
  `dag_dinamico`, e nenhum `af.dag` nem `af.task` e afirmado. Nenhum achado.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.unresolved]
expects_rules: []
```

---

`fixtures/airflow/python_invalido/input/quebrado.py` (Python inválido de propósito, o
arquivo inteiro):

```text
from airflow import DAG

with DAG(dag_id="carga",
```

`fixtures/airflow/python_invalido/meta.yaml`:

```yaml
name: python_invalido
proves: >
  Arquivo que nao parseia vira `af.unresolved` com `invalid_python`, com a linha e a
  coluna que o `SyntaxError` deu, e a sentinela sai do mesmo jeito -- prova de que o
  arquivo foi visto. Nenhum achado, e nenhuma excecao vazando.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.unresolved]
expects_rules: []
```

---

`fixtures/airflow/taskflow_decorador/input/carga_taskflow.py`:

```python
"""Fixture sintetica: TaskFlow API -- reconhecida e nomeada, nao lida."""
from datetime import datetime

from airflow.decorators import dag, task


@dag(schedule="0 8 * * *", start_date=datetime(2026, 1, 1), catchup=False)
def carga_taskflow():
    @task
    def extrair():
        return {"linhas": 0}

    extrair()


carga_taskflow()
```

`fixtures/airflow/taskflow_decorador/meta.yaml`:

```yaml
name: taskflow_decorador
proves: >
  A fronteira que o `define` poe fora de escopo, contada em vez de ignorada. `@dag` e
  `@task` viram `af.unresolved` com `taskflow_decorador` e o nome da funcao; nenhum
  `af.dag` nem `af.task` sai, porque a leitura adotada reconhece operador por classe
  instanciada e a TaskFlow nao instancia nenhuma. Nenhum achado.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [af.analyzed, af.unresolved]
expects_rules: []
```

### 2. Rodar e ver falhar

```bash
git add tests/test_fixtures_golden_airflow.py
python -m pytest tests/test_airflow_dag.py::test_fuse_liga_a_task_ao_job_e_nomeia_o_que_nao_liga tests/test_fixtures_golden_airflow.py -q
```

Falhas esperadas: `ImportError: cannot import name 'build_af_glue_link'` na coleta do
golden (a derivação é a unidade sob teste), e `ValueError: not enough values to unpack`
em `[link] = ...` no teste do `fuse`.

### 3. Código mínimo

**3a. A derivação, em `sparkforge/facts/airflow_dag.py`** (D5).

No docstring do módulo, troque

```text
- `af.glue_job_link` -- DERIVADO, nunca lido de arquivo: `build_af_glue_link` liga a
  task do `GlueJobOperator` ao `aws_glue_job` de mesmo `name` quando os dois estao no
  pool, e `fusion.fuse` a chama (D5). Ela entra em `EMITTED_KINDS` na T3, junto com o
  golden que a cobre.
```

por

```text
- `af.glue_job_link` -- DERIVADO, nunca lido de arquivo: `build_af_glue_link` liga a
  task do `GlueJobOperator` ao `aws_glue_job` de mesmo `name` quando os dois estao no
  pool, e `fusion.fuse` a chama (D5). As razoes de `af.unresolved` que so ela emite:
  `job_name_dynamic`, `job_name_absent`, `job_definition_absent`,
  `job_definition_ambiguous` e `glue_max_retries_not_literal`.
```

Imports: troque

```python
import ast
import hashlib
from dataclasses import dataclass, field
```

por

```python
import ast
import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
```

`EMITTED_KINDS`: troque

```python
EMITTED_KINDS = frozenset(
    {
        "af.dag",
        "af.task",
        "af.dependency",
        "af.unresolved",
        "af.analyzed",
    }
)
```

por

```python
EMITTED_KINDS = frozenset(
    {
        "af.dag",
        "af.task",
        "af.dependency",
        "af.unresolved",
        "af.analyzed",
        "af.glue_job_link",
    }
)

# O que liga a derivacao em `fusion.fuse`: sem `af.task` no pool, o `fuse` sai byte a
# byte igual ao de antes (molde de `timeout_diagnosis.SOURCE_KINDS`).
SOURCE_KINDS = frozenset({"af.task"})

# As duas origens de `job_name` que a derivacao recusa por serem resolvidas em
# execucao. `absent` e diferente das duas: o argumento nem foi escrito.
_ORIGENS_DINAMICAS = frozenset({"jinja", "nao_literal"})
```

E acrescente, logo antes de `__all__`:

```python
def _glue_jobs_por_nome(facts: Sequence[Fact]) -> dict[str, list[tuple[str, str, str]]]:
    """Nome literal do job -> [(arquivo, endereco, id do fact)], de `tf.attribute` `name`.

    GEMEA de `stepfunctions._glue_jobs_por_nome`, e duplicada de proposito NESTE
    incremento: um leitor de DAG nao deveria importar um leitor de ASL para saber ler
    Terraform. O lugar certo da funcao e um modulo proprio -- ver "Duvidas" no fim de
    `docs/sdd/AIRFLOW_DAG/plan.md` --, e ele nao esta no manifesto deste desenho.
    """
    nomes: dict[str, list[tuple[str, str, str]]] = {}
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        subject = fact.subject or {}
        attrs = fact.attrs or {}
        simbolo = str(subject.get("symbol") or "")
        if not simbolo.startswith("aws_glue_job."):
            continue
        if attrs.get("key") != "name" or attrs.get("block") != "root" or not attrs.get("literal"):
            continue
        arquivo = str(subject.get("file") or "")
        nomes.setdefault(str(attrs.get("value")), []).append((arquivo, simbolo, fact.id))
    return nomes


def _max_retries(
    facts: Sequence[Fact], arquivo: str, simbolo: str
) -> tuple[str, int | None, str | None]:
    """(`literal`, n, id), (`absent`, 0, None) ou (`not_literal`, None, id|None).

    `absent` vale 0 porque o atributo nao declarado nao pede retry. Valor interpolado
    vira `tf.unresolved` sem o endereco do recurso (`terraform.py`); por isso qualquer
    `tf.unresolved` de `max_retries` no MESMO arquivo torna a resposta `not_literal` --
    conservador de proposito: nunca um zero que ninguem leu. Gemea de
    `stepfunctions._max_retries`, pelo mesmo motivo da funcao acima.
    """
    for fact in facts:
        subject = fact.subject or {}
        if fact.kind != "tf.attribute" or subject.get("symbol") != simbolo:
            continue
        if subject.get("file") != arquivo:
            continue
        attrs = fact.attrs or {}
        if attrs.get("key") != "max_retries" or attrs.get("block") != "root":
            continue
        valor = (fact.measures or {}).get("value")
        if attrs.get("literal") and isinstance(valor, int | float) and not isinstance(valor, bool):
            return "literal", int(valor), fact.id
        return "not_literal", None, fact.id
    interpolado = any(
        f.kind == "tf.unresolved"
        and (f.attrs or {}).get("key") == "max_retries"
        and (f.subject or {}).get("file") == arquivo
        for f in facts
    )
    return ("not_literal", None, None) if interpolado else ("absent", 0, None)


def build_af_glue_link(facts: Sequence[Fact]) -> list[Fact]:
    """Liga cada `af.task` do `GlueJobOperator` ao `aws_glue_job` de mesmo `name` (D5).

    Derivacao pura sobre a UNIAO dos facts, no molde de `build_sfn_glue_link`: o motor
    avalia um fact por condicao, e os dois lados tem `subject` diferente -- a task do
    DAG e o recurso do Terraform --, entao `same_subject` nao os junta. Nao liga por
    substring: nome de job e chave exata na API do Glue.

    `airflow_retries_effective` e o `retries_effective` da task: o da propria task, ou
    o de `default_args`, ou o default publicado (`core.default_task_retries`, 0). O que
    nao liga sai nomeado em `af.unresolved`, nunca como vinculo.
    """
    nomes = _glue_jobs_por_nome(facts)
    saida: list[Fact] = []
    for task in facts:
        attrs = task.attrs or {}
        if task.kind != "af.task" or attrs.get("operator_family") != "glue_job":
            continue
        proveniencia: dict[str, Any] = {
            "artifact": str((task.provenance or {}).get("artifact", "")),
            "artifact_sha256": "",
            "extractor": EXTRACTOR_ID,
            "derived_from": [task.id],
        }
        nome = attrs.get("job_name")
        if not isinstance(nome, str):
            origem = str(attrs.get("job_name_source", ""))
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "job_name_dynamic" if origem in _ORIGENS_DINAMICAS else "job_name_absent",
                    proveniencia,
                    job_name_source=origem,
                    unblocked_by="`job_name` escrito como string literal na task",
                )
            )
            continue
        candidatos = nomes.get(nome, [])
        if len(candidatos) != 1:
            razao = "job_definition_absent" if not candidatos else "job_definition_ambiguous"
            saida.append(
                _unresolved(
                    dict(task.subject),
                    razao,
                    proveniencia,
                    job_name=nome,
                    resources=[simbolo for _, simbolo, _ in candidatos],
                    unblocked_by="sparkforge analyze terraform no aws_glue_job, e fuse",
                )
            )
            continue
        arquivo, simbolo, nome_id = candidatos[0]
        origem, retries, retries_id = _max_retries(facts, arquivo, simbolo)
        usados = [nome_id] + ([retries_id] if retries_id is not None else [])
        proveniencia = {**proveniencia, "derived_from": [task.id, *usados]}
        measures: dict[str, Any] = {}
        efetivo = (task.measures or {}).get("retries_effective")
        if efetivo is not None:
            measures["airflow_retries_effective"] = efetivo
        if retries is not None:
            measures["glue_max_retries"] = retries
        saida.append(
            Fact(
                kind="af.glue_job_link",
                subject=dict(task.subject),
                measures=measures,
                attrs={
                    "job_name": nome,
                    "resource": simbolo,
                    "resource_file": arquivo,
                    "glue_max_retries_source": origem,
                    "airflow_retries_defaulted": bool(attrs.get("retries_defaulted")),
                },
                provenance=proveniencia,
            )
        )
        if origem == "not_literal":
            saida.append(
                _unresolved(
                    dict(task.subject),
                    "glue_max_retries_not_literal",
                    proveniencia,
                    job_name=nome,
                    resource=simbolo,
                    unblocked_by="`max_retries` escrito como numero literal no aws_glue_job",
                )
            )
    return sort_facts(saida)
```

E no `__all__`, troque `    "EXTRACTOR_ID",` por

```python
    "EXTRACTOR_ID",
    "SOURCE_KINDS",
    "build_af_glue_link",
```

**3b. `sparkforge/facts/fusion.py`.** Imports: troque

```python
from sparkforge.facts.stepfunctions import EMITTED_KINDS as SFN_EMITTED_KINDS
```

por

```python
from sparkforge.facts.airflow_dag import EMITTED_KINDS as AF_EMITTED_KINDS
from sparkforge.facts.airflow_dag import SOURCE_KINDS as AF_SOURCE_KINDS
from sparkforge.facts.airflow_dag import build_af_glue_link
from sparkforge.facts.stepfunctions import EMITTED_KINDS as SFN_EMITTED_KINDS
```

(O `ruff`/isort quer `airflow_dag` antes de `stepfunctions`; se ele reordenar, aceite o
que ele escrever.)

E no fim de `fuse`, troque

```python
        for fact in derivados_sfn:
            combined[fact.id] = fact

    return sort_facts(combined.values())
```

por

```python
        for fact in derivados_sfn:
            combined[fact.id] = fact

    # `af.glue_job_link` deriva AQUI pela mesma razao de `sfn.glue_job_link`: a
    # `af.task` e o `aws_glue_job` tem `subject` diferente, e o motor nao junta dois
    # facts numa condicao. Guardado por `SOURCE_KINDS`: pool sem Airflow sai byte a
    # byte igual.
    if any(f.kind in AF_SOURCE_KINDS for f in facts):
        derivados_af = build_af_glue_link(facts)
        desconhecidos_af = {f.kind for f in derivados_af} - AF_EMITTED_KINDS
        if desconhecidos_af:
            raise AssertionError(
                f"kind fora do namespace de airflow_dag: {sorted(desconhecidos_af)}"
            )
        for fact in derivados_af:
            combined[fact.id] = fact

    return sort_facts(combined.values())
```

**3c. `rules/catalog/airflow.yaml`** (arquivo novo, inteiro):

```yaml
# Catálogo de regras — como o DAG do Apache Airflow dispara o job Glue
#
# Depende de `sparkforge/facts/airflow_dag.py`, que lê o arquivo `.py` do DAG por AST
# (nunca o executa) e, em `fuse`, liga a task ao `aws_glue_job` de mesmo `name`
# (`af.glue_job_link`). As frases citadas estão em
# `knowledge/airflow/glue-operator.md`; o desenho, em `docs/sdd/AIRFLOW_DAG/design.md`.
#
# O QUE A ÁREA NÃO JULGA, e por quê (D4):
# - código pesado no top-level do DAG: o que é "pesado" não se mede por AST sem
#   heurística, e heurística não é fact;
# - retry sem escrita idempotente: é a `SF-GLUE-004`, que já existe pelo lado do job;
# - dependência ENTRE DAGs (`ExternalTaskSensor`, `TriggerDagRunOperator`): fora de
#   escopo no `define` (abordagem C do explore);
# - operadores de EMR, Athena e afins: o extrator os registra, e nenhuma regra os julga.
#
# `runtime_scope: {}` nas quatro (D4), e a escolha é medida: não há fronteira de versão
# de Glue publicada para nenhuma delas, e o arquivo do DAG sozinho não detecta runtime
# Glue -- `{glue: "*"}` faria as quatro saírem em `skipped` até alguém declarar
# `--glue`, o defeito que `docs/gates-por-mudanca.md` descreve. Quem gateia é
# `requires_facts`: sem `af.task` (ou sem o `af.glue_job_link` que só o `fuse` deriva),
# a regra é pulada com a razão. A auditoria de texto AWS de
# `tests/test_databricks_rule_audit.py` fica satisfeita porque `airflow_dag` está em
# `SO_AWS`: as quatro regras julgam só o `GlueJobOperator`, que chama `StartJobRun` da
# API do AWS Glue.
#
# A ÂNCORA de cada regra é o fact que ela julga, com `same_subject: true`: um achado por
# task, nunca um por arquivo. O `subject.symbol` é o `task_id` literal quando há um.
#
# POR QUE `attrs.operator_family` e não o nome da classe: `sparkforge/rules/expr.py` tem
# seis comparadores e nenhuma função, e `where` só compara por igualdade (regra 33). O
# predicado "é um operador de job Glue" -- que precisa aceitar `GlueJobOperator` e o
# legado `AwsGlueJobOperator` -- é derivado no extrator e chega aqui como valor.

catalog_version: 1
schema_version: 1
area: SF-AIRFLOW
retrieved: 2026-09-20

rules:

  - id: SF-AIRFLOW-001
    category: airflow-dag
    title: "GlueJobOperator com wait_for_completion=False e tarefa a jusante: a próxima task roda com o job em execução"
    requires_facts: [af.task]
    when:
      same_subject: true
      all:
        - fact: af.task
          where:
            attrs.operator_family: glue_job
            attrs.wait_for_completion_effective: false
            attrs.has_downstream: true
    status: structural
    severity_default: P2
    runtime_scope: {}
    explanation: >
      A task declara `wait_for_completion=False` e tem tarefa a jusante declarada no
      DAG. O parâmetro é descrito pelo provider como "Whether to wait for job run
      completion", e o default publicado é `True`: escrever `False` é a decisão de NÃO
      esperar. A task termina quando o Glue aceita o `StartJobRun`, e a tarefa seguinte
      roda com o job ainda em execução — se ela lê a saída do job, lê dado parcial ou
      antigo, e o desfecho do JobRun não chega ao DAG. A regra exige tarefa a jusante:
      um disparo terminal, sem nada depois dele, é disparo deliberado sem espera, e não
      há tarefa seguinte a proteger. As dependências que o fact conhece são as
      declaradas por `>>`, `<<`, `set_downstream` e `set_upstream` e lidas
      estaticamente; elo montado em laço sai em `af.unresolved`, e então esta regra
      fica calada em vez de afirmar ordem que ninguém leu. Ver
      knowledge/airflow/glue-operator.md.
    proposed_change:
      - "Tirar o `wait_for_completion=False` (o default é esperar), para que a task só termine quando o JobRun terminar e falhe junto com ele."
      - "Se o disparo sem espera é deliberado, tirar a dependência: nenhuma tarefa seguinte pode ler a saída do job. Registrar a decisão no `doc_md` do DAG."
      - "Se a tarefa seguinte precisa do resultado mas o slot de worker não pode ficar preso, esperar de forma diferida: `deferrable=True` mantém a espera e devolve o slot (SF-AIRFLOW-003)."
    # `orchestration.change_job_definition` porque a troca e de forma da declaracao da
    # task, nao de politica de execucao. `moves` evita `runtime.wall_clock` de
    # proposito: o grupo desse eixo esta no teto de 12 que
    # `tests/test_agentic_executor_ordering.py` trava, e o que a troca muda de verdade e
    # o que a tarefa seguinte le.
    action:
      kind: orchestration.change_job_definition
      target: airflow.task.wait_for_completion
      direction: replace
      requires_absent: []
      moves:
        - correctness.write_result
      depends_on: []
    risks:
      - "Com a espera, a execução do DAG passa a durar o job inteiro, e o slot de worker fica ocupado por esse tempo se `deferrable` continuar `False`."
      - "Um job que hoje falha sem o DAG saber passa a falhar a task: alertas e SLA de DAG que nunca dispararam passam a disparar."
    tradeoffs:
      - "Esperar o job custa tempo de execução da task; disparar sem esperar custa a garantia de ordem entre o job e o resto do fluxo."
    validation:
      - "`sparkforge analyze airflow-dag --path <DAG corrigido>` mostra o `af.task` com `wait_for_completion_effective: true`, e `sparkforge judge` não produz mais SF-AIRFLOW-001 para a task."
      - "EIXO DE RESULTADO — numa execução de teste, a tarefa seguinte lê a saída completa do job: a contagem de linhas que ela lê é igual à que o JobRun escreveu, conferida no destino depois do `SUCCEEDED` do JobRun."
      - "Uma execução de teste em que o job falha marca a task como `failed` e não segue para a tarefa a jusante."
    rollback:
      - "Reverter o commit do arquivo do DAG e republicá-lo pelo caminho que publica a pasta de DAGs. Execuções já iniciadas seguem com a versão com que começaram."
    sources:
      - {url: "https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html", retrieved: 2026-09-20}

  - id: SF-AIRFLOW-002
    category: airflow-dag
    title: "execution_timeout com stop_job_run_on_kill ausente: o Airflow mata a task e o job Glue continua cobrando"
    requires_facts: [af.task]
    when:
      same_subject: true
      all:
        - fact: af.task
          where:
            attrs.operator_family: glue_job
            attrs.execution_timeout_declared: true
            attrs.stop_job_run_on_kill_effective: false
    status: structural
    severity_default: P1
    runtime_scope: {}
    explanation: >
      A task tem `execution_timeout` declarado — na própria task ou em `default_args` —
      e `stop_job_run_on_kill` ausente ou `False`. A documentação do Airflow diz o que o
      prazo faz: "If you want a task to have a maximum runtime, set its
      `execution_timeout` attribute to a `datetime.timedelta` value that is the maximum
      permissible runtime." E o provider diz o que o outro parâmetro faz quando é
      `True`: "If True, Operator will stop the job run when task is killed", com default
      `False`. Juntas, as duas frases sustentam uma coisa só, e é só essa que a regra
      afirma: quando o prazo estoura e a task é morta, o operador NÃO para o JobRun. O
      que a documentação do provider não descreve — e por isso a regra não afirma — é o
      que acontece com o JobRun depois disso (U3 do `define`): o Glue continua
      executando e faturando até terminar por conta própria ou bater no `Timeout` do
      job, e o DAG já marcou a task como falha. A regra julga a DECLARAÇÃO do prazo, não
      o valor dele: o valor só vira medida quando é `timedelta(**literais)`.
    proposed_change:
      - "Declarar `stop_job_run_on_kill=True` na task, para que matar a task pare o JobRun."
      - "Ou tirar o `execution_timeout` da task do Glue e deixar o prazo onde o job o conhece: o `timeout` do `aws_glue_job`, que o Glue impõe ao próprio JobRun."
      - "Se os dois prazos existem de propósito, alinhá-los: `execution_timeout` do Airflow maior que o `timeout` do job, para que o job termine por si antes de a task ser morta."
    action:
      kind: orchestration.change_job_definition
      target: airflow.task.stop_job_run_on_kill
      direction: add
      requires_absent: []
      moves:
        - cost.dpu_seconds
      depends_on: []
    risks:
      - "Com `stop_job_run_on_kill=True`, matar a task passa a interromper um JobRun no meio: escrita não transacional deixa saída parcial no destino."
      - "A role do Airflow precisa de `glue:BatchStopJobRun` para parar o job; sem a permissão, o parâmetro fica ligado e a parada falha."
    tradeoffs:
      - "Parar o job junto com a task economiza o resto do JobRun e arrisca saída parcial; deixar o job correr preserva a escrita e paga o run inteiro que ninguém vai usar."
    validation:
      - "`sparkforge analyze airflow-dag` mostra o `af.task` com `stop_job_run_on_kill_effective: true` (ou sem `execution_timeout_declared`), e `sparkforge judge` não produz mais SF-AIRFLOW-002 para a task."
      - "EIXO DE RESULTADO — numa execução de teste em que o prazo estoura, o destino tem a mesma contagem total e a mesma contagem por chave de negócio que antes da execução: a interrupção não deixou linha parcial."
      - "`aws glue get-job-run --job-name <job> --run-id <id>` mostra o JobRun em `STOPPED` no mesmo minuto em que a task foi marcada como falha, e não `RUNNING` depois dela."
    rollback:
      - "Reverter o commit do arquivo do DAG e republicá-lo."
    sources:
      - {url: "https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html", retrieved: 2026-09-20}
      - {url: "https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html", retrieved: 2026-09-20}

  - id: SF-AIRFLOW-003
    category: airflow-dag
    title: "Espera síncrona do job Glue: o slot de worker do Airflow fica preso pelo tempo do job"
    requires_facts: [af.task]
    when:
      same_subject: true
      all:
        - fact: af.task
          where:
            attrs.operator_family: glue_job
            attrs.wait_for_completion_effective: true
            attrs.deferrable_effective: false
    status: structural
    severity_default: P3
    runtime_scope: {}
    explanation: >
      A task espera o job terminar (`wait_for_completion` ausente ou `True` — o default
      publicado é `True`) e não pede espera diferida (`deferrable` ausente ou `False` —
      o default publicado é `False`). O provider descreve `deferrable` como "If True,
      the operator will wait asynchronously for the job to complete", e o contraste é o
      ponto: na espera síncrona o processo do worker fica ocupado consultando o job a
      cada `job_poll_interval` (default publicado `6` segundos) do começo ao fim do
      JobRun. Um job batch de horas segura um slot de worker por horas fazendo polling.
      A regra não afirma que a espera é errada — esperar é o comportamento correto para
      quem depende do resultado —, nem que o DAG está com falta de slot: ela nomeia o
      custo da forma de espera escolhida. A severidade é P3 porque o efeito é capacidade
      do Airflow, não correção do dado.
    proposed_change:
      - "Declarar `deferrable=True` na task, para que a espera saia do worker e vá para o triggerer."
      - "Antes disso, confirmar que existe um processo `triggerer` rodando no ambiente: sem ele a task diferida fica parada. Em ambiente gerenciado (MWAA), conferir a versão que o publica."
      - "Se o resultado do job não é lido por nenhuma tarefa a jusante, a outra saída é não esperar (`wait_for_completion=False`) — e aí vale a SF-AIRFLOW-001: nenhuma tarefa pode depender do job."
    # `cost.provisioned_capacity_time`: o que a troca move e o tempo em que o slot de
    # worker fica ocupado, com ou sem trabalho de CPU. NAO e `runtime.wall_clock` (o job
    # dura o mesmo) nem `capacity.worker_count` (o numero de workers declarado nao muda).
    action:
      kind: orchestration.change_job_definition
      target: airflow.task.deferrable
      direction: replace
      requires_absent: []
      moves:
        - cost.provisioned_capacity_time
      depends_on: []
    risks:
      - "A task diferida depende do processo `triggerer`: sem ele rodando, a task fica em `deferred` indefinidamente. Ver a lacuna 3 de knowledge/airflow/glue-operator.md — o arquivo do DAG não diz se o ambiente tem triggerer, e o extrator não o afirma."
      - "O caminho diferido do operador é código diferente do síncrono: um job que hoje termina bem pode expor um modo de falha que o caminho síncrono não exercitava."
    tradeoffs:
      - "A espera diferida devolve o slot e paga com uma peça a mais na infraestrutura; a espera síncrona é mais simples e paga com o slot ocupado pelo tempo do job."
    validation:
      - "`sparkforge analyze airflow-dag` mostra o `af.task` com `deferrable_effective: true`, e `sparkforge judge` não produz mais SF-AIRFLOW-003 para a task."
      - "EIXO DE RESULTADO — numa execução de teste, o destino tem a mesma contagem total e por chave de negócio que a execução síncrona equivalente: mudar a forma de esperar não muda o que o job escreve."
      - "Na execução de teste, a task passa pelo estado `deferred` e o slot fica livre no intervalo: o número de tarefas em execução no pool durante o job é menor do que era."
    rollback:
      - "Reverter o commit do arquivo do DAG e republicá-lo. Tarefas já diferidas terminam pelo triggerer; as novas voltam ao caminho síncrono."
    sources:
      - {url: "https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html", retrieved: 2026-09-20}

  # A ancora e o fact DERIVADO: sem `fuse` com o DAG e o Terraform no mesmo pool, a
  # regra sai em `skipped` com `reason: requires_facts` -- "nao perguntei", nunca "esta
  # tudo bem". `job_name` nao literal e job ausente saem em `af.unresolved` na derivacao.
  - id: SF-AIRFLOW-004
    category: airflow-dag
    title: "Retry nas duas camadas: o Airflow e o job Glue reexecutam a mesma falha"
    requires_facts: [af.glue_job_link]
    when:
      same_subject: true
      all:
        - fact: af.glue_job_link
          expr: "measures.airflow_retries_effective > 0 and measures.glue_max_retries > 0"
    status: structural
    severity_default: P2
    runtime_scope: {}
    explanation: >
      A task do `GlueJobOperator` tem `retries` efetivo maior que zero — da própria
      task, de `default_args`, e nunca do default publicado, que é `0` conforme
      `core.default_task_retries`, "The number of retries each task is going to have by
      default" — e o `aws_glue_job` de mesmo `name` declara `max_retries` maior que
      zero. As duas camadas de retry existem sobre o mesmo job. Cada retentativa do
      Airflow chama `StartJobRun` de novo: é um JobRun novo, que relê a entrada e
      reescreve a saída do começo, não uma retomada. Na API do Glue, `MaxRetries` é "The
      maximum number of times to retry this job after a JobRun fails.", e os parâmetros
      de `StartJobRun` não o incluem — leitura nossa: o Airflow não o sobrescreve. O que
      nenhuma das duas documentações descreve é a COMPOSIÇÃO das duas camadas (U1 do
      `define`). Esta regra afirma só que as duas existem; não afirma quantas vezes o
      job roda numa falha, porque esse número não é publicado. O vínculo entre a task e
      o recurso é por `job_name` literal igual ao `name` do recurso — nome em Jinja,
      variável ou recurso ausente saem em `af.unresolved`, nunca como vínculo. Ver
      knowledge/airflow/glue-operator.md, lacuna 1.
    proposed_change:
      - "Escolher UMA camada de retry para a falha do job: `max_retries = 0` no `aws_glue_job` e o retry no Airflow (onde `retries` e `retry_delay` são explícitos e aparecem no histórico da task), ou `retries = 0` na task e o retry no próprio Glue."
      - "Antes de escolher, medir: os JobRuns do job no intervalo de uma falha real (`sparkforge collect glue-job-runs`) ao lado das tentativas da task no Airflow mostram quantos JobRuns uma falha produziu de fato."
      - "Se o job escreve em modo append, tornar a escrita idempotente antes de manter qualquer retry: cada tentativa é um JobRun que escreve de novo (SF-GLUE-004)."
    action:
      kind: orchestration.restrict_run_policy
      target: glue.max_retries
      direction: decrease
      requires_absent: []
      moves:
        - cost.dpu_seconds
        - correctness.write_result
      depends_on: []
    risks:
      - "Zerar `max_retries` tira a retentativa que hoje cobre falhas transitórias quando o job roda fora do DAG (disparo manual ou outro gatilho)."
      - "A regra não mede quantas vezes o job rodou: o número depende da composição que a documentação não descreve."
    tradeoffs:
      - "Retry no Airflow é visível no histórico da task e configurável por DAG; retry no Glue vale para qualquer gatilho do job. Manter as duas é escolha possível, desde que alguém tenha medido o que ela custa."
    validation:
      - "`sparkforge fuse` sobre os facts de `analyze airflow-dag` e `analyze terraform` mostra o `af.glue_job_link` com `glue_max_retries: 0` ou `airflow_retries_effective: 0`, e `sparkforge judge` não produz mais SF-AIRFLOW-004."
      - "EIXO DE RESULTADO — numa execução de teste com falha induzida, o destino tem a mesma contagem total e por chave de negócio que uma execução sem falha, e o número de JobRuns do intervalo é o que a camada escolhida declara."
      - "O histórico da task no Airflow mostra, para a falha, no máximo 1 + `retries` tentativas, e `get-job-runs` mostra o número de JobRuns que a camada escolhida justifica."
    rollback:
      - "Restaurar o `max_retries` anterior no Terraform e o `retries` anterior no DAG, e reaplicar os dois."
    sources:
      - {url: "https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html", retrieved: 2026-09-20}
      - {url: "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html", retrieved: 2026-09-19}
      - {url: "https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html", retrieved: 2026-09-19}
```

`rules/catalog/action_kinds.yaml` **NÃO muda**: os dois `kind` e os três eixos usados já
estão no vocabulário fechado. Medido nesta árvore antes de começar: `cost.dpu_seconds`
vai de 3 para 5, `cost.provisioned_capacity_time` de 6 para 7, e `correctness.write_result`
é `nature: risk` e fica fora da restrição — o maior grupo continua sendo
`runtime.wall_clock` com **12**, que é o que `tests/test_agentic_executor_ordering.py`
afirma.

**3d. Rota — `rules/catalog/routing.yaml`** (tem BOM: edite com Edit, nunca reescreva o
arquivo inteiro). Troque

```yaml
fallback:
  recommended_skill: sparkforge-diagnose
```

por

```yaml
  # SF-AIRFLOW entrou com `docs/sdd/AIRFLOW_DAG/` (2026-09-20) e ganha ENTRADA PROPRIA
  # pelo motivo de sempre: `rule_areas` do agente NAO roteia, e `findings_area` conta
  # por prefixo exato do `rule_id` ate o ultimo hifen.
  #
  # `glue-infra-reviewer` e o dono pelo mesmo motivo de AGENT-086: as quatro regras
  # julgam COMO o job Glue e disparado e quantas vezes ele roda -- espera, prazo, forma
  # de esperar e retry --, e o conserto mora no arquivo do DAG e no `max_retries` do
  # `aws_glue_job`, nao no codigo do job. PRECEDENCIA: depois de AGENT-002 e de
  # AGENT-086; um case com SF-GLUE ou SF-SFN junto vai pela rota de cima, e o destino e
  # o mesmo.
  - id: AGENT-087
    phase_in: [diagnosis, hypothesis, design, verification, documentation]
    title: Achado dominante em como o DAG do Airflow dispara o job Glue
    when:
      all:
        - {findings_area: SF-AIRFLOW, count_gt: 0}
    recommended_agent: glue-infra-reviewer
    reason: >
      O DAG que dispara o job decide se o fluxo espera o job terminar, o que acontece
      com o JobRun quando a task e morta, se a espera segura um slot de worker, e
      quantas vezes uma falha reexecuta o job inteiro. O conserto mora no arquivo do DAG
      e no `max_retries` do `aws_glue_job` -- artefato de infraestrutura, que este
      coordenador ja le --, e nao no codigo do job.

fallback:
  recommended_skill: sparkforge-diagnose
```

**3e. Coordenador — `agents/glue-infra-reviewer.md`.** Troque
`rule_areas: [SF-GLUE, SF-ENV, SF-SFN]` por
`rule_areas: [SF-GLUE, SF-ENV, SF-SFN, SF-AIRFLOW]`, e troque

```markdown
como o default.

## Três armadilhas que a infraestrutura esconde
```

por

```markdown
como o default.

A área `SF-AIRFLOW` julga esses facts. Com o Terraform do mesmo job no case,
`sparkforge_fuse` liga a task ao `aws_glue_job` de mesmo `name` (`af.glue_job_link`), e
é aí que as duas camadas de retry aparecem juntas: o `max_retries` do job e o `retries`
do Airflow. A composição das duas não é documentada — afirme que as duas existem, nunca
quantas vezes o job roda numa falha. E lembre do que a leitura estática **não** alcança:
DAG montado em laço, TaskFlow API e argumento em Jinja saem em `af.unresolved` com a
razão, e nenhuma regra dispara sobre eles.

## Três armadilhas que a infraestrutura esconde
```

Espelhos: backup do `.claude/agents/README.md`, `python scripts/sync_skills.py`, devolva
o README; e o mesmo parágrafo **à mão** em `.codex/agents/glue-infra-reviewer.toml`, logo
depois da linha equivalente do `developer_instructions`.

**3f. As duas listas manuais do extrator, no mesmo commit do golden.**

`tests/test_rules_catalog_reachability.py` — as **duas** ocorrências (o import e a tupla
`EXTRACTORS`). No import, troque

```python
from sparkforge.facts import (
    athena_workgroup,
```

por

```python
from sparkforge.facts import (
    airflow_dag,
    athena_workgroup,
```

e na tupla `EXTRACTORS`, troque

```python
EXTRACTORS = (
    athena_workgroup,
```

por

```python
EXTRACTORS = (
    # `airflow_dag` entra nas DUAS listas manuais no MESMO commit da area SF-AIRFLOW:
    # sem ele aqui, os seis kinds `af.*` contam como orfaos e as quatro regras seriam
    # forcadas a `blocked_on` sobre um extrator que esta no repositorio.
    airflow_dag,
    athena_workgroup,
```

`tests/test_fixtures_kind_coverage.py` — import: troque

```python
from sparkforge.facts import (
    athena_workgroup,
```

por

```python
from sparkforge.facts import (
    airflow_dag,
    athena_workgroup,
```

e no dicionário `EXTRACTORS`, troque

```python
EXTRACTORS = {
    "athena_workgroup": athena_workgroup,
```

por

```python
EXTRACTORS = {
    # `airflow_dag` entra nas DUAS listas no MESMO commit de `fixtures/airflow/`: sem
    # ele aqui, os seis kinds `af.*` nao sao verificados por ninguem e o criterio de
    # golden -- todo kind de `EMITTED_KINDS` em algum golden -- passa sem ser avaliado,
    # que e pior do que falhar.
    "airflow_dag": airflow_dag,
    "athena_workgroup": athena_workgroup,
```

**3g. `scripts/regen_fixtures.py`** — o par do `_extract` do golden.

Imports: troque

```python
from sparkforge.facts.sql_literal import extract_sql_path  # noqa: E402
```

por

```python
from sparkforge.facts.airflow_dag import (  # noqa: E402
    build_af_glue_link,
    extract_airflow_dag_tree,
)
from sparkforge.facts.sql_literal import extract_sql_path  # noqa: E402
```

(Se o `ruff`/isort quiser o bloco do `airflow_dag` mais acima na lista de imports de
`sparkforge.facts.*`, aceite o que ele escrever.)

Constante: troque

```python
FIXTURES_STEPFUNCTIONS = ROOT / "fixtures" / "stepfunctions"
```

por

```python
FIXTURES_STEPFUNCTIONS = ROOT / "fixtures" / "stepfunctions"
FIXTURES_AIRFLOW = ROOT / "fixtures" / "airflow"
```

Função: troque

```python
def regen_dq(directory: Path) -> None:
```

por

```python
def regen_airflow(directory: Path) -> None:
    """DAGs do Apache Airflow: `*.py` sob input/, e `main.tf` ao lado quando houver.

    O PAR de `tests/test_fixtures_golden_airflow.py::_extract`, e a mesma porta do
    produto: fixture so com `.py` e o que `analyze airflow-dag` ve; com `.tf` ao lado,
    extrai o Terraform e deriva `af.glue_job_link` como `fusion.fuse` faz. Os `.py`
    daqui sao DAG, e NAO passam por `extract_tree` do PySpark: o corpus de
    `pyspark_ast` e outro, e repetir os dois aqui faria uma mudanca em `pyspark_ast`
    quebrar este golden pelo motivo errado.
    """
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    input_dir = directory / "input"
    facts = list(extract_airflow_dag_tree(input_dir, repo_root=input_dir))
    if any(input_dir.rglob("*.tf")):
        facts.extend(extract_terraform_tree(input_dir, repo_root=input_dir))
        facts.extend(build_af_glue_link(facts))
    facts = sort_facts(facts)
    findings = judge(facts, load_catalog(), meta["runtime"])
    _write_expected(directory, facts, findings)


def regen_dq(directory: Path) -> None:
```

Despacho por nome: troque

```python
                (FIXTURES_STEPFUNCTIONS / name, regen_stepfunctions),
```

por

```python
                (FIXTURES_STEPFUNCTIONS / name, regen_stepfunctions),
                (FIXTURES_AIRFLOW / name, regen_airflow),
```

Laço completo: troque

```python
    if FIXTURES_STEPFUNCTIONS.is_dir():
        for directory in sorted(p for p in FIXTURES_STEPFUNCTIONS.iterdir() if p.is_dir()):
            regen_stepfunctions(directory)
```

por

```python
    if FIXTURES_STEPFUNCTIONS.is_dir():
        for directory in sorted(p for p in FIXTURES_STEPFUNCTIONS.iterdir() if p.is_dir()):
            regen_stepfunctions(directory)
    # Mesma guarda de existencia: `fixtures/airflow/` nasce nesta entrega.
    if FIXTURES_AIRFLOW.is_dir():
        for directory in sorted(p for p in FIXTURES_AIRFLOW.iterdir() if p.is_dir()):
            regen_airflow(directory)
```

**3h. Regenerar e LER o golden.**

```bash
git add sparkforge/facts/airflow_dag.py tests/test_fixtures_golden_airflow.py
python scripts/regen_fixtures.py sem_espera timeout_sem_stop espera_sincrona retry_duas_camadas dag_limpo retry_so_no_glue retry_so_no_airflow job_name_nao_literal dag_dinamico python_invalido taskflow_decorador
```

Confira a saída linha a linha contra o `expects_rules` de cada `meta.yaml`:
SF-AIRFLOW-001 só em `sem_espera`; SF-AIRFLOW-002 só em `timeout_sem_stop`;
SF-AIRFLOW-003 só em `espera_sincrona`; SF-AIRFLOW-004 só em `retry_duas_camadas`; nada
em `dag_limpo`, `retry_so_no_glue`, `retry_so_no_airflow`, `job_name_nao_literal`,
`dag_dinamico`, `python_invalido` e `taskflow_decorador`.

- **Regra que apareça fora dessa lista é achado que ninguém pediu: pare e relate.**
- Se um `expects_kinds` divergir do conjunto medido, o `meta.yaml` é que está errado:
  corrija-o para o medido e diga no relatório qual mudou. `expects_rules` é contrato, e
  divergência nele é motivo de parar.

**3i. Registros que a regra e o extrator movem.**

- `manifest.json`: `"rule_count": 161,` → `"rule_count": 165,`.
- Fontes: `python scripts/refresh_knowledge.py --offline --update` (três URLs novas das
  regras entram em `knowledge/sources.lock.json`: o `index.html` do `GlueJobOperator` no
  provider Amazon, `configurations-ref` e `core-concepts/tasks` do core. As duas da API
  do Glue já estavam, por `rules/catalog/timeout.yaml` e `rules/catalog/stepfunctions.yaml`,
  e ganham o vínculo com `SF-AIRFLOW-004`.)
- Goldens de assessment (carregam a contagem do catálogo):
  `python scripts/regen_fixtures.py glue_40_para_60_salto_longo glue_51_para_60_iceberg_ansi glue_60_fgac_com_jar config_por_caminho_indireto lote_misto_iceberg_parquet`.
  Confira com `git diff --stat -- fixtures/scenarios evals/holdout` e
  `git diff -- fixtures/scenarios evals/holdout | grep '^[-+] '`: só `catalog_rules`
  (161 → 165), `unguarded_rules` (135 → 139: as quatro têm `runtime_scope: {}`) e a
  frase `statement` que repete os dois ("Catalogo: 165 regras, ... e 139 sem guarda").
  **Qualquer outra linha é achado que mudou: pare e relate.**
- `tests/test_databricks_rule_audit.py`, em `SO_AWS`: troque

  ```python
      "stepfunctions": (
          "le a definicao ASL do AWS Step Functions (`arn:aws:states`) e deriva "
          "`sfn.glue_job_link` do `aws_glue_job` do Terraform"
      ),
  ```

  por

  ```python
      "stepfunctions": (
          "le a definicao ASL do AWS Step Functions (`arn:aws:states`) e deriva "
          "`sfn.glue_job_link` do `aws_glue_job` do Terraform"
      ),
      # O ARTEFATO nao e da AWS -- o arquivo .py de um DAG do Apache Airflow --, e a
      # entrada aqui nao e sobre ele: as quatro regras SF-AIRFLOW julgam so o
      # `GlueJobOperator`, que chama `StartJobRun` da API do AWS Glue, e a derivacao
      # `af.glue_job_link` le o `aws_glue_job` do Terraform. Sem esta entrada, as
      # quatro (sem eixo de plataforma no `runtime_scope`) contariam como alcancaveis
      # num job Databricks, e o texto delas cita Glue.
      "airflow_dag": (
          "le o DAG do Airflow, e as regras julgam so o `GlueJobOperator` (StartJobRun "
          "da API do AWS Glue); deriva `af.glue_job_link` do `aws_glue_job` do Terraform"
      ),
  ```

- `sparkforge/agentic/executor/debate_evidence.py`, em `EVIDENCE_EXTRACTORS`: troque

  ```python
      "athena-workgroup": ("athena_workgroup", "extract_athena_workgroup_path"),
  ```

  por

  ```python
      "airflow-dag": ("airflow_dag", "extract_airflow_dag_path"),
      "athena-workgroup": ("athena_workgroup", "extract_athena_workgroup_path"),
  ```

  `extract_airflow_dag_path(path, repo_root)` tem a assinatura que
  `tests/test_agentic_debate_evidence.py::test_todo_extrator_da_lista_recebe_path_e_repo_root`
  exige, e o módulo não é de transcript. No comentário acima do dicionário, troque
  `carregar os 23 extratores para` por `carregar os 24 extratores para`.
- `docs/agentic-evolution-report.md` linha 205: `executor confere o extrator contra uma
  allowlist de 23, confina o` → `executor confere o extrator contra uma allowlist de 24,
  confina o`.
- Referência: `python scripts/gen_reference_docs.py` (a página do agente muda com
  `rule_areas`).

**3j. Números.** `docs/superpowers/STATUS.md`, trocas de prefixo de linha (o resto de
cada linha fica como está), antes → depois:

```text
| Regras de diagnóstico | **161**, sendo **98 `confirmed`** e **63 com `status: structural`**, todas executáveis —
| Regras de diagnóstico | **165**, sendo **98 `confirmed`** e **67 com `status: structural`**, todas executáveis — as quatro `SF-AIRFLOW` (como o DAG do Apache Airflow dispara o job Glue) entraram em 2026-09-20 (feature `docs/sdd/AIRFLOW_DAG/`), as quatro `structural`: nenhuma delas tem fronteira de versão publicada, e o que cada uma afirma é a forma declarada no DAG. Leitura anterior de **161**, sendo **98 `confirmed`** e **63 com `status: structural`**, todas executáveis —
```

```text
| Regras com eixo de resultado no `validation` | **161 de 161 têm `validation`** —
| Regras com eixo de resultado no `validation` | **165 de 165 têm `validation`** — as quatro `SF-AIRFLOW` (2026-09-20) entram com eixo de resultado. Leitura anterior de **161 de 161 têm `validation`** —
```

```text
| Fact kinds distintos emitidos | **238** —
| Fact kinds distintos emitidos | **239** — `af.glue_job_link` (2026-09-20), derivado em `fuse` quando o DAG e o Terraform do job estão no mesmo pool. Leitura anterior de **238** —
```

```text
| Rotas determinísticas | **41** —
| Rotas determinísticas | **42** — a acrescida é `AGENT-087` (2026-09-20, feature `docs/sdd/AIRFLOW_DAG/`), que leva achado `SF-AIRFLOW` a `glue-infra-reviewer`. Leitura anterior de **41** —
```

```text
| Fixtures golden | **528** em 57 domínios —
| Fixtures golden | **539** em 58 domínios — as **11** acrescidas formam o domínio novo `fixtures/airflow/` (2026-09-20, feature `docs/sdd/AIRFLOW_DAG/`), sintéticas a partir dos exemplos da documentação do provider Amazon; quatro trazem o `main.tf` do job ao lado do DAG. Leitura anterior de **528** em 57 domínios —
```

```text
| Fontes oficiais vigiadas | **262** (247 móveis, 15 fixas) —
| Fontes oficiais vigiadas | **265** (250 móveis, 15 fixas) — as **três** acrescidas são citadas pelas regras `SF-AIRFLOW` (2026-09-20, feature `docs/sdd/AIRFLOW_DAG/`): a página do `GlueJobOperator` no provider Amazon, `configurations-ref` e `core-concepts/tasks` do guia do Airflow. As duas da API do Glue já estavam no lock. Leitura anterior de **262** (247 móveis, 15 fixas) —
```

A linha "Regras com `runtime_scope` não-vazio" **não muda** (continua 26): as quatro
declaram `{}`. A linha "Coordenadores" **não muda** (continua 12): nenhum agente novo.

`README.md`: linha 45, `Os 40 extratores emitem 238 kinds distintos` →
`Os 40 extratores emitem 239 kinds distintos`; linha 46, `**161** regras de diagnóstico
em YAML, **161 delas executáveis**` → `**165** regras de diagnóstico em YAML, **165 delas
executáveis**`.

E a prosa auditada:

- `docs/guia/06-extrair-julgar-compor.md`: linha 86, `emitem 238 kinds` →
  `emitem 239 kinds`; linha 232, `nenhum dos 238 kinds` → `nenhum dos 239 kinds`.
- `docs/guia/07-conhecimento-e-catalogo.md`:
  - `desse conhecimento: **161** regras de` → `desse conhecimento: **165** regras de`;
  - `**161 delas executáveis**, ou seja, todas` → `**165 delas executáveis**, ou seja, todas`;
  - `mais **41** rotas determinísticas` → `mais **42** rotas determinísticas`;
  - ``As 161 executáveis se distribuem em 29 áreas (medido em 2026-09-19 com `area_of`):``
    → ``As 165 executáveis se distribuem em 30 áreas (medido em 2026-09-20 com `area_of`):``;
  - ``(fronteira do Spark 4), `SF-SFN` 4 (como o AWS`` →
    ``(fronteira do Spark 4), `SF-AIRFLOW` 4 (como o DAG do Apache Airflow dispara o job Glue), `SF-SFN` 4 (como o AWS``;
  - `Cada uma das 161 carrega` → `Cada uma das 165 carrega`.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_airflow_dag.py tests/test_fixtures_golden_airflow.py -q
python -m pytest tests/test_facts_fusion.py tests/test_fixtures_golden_fusion.py -q
python -m pytest tests/test_criterio_de_dominio.py -q
```

O primeiro comando fecha AC3–AC6: o golden prova as três regras que o DAG sozinho
sustenta e `test_fuse_liga_a_task_ao_job_e_nomeia_o_que_nao_liga` é o `verified_by` da
AC6. O último é o `verified_by` da AC8
(`test_todo_coordenador_tem_rota_por_artefato`): a área `SF-AIRFLOW` tem regra
executável que julga, o `glue-infra-reviewer` a declara, e a rota `AGENT-087` dispara
por `findings_area`.

### 5. Gates vizinhos

Regra, `runtime_scope`, área, extrator, corpus, routing, agent, fontes (seções de
`docs/gates-por-mudanca.md`), **um comando por vez**:

```bash
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py tests/test_rules_engine.py -q
python -m pytest tests/test_agent_coverage.py tests/test_router_agents.py tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py -q
python -m pytest tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py tests/test_rules_action_field.py tests/test_rules_campos_de_lista.py -q
python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py -q
python -m pytest tests/test_databricks_rule_audit.py tests/test_agentic_executor_ordering.py tests/test_harness_untrusted.py tests/test_sf_stubs.py -q
python -m pytest tests/test_agentic_debate_evidence.py tests/test_debate_suite.py -q
python -m pytest tests/test_verify_wheel.py tests/test_case_router.py tests/test_case_store.py tests/test_artifact_contents.py -q
python -m pytest tests/test_fixtures_scenarios.py tests/test_evals_holdout.py -q
python scripts/sync_skills.py --check
python -m pytest tests/test_agents_parity.py tests/test_sync_render.py tests/test_reference_docs.py -q
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py tests/test_facts_scan.py -q
python -m ruff check sparkforge scripts tests
python scripts/check_status_numbers.py --strict
python scripts/check_vnext_claims.py
```

(backup e devolução do `.claude/agents/README.md` em volta do sync e de
`test_agents_parity.py`.)

`test_rules_threshold_mutation.py` tem de passar **SEM entrada nova** em
`FRONTEIRA_SEM_GOLDEN`: `retry_so_no_glue` e `retry_so_no_airflow` existem para matar as
duas trocas `>`→`>=` da `expr` da `SF-AIRFLOW-004`, e as outras três regras não têm
`expr`. Se o teste pedir exceção, a fixture correspondente é que está errada.

O gate de lastro reprova de novo pelo corpus de `.py`: agora são **onze** arquivos novos
(o módulo de golden mais os dez DAGs de fixture — `retry_so_no_glue`,
`retry_so_no_airflow` e as outras oito, contando um `.py` por fixture). Remedie pelos
ids que a saída listar, como em T1.

### 6. Commit

`feat(rules): add the SF-AIRFLOW area judging how an Airflow DAG triggers Glue jobs`,
com no corpo: 4 regras (161 → 165), a rota `AGENT-087`, o kind derivado
`af.glue_job_link` em `fuse`, 11 fixtures no domínio novo, 3 fontes novas.

## T4 — o documento de conhecimento, o manual de uso e os registros finais

### 1. O teste que falha

Esta tarefa não tem teste próprio: o vermelho é o do **lock de superfície**, que acusa o
documento de `knowledge/` novo no disco enquanto o lock ainda diz 54 (regra 26).
Diferente do STEP_FUNCTIONS, o lock de **fontes** não fica vermelho aqui: as três URLs
do Airflow já entraram em T3, citadas pelas regras, e o documento cita as mesmas — o que
o `refresh_knowledge` acrescenta em T4 é só o vínculo `docs` de cada uma.

Escreva `knowledge/airflow/glue-operator.md` (arquivo novo, inteiro):

```markdown
# GlueJobOperator do Airflow: espera, prazo, forma de esperar e retry

> **Lido em 2026-09-20.** Três páginas oficiais do Apache Airflow — uma do provider
> Amazon e duas do core — mais as duas páginas da API do AWS Glue já citadas em
> `knowledge/stepfunctions/glue-integration.md`. Quem consome: o extrator
> `sparkforge/facts/airflow_dag.py` (os defaults publicados moram lá, com a URL ao
> lado) e as quatro regras de `rules/catalog/airflow.yaml`. Frase entre aspas é
> citação literal; o resto é leitura nossa, e diz de qual frase veio.

## 1. Os três parâmetros do operador que decidem o que acontece com o job

Da página do `GlueJobOperator` no provider Amazon:

| parâmetro | default publicado | o que a documentação diz |
|---|---|---|
| `wait_for_completion` | `True` | "Whether to wait for job run completion" |
| `deferrable` | `False` | "If True, the operator will wait asynchronously for the job to complete" |
| `stop_job_run_on_kill` | `False` | "If True, Operator will stop the job run when task is killed" |
| `job_poll_interval` | `6` | intervalo entre consultas ao job |
| `job_name` | `aws_glue_default_job` | nome do job Glue a disparar |

Leitura nossa, a partir das três primeiras linhas: **nenhum dos três aparece no código
PySpark nem no event log do job.** Eles moram no arquivo do DAG, e é por isso que o
SparkForge o lê.

## 2. O prazo da task, e o que o core publica

- `execution_timeout` (core-concepts/tasks): "If you want a task to have a maximum
  runtime, set its `execution_timeout` attribute to a `datetime.timedelta` value that
  is the maximum permissible runtime." A mesma página **não** publica o default de
  `retries`.
- `core.default_task_retries`, default `0` (configurations-ref): "The number of retries
  each task is going to have by default". `core.default_task_retry_delay` é `300`, e
  `core.default_task_execution_timeout` é vazio.

Leitura nossa: um DAG que não escreve `retries` em lugar nenhum tem `retries` efetivo
`0`, e por isso a `SF-AIRFLOW-004` não dispara sobre DAG que nunca pediu retentativa.

## 3. O lado do Glue

- `MaxRetries`: "The maximum number of times to retry this job after a JobRun fails."
  (aws-glue-api-jobs-job).
- Os parâmetros de `StartJobRun` não incluem `MaxRetries` (aws-glue-api-jobs-runs):
  leitura nossa — o Airflow não o sobrescreve ao disparar.

## 4. O que cada regra afirma, e o que ela não afirma

| regra | afirma | não afirma |
|---|---|---|
| SF-AIRFLOW-001 | `wait_for_completion=False` com tarefa a jusante: a próxima roda com o job em execução | que o job vai falhar |
| SF-AIRFLOW-002 | prazo declarado com `stop_job_run_on_kill` ausente ou `False`: o operador não para o JobRun | o que acontece com o JobRun depois disso (lacuna 2) |
| SF-AIRFLOW-003 | espera síncrona: o slot de worker fica ocupado pelo tempo do job | que falta slot no ambiente — isso é medida do Airflow, e não está aqui |
| SF-AIRFLOW-004 | as duas camadas de retry existem sobre o mesmo job | quantas vezes o job roda numa falha (lacuna 1) |

O vínculo da SF-AIRFLOW-004 é por `job_name` literal igual ao `name` do `aws_glue_job`,
feito em `fuse`. Nome em `{{ jinja }}`, variável, f-string e job ausente do Terraform
saem em `af.unresolved` com a razão, nunca como vínculo.

## 5. Lacunas nomeadas

1. **Composição dos retries.** Nenhuma das duas documentações descreve como o `retries`
   do Airflow compõe com o `MaxRetries` do Glue. Cada retentativa da task é um
   `StartJobRun` novo, e o retry do Glue é outro JobRun. O que destrava afirmar a
   contagem de tentativas: os JobRuns do intervalo de uma falha real
   (`sparkforge collect glue-job-runs`) ao lado do histórico da task.
2. **JobRun quando a task é morta com `stop_job_run_on_kill` False.** A documentação do
   provider diz o que o parâmetro faz quando é `True`, e não descreve o que acontece
   com o JobRun quando é `False` e a task é morta (U3 de
   `docs/sdd/AIRFLOW_DAG/define.md`). A regra afirma o que a documentação sustenta — o
   operador não para o job — e não afirma o que o Glue faz depois.
3. **Triggerer.** A espera diferida (`deferrable=True`) precisa de um processo
   `triggerer` no ambiente. **Nenhuma das três páginas lidas publica esse requisito**, e
   o arquivo do DAG não diz se o ambiente tem um: por isso a `SF-AIRFLOW-003` traz o
   ponto como `risks` e nenhum fact o afirma. O que destrava: ler a página de deferring
   do guia do Airflow e a página de versões do ambiente gerenciado em uso.
4. **DAG real não observado.** O corpus `fixtures/airflow/` é sintético, montado a
   partir dos exemplos da documentação do provider (U2 do `define`). Um DAG real do
   operador, lido na conversa e nunca commitado, é o que o testaria contra produção.
5. **O que a leitura estática não alcança.** DAG montado em laço ou por factory,
   TaskFlow API (`@task`, `@dag`) e argumento resolvido em execução (variável,
   f-string, `{{ jinja }}`) saem em `af.unresolved` nomeado. Importar o DAG para
   resolvê-los executaria código do operador, e o repositório não executa artefato.

## Fontes

- Provider Amazon — `GlueJobOperator`: `wait_for_completion`, `deferrable`, `stop_job_run_on_kill`, `job_poll_interval` e `job_name`, com os defaults. https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/operators/glue/index.html (retrieved 2026-09-20)
- Guia do Apache Airflow — referência de configuração: `core.default_task_retries`, `core.default_task_retry_delay` e `core.default_task_execution_timeout`. https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html (retrieved 2026-09-20)
- Guia do Apache Airflow — tasks: `execution_timeout`. https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/tasks.html (retrieved 2026-09-20)
- API do AWS Glue — Jobs: `MaxRetries`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-job.html (retrieved 2026-09-19)
- API do AWS Glue — Job runs: os parâmetros de `StartJobRun`. https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html (retrieved 2026-09-19)
```

### 2. Rodar e ver falhar

```bash
python -m pytest "tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches" -q
```

Falha esperada: `AssertionError` com `document_count` 55 medido contra 54 no lock (e o
`by_name_sha256` divergindo junto).

### 3. Código mínimo

`knowledge/airflow-pipelines.md` — o ponteiro para o documento novo (D7). Troque

```markdown
Fonte: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
```

por

```markdown
Os defaults do `GlueJobOperator` — `wait_for_completion`, `deferrable` e
`stop_job_run_on_kill` — e o `retries` do Airflow estão com a frase citada e a data de
leitura em [`knowledge/airflow/glue-operator.md`](airflow/glue-operator.md), que é o que
as regras `SF-AIRFLOW` consomem. Este arquivo guarda princípio; aquele guarda fonte.

Fonte: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
```

Lock de fontes (o vínculo `docs` das três URLs passa a citar o documento novo):

```bash
python scripts/refresh_knowledge.py --offline --update
```

Manifesto offline — o `sha256` pela função que o gate confere, nunca por outro hash:

```bash
python -c "import json; from pathlib import Path; from sparkforge.tools.offline import _content_sha256; p = Path('knowledge/offline-manifest.json'); m = json.loads(p.read_text(encoding='utf-8')); doc = 'knowledge/airflow/glue-operator.md'; m['documents'] = [d for d in m['documents'] if d['path'] != doc] + [{'path': doc, 'title': 'glue-operator', 'sha256': _content_sha256(Path(doc))}]; m['documents'].sort(key=lambda d: d['path']); p.write_bytes((json.dumps(m, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))"
```

(O manifesto está ordenado por `path` e gravado como `json.dumps(indent=2)` mais `\n` —
medido nesta árvore; `write_bytes` evita o CRLF do Windows. `knowledge/airflow-pipelines.md`
já está no manifesto e o `sha256` dele **também muda**, porque o ponteiro acima altera o
arquivo: repita a mesma receita para ele, trocando `doc` e o `title`.)

`parity.yaml`, na capacidade de T2: troque

```yaml
    cli: [analyze airflow-dag]
    platforms:
```

por

```yaml
    cli: [analyze airflow-dag]
    knowledge:
      - knowledge/airflow/glue-operator.md
    platforms:
```

Manual de uso — `docs/guia/usos/airflow.md` (arquivo novo, inteiro; o bloco externo usa
`~~~~` porque o manual tem blocos de código dentro. Os links relativos são
`../../../` — três níveis, porque a página mora em `docs/guia/usos/`):

~~~~markdown
# Airflow: como o DAG dispara o job Glue

O **Apache Airflow** dispara boa parte dos jobs Glue, e três defaults do
`GlueJobOperator` decidem o que acontece com o job sem aparecer no código PySpark nem no
event log: `wait_for_completion`, `deferrable` e `stop_job_run_on_kill`. Este manual
mostra como o SparkForge lê o arquivo `.py` do DAG e confere quatro coisas: se o fluxo
**espera** o job, se o Airflow **mata** a task deixando o job rodando, se a espera
**segura** um slot de worker, e — com o Terraform do job ao lado — se o **retry** existe
nas duas camadas.

O SparkForge **não importa e não executa** o DAG: ele o lê por AST. Todos os exemplos
usam arquivos sintéticos de `fixtures/airflow/`.

## Receita rápida

```bash
mkdir -p /tmp/af

# 1. Extrair os facts do DAG (arquivo .py ou a pasta de DAGs)
sparkforge analyze airflow-dag \
  --path fixtures/airflow/sem_espera/input --out /tmp/af/facts_airflow.json

# 2. Julgar: SF-AIRFLOW-001 a 003 leem so o DAG
sparkforge judge --facts /tmp/af/facts_airflow.json

# 3. Com o Terraform do job: extrair os dois lados, fundir e julgar
sparkforge analyze airflow-dag \
  --path fixtures/airflow/retry_duas_camadas/input --out /tmp/af/af.json
sparkforge analyze terraform \
  --path fixtures/airflow/retry_duas_camadas/input --out /tmp/af/tf.json
sparkforge fuse --facts /tmp/af/af.json --facts /tmp/af/tf.json --out /tmp/af/fundidos.json
sparkforge judge --facts /tmp/af/fundidos.json
```

## O que sai

| kind | um por | o que diz |
|---|---|---|
| `af.dag` | chamada `DAG(...)` | `dag_id` e `schedule` quando literais, e o `default_args` com `retries` e `execution_timeout` |
| `af.task` | operador instanciado | classe, `task_id`, `has_downstream`, e para o `GlueJobOperator` o `job_name` literal, o efetivo de `wait_for_completion`/`deferrable`/`stop_job_run_on_kill` com a marca de omitido, o `retries` efetivo e se `execution_timeout` está declarado |
| `af.dependency` | elo declarado | `>>`, `<<`, `set_downstream` ou `set_upstream`, com a forma que o declarou |
| `af.glue_job_link` | task ligada a um `aws_glue_job` (só em `fuse`) | o `retries` efetivo do Airflow e o `max_retries` do job |
| `af.unresolved` | o que não deu para ler ou ligar | a razão: argumento não literal, DAG em laço, TaskFlow, Python inválido, `job_name` dinâmico, job ausente do Terraform |
| `af.analyzed` | arquivo | as contagens — prova de que o arquivo foi lido |

**Argumento que não é literal nunca vira o default.** `wait_for_completion=ESPERA`,
`job_name=f"carga-{dominio}"` e `job_name="{{ var.value.job }}"` saem em `af.unresolved`
com a razão, e o atributo correspondente fica ausente — a regra então fica calada, em
vez de julgar um valor que ninguém leu.

## As quatro regras

| regra | dispara quando | severidade |
|---|---|---|
| `SF-AIRFLOW-001` | `wait_for_completion=False` e a task tem tarefa a jusante: a próxima roda com o job em execução | P2 |
| `SF-AIRFLOW-002` | `execution_timeout` declarado (na task ou em `default_args`) e `stop_job_run_on_kill` ausente ou `False`: o Airflow mata a task e o operador não para o JobRun | P1 |
| `SF-AIRFLOW-003` | a task espera o job (default `True`) sem `deferrable` (default `False`): o slot de worker fica preso pelo tempo do job | P3 |
| `SF-AIRFLOW-004` | a task ligada ao job tem `retries` efetivo maior que zero e o job tem `max_retries` maior que zero | P2 |

A `SF-AIRFLOW-004` afirma só que as duas camadas existem. **Quantas vezes o job roda
numa falha não é documentado** — cada retentativa da task é um `StartJobRun` novo, e o
retry do Glue é outro JobRun. Medir exige os JobRuns do intervalo de uma falha real
(`sparkforge collect glue-job-runs`) ao lado do histórico da task.

## O que ele não faz

- Não importa nem executa o DAG, e por isso não resolve DAG montado em laço, por factory
  ou por import: sai `af.unresolved` com `dag_dinamico`.
- Não lê a TaskFlow API além de reconhecer `@dag`, `@task` e `@task_group` e nomear o
  que não leu.
- Não lê metadado do Airflow em execução (task instances, duração, retentativas que
  aconteceram): isso exige acesso ao banco ou à API.
- Não lê dependência **entre DAGs** (`ExternalTaskSensor`, `TriggerDagRunOperator`).
- Não julga outros operadores (EMR, Athena, Lambda): o extrator os registra, e nenhuma
  regra os julga.

## Referência

- As frases citadas e as lacunas: [`knowledge/airflow/glue-operator.md`](../../../knowledge/airflow/glue-operator.md).
- As regras: [`rules/catalog/airflow.yaml`](../../../rules/catalog/airflow.yaml).
- O corpus: [`fixtures/airflow/`](../../../fixtures/airflow/).
~~~~

Superfície (documento de `knowledge/` novo move o lock — regra 26):

```bash
python scripts/check_surface_lock.py --update
```

Critério de domínio — `docs/gates-por-mudanca.md`, seção "Critério de domínio: artefato
antes de nome": Airflow deixa de estar entre os domínios sem artefato. Troque

```markdown
depois o coordenador que sabe quando investigá-la. Domínio que ainda não tem artefato
(Airflow, DynamoDB, Kinesis, Lambda) não ganha agente nem área: ganha `unresolved`
nomeando o artefato que falta. Step Functions saiu desta lista em 2026-09-19 pela porta
certa (`docs/sdd/STEP_FUNCTIONS/`): o extrator da definição ASL veio primeiro, a área
`SF-SFN` julga os facts dele, e `glue-infra-reviewer` a declara com rota por
`findings_area`. Foi por essa porta que 35 áreas e 26
```

por

```markdown
depois o coordenador que sabe quando investigá-la. Domínio que ainda não tem artefato
(DynamoDB, Kinesis, Lambda) não ganha agente nem área: ganha `unresolved` nomeando o
artefato que falta. Step Functions saiu desta lista em 2026-09-19 pela porta certa
(`docs/sdd/STEP_FUNCTIONS/`): o extrator da definição ASL veio primeiro, a área
`SF-SFN` julga os facts dele, e `glue-infra-reviewer` a declara com rota por
`findings_area`. Airflow saiu em 2026-09-20 pela mesma porta
(`docs/sdd/AIRFLOW_DAG/`): o extrator do arquivo `.py` do DAG veio primeiro, a área
`SF-AIRFLOW` julga os facts dele, e o mesmo coordenador a declara com a rota
`AGENT-087`. Foi por essa porta que 35 áreas e 26
```

Nenhuma linha da tabela *Números correntes* de `docs/superpowers/STATUS.md` se move nesta
tarefa: as três URLs entraram em T3, e não há medida publicada de documento de
`knowledge/` — o que trava esse crescimento é `docs/surface.lock.json` (regra 26).

### 4. Rodar e ver passar

```bash
python -m pytest "tests/test_surface_lock.py::TestOLockBateComAMedida::test_the_knowledge_matches" -q
python scripts/verify_offline_bundle.py
python scripts/check_status_numbers.py --strict
```

Os dois últimos são os `verified_by` da AC9 e da AC10: `"ok": true` e
`0 divergencia(s)`.

### 5. Gates vizinhos

"Editar um documento em `knowledge/`", a referência gerada e os números:

```bash
python -m pytest tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q
python -m pytest tests/test_capability_parity.py tests/test_surface_lock.py tests/test_reference_docs.py -q
python -m pytest tests/test_status_numbers_gate.py tests/test_criterio_de_dominio.py tests/test_sdd.py -q
python -m pytest tests/test_docs_coverage.py tests/test_knowledge_freshness.py -q
python scripts/check_vnext_claims.py
```

`test_reference_docs.py` confere que todo comando que o manual ensina existe
(`analyze airflow-dag`, `analyze terraform`, `fuse`, `judge`) e que os links relativos
resolvem — é ele que pega o erro de profundidade (`../../` em vez de `../../../`).

### 6. Commit

`docs(knowledge): cite the Airflow GlueJobOperator sources and add the usage guide`,
com o crescimento da superfície em bytes no corpo.

## Antes de fechar a feature

```bash
sparkforge sdd stamp --repo . --feature AIRFLOW_DAG --phase plan
sparkforge sdd check --repo . --feature AIRFLOW_DAG --phase plan
```

E, quando os quatro commits estiverem de pé, a suíte **em lotes, um por vez**, pela
receita de `tests/test_suite_batches.py::LOTES` — nunca a suíte inteira num processo só,
e nunca com edição na árvore ao mesmo tempo.

---

## Dúvidas

Três refinações do desenho, já aplicadas no corpo do plano, e duas perguntas de
manifesto. As cinco precisam de confirmação; nenhuma bloqueia a execução.

1. **`execution_timeout`: declaração lida, valor medido só quando exato.** D2 manda que
   argumento não literal deixe o atributo ausente. `timedelta(hours=2)` é `ast.Call` —
   não literal —, e aplicar D2 ao pé da letra deixaria a `SF-AIRFLOW-002` calada em todo
   DAG real. O plano separa DECLARAÇÃO (lida do AST, sempre exata) de VALOR (medida só
   quando é `timedelta(**literais)`), e não emite `af.unresolved` quando o valor não é
   computável, porque nada do que a regra lê deixou de ser lido. **Confirme ou peça a
   leitura literal de D2** — e, se for a literal, a `SF-AIRFLOW-002` precisa de outro
   gatilho.
2. **Uma razão a mais que a lista de D1: `multiplos_dags`.** Com dois ou mais `DAG(...)`
   no mesmo arquivo, não há como dizer de qual vem o `default_args` de uma task. O plano
   recusa: `default_args` fica ilegível para o arquivo inteiro e a lacuna sai nomeada.
   A alternativa seria herdar do primeiro DAG, que é afirmação sem leitura.
3. **Uma fixture a mais que a lista de D8: `retry_so_no_airflow`.** Medido:
   `tests/test_rules_threshold_mutation.py` compara `FRONTEIRA_SEM_GOLDEN` por igualdade
   exata, e a `expr` da `SF-AIRFLOW-004` tem duas comparações `> 0`. D8 traz só a
   fixture que mata uma delas. São 11 fixtures, e a contagem publicada vira 539 em 58
   domínios.
4. **Duplicação declarada: `_glue_jobs_por_nome` e `_max_retries`.** As duas são gêmeas
   das de `sparkforge/facts/stepfunctions.py`, e o plano as duplica em
   `airflow_dag.py` com o comentário dizendo por quê (um leitor de DAG não deveria
   importar um leitor de ASL para ler Terraform). O lugar certo delas é um módulo
   próprio — `sparkforge/facts/glue_terraform.py` —, que **não está no manifesto deste
   desenho** e custaria refatorar um arquivo recém-mesclado. Proposta: incremento
   separado, depois desta feature. Confirme ou mande unificar agora.
5. **Páginas geradas e espelhos que o manifesto lista, e os cinco goldens de
   assessment.** `gen_reference_docs.py` reescreve `docs/guia/referencia/cli/analyze.md`
   e `docs/guia/referencia/agents/glue-infra-reviewer.md` (T2 e T3), e `sync_skills.py`
   reescreve os três espelhos de `glue-infra-reviewer` (T2 e T3) — o manifesto os lista,
   e o `files` das tarefas também. Já o manifesto lista **um** golden de assessment
   (`glue_40_para_60_salto_longo`) dizendo que ele representa "três cenários e dois
   holdout"; o `files` de T3 lista os cinco por extenso, como o STEP_FUNCTIONS fez.
   Confirme ou reduza.

