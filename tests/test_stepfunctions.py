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
