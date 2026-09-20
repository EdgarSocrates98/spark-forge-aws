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
    """As tasks por `task_id`: o `subject` da `af.task` nao afirma simbolo.

    Ver `test_o_subject_da_task_nao_afirma_simbolo_de_codigo`: a task ancora
    localizacao, e quem carrega o `task_id` e `attrs`.
    """
    return {f.attrs["task_id"]: f for f in facts if f.kind == kind}


def _task_id_derivado(facts, fact):
    """O `task_id` da `af.task` de que ESTE fact derivou, pela propria procedencia.

    Os facts de `build_af_glue_link` copiam o subject da task, que nao nomeia a
    task. `provenance.derived_from` e a referencia que sobra -- e a mesma que a
    derivacao declara.
    """
    tasks = {f.id: f for f in facts if f.kind == "af.task"}
    for origem in (fact.provenance or {}).get("derived_from", []):
        if origem in tasks:
            return tasks[origem].attrs["task_id"]
    return ""


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


def test_o_subject_da_task_nao_afirma_simbolo_de_codigo():
    """`task_id` e variavel de modulo, e `subject.symbol` promete SIMBOLO indexado.

    O gold set de recuperacao (`sparkforge/economy/goldset.py`) segue a cadeia
    `finding.evidence -> fact.subject.{file, symbol}` e exige que o simbolo
    exista no indice de codigo daquele arquivo `.py`. Um `task_id` ali dentro
    pede do pack um `def`/`class` que nunca existiu, e a ancora nao fecha.

    A task se identifica por LOCALIZACAO -- `file` e `line` --, que e o que
    `_subject_group_key` usa quando nao ha `symbol`, e e o mesmo recorte do
    `sfn.task`. O `task_id` continua em `attrs`, onde a regra o le.
    """
    facts = extract_airflow_dag(DAG_COM_TRES_TASKS, "dags/carga_diaria.py")

    tasks = [f for f in facts if f.kind == "af.task"]
    assert {t.attrs["task_id"] for t in tasks} == {"carga", "enriquecer", "publicar"}
    assert {t.subject["symbol"] for t in tasks} == {""}
    # A identidade nao sumiu: a linha separa as tres tasks do mesmo arquivo.
    assert len({(t.subject["file"], t.subject["line"]) for t in tasks}) == 3


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
    # O vinculo herda o subject da task: localizacao, sem simbolo afirmado.
    assert link.subject == _por_kind(fundidos, "af.task")["ligada"].subject
    assert _task_id_derivado(fundidos, link) == "ligada"
    assert link.attrs["resource"] == "aws_glue_job.carga_diaria"
    assert link.attrs["job_name"] == "carga-diaria"
    assert link.attrs["glue_max_retries_source"] == "literal"
    assert link.measures == {"airflow_retries_effective": 2, "glue_max_retries": 2}
    assert len(link.provenance["derived_from"]) == 3

    motivos = {
        _task_id_derivado(fundidos, f): f.attrs["reason"]
        for f in fundidos
        if f.kind == "af.unresolved" and f.attrs["reason"] != "arg_nao_literal"
    }
    assert motivos == {
        "dinamica": "job_name_dynamic",
        "sem_definicao": "job_definition_absent",
    }

    achados = judge(fundidos, load_catalog(), RUNTIME_GLUE)
    [quatro] = [a for a in achados if a.rule_id == "SF-AIRFLOW-004"]
    # O achado aponta a LOCALIZACAO da task `ligada`, nao um simbolo de codigo.
    assert quatro.subject == _por_kind(fundidos, "af.task")["ligada"].subject

    # fuse sem Terraform no pool nao inventa vinculo
    assert not [f for f in fuse(so_dag) if f.kind == "af.glue_job_link"]
    # e pool sem Airflow sai do fuse sem nenhum af.*
    assert not [f for f in fuse(so_tf) if f.kind.startswith("af.")]


DAG_COM_O_QUE_NAO_SE_LE = '''
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import baseoperator
from airflow.decorators import dag
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

PRAZO = timedelta(hours=1)

with DAG(
    dag_id="cargas",
    schedule=AGENDA,
    start_date=datetime(2026, 1, 1),
) as principal:
    abrir = EmptyOperator(task_id="abrir")
    carga = GlueJobOperator(
        task_id="carga",
        job_name="carga-diaria",
        execution_timeout=PRAZO,
    )
    fechar = EmptyOperator(task_id="fechar")

    abrir.set_downstream(carga)
    fechar << carga
    baseoperator.chain(abrir, fechar)


@dag(schedule="@daily", start_date=datetime(2026, 1, 1))
def fluxo():
    dentro = GlueJobOperator(task_id="dentro", job_name="carga-dentro")
    return dentro
'''


