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


def test_tipo_desconhecido_no_meio_da_cadeia_nao_apaga_a_tentativa():
    """A cadeia de `previousEventId` passa POR CIMA do evento que o extrator nao conhece.

    `HistoryEventType` cresce: um tipo novo entre o `TaskStateEntered` e o
    `TaskScheduled` e a API que andou, nao o artefato que quebrou. Descarta-lo da
    travessia partia a cadeia (`chain_broken`) e zerava as tentativas do ramo inteiro
    -- o extrator deixava de medir o que estava ali, por causa de um evento que nao
    era sobre a tentativa. Ele continua FORA de tudo o mais, e a recusa continua saindo.
    """
    no_meio = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "EventoDoFuturo", 2),
            _evento(4, 3, "TaskScheduled", 3, **_agendado()),
            _evento(5, 4, "TaskSubmitted", 4, **_submetido({"JobRunId": "jr_meio"})),
            _evento(6, 5, "TaskSucceeded", 9),
            _evento(7, 6, "ExecutionSucceeded", 10),
        ]
    }
    facts = extract_sfn_history(no_meio, "no-meio.json")

    [tentativa] = _de(facts, "sfn.attempt")
    assert tentativa.attrs["state_name"] == "Carga"
    assert tentativa.attrs["result"] == "succeeded"
    assert tentativa.subject["symbol"] == "Carga#1"
    [corrida] = _de(facts, "sfn.job_run")
    assert corrida.attrs["job_run_id"] == "jr_meio"

    # A recusa continua ao lado: "a API cresceu" e informacao, nao ruido a esconder.
    [falha] = _de(facts, "sfn.unresolved")
    assert falha.attrs["reason"] == "event_type_unknown"
    assert falha.attrs["type"] == "EventoDoFuturo"

    # E ele nao entra em nada alem da travessia: a contagem de eventos so conta os
    # lidos, e o instante final vem do ultimo evento CONHECIDO.
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.measures["event_count"] == 6
    assert execucao.attrs["status"] == "succeeded"


def test_id_de_evento_repetido_sai_nomeado(tmp_path):
    """`id` repetido nao e leitura, e ate aqui ele passava calado (A7).

    `por_id` e `tentativas` sao dict por `id`, e a segunda ocorrencia sobrescrevia a
    primeira -- mas `ordem_por_estado` ja tinha contado as duas. Dois `TaskScheduled`
    com `id: 3` viravam UMA tentativa, com indice 2, e nenhuma recusa: o extrator
    afirmava uma ordem de tentativa que o arquivo nao sustenta. O `id` e unico na
    execucao pela propria API, entao repeti-lo e arquivo montado a mao, paginas
    concatenadas ou colagem errada -- e isso tem nome.
    """
    repetido = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(3, 2, "TaskScheduled", 3, **_agendado()),
            _evento(4, 3, "TaskSucceeded", 9),
            _evento(5, 4, "ExecutionSucceeded", 10),
        ]
    }
    facts = extract_sfn_history(repetido, "repetido.json")

    [recusa] = [
        f for f in _de(facts, "sfn.unresolved") if f.attrs["reason"] == "event_id_duplicated"
    ]
    assert recusa.measures["event_id"] == 3
    assert recusa.attrs["type"] == "TaskScheduled"

    # O repetido e DESCARTADO, e a primeira ocorrencia vence: a tentativa volta a ter
    # o indice que o arquivo sustenta, e a contagem de eventos nao conta o que nao leu.
    [tentativa] = _de(facts, "sfn.attempt")
    assert tentativa.measures["attempt_index"] == 1
    assert tentativa.subject["symbol"] == "Carga#1"
    [execucao] = _de(facts, "sfn.execution")
    assert execucao.measures["event_count"] == 5


