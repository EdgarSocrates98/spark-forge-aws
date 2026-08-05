"""Testes semanticos do extrator de application EMR Serverless.

`fixtures/emr_serverless/` prova o comportamento de ponta a ponta contra o
catalogo; este modulo prova as decisoes do extrator isoladamente, sobre payloads
construidos na mao -- em especial as que NAO chegam a virar Fact e por isso nao
aparecem num golden: chave omitida contra chave escrita `False`, unidade fora do
conjunto documentado, e a correlacao de capacidade que nao da para decidir.

O invariante central e o mesmo do resto do pacote: nenhum caminho pode produzir
uma resposta que o payload nao afirme. Um `auto_stop_enabled: false` fabricado
numa application que simplesmente nao trouxe o bloco acusaria justamente quem
esta no default seguro da AWS.
"""
import json

import pytest

from sparkforge.facts.emr_serverless import (
    EMITTED_KINDS,
    extract_emr_serverless,
    extract_emr_serverless_path,
    extract_emr_serverless_tree,
)


def _extract(payload, path="application.json"):
    return extract_emr_serverless(payload, path)


def _of(facts, kind):
    return [f for f in facts if f.kind == kind]


def _one(facts, kind):
    got = _of(facts, kind)
    assert got, f"nenhum fact {kind}"
    return got[0]


def _reasons(facts):
    return [f.attrs["reason"] for f in _of(facts, "emrs.unresolved")]


def _sentinel(facts):
    return next(f for f in facts if f.kind == "emrs.analyzed")


def _app(**overrides):
    base = {
        "applicationId": "00fabc",
        "name": "etl",
        "releaseLabel": "emr-7.5.0",
        "type": "Spark",
        "state": "STARTED",
        "architecture": "X86_64",
    }
    base.update(overrides)
    return {"application": base}


class TestSentinelaEVocabulario:
    def test_payload_vazio_emite_unresolved_e_sentinela(self):
        facts = _extract({}, path="vazio.json")
        kinds = [f.kind for f in facts]
        assert "emrs.unresolved" in kinds
        assert "emrs.analyzed" in kinds
        sentinela = _sentinel(facts)
        assert sentinela.measures["application_count"] == 0
        assert sentinela.measures["unresolved_count"] == 1

    def test_razao_do_payload_vazio_e_fechada(self):
        assert _reasons(_extract({})) == ["missing_application"]

    def test_payload_que_nao_e_dict_nao_levanta(self):
        facts = _extract(["nao", "e", "um", "objeto"])
        assert _reasons(facts) == ["malformed_json"]
        assert _sentinel(facts).measures["application_count"] == 0

    def test_application_com_tipo_errado_e_malformada_nao_ausente(self):
        assert _reasons(_extract({"application": []})) == ["malformed_json"]

    def test_application_sem_id_nao_ancora_nada(self):
        facts = _extract({"application": {"name": "etl"}})
        assert _reasons(facts) == ["missing_application_id"]
        assert _of(facts, "emrs.application") == []

    def test_todo_kind_emitido_esta_declarado(self):
        payload = _app(
            autoStopConfiguration={"enabled": False},
            initialCapacity={"DRIVER": {"workerCount": 1, "workerConfiguration": {
                "cpu": "4vCPU", "memory": "16GB", "disk": "20GB"}}},
            maximumCapacity={"cpu": "1vCPU", "memory": "1GB", "disk": "1GB"},
            runtimeConfiguration=[{"classification": "spark-defaults",
                                   "properties": {"spark.executor.cores": "4"}}],
            monitoringConfiguration={"s3MonitoringConfiguration": {"logUri": "s3://b/l"}},
        )
        kinds = {f.kind for f in _extract(payload)}
        assert kinds <= EMITTED_KINDS
        assert "emrs.application" in kinds
        assert "emrs.initial_capacity" in kinds
        assert "emrs.configuration" in kinds
        assert "emrs.monitoring" in kinds

    def test_sentinela_conta_o_que_saiu(self):
        payload = _app(
            initialCapacity={
                "DRIVER": {"workerCount": 1, "workerConfiguration": {"cpu": "4", "memory": "16"}},
                "EXECUTOR": {"workerCount": 2, "workerConfiguration": {"cpu": "4", "memory": "16"}},
            },
            runtimeConfiguration=[{"classification": "spark-defaults",
                                   "properties": {"a": "1", "b": "2"}}],
        )
        medidas = _sentinel(_extract(payload)).measures
        assert medidas["application_count"] == 1
        assert medidas["initial_capacity_count"] == 2
        assert medidas["configuration_count"] == 2


