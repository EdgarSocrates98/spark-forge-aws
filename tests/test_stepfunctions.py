"""O extrator de ASL do AWS Step Functions: o que a definicao diz sobre como chama o Glue.

Definicoes sinteticas, montadas a partir dos exemplos oficiais: nenhum ASL real foi
observado (U2 de `docs/sdd/STEP_FUNCTIONS/define.md`).
"""
import json

from sparkforge.facts.stepfunctions import (
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_TIMEOUT_SECONDS,
    extract_stepfunctions,
    extract_stepfunctions_path,
    extract_stepfunctions_tree,
)

ASL_COM_PARALLEL_E_MAP = {
    "Comment": "Glue .sync com retry implicito, Glue sem .sync, e um Map com Lambda",
    "StartAt": "Cargas",
    "States": {
        "Cargas": {
            "Type": "Parallel",
            "Branches": [
                {
                    "StartAt": "CargaClientes",
                    "States": {
                        "CargaClientes": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::glue:startJobRun.sync",
                            "Parameters": {"JobName": "carga-clientes"},
                            "Retry": [{"ErrorEquals": ["States.ALL"]}],
                            "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ClientesFalhou"}],
                            "End": True,
                        },
                        "ClientesFalhou": {"Type": "Fail"},
                    },
                },
                {
                    "StartAt": "CargaPedidos",
                    "States": {
                        "CargaPedidos": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::glue:startJobRun",
                            "Parameters": {"JobName.$": "$.job"},
                            "TimeoutSeconds": 3600,
                            "Next": "Esperar",
                        },
                        "Esperar": {"Type": "Wait", "Seconds": 5, "End": True},
                    },
                },
            ],
            "Next": "Lotes",
        },
        "Lotes": {
            "Type": "Map",
            "ItemProcessor": {
                "ProcessorConfig": {"Mode": "INLINE"},
                "StartAt": "Validar",
                "States": {
                    "Validar": {
                        "Type": "Task",
                        "Resource": "arn:aws:states:::lambda:invoke.waitForTaskToken",
                        "Parameters": {
                            "FunctionName": "validar-lote",
                            "Payload": {"token.$": "$$.Task.Token"},
                        },
                        "End": True,
                    }
                },
            },
            "End": True,
        },
    },
}

CLIENTES = "States/Cargas/Branches/0/States/CargaClientes"
PEDIDOS = "States/Cargas/Branches/1/States/CargaPedidos"
VALIDAR = "States/Lotes/ItemProcessor/States/Validar"


def _tasks(facts):
    return {f.subject["symbol"]: f for f in facts if f.kind == "sfn.task"}


def test_task_glue_vira_fact_com_retry_efetivo():
    facts = extract_stepfunctions(ASL_COM_PARALLEL_E_MAP, "sm.asl.json")
    tasks = _tasks(facts)
    assert set(tasks) == {CLIENTES, PEDIDOS, VALIDAR}

    clientes = tasks[CLIENTES]
    assert clientes.attrs["service"] == "glue"
    assert clientes.attrs["api"] == "startJobRun"
    assert clientes.attrs["pattern"] == "sync"
    assert clientes.attrs["job_name"] == "carga-clientes"
    assert clientes.attrs["job_name_dynamic"] is False
    assert clientes.attrs["retriers"] == [
        {
            "error_equals": ["States.ALL"],
            "max_attempts": DEFAULT_MAX_ATTEMPTS,
            "max_attempts_defaulted": True,
        }
    ]
    assert clientes.attrs["failure_retry_matched"] is True
    assert clientes.attrs["failure_retry_defaulted"] is True
    assert clientes.measures["failure_retry_max_attempts"] == 3
    assert clientes.attrs["has_catch"] is True
    assert clientes.attrs["timeout_declared"] is False
    assert clientes.measures["timeout_seconds"] == DEFAULT_TIMEOUT_SECONDS
    assert clientes.attrs["state_machine_type"] == "undeclared"

    pedidos = tasks[PEDIDOS]
    assert pedidos.attrs["pattern"] == "request_response"
    assert pedidos.attrs["has_next"] is True
    assert pedidos.attrs["job_name"] is None
    assert pedidos.attrs["job_name_dynamic"] is True
    assert pedidos.attrs["job_name_source"] == "jsonpath"
    assert pedidos.attrs["retriers"] == []
    assert pedidos.attrs["failure_retry_matched"] is False
    assert pedidos.measures["failure_retry_max_attempts"] == 0
    assert pedidos.attrs["has_catch"] is False
    assert pedidos.attrs["timeout_declared"] is True
    assert pedidos.measures["timeout_seconds"] == 3600

    validar = tasks[VALIDAR]
    assert (validar.attrs["service"], validar.attrs["pattern"]) == ("lambda", "callback")
    assert validar.attrs["job_name_source"] == "not_applicable"

    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "undeclared"
    assert maquina.attrs["type_declared"] is False
    assert maquina.attrs["source"] == "asl"
    assert maquina.measures == {"state_count": 7, "task_count": 3}
    [sentinela] = [f for f in facts if f.kind == "sfn.analyzed"]
    assert sentinela.measures == {"state_machine_count": 1, "task_count": 3, "unresolved_count": 0}