def test_recusas_do_mesmo_arquivo_nao_colidem_de_id():
    """Tres recusas iguais em `attrs` sao UMA recusa para o `fuse` (A3).

    `Fact.id` e sha1 de `kind + subject + measures`, e `provenance` nao entra. Tres
    eventos de tipo desconhecido no MESMO arquivo tem o mesmo kind e o mesmo subject de
    arquivo, e o discriminador vivia so em `attrs` -- fora do hash. Os tres viravam o
    mesmo id, e `fusion.fuse` (`combined[fact.id] = fact`) deixava um. Contar recusa
    errado e pior do que nao contar: a regra 20 pede a lacuna NOMEADA, e tres eventos
    que a API nao publica nao sao um.
    """
    from sparkforge.facts.fusion import fuse

    tres_desconhecidos = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "EventoDoFuturo", 1),
            _evento(3, 2, "EventoDoFuturo", 2),
            _evento(4, 3, "EventoDoFuturo", 3),
            _evento(5, 4, "ExecutionSucceeded", 4),
        ]
    }
    facts = extract_sfn_history(tres_desconhecidos, "tres.json")
    recusas = _de(facts, "sfn.unresolved")
    assert len(recusas) == 3
    assert len({f.id for f in recusas}) == 3, "tres recusas, tres ids"
    assert sorted(f.measures["event_id"] for f in recusas) == [2, 3, 4]

    # E o `fuse` as preserva: e ele que indexa por id e descartava as repetidas.
    sobreviventes = [
        f
        for f in fuse(facts)
        if f.kind == "sfn.unresolved" and f.attrs["reason"] == "event_type_unknown"
    ]
    assert len(sobreviventes) == 3

    # O mesmo vale para `event_not_an_object`, cujo discriminador e o INDICE na lista.
    nao_objetos = {"events": ["a", "b", "c"]}
    facts = extract_sfn_history(nao_objetos, "nao-objetos.json")
    recusas = _de(facts, "sfn.unresolved")
    assert len({f.id for f in recusas}) == 3
    assert sorted(f.measures["index"] for f in recusas) == [0, 1, 2]
    assert len([f for f in fuse(facts) if f.kind == "sfn.unresolved"]) == 3


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


ASL_COM_RETRY_DE_UMA = {
    "StartAt": "CargaDiaria",
    "States": {
        "CargaDiaria": {
            "Type": "Task",
            "Resource": "arn:aws:states:::glue:startJobRun.sync",
            "Parameters": {"JobName": "carga-diaria"},
            "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 1}],
            "End": True,
        }
    },
}


ASL_COM_RETRY_DE_DUAS = {
    "StartAt": "Carga",
    "States": {
        "Carga": {
            "Type": "Task",
            "Resource": "arn:aws:states:::glue:startJobRun.sync",
            "Parameters": {"JobName": "carga"},
            "Retry": [{"ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 2}],
            "End": True,
        }
    },
}


def _historico_de_duas_tentativas(job_run_a: str, job_run_b: str) -> dict:
    """Uma execucao com DUAS tentativas do estado `Carga`, as duas falhando."""
    return {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(3, 2, "TaskScheduled", 2, **_agendado()),
            _evento(4, 3, "TaskSubmitted", 3, **_submetido({"JobRunId": job_run_a})),
            _evento(
                5,
                4,
                "TaskFailed",
                30,
                taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "falhou"},
            ),
            _evento(6, 5, "TaskScheduled", 31, **_agendado()),
            _evento(7, 6, "TaskSubmitted", 32, **_submetido({"JobRunId": job_run_b})),
            _evento(
                8,
                7,
                "TaskFailed",
                60,
                taskFailedEventDetails={"error": "Glue.AWSGlueException", "cause": "falhou"},
            ),
            _evento(
                9,
                8,
                "ExecutionFailed",
                61,
                executionFailedEventDetails={"error": "Glue.AWSGlueException"},
            ),
        ]
    }


def test_duas_execucoes_nao_somam_tentativas_uma_da_outra():
    """Cada EXECUCAO tem o seu proprio orcamento de retry (A1).

    O pareamento com o `sfn.task` do ASL e pelo NOME do estado -- e o unico que o
    historico permite --, mas o lado MEDIDO e por EXECUCAO: dois historicos do mesmo
    estado no mesmo pool sao duas execucoes, nao uma com o dobro das tentativas.
    Somar os dois faria a `SF-SFNX-001` acusar dois runs que CABEM no retry declarado.
    """
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.stepfunctions import extract_stepfunctions

    primeira = extract_sfn_history(
        _historico_de_duas_tentativas("jr_1a", "jr_1b"), "execucao-a.json"
    )
    segunda = extract_sfn_history(
        _historico_de_duas_tentativas("jr_2a", "jr_2b"), "execucao-b.json"
    )
    definicao = extract_stepfunctions(ASL_COM_RETRY_DE_DUAS, "carga.asl.json")

    fundidos = fuse(definicao + primeira + segunda)
    confrontos = sorted(
        (f for f in fundidos if f.kind == "sfn.retry_observado"),
        key=lambda f: f.subject["file"],
    )
    assert [f.subject["file"] for f in confrontos] == ["execucao-a.json", "execucao-b.json"]
    for confronto in confrontos:
        assert confronto.subject["symbol"] == "Carga"
        # 1 + MaxAttempts = 3, e cada execucao agendou 2: nenhuma passa do teto.
        assert confronto.measures == {"tentativas_observadas": 2, "teto_declarado": 3}
        assert confronto.measures["tentativas_observadas"] <= confronto.measures[
            "teto_declarado"
        ]
    # A proveniencia de cada um cita SO as tentativas daquela execucao, mais o `sfn.task`.
    por_arquivo = {
        "execucao-a.json": primeira,
        "execucao-b.json": segunda,
    }
    for confronto in confrontos:
        esperado = {
            f.id for f in por_arquivo[confronto.subject["file"]] if f.kind == "sfn.attempt"
        } | {f.id for f in definicao if f.kind == "sfn.task"}
        assert set(confronto.provenance["derived_from"]) == esperado