class TestApplication:
    def test_carrega_release_e_identidade(self):
        app = _one(_extract(_app()), "emrs.application")
        assert app.attrs["application_id"] == "00fabc"
        assert app.attrs["name"] == "etl"
        assert app.attrs["release_label"] == "emr-7.5.0"
        assert app.attrs["type"] == "Spark"
        assert app.attrs["state"] == "STARTED"
        assert app.attrs["architecture"] == "X86_64"
        assert app.measures["release_major"] == 7
        assert app.measures["release_minor"] == 5

    def test_campo_ausente_nao_vira_chave(self):
        """`engine._where_matches` rejeita caminho ausente, e e assim que este
        motor diz "nao sei". `None` ou `False` diriam outra coisa."""
        app = _one(_extract({"application": {"applicationId": "00f"}}), "emrs.application")
        for chave in ("name", "release_label", "type", "state", "architecture"):
            assert chave not in app.attrs

    @pytest.mark.parametrize("label", ["emr-spark-8.0.0", "emr-spark-8.0-preview"])
    def test_label_fora_da_forma_numerica_nao_inventa_serie(self, label):
        """`emr-spark-8.0.0` e `emr-spark-8.0-preview` sao release labels validos
        do Serverless (knowledge/emr-serverless/runtime-matrix.md secao 4). Um
        `8` extraido deles por regex frouxo seria numero inventado."""
        app = _one(_extract(_app(releaseLabel=label)), "emrs.application")
        assert app.attrs["release_label"] == label
        assert "release_major" not in app.measures
        assert "release_minor" not in app.measures


class TestAutoStop:
    def test_desligado_de_proposito_e_afirmacao(self):
        facts = _extract(_app(autoStopConfiguration={"enabled": False}))
        app = _one(facts, "emrs.application")
        assert app.attrs["auto_stop_enabled"] is False
        assert app.attrs["auto_stop_declared"] is True

    def test_ligado_com_janela_vira_measure(self):
        payload = _app(autoStopConfiguration={"enabled": True, "idleTimeoutMinutes": 720})
        app = _one(_extract(payload), "emrs.application")
        assert app.attrs["auto_stop_enabled"] is True
        assert app.measures["idle_timeout_minutes"] == 720

    def test_bloco_ausente_nao_materializa_o_default_da_aws(self):
        """A AWS documenta default ligado com 15 minutos, mas o default e
        documentacao, nao artefato. Materializa-lo tornaria indistinguivel, no
        golden e na evidencia do achado, o que foi lido do que foi presumido --
        e as duas regras que consomem estes campos acusam o estado PERIGOSO
        (`enabled == false`, janela longa), entao a omissao ja produz o silencio
        correto."""
        app = _one(_extract(_app()), "emrs.application")
        assert "auto_stop_enabled" not in app.attrs
        assert "idle_timeout_minutes" not in app.measures
        assert app.attrs["auto_stop_declared"] is False

    def test_bloco_presente_sem_enabled_declara_sem_afirmar(self):
        facts = _extract(_app(autoStopConfiguration={"idleTimeoutMinutes": 30}))
        app = _one(facts, "emrs.application")
        assert app.attrs["auto_stop_declared"] is True
        assert "auto_stop_enabled" not in app.attrs
        assert app.measures["idle_timeout_minutes"] == 30

    def test_auto_start_segue_a_mesma_regra(self):
        app = _one(_extract(_app(autoStartConfiguration={"enabled": False})), "emrs.application")
        assert app.attrs["auto_start_enabled"] is False
        assert "auto_start_enabled" not in _one(_extract(_app()), "emrs.application").attrs


