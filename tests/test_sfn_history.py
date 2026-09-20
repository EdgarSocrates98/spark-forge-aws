"""O extrator do historico de execucao do AWS Step Functions: o que ACONTECEU.

Historicos sinteticos, montados a partir da forma de evento publicada em
`API_GetExecutionHistory`: nenhum historico real foi observado (U2 de
`docs/sdd/SFN_HISTORY/define.md`). A forma exata do `output` do `TaskSubmitted` do
Glue e a lacuna U1, e por isso o extrator le tres formas e nomeia o que nao reconhece.
"""
import json

from sparkforge.facts.sfn_history import (
    extract_sfn_history,
    extract_sfn_history_path,
    extract_sfn_history_tree,
)


def _evento(id_, anterior, tipo, segundo, **detalhes):
    # `segundo` e o DESLOCAMENTO em segundos desde 03:00:00, e por isso vira minuto e
    # segundo: `03:00:91` nao e ISO 8601, e o extrator recusaria a leitura do instante.
    evento = {
        "id": id_,
        "previousEventId": anterior,
        "timestamp": f"2026-09-18T03:{segundo // 60:02d}:{segundo % 60:02d}.000000+00:00",
        "type": tipo,
    }
    evento.update(detalhes)
    return evento


def _agendado(**extra):
    detalhes = {"resource": "startJobRun.sync", "resourceType": "glue"}
    detalhes.update(extra)
    return {"taskScheduledEventDetails": detalhes}


def _submetido(saida):
    detalhes = {"resource": "startJobRun.sync", "resourceType": "glue"}
    if saida is not None:
        detalhes["output"] = saida
    return {"taskSubmittedEventDetails": detalhes}


# Tres tentativas do MESMO estado, cada uma com um JobRun proprio, e a execucao
# terminando em falha. E o formato de resposta da API: objeto com `events`.
HISTORICO_COM_TRES_TENTATIVAS = {
    "events": [
        _evento(1, 0, "ExecutionStarted", 0),
        _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "CargaDiaria"}),
        _evento(3, 2, "TaskScheduled", 2, **_agendado(timeoutInSeconds=3600)),
        _evento(4, 3, "TaskStarted", 3, taskStartedEventDetails={"resourceType": "glue"}),
        _evento(
            5,
            4,
            "TaskSubmitted",
            4,
            **_submetido('{"JobRunId": "jr_a", "JobName": "carga-diaria"}'),
        ),
        _evento(
            6,
            5,
            "TaskFailed",
            30,
            taskFailedEventDetails={
                "resource": "startJobRun.sync",
                "resourceType": "glue",
                "error": "Glue.AWSGlueException",
                "cause": "JobRun jr_a FAILED",
            },
        ),
        _evento(7, 6, "TaskScheduled", 31, **_agendado()),
        _evento(8, 7, "TaskStarted", 32),
        _evento(9, 8, "TaskSubmitted", 33, **_submetido({"JobRunId": "jr_b"})),
        _evento(
            10,
            9,
            "TaskFailed",
            60,
            taskFailedEventDetails={
                "error": "Glue.AWSGlueException",
                "cause": "JobRun jr_b FAILED",
            },
        ),
        _evento(11, 10, "TaskScheduled", 61, **_agendado()),
        _evento(12, 11, "TaskStarted", 62),
        _evento(13, 12, "TaskSubmitted", 63, **_submetido({"JobRun": {"Id": "jr_c"}})),
        _evento(
            14,
            13,
            "TaskFailed",
            90,
            taskFailedEventDetails={
                "error": "Glue.AWSGlueException",
                "cause": "JobRun jr_c FAILED",
            },
        ),
        _evento(
            15,
            14,
            "ExecutionFailed",
            91,
            executionFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "esgotou"},
        ),
    ]
}