def test_o_grupo_e_ordenado_pelo_indice_da_tentativa_e_nao_pelo_hash():
    """`grupo[-1]` tem de ser a ULTIMA tentativa, nao a de id que calhou de ser maior.

    O grupo era `sorted(..., key=lambda f: f.id)`, e `Fact.id` e sha1 do conteudo: uma
    ordem de hash, nao uma ordem de tentativa. `grupo[-1].attrs["execution_outcome"]`
    virava escolha arbitraria. Para o estado `Carga`, a tentativa 2 tem id MENOR que a
    1 (`f_e4e5b3` < `f_ed540c`), e por isso a ordem de hash inverte as duas.

    Nenhum historico REAL produz duas tentativas da mesma execucao com
    `execution_outcome` diferente -- ele e por arquivo. Por isso o caso e montado sobre
    a derivacao direto, que e onde o contrato mora: o que este teste trava e a ORDEM,
    para que o proximo campo lido de `grupo[-1]` ou de `grupo[0]` nao herde um hash.
    """
    from sparkforge.facts.sfn_history import build_sfn_retry_observado
    from sparkforge.facts.stepfunctions import extract_stepfunctions
    from sparkforge.findings.models import Fact

    def _tentativa(indice: int, desfecho: str) -> Fact:
        return Fact(
            kind="sfn.attempt",
            subject={
                "type": "source_location",
                "file": "execucao.json",
                "line": 0,
                "col": 0,
                "symbol": f"Carga#{indice}",
                "snippet": "",
            },
            measures={"attempt_index": indice},
            attrs={
                "state_name": "Carga",
                "service": "glue",
                "api": "startJobRun",
                "execution_outcome": desfecho,
            },
            provenance={
                "artifact": "execucao.json",
                "artifact_sha256": "",
                "extractor": "sfn_history@0.1.0",
            },
        )

    primeira, segunda = _tentativa(1, "primeira"), _tentativa(2, "segunda")
    assert segunda.id < primeira.id, "a premissa do caso: o hash inverte as duas"

    definicao = extract_stepfunctions(ASL_COM_RETRY_DE_DUAS, "carga.asl.json")
    [confronto] = [
        f
        for f in build_sfn_retry_observado([*definicao, primeira, segunda])
        if f.kind == "sfn.retry_observado"
    ]
    assert confronto.attrs["execution_outcome"] == "segunda"
    assert confronto.measures["tentativas_observadas"] == 2

    # E a ordem nao depende da ordem em que os facts chegaram.
    [invertido] = [
        f
        for f in build_sfn_retry_observado([*definicao, segunda, primeira])
        if f.kind == "sfn.retry_observado"
    ]
    assert invertido.to_dict() == confronto.to_dict()


def test_tentativa_que_nao_e_glue_sai_em_recusa_nomeada():
    """O confronto de retry so sabe julgar `glue:startJobRun` -- e diz isso (A5).

    A integracao `aws-sdk` publica `resourceType: "aws-sdk:glue"` e `resource:
    "startJobRun"`: mesmo servico, outra forma de chamar, e o filtro dos dois lados de
    `_glue_de_kind` nao a alcanca. A derivacao devolvia `[]` em silencio, e o operador
    via um case sem `sfn.retry_observado` e sem uma linha dizendo por que -- contra a
    regra 20, que pede a lacuna NOMEADA. "Nao sei julgar esta integracao" e diferente
    de "esta tudo bem".
    """
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.stepfunctions import extract_stepfunctions

    pelo_sdk = {
        "events": [
            _evento(1, 0, "ExecutionStarted", 0),
            _evento(2, 1, "TaskStateEntered", 1, stateEnteredEventDetails={"name": "Carga"}),
            _evento(
                3,
                2,
                "TaskScheduled",
                2,
                taskScheduledEventDetails={
                    "resource": "startJobRun",
                    "resourceType": "aws-sdk:glue",
                },
            ),
            _evento(4, 3, "TaskSucceeded", 9),
            _evento(5, 4, "ExecutionSucceeded", 10),
        ]
    }
    historico = extract_sfn_history(pelo_sdk, "pelo-sdk.json")
    definicao = extract_stepfunctions(ASL_COM_RETRY_DE_DUAS, "carga.asl.json")

    # A tentativa foi medida -- o que falta e o confronto, nao a leitura.
    [tentativa] = _de(historico, "sfn.attempt")
    assert tentativa.attrs["service"] == "aws-sdk:glue"

    fundidos = fuse(definicao + historico)
    assert not [f for f in fundidos if f.kind == "sfn.retry_observado"]
    [recusa] = [
        f
        for f in fundidos
        if f.kind == "sfn.unresolved" and f.attrs["reason"] == "glue_attempt_absent"
    ]
    assert recusa.subject["file"] == "pelo-sdk.json"
    # A recusa NOMEIA o que estava la, que e por onde o operador fecha a lacuna.
    assert recusa.attrs["observed"] == ["aws-sdk:glue:startJobRun"]
    assert recusa.measures["attempt_count"] == 1

    # E com `glue:startJobRun` no pool, ela nao sai: recusa que aparece em todo case
    # nao informa nada.
    com_glue = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")
    motivos = {
        f.attrs["reason"] for f in fuse(com_glue) if f.kind == "sfn.unresolved"
    }
    assert "glue_attempt_absent" not in motivos