class TestInitialCapacity:
    def _cap(self, **workers):
        return _extract(_app(initialCapacity=workers))

    def test_um_fact_por_worker_type(self):
        facts = self._cap(
            DRIVER={"workerCount": 1, "workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"}},
            EXECUTOR={"workerCount": 10, "workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"}},
        )
        tipos = {f.attrs["worker_type"] for f in _of(facts, "emrs.initial_capacity")}
        assert tipos == {"DRIVER", "EXECUTOR"}

    def test_unidade_colada_e_a_forma_dos_exemplos_da_aws(self):
        facts = self._cap(DRIVER={"workerCount": 2, "workerConfiguration": {
            "cpu": "2vCPU", "memory": "4GB", "disk": "20GB"}})
        cap = _one(facts, "emrs.initial_capacity")
        assert cap.measures == {"worker_count": 2, "cpu": 2, "memory_gb": 4, "disk_gb": 20}

    def test_unidade_com_espaco_tambem_e_valida(self):
        facts = self._cap(DRIVER={"workerCount": 1, "workerConfiguration": {
            "cpu": "4 vCPU", "memory": "16 GB"}})
        cap = _one(facts, "emrs.initial_capacity")
        assert cap.measures["cpu"] == 4
        assert cap.measures["memory_gb"] == 16

    def test_unidade_ausente_e_legitima_em_cpu_e_memoria(self):
        """O pattern da referencia de API termina em `)?` para `cpu` e `memory`:
        a unidade e opcional. Exigir sufixo emitiria `unresolved` para valor
        legitimo."""
        facts = self._cap(DRIVER={"workerCount": 1, "workerConfiguration": {
            "cpu": "4", "memory": "16"}})
        cap = _one(facts, "emrs.initial_capacity")
        assert cap.measures["cpu"] == 4
        assert cap.measures["memory_gb"] == 16
        assert "unknown_capacity_unit" not in _reasons(facts)

    def test_grafias_alternativas_da_unidade_sao_o_mesmo_numero(self):
        facts = self._cap(DRIVER={"workerCount": 1, "workerConfiguration": {
            "cpu": "4VCPU", "memory": "16Gb", "disk": "20gb"}})
        cap = _one(facts, "emrs.initial_capacity")
        lidos = (cap.measures["cpu"], cap.measures["memory_gb"], cap.measures["disk_gb"])
        assert lidos == (4, 16, 20)

    def test_unidade_fora_do_conjunto_vira_unresolved_e_nao_numero(self):
        """`MB` nao e expressavel pelo pattern da AWS. Ler `16384 MB` como 16384
        GB produziria um fact errado, e fact errado neste motor vira achado
        confiante e falso."""
        facts = self._cap(DRIVER={"workerCount": 1, "workerConfiguration": {
            "cpu": "4vCPU", "memory": "16384 MB"}})
        assert "unknown_capacity_unit" in _reasons(facts)
        cap = _one(facts, "emrs.initial_capacity")
        assert "memory_gb" not in cap.measures
        assert cap.measures["cpu"] == 4

    def test_valor_nao_inteiro_nao_vira_numero(self):
        facts = self._cap(DRIVER={"workerCount": 1, "workerConfiguration": {"cpu": "2.5vCPU"}})
        assert "unknown_capacity_unit" in _reasons(facts)
        assert "cpu" not in _one(facts, "emrs.initial_capacity").measures

    def test_worker_count_ausente_e_contado_e_nao_presumido(self):
        facts = self._cap(DRIVER={"workerConfiguration": {"cpu": "4vCPU", "memory": "16GB"}})
        assert "missing_worker_count" in _reasons(facts)
        assert "worker_count" not in _one(facts, "emrs.initial_capacity").measures

    def test_disk_type_declarado_viaja(self):
        facts = self._cap(EXECUTOR={"workerCount": 1, "workerConfiguration": {
            "cpu": "4vCPU", "memory": "16GB", "disk": "200GB", "diskType": "SHUFFLE_OPTIMIZED"}})
        assert _one(facts, "emrs.initial_capacity").attrs["disk_type"] == "SHUFFLE_OPTIMIZED"

    def test_capacidade_malformada_nao_derruba_a_extracao(self):
        facts = _extract(_app(initialCapacity=["DRIVER"]))
        assert "malformed_json" in _reasons(facts)
        assert _of(facts, "emrs.application")

    def test_worker_type_nao_e_vocabulario_fechado(self):
        """A chave do map aceita `[a-zA-Z]+[-_]*[a-zA-Z]+`, que e aberto. Um
        conjunto fechado inventado descartaria capacidade real."""
        facts = self._cap(TEZ_TASK={"workerCount": 3, "workerConfiguration": {
            "cpu": "1vCPU", "memory": "4GB"}})
        assert _one(facts, "emrs.initial_capacity").attrs["worker_type"] == "TEZ_TASK"