def test_o_que_a_leitura_estatica_nao_alcanca_sai_com_razao_PROPRIA():
    """Cada lacuna tem nome proprio: `dag_dinamico` nao e o apelido de todas elas."""
    facts = extract_airflow_dag(DAG_COM_O_QUE_NAO_SE_LE, "dags/cargas.py")

    # `schedule=AGENDA` nao e literal: a MARCA sai, como `dag_id_literal` faz.
    [dag_fact] = [f for f in facts if f.kind == "af.dag"]
    assert dag_fact.attrs["schedule_declared"] is True
    assert dag_fact.attrs["schedule_literal"] is False
    assert "schedule" not in dag_fact.attrs

    # `execution_timeout=PRAZO`: a DECLARACAO e lida, o valor nao vira medida, e
    # nenhum `af.unresolved` sai -- nada do que a regra le deixou de ser lido (D2).
    tasks = _por_kind(facts, "af.task")
    carga = tasks["carga"]
    assert carga.attrs["execution_timeout_declared"] is True
    assert carga.attrs["execution_timeout_source"] == "task"
    assert "execution_timeout_seconds" not in carga.measures

    elos = sorted(
        (f.attrs["upstream"], f.attrs["downstream"], f.attrs["form"])
        for f in facts
        if f.kind == "af.dependency"
    )
    assert elos == [
        ("abrir", "carga", "set_downstream"),
        ("carga", "fechar", "lshift"),
    ]

    razoes = sorted(
        (f.attrs["reason"], f.attrs.get("form") or f.subject["symbol"])
        for f in facts
        if f.kind == "af.unresolved"
    )
    assert razoes == [
        # `baseoperator.chain(...)` chamado como ATRIBUTO nao some em silencio.
        ("dependencia_dinamica", "chain"),
        # Operador classico dentro de `def`: razao propria, nao `dag_dinamico`.
        ("operador_em_funcao", "dentro"),
        ("taskflow_decorador", "fluxo"),
    ]


def test_a_derivacao_nomeia_o_terraform_ambiguo_e_o_max_retries_nao_literal(tmp_path):
    """Os dois ramos de `build_af_glue_link` que nenhuma fixture exercita."""
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.terraform import extract_terraform_tree

    (tmp_path / "cargas.py").write_text(DAG_PAREADO, encoding="utf-8")
    (tmp_path / "main.tf").write_text(
        TF_CARGA_DIARIA
        + '\nresource "aws_glue_job" "carga_diaria_bis" {\n'
        '  name        = "carga-diaria"\n'
        "  role_arn    = aws_iam_role.glue_role.arn\n"
        "  max_retries = var.retries\n"
        "}\n",
        encoding="utf-8",
    )
    fundidos = fuse(
        extract_airflow_dag_tree(tmp_path, repo_root=tmp_path)
        + extract_terraform_tree(tmp_path, repo_root=tmp_path)
    )
    ambiguo = [f for f in fundidos if (f.attrs or {}).get("reason") == "job_definition_ambiguous"]
    assert [_task_id_derivado(fundidos, f) for f in ambiguo] == ["ligada"]
    assert ambiguo[0].attrs["resources"] == [
        "aws_glue_job.carga_diaria",
        "aws_glue_job.carga_diaria_bis",
    ]
    assert not [f for f in fundidos if f.kind == "af.glue_job_link"]

    (tmp_path / "main.tf").write_text(
        'resource "aws_glue_job" "carga_diaria" {\n'
        '  name        = "carga-diaria"\n'
        "  role_arn    = aws_iam_role.glue_role.arn\n"
        "  max_retries = var.retries\n"
        "}\n",
        encoding="utf-8",
    )
    fundidos = fuse(
        extract_airflow_dag_tree(tmp_path, repo_root=tmp_path)
        + extract_terraform_tree(tmp_path, repo_root=tmp_path)
    )
    [link] = [f for f in fundidos if f.kind == "af.glue_job_link"]
    assert link.attrs["glue_max_retries_source"] == "not_literal"
    assert "glue_max_retries" not in link.measures
    assert [
        _task_id_derivado(fundidos, f)
        for f in fundidos
        if (f.attrs or {}).get("reason") == "glue_max_retries_not_literal"
    ] == ["ligada"]