def _de(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_historico_vira_execucao_e_tentativas():
    facts = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")

    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["status"] == "failed"
    assert execucao.attrs["arn_declared"] is False
    assert execucao.attrs["source"] == "get_execution_history"
    assert execucao.attrs["truncated"] is False
    assert execucao.measures == {
        "event_count": 15,
        "attempt_count": 3,
        "job_run_count": 3,
        "duration_seconds": 91.0,
    }

    tentativas = sorted(_de(facts, "sfn.attempt"), key=lambda f: f.measures["attempt_index"])
    assert [t.measures["attempt_index"] for t in tentativas] == [1, 2, 3]
    assert {t.subject["symbol"] for t in tentativas} == {
        "CargaDiaria#1",
        "CargaDiaria#2",
        "CargaDiaria#3",
    }
    primeira = tentativas[0]
    assert primeira.attrs["state_name"] == "CargaDiaria"
    assert (primeira.attrs["service"], primeira.attrs["api"]) == ("glue", "startJobRun")
    assert primeira.attrs["pattern"] == "sync"
    assert primeira.attrs["resource"] == "startJobRun.sync"
    assert primeira.attrs["result"] == "failed"
    assert primeira.attrs["terminal_present"] is True
    assert primeira.attrs["submitted"] is True
    assert primeira.attrs["error"] == "Glue.AWSGlueException"
    assert primeira.attrs["cause"] == "JobRun jr_a FAILED"
    assert primeira.attrs["job_run_outcome_observed"] is True
    assert primeira.attrs["execution_outcome"] == "failed"
    assert primeira.attrs["execution_outcome_class"] == "finished"
    assert primeira.measures["duration_seconds"] == 28.0
    assert primeira.measures["timeout_seconds"] == 3600

    [sentinela] = _de(facts, "sfn.analyzed")
    assert sentinela.measures == {
        "execution_count": 1,
        "attempt_count": 3,
        "job_run_count": 3,
        "unresolved_count": 0,
    }


def test_job_run_vem_do_output_e_a_ausencia_sai_nomeada():
    facts = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")
    corridas = sorted(_de(facts, "sfn.job_run"), key=lambda f: f.subject["symbol"])
    assert [c.attrs["job_run_id"] for c in corridas] == ["jr_a", "jr_b", "jr_c"]
    # As TRES formas que o extrator aceita, e de qual chave cada uma veio (U1).
    assert [c.attrs["read_from"] for c in corridas] == ["JobRunId", "JobRunId", "JobRun.Id"]
    assert corridas[0].attrs["job_name"] == "carga-diaria"
    assert corridas[1].attrs["job_name"] is None
    assert [c.subject["symbol"] for c in corridas] == [
        "CargaDiaria#1",
        "CargaDiaria#2",
        "CargaDiaria#3",
    ]

    # `includeExecutionData` desligado: o `TaskSubmitted` vem sem `output`. Nenhum
    # `sfn.job_run` e afirmado, e a lacuna sai nomeada.
    sem_dado = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSubmitted", 3, **_submetido(None)),
            _evento(5, 4, "TaskSucceeded", 9),
            _evento(6, 5, "ExecutionSucceeded", 10),
        ]
    }
    facts = extract_sfn_history(sem_dado, "sem-dado.json")
    assert _de(facts, "sfn.job_run") == []
    motivos = {f.attrs["reason"] for f in _de(facts, "sfn.unresolved")}
    assert motivos == {"execution_data_absent"}

    # `output` presente e com forma que o extrator NAO reconhece: as chaves de topo
    # saem no fact, porque e delas que sai a resposta da lacuna U1.
    desconhecido = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSubmitted", 3, **_submetido({"SomethingElse": 1, "Outra": 2})),
            _evento(5, 4, "TaskSucceeded", 9),
            _evento(6, 5, "ExecutionSucceeded", 10),
        ]
    }
    facts = extract_sfn_history(desconhecido, "desconhecido.json")
    assert _de(facts, "sfn.job_run") == []
    [falha] = _de(facts, "sfn.unresolved")
    assert falha.attrs["reason"] == "job_run_id_unrecognized"
    assert falha.attrs["output_keys"] == ["Outra", "SomethingElse"]