def test_describe_state_machine_le_definition_e_tipo(tmp_path):
    definicao = {
        "StartAt": "Rodar",
        "States": {
            "Rodar": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun.sync",
                "Parameters": {"JobName": "carga-diaria"},
                "End": True,
            }
        },
    }
    express = {"name": "carga-expressa", "type": "EXPRESS", "definition": json.dumps(definicao)}
    sem_tipo = {"name": "carga", "definition": json.dumps(definicao)}
    (tmp_path / "express.json").write_text(json.dumps(express), encoding="utf-8")
    (tmp_path / "sem_tipo.json").write_text(json.dumps(sem_tipo), encoding="utf-8")

    facts = extract_stepfunctions_path(tmp_path / "express.json", repo_root=tmp_path)
    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "EXPRESS"
    assert maquina.attrs["type_declared"] is True
    assert maquina.attrs["source"] == "describe_state_machine"
    assert maquina.attrs["name"] == "carga-expressa"
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert task.attrs["state_machine_type"] == "EXPRESS"
    assert task.subject["file"] == "express.json"
    assert task.subject["symbol"] == "States/Rodar"

    facts = extract_stepfunctions_path(tmp_path / "sem_tipo.json", repo_root=tmp_path)
    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "undeclared"
    assert maquina.attrs["type_declared"] is False
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert task.attrs["state_machine_type"] == "undeclared"

    nao_string = {"name": "x", "type": "STANDARD", "definition": definicao}
    facts = extract_stepfunctions(nao_string, "q.json")
    motivos = [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"]
    assert motivos == ["definition_not_string"]


def test_o_que_nao_le_sai_nomeado(tmp_path):
    (tmp_path / "quebrado.asl.json").write_text('{"StartAt": "A", "States": {', encoding="utf-8")
    (tmp_path / "inventario.json").write_text('{"jobs": ["carga-diaria"]}', encoding="utf-8")
    facts = extract_stepfunctions_tree(tmp_path, repo_root=tmp_path)
    motivos = sorted(
        (f.subject["file"], f.attrs["reason"]) for f in facts if f.kind == "sfn.unresolved"
    )
    assert motivos == [
        ("inventario.json", "not_a_state_machine"),
        ("quebrado.asl.json", "invalid_json"),
    ]
    assert len([f for f in facts if f.kind == "sfn.analyzed"]) == 2

    asl = {
        "QueryLanguage": "JSONata",
        "StartAt": "Dinamico",
        "States": {
            "Dinamico": {"Type": "Task", "Resource": "{% $states.input.recurso %}", "End": True},
            "Jsonata": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun.sync",
                "Arguments": {"JobName": "{% $states.input.job %}"},
                "Retry": [
                    {"ErrorEquals": ["Glue.ConcurrentRunsExceededException"], "MaxAttempts": 5},
                    {"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 0},
                ],
                "End": True,
            },
            "Texto": "nao e um estado",
        },
    }
    facts = extract_stepfunctions(asl, "sm.asl.json")
    motivos = {f.subject["symbol"]: f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"}
    assert motivos == {"States/Dinamico": "resource_dynamic", "States/Texto": "state_not_an_object"}
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert task.attrs["job_name_source"] == "jsonata"
    assert task.attrs["job_name_dynamic"] is True
    assert task.attrs["query_language"] == "JSONata"
    assert task.attrs["failure_retry_matched"] is True
    assert task.attrs["failure_retry_defaulted"] is False
    assert task.measures["failure_retry_max_attempts"] == 0


def test_cli_e_tool_devolvem_os_mesmos_facts(tmp_path, capsys):
    from sparkforge.adapters.cli import main
    from sparkforge.adapters.tools import call_tool

    entrada = tmp_path / "entrada"
    entrada.mkdir()
    (entrada / "sm.asl.json").write_text(json.dumps(ASL_COM_PARALLEL_E_MAP), encoding="utf-8")
    saida = tmp_path / "facts.json"

    codigo = main(["analyze", "step-functions", "--path", str(entrada), "--out", str(saida)])
    capsys.readouterr()
    assert codigo == 0
    pela_cli = json.loads(saida.read_text(encoding="utf-8"))

    pela_tool = call_tool(
        "sparkforge_analyze_step_functions", {"path": str(entrada), "limit": 1000}
    )
    assert "error" not in pela_tool, pela_tool
    assert pela_tool["total_count"] == len(pela_cli)
    assert pela_tool["items"] == pela_cli
    assert pela_tool["by_kind"]["sfn.task"] == 3
    assert pela_tool["unresolved"] == 0

    erro = call_tool("sparkforge_analyze_step_functions", {"path": str(tmp_path / "nao-existe")})
    assert "sparkforge analyze step-functions" in erro["error"]


TF_CARGA_DIARIA = """resource "aws_glue_job" "carga_diaria" {
  name        = "carga-diaria"
  role_arn    = aws_iam_role.glue_role.arn
  max_retries = 2
}
"""

RUNTIME_GLUE = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def _glue_sync(nome_do_job: dict, retry: list, proximo: dict) -> dict:
    return {
        "Type": "Task",
        "Resource": "arn:aws:states:::glue:startJobRun.sync",
        "Parameters": nome_do_job,
        "Retry": retry,
        **proximo,
    }


def test_fuse_liga_task_ao_job_e_nomeia_o_que_nao_liga(tmp_path):
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.terraform import extract_terraform_tree
    from sparkforge.rules.engine import judge
    from sparkforge.rules.loader import load_catalog

    asl = {
        "StartAt": "Ligada",
        "States": {
            "Ligada": _glue_sync(
                {"JobName": "carga-diaria"},
                [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 2}],
                {"Next": "Dinamica"},
            ),
            "Dinamica": _glue_sync(
                {"JobName.$": "$.job"},
                [{"ErrorEquals": ["States.ALL"]}],
                {"Next": "SemDefinicao"},
            ),
            "SemDefinicao": _glue_sync(
                {"JobName": "job-que-nao-esta-no-terraform"},
                [{"ErrorEquals": ["States.ALL"]}],
                {"End": True},
            ),
        },
    }
    (tmp_path / "sm.asl.json").write_text(json.dumps(asl), encoding="utf-8")
    (tmp_path / "main.tf").write_text(TF_CARGA_DIARIA, encoding="utf-8")
    so_asl = extract_stepfunctions_tree(tmp_path, repo_root=tmp_path)
    so_tf = extract_terraform_tree(tmp_path, repo_root=tmp_path)

    fundidos = fuse(so_asl + so_tf)

    [link] = [f for f in fundidos if f.kind == "sfn.glue_job_link"]
    assert link.subject["symbol"] == "States/Ligada"
    assert link.attrs["resource"] == "aws_glue_job.carga_diaria"
    assert link.attrs["job_name"] == "carga-diaria"
    assert link.attrs["glue_max_retries_source"] == "literal"
    assert link.measures == {"sfn_retry_effective": 2, "glue_max_retries": 2}
    motivos = {
        f.subject["symbol"]: f.attrs["reason"] for f in fundidos if f.kind == "sfn.unresolved"
    }
    assert motivos == {
        "States/Dinamica": "job_name_dynamic",
        "States/SemDefinicao": "job_definition_absent",
    }

    achados = judge(fundidos, load_catalog(), RUNTIME_GLUE)
    quatro = [a.subject["symbol"] for a in achados if a.rule_id == "SF-SFN-004"]
    assert quatro == ["States/Ligada"]

    # fuse sem Terraform no pool nao inventa vinculo
    assert not [f for f in fuse(so_asl) if f.kind == "sfn.glue_job_link"]
    # e pool sem Step Functions sai do fuse sem nenhum sfn.*
    assert not [f for f in fuse(so_tf) if f.kind.startswith("sfn.")]


# --------------------------------------------------------------------------
# Revisao final da feature: os achados, um teste por achado.
# --------------------------------------------------------------------------

TF_DOIS_JOBS_MESMO_NOME = """resource "aws_glue_job" "a" {
  name        = "carga-diaria"
  role_arn    = aws_iam_role.glue_role.arn
  max_retries = 1
}

resource "aws_glue_job" "b" {
  name        = "carga-diaria"
  role_arn    = aws_iam_role.glue_role.arn
  max_retries = 1
}
"""

TF_MAX_RETRIES_INTERPOLADO = """resource "aws_glue_job" "carga_diaria" {
  name        = "carga-diaria"
  role_arn    = aws_iam_role.glue_role.arn
  max_retries = var.tentativas
}
"""


def _fundir(pasta, asl: dict, tf: str = TF_CARGA_DIARIA):
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.terraform import extract_terraform_tree

    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "sm.asl.json").write_text(json.dumps(asl), encoding="utf-8")
    (pasta / "main.tf").write_text(tf, encoding="utf-8")
    so_asl = extract_stepfunctions_tree(pasta, repo_root=pasta)
    so_tf = extract_terraform_tree(pasta, repo_root=pasta)
    return fuse(so_asl + so_tf)


