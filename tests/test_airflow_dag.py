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