def test_historico_incompleto_sai_nomeado_sem_perder_o_que_leu(tmp_path):
    # Truncado: `nextToken` na saida salva. O que foi lido continua valendo, e a
    # execucao sai `unresolved` porque o evento terminal pode estar na pagina que
    # ninguem salvou.
    truncado = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskStarted", 3),
        ],
        "nextToken": "AAAAKgAAAAIAAAAAAAAAAg==",
    }
    facts = extract_sfn_history(truncado, "truncado.json")
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["status"] == "unresolved"
    assert execucao.attrs["truncated"] is True
    [tentativa] = _de(facts, "sfn.attempt")
    assert tentativa.attrs["result"] == "none"
    assert tentativa.attrs["terminal_present"] is False
    assert tentativa.attrs["execution_outcome_class"] == "unresolved"
    assert "duration_seconds" not in tentativa.measures
    motivos = sorted(f.attrs["reason"] for f in _de(facts, "sfn.unresolved"))
    assert motivos == ["execution_terminal_absent", "truncated"]

    # Cadeia quebrada (o evento 7 aponta para um id que nao esta no arquivo), tipo
    # desconhecido, e evento que nao e objeto.
    esburacado = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSucceeded", 9),
            _evento(5, 4, "ExecutionSucceeded", 10),
            _evento(6, 4, "EventoDoFuturo", 10),
            _evento(7, 99, "TaskScheduled", 11, **_agendado()),
            "nao e um evento",
        ]
    }
    facts = extract_sfn_history(esburacado, "esburacado.json")
    motivos = sorted(f.attrs["reason"] for f in _de(facts, "sfn.unresolved"))
    assert motivos == ["event_not_an_object", "event_type_unknown", "state_unresolved"]
    desconhecido = [f for f in facts if f.attrs.get("reason") == "event_type_unknown"]
    assert desconhecido[0].attrs["type"] == "EventoDoFuturo"
    # O que foi lido continua valendo: a tentativa completa saiu.
    [tentativa] = _de(facts, "sfn.attempt")
    assert (tentativa.attrs["state_name"], tentativa.attrs["result"]) == ("Carga", "succeeded")

    # JSON invalido e JSON que nao e historico: um `sfn.unresolved` por arquivo, e a
    # sentinela sai dos dois.
    (tmp_path / "quebrado.json").write_text('{"events": [', encoding="utf-8")
    (tmp_path / "inventario.json").write_text('{"jobs": ["carga-diaria"]}', encoding="utf-8")
    facts = extract_sfn_history_tree(tmp_path, repo_root=tmp_path)
    assert sorted(
        (f.subject["file"], f.attrs["reason"]) for f in _de(facts, "sfn.unresolved")
    ) == [
        ("inventario.json", "not_an_execution_history"),
        ("quebrado.json", "invalid_json"),
    ]
    assert len(_de(facts, "sfn.analyzed")) == 2

    # A lista crua de eventos, sem o envelope da resposta, tambem e lida.
    (tmp_path / "lista.json").write_text(
        json.dumps(HISTORICO_COM_TRES_TENTATIVAS["events"]), encoding="utf-8"
    )
    facts = extract_sfn_history_path(tmp_path / "lista.json", repo_root=tmp_path)
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.attrs["source"] == "event_list"
    assert len(_de(facts, "sfn.attempt")) == 3


def test_cli_e_tool_devolvem_os_mesmos_facts(tmp_path, capsys):
    from sparkforge.adapters.cli import main
    from sparkforge.adapters.tools import call_tool

    entrada = tmp_path / "entrada"
    entrada.mkdir()
    (entrada / "execucao.json").write_text(
        json.dumps(HISTORICO_COM_TRES_TENTATIVAS), encoding="utf-8"
    )
    saida = tmp_path / "facts.json"

    codigo = main(["analyze", "sfn-history", "--path", str(entrada), "--out", str(saida)])
    capsys.readouterr()
    assert codigo == 0
    pela_cli = json.loads(saida.read_text(encoding="utf-8"))

    pela_tool = call_tool("sparkforge_analyze_sfn_history", {"path": str(entrada), "limit": 1000})
    assert "error" not in pela_tool, pela_tool
    assert pela_tool["total_count"] == len(pela_cli)
    assert pela_tool["items"] == pela_cli
    assert pela_tool["by_kind"]["sfn.attempt"] == 3
    assert pela_tool["by_kind"]["sfn.job_run"] == 3
    assert pela_tool["unresolved"] == 0

    erro = call_tool("sparkforge_analyze_sfn_history", {"path": str(tmp_path / "nao-existe")})
    assert "sparkforge analyze sfn-history" in erro["error"]