def test_fuse_confronta_o_retry_declarado_com_o_observado(tmp_path):
    from sparkforge.facts.fusion import fuse
    from sparkforge.facts.stepfunctions import extract_stepfunctions

    historico = extract_sfn_history(HISTORICO_COM_TRES_TENTATIVAS, "execucao.json")
    definicao = extract_stepfunctions(ASL_COM_RETRY_DE_UMA, "carga.asl.json")

    fundidos = fuse(definicao + historico)
    [confronto] = [f for f in fundidos if f.kind == "sfn.retry_observado"]
    assert confronto.subject["symbol"] == "CargaDiaria"
    assert confronto.measures == {"tentativas_observadas": 3, "teto_declarado": 2}
    assert confronto.attrs["state_name"] == "CargaDiaria"
    assert confronto.attrs["job_name"] == "carga-diaria"
    assert confronto.attrs["pattern"] == "sync"
    assert confronto.attrs["declared_retry_defaulted"] is False
    # A proveniencia liga o confronto as tres tentativas E ao `sfn.task`: sem isso, o
    # achado citaria um fact que ninguem consegue reencontrar.
    derivados = set(confronto.provenance["derived_from"])
    assert derivados == {f.id for f in historico if f.kind == "sfn.attempt"} | {
        f.id for f in definicao if f.kind == "sfn.task"
    }

    # Sem o ASL no pool, nenhum confronto e a lacuna sai nomeada.
    so_historico = fuse(historico)
    assert not [f for f in so_historico if f.kind == "sfn.retry_observado"]
    motivos = {
        f.attrs["reason"] for f in so_historico if f.kind == "sfn.unresolved"
    }
    assert "asl_absent" in motivos

    # ASL presente, estado com OUTRO nome: perguntou-se e nao bateu, que e diferente
    # de nao ter perguntado.
    outro = extract_stepfunctions(
        {
            "StartAt": "CargaMensal",
            "States": {
                "CargaMensal": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                    "Parameters": {"JobName": "carga-mensal"},
                    "End": True,
                }
            },
        },
        "mensal.asl.json",
    )
    fundidos = fuse(outro + historico)
    assert not [f for f in fundidos if f.kind == "sfn.retry_observado"]
    motivos = {f.attrs["reason"] for f in fundidos if f.kind == "sfn.unresolved"}
    assert "state_name_absent_in_asl" in motivos

    # Dois estados de MESMO nome em ramos de um Parallel: o historico so sabe o nome,
    # e escolher um seria chutar.
    ambiguo = extract_stepfunctions(
        {
            "StartAt": "Cargas",
            "States": {
                "Cargas": {
                    "Type": "Parallel",
                    "Branches": [
                        {
                            "StartAt": "CargaDiaria",
                            "States": {
                                "CargaDiaria": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                                    "Parameters": {"JobName": "carga-diaria"},
                                    "End": True,
                                }
                            },
                        },
                        {
                            "StartAt": "CargaDiaria",
                            "States": {
                                "CargaDiaria": {
                                    "Type": "Task",
                                    "Resource": "arn:aws:states:::glue:startJobRun.sync",
                                    "Parameters": {"JobName": "carga-diaria-bis"},
                                    "End": True,
                                }
                            },
                        },
                    ],
                    "End": True,
                }
            },
        },
        "ambiguo.asl.json",
    )
    fundidos = fuse(ambiguo + historico)
    assert not [f for f in fundidos if f.kind == "sfn.retry_observado"]
    [falha] = [
        f
        for f in fundidos
        if f.kind == "sfn.unresolved" and f.attrs["reason"] == "state_name_ambiguous"
    ]
    assert falha.attrs["declared_count"] == 2