class TestPreInitNoMesmoFactDoAutoStop:
    """A cobranca de worker so corre com capacidade pre-inicializada, entao
    "auto-stop desligado" e "auto-stop desligado COM pre-init" nao sao o mesmo
    defeito. Duas condicoes em kinds diferentes casariam a application A com a
    capacidade da application B; a resposta precisa caber num fact so."""

    def test_soma_os_workers_lidos_do_map(self):
        """WORKER, nao entrada do map: duas entradas, seis workers."""
        payload = _app(initialCapacity={
            "DRIVER": {"workerCount": 1, "workerConfiguration": {"cpu": "4", "memory": "16"}},
            "EXECUTOR": {"workerCount": 5, "workerConfiguration": {"cpu": "4", "memory": "16"}},
        })
        app = _one(_extract(payload), "emrs.application")
        assert app.measures["initial_capacity_worker_count"] == 6

    def test_sai_zerado_quando_o_payload_nao_traz_capacidade(self):
        app = _one(_extract(_app()), "emrs.application")
        assert app.measures["initial_capacity_worker_count"] == 0

    def test_entrada_com_zero_workers_nao_e_worker_existente(self):
        """A P0 que a revisao final da Fase 5d mediu (D-5d-43): entrada existe,
        worker nenhum existe. A `explanation` de SF-EMRS-001 funda o achado em
        "o que se cobra e worker existente" -- contar a ENTRADA fazia a regra
        acusar uma application que nao paga worker nenhum.

        A contagem de entradas nao se perdeu: ela e
        `emrs.analyzed.initial_capacity_count`, e continua 1 aqui.
        """
        payload = _app(
            autoStopConfiguration={"enabled": False},
            initialCapacity={"DRIVER": {"workerCount": 0, "workerConfiguration": {
                "cpu": "4vCPU", "memory": "16GB", "disk": "20GB"}}},
            maximumCapacity={"cpu": "400vCPU", "memory": "3000GB", "disk": "20000GB"},
        )
        facts = _extract(payload)
        app = _one(facts, "emrs.application")
        assert app.measures["initial_capacity_worker_count"] == 0
        assert _one(facts, "emrs.analyzed").measures["initial_capacity_count"] == 1
        # Zero LIDO nao e ponto cego: nada aqui e `unresolved`.
        assert _reasons(facts) == []

    def test_entrada_sem_worker_count_nao_soma_valor_presumido(self):
        """O caso irmao, e o pior: o ponto cego JA foi declarado
        (`missing_worker_count`), e somar um valor presumido o apagaria --
        erguendo uma P0 sobre o que o extrator acabou de dizer que nao sabe."""
        payload = _app(
            autoStopConfiguration={"enabled": False},
            initialCapacity={"DRIVER": {"workerConfiguration": {
                "cpu": "4vCPU", "memory": "16GB"}}},
        )
        facts = _extract(payload)
        assert _one(facts, "emrs.application").measures["initial_capacity_worker_count"] == 0
        assert _reasons(facts) == ["missing_worker_count"]

    def test_a_pergunta_p0_cabe_num_fact_so(self):
        payload = _app(
            autoStopConfiguration={"enabled": False},
            initialCapacity={"EXECUTOR": {"workerCount": 4, "workerConfiguration": {
                "cpu": "4vCPU", "memory": "16GB"}}},
        )
        app = _one(_extract(payload), "emrs.application")
        assert app.attrs["auto_stop_enabled"] is False
        assert app.measures["initial_capacity_worker_count"] > 0