def _regras(facts, regra: str) -> list:
    from sparkforge.rules.engine import judge
    from sparkforge.rules.loader import load_catalog

    return [a for a in judge(facts, load_catalog(), RUNTIME_GLUE) if a.rule_id == regra]


def _motivos(facts) -> list[tuple[str, str]]:
    return sorted(
        (f.subject["symbol"], f.attrs["reason"]) for f in facts if f.kind == "sfn.unresolved"
    )


def test_link_so_para_task_sync(tmp_path):
    """Request Response: o retrier cobre so a chamada StartJobRun, nao a falha do job."""
    asl = {
        "StartAt": "Disparo",
        "States": {
            "Disparo": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun",
                "Parameters": {"JobName": "carga-diaria"},
                "Retry": [{"ErrorEquals": ["States.ALL"], "MaxAttempts": 2}],
                "End": True,
            }
        },
    }
    fundidos = _fundir(tmp_path, asl)
    assert not [f for f in fundidos if f.kind == "sfn.glue_job_link"]
    assert not [f for f in fundidos if f.kind == "sfn.unresolved"]
    assert not _regras(fundidos, "SF-SFN-004")


def test_max_attempts_ilegivel_sai_nomeado_com_estado_e_indice():
    asl = {
        "StartAt": "Rodar",
        "States": {
            "Rodar": {
                "Type": "Task",
                "Resource": "arn:aws:states:::glue:startJobRun.sync",
                "Parameters": {"JobName": "carga-diaria"},
                "Retry": [
                    {"ErrorEquals": ["States.ALL"], "MaxAttempts": "2"},
                    {"ErrorEquals": ["Glue.X"], "MaxAttempts": 2.5},
                    {"ErrorEquals": ["Glue.Y"], "MaxAttempts": -1},
                    {"ErrorEquals": ["Glue.Z"], "MaxAttempts": 1},
                ],
                "End": True,
            }
        },
    }
    facts = extract_stepfunctions(asl, "sm.asl.json")
    ilegiveis = sorted(
        (f.subject["symbol"], f.attrs["reason"], f.attrs["retrier_index"])
        for f in facts
        if f.kind == "sfn.unresolved"
    )
    assert ilegiveis == [
        ("States/Rodar", "max_attempts_unreadable", 0),
        ("States/Rodar", "max_attempts_unreadable", 1),
        ("States/Rodar", "max_attempts_unreadable", 2),
    ]
    [task] = [f for f in facts if f.kind == "sfn.task"]
    assert "failure_retry_max_attempts" not in task.measures
    assert all(
        isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in task.measures.values()
    )


