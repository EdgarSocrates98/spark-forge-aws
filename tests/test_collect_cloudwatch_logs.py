"""Testes de `sparkforge.collect.cloudwatch_logs` com um cliente `logs` falso.

Nunca chama AWS. `require_boto3` e monkeypatchado para devolver um objeto cujo
`.client("logs")` e um stub com exatamente o metodo que o coletor usa.

## O FAKE, e o que ele NAO pode esconder

A auditoria de fakes de 2026-09-03 achou dois fakes que escondiam defeito pelo
mesmo mecanismo: eles devolviam UMA resposta para uma chamada que na vida real
pagina, e por isso o laco de paginacao nunca era exercitado -- serie truncada
indistinguivel da completa, e nada acusava.

`FakeLogsClient` foi escrito para nao poder fazer isso:

  * ele serve N paginas com eventos **DISTINTOS** (mensagem carrega o numero da
    pagina), entao um coletor que lesse so a primeira devolveria um conjunto
    ESTRITAMENTE menor -- e o teste compara conteudo, nao contagem;
  * ele registra `self.calls`, e o teste cobra o `nextToken` da segunda chamada
    em diante: um coletor que paginasse "por acaso" (chamando duas vezes sem o
    token) traria a primeira pagina duas vezes e cairia;
  * ele nunca devolve `nextToken` na ultima pagina, entao um coletor que
    ignorasse a condicao de parada estouraria o teto e falharia por
    `CollectionFailed` em vez de passar.

O que ele AINDA pode esconder, dito por escrito porque a lista honesta e a que
inclui o buraco: ele nao reproduz o limite de 1 MB por resposta da API real
(paginacao por tamanho, nao por contagem), nem a ordenacao por `timestamp`
entre streams. Nenhum dos dois muda o laco -- os dois chegam como `nextToken` do
mesmo jeito --, mas nenhum teste aqui os prova.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.collect import cloudwatch_logs as cwl
from sparkforge.collect.aws import CollectionFailed
from sparkforge.collect.base import CollectorUnavailable, load_manifest, verify_all

JOB = "meu-job"
RUN = "jr_abc123"
GRUPO = "/aws-glue/jobs/error"
INICIO = "2026-09-09T10:00:00Z"
FIM = "2026-09-09T11:00:00Z"
AGORA = "2026-09-09T12:00:00Z"


class FakeLogsClient:
    """`filter_log_events` paginado, com eventos distintos por pagina."""

    def __init__(self, paginas: int = 1, por_pagina: int = 2, mensagens=None):
        self.calls: list[dict] = []
        self._paginas = paginas
        self._por_pagina = por_pagina
        self._mensagens = mensagens
        self._servidas = 0

    def filter_log_events(self, **kwargs):
        self.calls.append(kwargs)
        self._servidas += 1
        pagina = self._servidas
        if self._mensagens is not None:
            eventos = [
                {
                    "logStreamName": RUN,
                    "timestamp": 1_700_000_000_000 + i,
                    "message": m,
                }
                for i, m in enumerate(self._mensagens)
            ]
            return {"events": eventos}
        eventos = [
            {
                "logStreamName": f"{RUN}",
                "timestamp": 1_700_000_000_000 + pagina * 1000 + i,
                "message": f"linha p{pagina}e{i}",
            }
            for i in range(self._por_pagina)
        ]
        resposta = {"events": eventos}
        if pagina < self._paginas:
            resposta["nextToken"] = f"tok{pagina}"
        return resposta


class ClienteQueNuncaPara:
    """Sempre devolve `nextToken`: exercita o teto de paginas."""

    def filter_log_events(self, **kwargs):
        return {
            "events": [{"logStreamName": RUN, "timestamp": 1, "message": "x"}],
            "nextToken": "sempre",
        }


class ClienteVazio:
    def filter_log_events(self, **kwargs):
        return {"events": []}


class _ErroDeApi(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class ClienteQueFalha:
    def __init__(self, exc: BaseException):
        self._exc = exc

    def filter_log_events(self, **kwargs):
        raise self._exc


class NoCredentialsError(Exception):
    """Mesmo NOME da classe do botocore -- e o nome que o coletor compara,
    porque botocore nunca e importado la (mesma disciplina de `require_boto3`)."""


class FakeBoto3:
    def __init__(self, **clients):
        self._clients = clients

    def client(self, name, **kwargs):
        return self._clients[name]


def _coletar(tmp_path, monkeypatch, client, **kwargs):
    monkeypatch.setattr(cwl, "require_boto3", lambda: FakeBoto3(logs=client))
    return cwl.collect_cloudwatch_logs(
        JOB,
        RUN,
        tmp_path,
        now=AGORA,
        log_group=GRUPO,
        start=INICIO,
        end=FIM,
        **kwargs,
    )


def _payload(tmp_path, entry) -> dict:
    return json.loads((Path(tmp_path) / entry.path).read_text(encoding="utf-8"))


class TestPaginacao:
    def test_junta_todas_as_paginas_e_nao_so_a_primeira(self, tmp_path, monkeypatch):
        """O teste que um fake de pagina unica nao consegue fazer.

        Compara o CONTEUDO: as mensagens de p2 e p3 so existem se o laco pediu
        as paginas seguintes.
        """
        logs = FakeLogsClient(paginas=3, por_pagina=2)
        entry = _coletar(tmp_path, monkeypatch, logs)
        payload = _payload(tmp_path, entry)
        mensagens = [e["message"] for e in payload["events"]]
        assert mensagens == [
            "linha p1e0",
            "linha p1e1",
            "linha p2e0",
            "linha p2e1",
            "linha p3e0",
            "linha p3e1",
        ]
        assert payload["events_collected"] == 6
        assert payload["truncated"] is False

    def test_a_segunda_chamada_leva_o_token_da_primeira(self, tmp_path, monkeypatch):
        """Paginar "por acaso" -- chamar duas vezes sem `nextToken` -- traria a
        primeira pagina duas vezes. Isto cobra o token."""
        logs = FakeLogsClient(paginas=3, por_pagina=1)
        _coletar(tmp_path, monkeypatch, logs)
        assert len(logs.calls) == 3
        assert "nextToken" not in logs.calls[0]
        assert logs.calls[1]["nextToken"] == "tok1"
        assert logs.calls[2]["nextToken"] == "tok2"

    def test_paginacao_infinita_falha_DIZENDO_em_vez_de_gravar_parcial(
        self, tmp_path, monkeypatch
    ):
        with pytest.raises(CollectionFailed) as exc:
            _coletar(tmp_path, monkeypatch, ClienteQueNuncaPara(), max_events=10_000)
        assert "paginava" in str(exc.value)
        assert not (Path(tmp_path) / ".sparkforge" / "artifacts").exists()

    def test_o_teto_de_eventos_sai_DECLARADO(self, tmp_path, monkeypatch):
        """Corte silencioso e log parcial com cara de completo."""
        logs = FakeLogsClient(paginas=5, por_pagina=4)
        entry = _coletar(tmp_path, monkeypatch, logs, max_events=3)
        payload = _payload(tmp_path, entry)
        assert payload["truncated"] is True
        assert payload["events_collected"] == 3
        assert payload["max_events"] == 3

    def test_max_events_invalido_e_recusado_antes_de_tocar_a_rede(
        self, tmp_path, monkeypatch
    ):
        def boom():
            raise AssertionError("nao deveria chamar require_boto3")

        monkeypatch.setattr(cwl, "require_boto3", boom)
        with pytest.raises(ValueError):
            cwl.collect_cloudwatch_logs(
                JOB,
                RUN,
                tmp_path,
                now=AGORA,
                log_group=GRUPO,
                start=INICIO,
                end=FIM,
                max_events=0,
            )


class TestOsArgumentosQueVaoParaAApi:
    def test_restringe_pelo_prefixo_de_stream_do_run(self, tmp_path, monkeypatch):
        logs = FakeLogsClient()
        _coletar(tmp_path, monkeypatch, logs)
        chamada = logs.calls[0]
        assert chamada["logGroupName"] == GRUPO
        assert chamada["logStreamNamePrefix"] == RUN

    def test_a_janela_vira_epoch_em_milissegundos(self, tmp_path, monkeypatch):
        logs = FakeLogsClient()
        _coletar(tmp_path, monkeypatch, logs)
        chamada = logs.calls[0]
        assert chamada["startTime"] == 1_788_948_000_000
        assert chamada["endTime"] == 1_788_951_600_000
        assert chamada["endTime"] - chamada["startTime"] == 3_600_000

    def test_filtro_vazio_nao_vira_filterPattern(self, tmp_path, monkeypatch):
        """`filterPattern: ""` nao e o mesmo que nao filtrar em toda API, e
        mandar o campo vazio pede a AWS para interpretar o vazio."""
        logs = FakeLogsClient()
        _coletar(tmp_path, monkeypatch, logs)
        assert "filterPattern" not in logs.calls[0]

    def test_filtro_declarado_e_repassado_ao_servidor(self, tmp_path, monkeypatch):
        logs = FakeLogsClient()
        _coletar(tmp_path, monkeypatch, logs, filter_pattern="?ERROR ?Exception")
        assert logs.calls[0]["filterPattern"] == "?ERROR ?Exception"


class TestRecusaTemNome:
    """As quatro razoes produzem a MESMA lista vazia. Sem `status`, o operador
    nao sabe se aumenta a janela, corrige o grupo, pede permissao ou faz login.
    """

    def test_janela_sem_evento_sai_como_vazio_e_nao_como_ok(self, tmp_path, monkeypatch):
        entry = _coletar(tmp_path, monkeypatch, ClienteVazio())
        assert _payload(tmp_path, entry)["status"] == "vazio"

    @pytest.mark.parametrize(
        "codigo,esperado",
        [
            ("ResourceNotFoundException", "log_group_inexistente"),
            ("AccessDeniedException", "sem_permissao"),
            ("AccessDenied", "sem_permissao"),
        ],
    )
    def test_erro_da_api_vira_status_nomeado(
        self, tmp_path, monkeypatch, codigo, esperado
    ):
        entry = _coletar(tmp_path, monkeypatch, ClienteQueFalha(_ErroDeApi(codigo)))
        payload = _payload(tmp_path, entry)
        assert payload["status"] == esperado
        assert payload["events"] == []

    def test_credencial_ausente_vira_status_e_nao_erro_de_fronteira(
        self, tmp_path, monkeypatch
    ):
        entry = _coletar(
            tmp_path, monkeypatch, ClienteQueFalha(NoCredentialsError("sem cred"))
        )
        assert _payload(tmp_path, entry)["status"] == "sem_credencial"

    def test_as_quatro_recusas_sao_DISTINGUIVEIS_entre_si(self, tmp_path, monkeypatch):
        """O invariante que da sentido as tres asserções acima: se duas razoes
        colapsassem no mesmo `status`, a recusa nomeada nao nomearia nada."""
        vistos = set()
        casos = [
            (ClienteVazio(), "vazio"),
            (ClienteQueFalha(_ErroDeApi("ResourceNotFoundException")), "x"),
            (ClienteQueFalha(_ErroDeApi("AccessDeniedException")), "y"),
            (ClienteQueFalha(NoCredentialsError("z")), "w"),
        ]
        for i, (client, _) in enumerate(casos):
            raiz = tmp_path / f"caso{i}"
            raiz.mkdir()
            entry = _coletar(raiz, monkeypatch, client)
            vistos.add(_payload(raiz, entry)["status"])
        assert len(vistos) == 4, vistos

    def test_erro_desconhecido_SOBE_em_vez_de_virar_recusa_nomeada(
        self, tmp_path, monkeypatch
    ):
        """Engolir erro que ninguem classificou e um coletor que mente: o
        artefato sairia com `status: vazio` e a causa real sumiria."""
        with pytest.raises(_ErroDeApi):
            _coletar(tmp_path, monkeypatch, ClienteQueFalha(_ErroDeApi("ThrottlingException")))


class TestManifestoEOfflineFirst:
    def test_registra_no_manifesto_com_o_kind_proprio(self, tmp_path, monkeypatch):
        entry = _coletar(tmp_path, monkeypatch, FakeLogsClient())
        assert entry.kind == "cloudwatch_logs"
        assert entry.collected_at == AGORA
        registrado = load_manifest(tmp_path)
        assert [e["path"] for e in registrado] == [entry.path]
        assert all(r["hash_matches"] for r in verify_all(tmp_path))

    def test_o_comando_de_recoleta_nomeia_o_log_group(self, tmp_path, monkeypatch):
        entry = _coletar(tmp_path, monkeypatch, FakeLogsClient())
        assert "--log-group /aws-glue/jobs/error" in entry.collect_command

    def test_dois_grupos_do_mesmo_run_sao_dois_artefatos(self, tmp_path, monkeypatch):
        """Colapsar `error` e `output` num arquivo so faria a segunda coleta
        sobrescrever a primeira, e o sha256 do manifesto mudaria sozinho."""
        monkeypatch.setattr(
            cwl, "require_boto3", lambda: FakeBoto3(logs=FakeLogsClient())
        )
        um = cwl.collect_cloudwatch_logs(
            JOB, RUN, tmp_path, now=AGORA, log_group="/aws-glue/jobs/error",
            start=INICIO, end=FIM,
        )
        outro = cwl.collect_cloudwatch_logs(
            JOB, RUN, tmp_path, now=AGORA, log_group="/aws-glue/jobs/output",
            start=INICIO, end=FIM,
        )
        assert um.path != outro.path
        assert len(load_manifest(tmp_path)) == 2

    def test_segunda_coleta_com_hash_integro_nao_toca_boto3(self, tmp_path, monkeypatch):
        _coletar(tmp_path, monkeypatch, FakeLogsClient())

        def boom():
            raise AssertionError("offline hit nao deveria tocar boto3")

        monkeypatch.setattr(cwl, "require_boto3", boom)
        entry = cwl.collect_cloudwatch_logs(
            JOB, RUN, tmp_path, now="2026-09-09T13:00:00Z", log_group=GRUPO,
            start=INICIO, end=FIM,
        )
        assert entry.collected_at == AGORA

    def test_recoleta_quando_o_arquivo_local_foi_corrompido(self, tmp_path, monkeypatch):
        entry = _coletar(tmp_path, monkeypatch, FakeLogsClient())
        (Path(tmp_path) / entry.path).write_text("lixo", encoding="utf-8")
        novo = _coletar(tmp_path, monkeypatch, FakeLogsClient())
        assert novo.sha256 == entry.sha256
        assert all(r["hash_matches"] for r in verify_all(tmp_path))

    def test_boto3_ausente_levanta_CollectorUnavailable(self, tmp_path, monkeypatch):
        def boom():
            raise CollectorUnavailable("boto3 nao disponivel")

        monkeypatch.setattr(cwl, "require_boto3", boom)
        with pytest.raises(CollectorUnavailable):
            cwl.collect_cloudwatch_logs(
                JOB, RUN, tmp_path, now=AGORA, log_group=GRUPO, start=INICIO, end=FIM,
            )


class TestOColetorNaoRedige:
    """A redacao mora no EXTRATOR, e este teste tranca a fronteira.

    Artefato bruto nunca e committado (`sparkforge/collect/base.py`); `facts.json`
    e. Redigir na coleta apagaria do artefato local a evidencia que o operador
    pode precisar ler, e ainda assim nao protegeria nada -- o que vaza e o fact.
    """

    def test_a_linha_crua_chega_intacta_ao_artefato(self, tmp_path, monkeypatch):
        segredo = "jdbc:postgresql://usuario:senha123@host:5432/db"
        logs = FakeLogsClient(mensagens=[segredo])
        entry = _coletar(tmp_path, monkeypatch, logs)
        payload = _payload(tmp_path, entry)
        assert payload["events"][0]["message"] == segredo

    def test_e_o_extrator_e_quem_redige(self, tmp_path, monkeypatch):
        """O par positivo: a mesma linha, passada pelo extrator, sai redigida.
        Sem este teste, o de cima sozinho poderia estar provando um vazamento."""
        from sparkforge.facts.cloudwatch_logs import extract_cloudwatch_logs

        segredo = "jdbc:postgresql://usuario:senha123@host:5432/db"
        logs = FakeLogsClient(mensagens=[segredo])
        entry = _coletar(tmp_path, monkeypatch, logs)
        facts = extract_cloudwatch_logs(_payload(tmp_path, entry), entry.path)
        linhas = [f for f in facts if f.kind == "cloudwatch.log_event"]
        assert len(linhas) == 1
        assert linhas[0].attrs["message"] == "<redigido>"
        assert linhas[0].attrs["redacted"] is True