class TestCorrelacaoDeCapacidade:
    """`engine._condition_candidates` avalia um fact por vez, entao a comparacao
    entre `initialCapacity` e `maximumCapacity` nao e expressavel no catalogo.
    Ela mora aqui, e os tres casos precisam ser distinguiveis."""

    def _decide(self, initial, maximum):
        kwargs = {"initialCapacity": initial}
        if maximum is not None:
            kwargs["maximumCapacity"] = maximum
        return _extract(_app(**kwargs))

    _CHEIO = {"cpu": "4vCPU", "memory": "16GB", "disk": "20GB"}

    def test_excede_diz_qual_eixo(self):
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 10, "workerConfiguration": self._CHEIO}},
            {"cpu": "20vCPU", "memory": "400GB", "disk": "400GB"},
        )
        app = _one(facts, "emrs.application")
        assert app.attrs["initial_exceeds_maximum"] is True
        assert app.attrs["capacity_axes_exceeded"] == ["cpu"]

    def test_nao_excede_e_afirmacao_tambem(self):
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 2, "workerConfiguration": self._CHEIO}},
            {"cpu": "100vCPU", "memory": "400GB", "disk": "400GB"},
        )
        app = _one(facts, "emrs.application")
        assert app.attrs["initial_exceeds_maximum"] is False
        assert app.attrs["capacity_axes_exceeded"] == []

    def test_sem_maximum_capacity_nao_da_para_decidir(self):
        """`maximumCapacity` e `Required: No` na referencia de API: este caso e
        comum, nao excepcional."""
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 2, "workerConfiguration": self._CHEIO}}, None
        )
        app = _one(facts, "emrs.application")
        assert "initial_exceeds_maximum" not in app.attrs
        assert "capacity_axes_exceeded" not in app.attrs
        assert "capacity_comparison_undecidable" in _reasons(facts)

    def test_eixo_ausente_de_um_dos_lados_nao_da_para_decidir(self):
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 2, "workerConfiguration": self._CHEIO}},
            {"cpu": "4vCPU", "memory": "8GB"},
        )
        assert "initial_exceeds_maximum" not in _one(facts, "emrs.application").attrs
        assert "capacity_comparison_undecidable" in _reasons(facts)

    def test_unidade_ilegivel_num_worker_nao_da_para_decidir(self):
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 2, "workerConfiguration": {
                "cpu": "4vCPU", "memory": "16384 MB", "disk": "20GB"}}},
            {"cpu": "1vCPU", "memory": "1GB", "disk": "1GB"},
        )
        assert "initial_exceeds_maximum" not in _one(facts, "emrs.application").attrs

    def test_ponto_cego_de_unidade_nao_e_contado_duas_vezes(self):
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 2, "workerConfiguration": {
                "cpu": "4vCPU", "memory": "16384 MB", "disk": "20GB"}}},
            {"cpu": "1vCPU", "memory": "1GB", "disk": "1GB"},
        )
        assert _reasons(facts).count("unknown_capacity_unit") == 1
        assert "capacity_comparison_undecidable" not in _reasons(facts)

    def test_sem_capacidade_inicial_nao_ha_o_que_comparar(self):
        facts = _extract(_app(maximumCapacity={"cpu": "4vCPU", "memory": "8GB"}))
        assert "capacity_comparison_undecidable" not in _reasons(facts)
        assert "initial_exceeds_maximum" not in _one(facts, "emrs.application").attrs

    def test_eixos_sao_independentes(self):
        facts = self._decide(
            {"EXECUTOR": {"workerCount": 4, "workerConfiguration": self._CHEIO}},
            {"cpu": "100vCPU", "memory": "8GB", "disk": "8GB"},
        )
        app = _one(facts, "emrs.application")
        assert app.attrs["capacity_axes_exceeded"] == ["disk_gb", "memory_gb"]