def test_json_profundo_e_arquivo_grande_nao_derrubam(tmp_path, monkeypatch):
    from sparkforge.facts import scan

    profundo = "[" * 200_000 + "]" * 200_000
    (tmp_path / "fundo.asl.json").write_text(profundo, encoding="utf-8")
    facts = extract_stepfunctions_path(tmp_path / "fundo.asl.json", repo_root=tmp_path)
    assert [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"] == ["json_too_deep"]

    describe = {"name": "x", "type": "STANDARD", "definition": profundo}
    facts = extract_stepfunctions(describe, "describe.json")
    assert [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"] == ["json_too_deep"]

    (tmp_path / "grande.asl.json").write_text(json.dumps(ASL_COM_PARALLEL_E_MAP), encoding="utf-8")
    monkeypatch.setattr(scan, "TAMANHO_MAXIMO_DADOS_BYTES", 16)
    facts = extract_stepfunctions_path(tmp_path / "grande.asl.json", repo_root=tmp_path)
    assert [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"] == [
        "size_above_limit"
    ]
    assert len([f for f in facts if f.kind == "sfn.analyzed"]) == 1


def test_memory_error_do_decodificador_vira_recusa_nomeada(tmp_path, monkeypatch):
    """O `_loads` daqui e o de `sfn_history.py` sao gemeos, e tratavam falhas diferentes.

    `sfn_history._loads` ja nomeava `MemoryError` como `json_too_large`; este nao, e
    `extract_stepfunctions_path` chamado direto -- fora de `_tree`, que tem `except
    Exception` -- propagaria o erro e quebraria o "NUNCA levanta excecao por payload
    malformado" do proprio docstring do modulo. Payload hostil grande o bastante e a
    terceira forma de falha do decodificador, ao lado de `RecursionError` e
    `ValueError`, e ela nao derruba quem chamou.
    """
    import json as _json

    from sparkforge.facts import stepfunctions

    def _estoura(*args, **kwargs):
        raise MemoryError("payload hostil")

    (tmp_path / "hostil.asl.json").write_text(
        _json.dumps({"StartAt": "A", "States": {}}), encoding="utf-8"
    )
    monkeypatch.setattr(stepfunctions.json, "loads", _estoura)

    facts = extract_stepfunctions_path(tmp_path / "hostil.asl.json", repo_root=tmp_path)
    assert [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"] == [
        "json_too_large"
    ]
    # A sentinela sai do mesmo jeito: o arquivo foi visitado, e isso continua verdade.
    assert len([f for f in facts if f.kind == "sfn.analyzed"]) == 1

    # E pelo `definition` do `describe-state-machine`, que e o outro chamador.
    facts = extract_stepfunctions(
        {"name": "x", "type": "STANDARD", "definition": "{}"}, "describe.json"
    )
    assert "json_too_large" in [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"]


ASL_POLLING = {
    "Comment": "startJobRun sem .sync, Wait, aws-sdk glue:getJobRun e Choice",
    "StartAt": "Iniciar",
    "States": {
        "Iniciar": {
            "Type": "Task",
            "Resource": "arn:aws:states:::glue:startJobRun",
            "Parameters": {"JobName": "carga-diaria"},
            "Next": "Esperar",
        },
        "Esperar": {"Type": "Wait", "Seconds": 60, "Next": "Consultar"},
        "Consultar": {
            "Type": "Task",
            "Resource": "arn:aws:states:::aws-sdk:glue:getJobRun",
            "Parameters": {"JobName": "carga-diaria", "RunId.$": "$.JobRunId"},
            "Next": "Terminou",
        },
        "Terminou": {
            "Type": "Choice",
            "Choices": [
                {"Variable": "$.JobRun.JobRunState", "StringEquals": "RUNNING", "Next": "Esperar"}
            ],
            "Default": "Fim",
        },
        "Fim": {"Type": "Succeed"},
    },
}


def test_polling_com_get_job_run_nao_e_sf_sfn_001():
    facts = extract_stepfunctions(ASL_POLLING, "sm.asl.json")
    tasks = _tasks(facts)
    assert tasks["States/Iniciar"].attrs["polled_by_get_job_run"] is True
    consultar = tasks["States/Consultar"]
    assert (consultar.attrs["service"], consultar.attrs["api"]) == ("glue", "getJobRun")
    assert not _regras(facts, "SF-SFN-001")

    sem_consulta = json.loads(json.dumps(ASL_POLLING))
    del sem_consulta["States"]["Consultar"]
    sem_consulta["States"]["Esperar"]["Next"] = "Fim"
    facts = extract_stepfunctions(sem_consulta, "sm.asl.json")
    assert _tasks(facts)["States/Iniciar"].attrs["polled_by_get_job_run"] is False
    [achado] = _regras(facts, "SF-SFN-001")
    assert achado.severity == "P2"
    assert "o desfecho do JobRun" not in achado.explanation


def _parallel(task_end: dict, conteiner: dict) -> dict:
    return {
        "StartAt": "Cargas",
        "States": {
            "Cargas": {
                "Type": "Parallel",
                "Branches": [
                    {
                        "StartAt": "Disparo",
                        "States": {
                            "Disparo": {
                                "Type": "Task",
                                "Resource": "arn:aws:states:::glue:startJobRun",
                                "Parameters": {"JobName": "carga-diaria"},
                                **task_end,
                            }
                        },
                    }
                ],
                **conteiner,
            },
            "Publicar": {"Type": "Pass", "End": True},
        },
    }


def test_task_end_de_ramo_herda_o_next_do_conteiner():
    simbolo = "States/Cargas/Branches/0/States/Disparo"
    com_next = extract_stepfunctions(_parallel({"End": True}, {"Next": "Publicar"}), "a.json")
    task = _tasks(com_next)[simbolo]
    assert task.attrs["has_next"] is False
    assert task.attrs["enclosing_has_next"] is True
    assert task.attrs["effective_has_next"] is True
    assert [a.subject["symbol"] for a in _regras(com_next, "SF-SFN-001")] == [simbolo]

    terminal = extract_stepfunctions(_parallel({"End": True}, {"End": True}), "b.json")
    task = _tasks(terminal)[simbolo]
    assert task.attrs["enclosing_has_next"] is False
    assert task.attrs["effective_has_next"] is False
    assert not _regras(terminal, "SF-SFN-001")

    # No nivel de cima nao ha conteiner: o efetivo e o Next do proprio estado.
    topo = extract_stepfunctions(ASL_COM_PARALLEL_E_MAP, "c.json")
    assert _tasks(topo)[PEDIDOS].attrs["effective_has_next"] is True


def test_job_name_ausente_nao_e_dinamico(tmp_path):
    asl = {
        "StartAt": "SemNome",
        "States": {
            "SemNome": _glue_sync({}, [{"ErrorEquals": ["States.ALL"]}], {"Next": "NaoTexto"}),
            "NaoTexto": _glue_sync(
                {"JobName": 42}, [{"ErrorEquals": ["States.ALL"]}], {"End": True}
            ),
        },
    }
    fundidos = _fundir(tmp_path, asl)
    assert _motivos(fundidos) == [
        ("States/NaoTexto", "job_name_absent"),
        ("States/SemNome", "job_name_absent"),
    ]
    assert all(t.attrs["job_name_dynamic"] is False for t in _tasks(fundidos).values())


def test_link_deriva_dos_tf_attribute_que_usou(tmp_path):
    asl = {
        "StartAt": "Ligada",
        "States": {
            "Ligada": _glue_sync(
                {"JobName": "carga-diaria"},
                [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 2}],
                {"End": True},
            )
        },
    }
    fundidos = _fundir(tmp_path, asl)
    [link] = [f for f in fundidos if f.kind == "sfn.glue_job_link"]
    usados = {
        f.attrs["key"]: f.id
        for f in fundidos
        if f.kind == "tf.attribute"
        and f.attrs.get("block") == "root"
        and f.attrs["key"] in {"name", "max_retries"}
    }
    [task] = [f for f in fundidos if f.kind == "sfn.task"]
    assert link.provenance["derived_from"] == [task.id, usados["name"], usados["max_retries"]]


def test_tipo_fora_de_standard_e_express_sai_nomeado():
    definicao = json.dumps({"StartAt": "P", "States": {"P": {"Type": "Pass", "End": True}}})
    facts = extract_stepfunctions({"type": "EXPRESSO", "definition": definicao}, "d.json")
    assert [f.attrs["reason"] for f in facts if f.kind == "sfn.unresolved"] == [
        "type_unrecognized"
    ]
    [maquina] = [f for f in facts if f.kind == "sfn.state_machine"]
    assert maquina.attrs["type"] == "undeclared"


def test_map_iterator_legado_e_lido():
    asl = {
        "StartAt": "Lotes",
        "States": {
            "Lotes": {
                "Type": "Map",
                "Iterator": {
                    "StartAt": "Carga",
                    "States": {
                        "Carga": {
                            "Type": "Task",
                            "Resource": "arn:aws:states:::glue:startJobRun.sync",
                            "Parameters": {"JobName": "carga-diaria"},
                            "End": True,
                        }
                    },
                },
                "End": True,
            }
        },
    }
    facts = extract_stepfunctions(asl, "m.json")
    assert set(_tasks(facts)) == {"States/Lotes/Iterator/States/Carga"}


def test_job_ambiguo_e_max_retries_nao_literal_saem_nomeados(tmp_path):
    asl = {
        "StartAt": "Ligada",
        "States": {
            "Ligada": _glue_sync(
                {"JobName": "carga-diaria"}, [{"ErrorEquals": ["States.ALL"]}], {"End": True}
            )
        },
    }
    ambiguo = _fundir(tmp_path / "a", asl, TF_DOIS_JOBS_MESMO_NOME)
    assert _motivos(ambiguo) == [("States/Ligada", "job_definition_ambiguous")]
    assert not [f for f in ambiguo if f.kind == "sfn.glue_job_link"]

    interpolado = _fundir(tmp_path / "b", asl, TF_MAX_RETRIES_INTERPOLADO)
    assert _motivos(interpolado) == [("States/Ligada", "glue_max_retries_not_literal")]
    [link] = [f for f in interpolado if f.kind == "sfn.glue_job_link"]
    assert link.attrs["glue_max_retries_source"] == "not_literal"
    assert "glue_max_retries" not in link.measures
    assert not _regras(interpolado, "SF-SFN-004")


def test_step_functions_e_extrator_de_evidencia_do_debate():
    from sparkforge.agentic.executor import debate_evidence as de

    assert de._extrator("step-functions") is extract_stepfunctions_path