class TestRuntimeConfiguration:
    def _conf(self, entries):
        return _extract(_app(runtimeConfiguration=entries))

    def test_propriedade_vira_fact_por_chave(self):
        facts = self._conf([{"classification": "spark-defaults",
                             "properties": {"spark.executor.cores": "4"}}])
        conf = _one(facts, "emrs.configuration")
        assert conf.attrs["classification"] == "spark-defaults"
        assert conf.attrs["key"] == "spark.executor.cores"
        assert conf.attrs["value"] == "4"

    def test_nao_carrega_level(self):
        """Serverless nao tem grupo de instancia, logo nao tem override, logo
        nao ha nivel a declarar (D-3 do spec)."""
        facts = self._conf([{"classification": "spark", "properties": {"k": "v"}}])
        assert "level" not in _one(facts, "emrs.configuration").attrs

    def test_aninhamento_desce(self):
        facts = self._conf([{
            "classification": "spark-defaults",
            "properties": {"a": "1"},
            "configurations": [{"classification": "spark-env", "properties": {"b": "2"}}],
        }])
        confs = _of(facts, "emrs.configuration")
        pares = {(f.attrs["classification"], f.attrs["key"]) for f in confs}
        assert pares == {("spark-defaults", "a"), ("spark-env", "b")}

    def test_classificacao_ausente_e_contada(self):
        assert "missing_classification" in _reasons(self._conf([{"properties": {"a": "1"}}]))

    def test_forma_inesperada_e_contada(self):
        assert "malformed_json" in _reasons(self._conf({"classification": "spark"}))

    def test_duas_propriedades_iguais_nao_colidem_em_um_id(self):
        facts = self._conf([
            {"classification": "spark-defaults", "properties": {"k": "1"}},
            {"classification": "spark-defaults", "properties": {"k": "2"}},
        ])
        confs = _of(facts, "emrs.configuration")
        assert len(confs) == 2
        assert len({f.id for f in confs}) == 2


class TestSegredo:
    def _conf(self, key, value):
        facts = _extract(_app(runtimeConfiguration=[
            {"classification": "spark-defaults", "properties": {key: value}}]))
        return _one(facts, "emrs.configuration")

    def test_chave_de_acesso_e_redigida_antes_de_virar_fact(self):
        # `_AKIA_RE` casa `AKIA` seguido de 16 alfanumericos maiusculos. O teste
        # precisa do FORMATO, nao de um valor real: montado assim, e
        # inequivocamente sintetico para leitor humano e para scanner.
        chave = "AKIA" + "X" * 16
        conf = self._conf("spark.hadoop.fs.s3a.access.key", chave)
        assert conf.attrs["value"] == "<redigido>"
        assert conf.attrs["secret_pattern_match"] is True
        assert conf.attrs["redacted"] is True

    def test_senha_em_url_e_redigida(self):
        conf = self._conf("spark.hadoop.javax.jdo.option.ConnectionURL",
                          "jdbc://usuario:trocar123@host/db")
        assert conf.attrs["value"] == "<redigido>"

    def test_valor_comum_nao_e_acusado(self):
        conf = self._conf("spark.executor.cores", "4")
        assert "secret_pattern_match" not in conf.attrs
        assert conf.attrs["value"] == "4"

    def test_anotacao_de_segredo_e_o_estado_correto_nao_o_defeito(self):
        """`EMR.secret@{{Nome}}` e um ID de segredo, nao um segredo. Acusa-lo
        seria acusar exatamente a correcao que o achado pede."""
        conf = self._conf("spark.hadoop.javax.jdo.option.ConnectionPassword",
                          "EMR.secret@{{MinhaSenha}}")
        assert conf.attrs["secret_reference"] is True
        assert "secret_pattern_match" not in conf.attrs
        assert "redacted" not in conf.attrs
        assert conf.attrs["value"] == "EMR.secret@{{MinhaSenha}}"

    def test_anotacao_vence_a_heuristica_de_entropia(self):
        """O nome do segredo pode casar os padroes de segredo por acidente --
        `_AKIA_RE` usa `search`, nao `fullmatch`. Sem precedencia explicita, a
        anotacao correta seria acusada justamente quando o nome do segredo
        parece uma credencial."""
        conf = self._conf("spark.hadoop.fs.s3a.access.key", "EMR.secret@AKIAIOSFODNN7EXAMPLE")
        assert conf.attrs["secret_reference"] is True
        assert "secret_pattern_match" not in conf.attrs
        assert conf.attrs["value"] == "EMR.secret@AKIAIOSFODNN7EXAMPLE"

    def test_anotacao_sem_nome_ainda_e_referencia(self):
        assert self._conf("spark.k.password", "EMR.secret@").attrs["secret_reference"] is True

    def test_valor_que_apenas_menciona_a_anotacao_no_meio_nao_e_referencia(self):
        conf = self._conf("spark.executor.cores", "veja EMR.secret@algo")
        assert "secret_reference" not in conf.attrs


class TestMonitoring:
    def _mon(self, monitoring=None):
        kwargs = {} if monitoring is None else {"monitoringConfiguration": monitoring}
        return _one(_extract(_app(**kwargs)), "emrs.monitoring")

    def test_sai_sempre_que_a_application_e_lida(self):
        assert self._mon().attrs["monitoring_declared"] is False

    def test_default_da_aws_mantem_managed_persistence_ligada(self):
        """`managedPersistenceMonitoringConfiguration.enabled` *defaults to
        true*: bloco ausente significa PROTEGIDO. Uma regra por ausencia
        acusaria toda application no default seguro."""
        mon = self._mon()
        assert mon.attrs["managed_persistence_enabled"] is True
        assert mon.attrs["cloudwatch_enabled"] is False
        assert mon.attrs["s3_log_uri_present"] is False
        assert mon.measures["log_destination_count"] == 1

    def test_s3_declarado_conta_como_destino(self):
        mon = self._mon({"s3MonitoringConfiguration": {"logUri": "s3://b/logs/"}})
        assert mon.attrs["s3_log_uri_present"] is True
        assert mon.attrs["s3_log_uri"] == "s3://b/logs/"
        assert mon.measures["log_destination_count"] == 2

    def test_cloudwatch_so_conta_quando_habilitado_explicitamente(self):
        assert self._mon({"cloudWatchLoggingConfiguration": {"enabled": False}}).attrs[
            "cloudwatch_enabled"] is False
        mon = self._mon({"cloudWatchLoggingConfiguration": {"enabled": True}})
        assert mon.attrs["cloudwatch_enabled"] is True
        assert mon.measures["log_destination_count"] == 2

    def test_nenhum_destino_exige_ato_deliberado(self):
        mon = self._mon({"managedPersistenceMonitoringConfiguration": {"enabled": False}})
        assert mon.attrs["managed_persistence_enabled"] is False
        assert mon.measures["log_destination_count"] == 0

    def test_prometheus_nao_e_destino_de_log(self):
        """`prometheusMonitoringConfiguration` carrega `remoteWriteUrl` e e
        destino de METRICA. Conta-lo apagaria o achado de log ausente."""
        mon = self._mon({
            "managedPersistenceMonitoringConfiguration": {"enabled": False},
            "prometheusMonitoringConfiguration": {"remoteWriteUrl": "https://p/api/v1/write"},
        })
        assert mon.measures["log_destination_count"] == 0

    def test_declaracao_e_distinguivel_do_default(self):
        mon = self._mon({"managedPersistenceMonitoringConfiguration": {"enabled": True}})
        assert mon.attrs["managed_persistence_declared"] is True
        assert self._mon().attrs["managed_persistence_declared"] is False

    def test_monitoring_malformado_e_contado(self):
        facts = _extract(_app(monitoringConfiguration=[]))
        assert "malformed_json" in _reasons(facts)


class TestArquivoEArvore:
    def test_arquivo_inexistente_vira_read_error(self, tmp_path):
        facts = extract_emr_serverless_path(tmp_path / "nao_existe.json", repo_root=tmp_path)
        assert _reasons(facts) == ["read_error"]
        assert _sentinel(facts).measures["unresolved_count"] == 1

    def test_json_invalido_vira_malformed(self, tmp_path):
        alvo = tmp_path / "app.json"
        alvo.write_text("{nao e json", encoding="utf-8")
        assert _reasons(extract_emr_serverless_path(alvo, repo_root=tmp_path)) == ["malformed_json"]

    def test_provenance_carrega_sha_do_artefato(self, tmp_path):
        alvo = tmp_path / "app.json"
        alvo.write_text(json.dumps(_app()), encoding="utf-8")
        facts = extract_emr_serverless_path(alvo, repo_root=tmp_path)
        app = _one(facts, "emrs.application")
        assert app.provenance["artifact"] == "app.json"
        assert len(app.provenance["artifact_sha256"]) == 64
        assert app.provenance["extractor"].startswith("emr_serverless@")

    def test_arvore_le_todos_os_json_em_ordem(self, tmp_path):
        (tmp_path / "b.json").write_text(json.dumps(_app(applicationId="00b")), encoding="utf-8")
        (tmp_path / "a.json").write_text(json.dumps(_app(applicationId="00a")), encoding="utf-8")
        facts = extract_emr_serverless_tree(tmp_path, repo_root=tmp_path)
        ids = [f.attrs["application_id"] for f in _of(facts, "emrs.application")]
        assert sorted(ids) == ["00a", "00b"]
