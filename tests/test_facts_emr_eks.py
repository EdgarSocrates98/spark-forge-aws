"""Testes do extrator de Amazon EMR on EKS (`emr-containers`)."""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts.emr_eks import (
    EMITTED_KINDS,
    extract_emr_eks,
    extract_emr_eks_path,
)


def _reasons(facts: list) -> list[str]:
    return sorted(f.attrs["reason"] for f in facts if f.kind == "emrc.unresolved")


def _kinds(facts: list) -> set[str]:
    return {f.kind for f in facts}


def test_payload_que_nao_e_dict_vira_unresolved_e_nao_excecao():
    facts = extract_emr_eks(["nao", "sou", "dict"], "x.json")
    assert _reasons(facts) == ["malformed_json"]
    assert "emrc.analyzed" in _kinds(facts)


def test_payload_sem_job_run_diz_qual_comando_falta():
    facts = extract_emr_eks({"virtualCluster": {"id": "abc"}}, "x.json")
    assert _reasons(facts) == ["missing_job_run"]
    assert "emrc.analyzed" in _kinds(facts)


def test_job_run_sem_id_nao_ancora_nada():
    facts = extract_emr_eks({"jobRun": {"name": "etl"}}, "x.json")
    assert _reasons(facts) == ["missing_job_run_id"]


def test_a_sentinela_sai_sempre_inclusive_quando_nada_pode_ser_lido():
    facts = extract_emr_eks({}, "x.json")
    sentinelas = [f for f in facts if f.kind == "emrc.analyzed"]
    assert len(sentinelas) == 1
    assert sentinelas[0].measures["unresolved_count"] == 1


def test_nenhum_kind_escapa_do_namespace_declarado():
    facts = extract_emr_eks({}, "x.json")
    assert {f.kind for f in facts} <= EMITTED_KINDS


def test_arquivo_ilegivel_vira_read_error(tmp_path: Path):
    alvo = tmp_path / "ausente.json"
    assert _reasons(extract_emr_eks_path(alvo, repo_root=tmp_path)) == ["read_error"]


def test_json_invalido_vira_malformed_json(tmp_path: Path):
    alvo = tmp_path / "quebrado.json"
    alvo.write_text("{isto nao e json", encoding="utf-8")
    assert _reasons(extract_emr_eks_path(alvo, repo_root=tmp_path)) == ["malformed_json"]


_PAYLOAD_COMPLETO = {
    "virtualCluster": {
        "id": "0abc",
        "name": "analytics",
        "state": "RUNNING",
        "containerProvider": {
            "type": "EKS",
            "id": "meu-cluster-eks",
            "info": {"eksInfo": {"namespace": "spark"}},
        },
    },
    "jobRun": {
        "id": "0000000abc",
        "name": "etl-diario",
        "virtualClusterId": "0abc",
        "state": "COMPLETED",
        "releaseLabel": "emr-7.5.0-latest",
        "executionRoleArn": "arn:aws:iam::111122223333:role/EMRContainers-JobRole",
    },
}


def _um(facts: list, kind: str):
    encontrados = [f for f in facts if f.kind == kind]
    assert len(encontrados) == 1, f"esperado 1 {kind}, achei {len(encontrados)}"
    return encontrados[0]


def test_virtual_cluster_carrega_eks_e_namespace():
    fato = _um(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json"), "emrc.virtual_cluster")
    assert fato.attrs["virtual_cluster_id"] == "0abc"
    assert fato.attrs["state"] == "RUNNING"
    assert fato.attrs["container_provider_type"] == "EKS"
    assert fato.attrs["eks_cluster_name"] == "meu-cluster-eks"
    assert fato.attrs["namespace"] == "spark"


def test_job_run_carrega_release_e_role():
    fato = _um(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json"), "emrc.job_run")
    assert fato.attrs["job_run_id"] == "0000000abc"
    assert fato.attrs["release_label"] == "emr-7.5.0-latest"
    assert fato.attrs["execution_role_arn"].endswith("EMRContainers-JobRole")
    assert fato.measures["release_major"] == 7
    assert fato.measures["release_minor"] == 5


def test_variante_de_imagem_nao_impede_a_leitura_da_serie():
    # O EKS publica sufixos que o Serverless nao tem, e ate TRES segmentos:
    # `emr-7.7.0-spark-rapids-java8-latest`. Uma regex que rejeitasse o sufixo
    # deixaria a maior parte dos job runs de EKS sem serie.
    for label, esperado in [
        ("emr-6.15.0", (6, 15)),
        ("emr-7.7.0-java8-latest", (7, 7)),
        ("emr-7.7.0-spark-rapids-java8-latest", (7, 7)),
    ]:
        payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
        payload["jobRun"]["releaseLabel"] = label
        fato = _um(extract_emr_eks(payload, "x.json"), "emrc.job_run")
        assert (fato.measures["release_major"], fato.measures["release_minor"]) == esperado


def test_release_fora_da_forma_omite_a_serie_em_vez_de_inventar():
    # `emr-spark-8.0.0-latest` (o runtime AWS para Apache Spark) e
    # `notebook-spark/emr-7.13.0-latest` NAO sao `emr-<major>.<minor>`, e
    # forcar um par deles seria inventar versao.
    for label in ["custom-build", "emr-spark-8.0.0-latest", "notebook-spark/emr-7.13.0-latest"]:
        payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
        payload["jobRun"]["releaseLabel"] = label
        fato = _um(extract_emr_eks(payload, "x.json"), "emrc.job_run")
        assert "release_major" not in fato.measures
        assert fato.attrs["release_label"] == label


def test_campo_ausente_e_chave_OMITIDA_e_nao_valor_nulo():
    # `engine._where_matches` rejeita caminho ausente, e e assim que o motor diz
    # "nao sei". Escrever None diria "sei que nao ha".
    payload = {"jobRun": {"id": "0000000abc"}}
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.job_run")
    assert fato.attrs == {"job_run_id": "0000000abc"}
    assert fato.measures == {}


def test_virtual_cluster_ausente_nao_impede_o_job_run():
    # Os dois artefatos vem de chamadas separadas, e o operador pode trazer so
    # um. O job run sozinho ainda sustenta regra.
    payload = {"jobRun": _PAYLOAD_COMPLETO["jobRun"]}
    facts = extract_emr_eks(payload, "x.json")
    assert _kinds(facts) >= {"emrc.job_run", "emrc.analyzed"}
    assert "emrc.virtual_cluster" not in _kinds(facts)
    assert _reasons(facts) == []


def test_virtual_cluster_sem_id_vira_unresolved_e_nao_derruba_o_job_run():
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    del payload["virtualCluster"]["id"]
    facts = extract_emr_eks(payload, "x.json")
    assert _reasons(facts) == ["missing_virtual_cluster_id"]
    assert "emrc.job_run" in _kinds(facts)


def test_a_sentinela_conta_o_que_saiu():
    facts = extract_emr_eks(_PAYLOAD_COMPLETO, "x.json")
    sentinela = _um(facts, "emrc.analyzed")
    assert sentinela.measures["virtual_cluster_count"] == 1
    assert sentinela.measures["job_run_count"] == 1
    assert sentinela.measures["unresolved_count"] == 0


def _confs(facts: list) -> dict[str, str]:
    return {
        f.attrs["key"]: f.attrs["value"]
        for f in facts
        if f.kind == "emrc.spark_submit_parameters"
    }


def _com_driver(driver: dict) -> dict:
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["jobDriver"] = driver
    return payload


def test_conf_do_spark_submit_sai_par_a_par():
    payload = _com_driver(
        {
            "sparkSubmitJobDriver": {
                "entryPoint": "s3://bucket/etl.py",
                "sparkSubmitParameters": (
                    "--conf spark.executor.instances=4 --conf spark.executor.memory=8g"
                ),
            }
        }
    )
    assert _confs(extract_emr_eks(payload, "x.json")) == {
        "spark.executor.instances": "4",
        "spark.executor.memory": "8g",
    }


def test_entry_point_arguments_nao_vira_configuracao():
    # Argumento de aplicacao NAO e configuracao de Spark. Confundir os dois faria
    # o detector de segredo varrer a superficie errada, e faria uma regra acusar
    # valor que o Spark nunca leu.
    payload = _com_driver(
        {
            "sparkSubmitJobDriver": {
                "entryPoint": "s3://bucket/etl.py",
                "entryPointArguments": ["--conf", "spark.nao.sou.conf=1"],
                "sparkSubmitParameters": "--conf spark.executor.cores=2",
            }
        }
    )
    assert _confs(extract_emr_eks(payload, "x.json")) == {"spark.executor.cores": "2"}


def test_flag_do_spark_submit_que_nao_e_conf_e_ignorada():
    payload = _com_driver(
        {
            "sparkSubmitJobDriver": {
                "sparkSubmitParameters": "--class Main --conf spark.executor.cores=2 --verbose"
            }
        }
    )
    assert _confs(extract_emr_eks(payload, "x.json")) == {"spark.executor.cores": "2"}


def test_conf_sem_igual_vira_unresolved_em_vez_de_par_torto():
    # Aceitar `--conf spark.sem.valor` produziria um fact com valor vazio,
    # indistinguivel de uma propriedade legitimamente vazia.
    payload = _com_driver(
        {"sparkSubmitJobDriver": {"sparkSubmitParameters": "--conf spark.sem.valor"}}
    )
    facts = extract_emr_eks(payload, "x.json")
    assert _reasons(facts) == ["malformed_conf"]
    assert _confs(facts) == {}


def test_conf_no_fim_sem_par_nenhum_vira_unresolved():
    payload = _com_driver(
        {"sparkSubmitJobDriver": {"sparkSubmitParameters": "--class Main --conf"}}
    )
    facts = extract_emr_eks(payload, "x.json")
    assert _reasons(facts) == ["malformed_conf"]
    assert _confs(facts) == {}


def test_valor_com_igual_dentro_nao_e_truncado():
    # `spark.driver.extraJavaOptions=-Da=1` tem `=` no valor. Partir no PRIMEIRO
    # `=` e o unico jeito de nao truncar.
    payload = _com_driver(
        {
            "sparkSubmitJobDriver": {
                "sparkSubmitParameters": "--conf spark.driver.extraJavaOptions=-Da=1"
            }
        }
    )
    assert _confs(extract_emr_eks(payload, "x.json")) == {
        "spark.driver.extraJavaOptions": "-Da=1"
    }


def test_spark_sql_job_driver_tambem_e_lido():
    # A API aceita `sparkSqlJobDriver` no lugar de `sparkSubmitJobDriver`. Ler so
    # o primeiro deixaria todo job SQL sem um unico fact de configuracao.
    payload = _com_driver(
        {
            "sparkSqlJobDriver": {
                "entryPoint": "s3://bucket/query.sql",
                "sparkSqlParameters": "--conf spark.sql.shuffle.partitions=800",
            }
        }
    )
    assert _confs(extract_emr_eks(payload, "x.json")) == {
        "spark.sql.shuffle.partitions": "800"
    }


def test_o_fact_diz_de_qual_superficie_e_de_qual_driver_o_valor_veio():
    payload = _com_driver(
        {"sparkSubmitJobDriver": {"sparkSubmitParameters": "--conf spark.executor.cores=2"}}
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.spark_submit_parameters")
    assert fato.attrs["surface"] == "spark_submit_parameters"
    assert fato.attrs["driver"] == "sparkSubmitJobDriver"


def test_sem_job_driver_nao_ha_conf_e_nao_ha_erro():
    facts = extract_emr_eks(_PAYLOAD_COMPLETO, "x.json")
    assert _confs(facts) == {}
    assert _reasons(facts) == []


def test_job_driver_com_tipo_errado_nao_derruba_nada():
    payload = _com_driver(["nao", "sou", "dict"])
    facts = extract_emr_eks(payload, "x.json")
    assert _confs(facts) == {}
    assert "emrc.job_run" in _kinds(facts)


def test_a_sentinela_conta_os_pares_de_conf():
    payload = _com_driver(
        {
            "sparkSubmitJobDriver": {
                "sparkSubmitParameters": "--conf a.b=1 --conf c.d=2 --conf e.f=3"
            }
        }
    )
    sentinela = _um(extract_emr_eks(payload, "x.json"), "emrc.analyzed")
    assert sentinela.measures["conf_parameter_count"] == 3


def _com_overrides(overrides: dict) -> dict:
    payload = json.loads(json.dumps(_PAYLOAD_COMPLETO))
    payload["jobRun"]["configurationOverrides"] = overrides
    return payload


def _cfgs(facts: list) -> dict[str, str]:
    return {
        f.attrs["key"]: f.attrs["value"] for f in facts if f.kind == "emrc.configuration"
    }


def test_application_configuration_sai_por_propriedade():
    payload = _com_overrides(
        {
            "applicationConfiguration": [
                {
                    "classification": "spark-defaults",
                    "properties": {"spark.sql.shuffle.partitions": "400"},
                }
            ]
        }
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.configuration")
    assert fato.attrs["classification"] == "spark-defaults"
    assert fato.attrs["key"] == "spark.sql.shuffle.partitions"
    assert fato.attrs["value"] == "400"
    assert fato.attrs["surface"] == "application_configuration"


def test_classificacao_aninhada_e_lida():
    # A API permite `configurations` dentro de `configurations`. Nao descer nela
    # esconderia exatamente o valor que alguem enterrou.
    payload = _com_overrides(
        {
            "applicationConfiguration": [
                {
                    "classification": "spark-defaults",
                    "properties": {"a.b": "1"},
                    "configurations": [
                        {"classification": "spark-env", "properties": {"c.d": "2"}}
                    ],
                }
            ]
        }
    )
    assert _cfgs(extract_emr_eks(payload, "x.json")) == {"a.b": "1", "c.d": "2"}


def test_as_duas_superficies_convivem_sem_se_apagar():
    # A mesma propriedade nas DUAS superficies produz DOIS facts. Fundi-las
    # apagaria a pergunta que importa quando divergem: qual venceu.
    payload = _com_overrides(
        {
            "applicationConfiguration": [
                {"classification": "spark-defaults", "properties": {"spark.executor.cores": "8"}}
            ]
        }
    )
    payload["jobRun"]["jobDriver"] = {
        "sparkSubmitJobDriver": {"sparkSubmitParameters": "--conf spark.executor.cores=2"}
    }
    facts = extract_emr_eks(payload, "x.json")
    assert {
        (f.attrs["surface"], f.attrs["value"])
        for f in facts
        if f.attrs.get("key") == "spark.executor.cores"
    } == {("spark_submit_parameters", "2"), ("application_configuration", "8")}


def test_application_configuration_com_tipo_errado_vira_unresolved():
    payload = _com_overrides({"applicationConfiguration": "nao sou lista"})
    facts = extract_emr_eks(payload, "x.json")
    assert _reasons(facts) == ["malformed_json"]
    assert _cfgs(facts) == {}


def test_monitoring_conta_os_destinos_de_log():
    payload = _com_overrides(
        {
            "monitoringConfiguration": {
                "persistentAppUI": "ENABLED",
                "s3MonitoringConfiguration": {"logUri": "s3://bucket/logs/"},
            }
        }
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.attrs["s3_log_uri_present"] is True
    assert fato.attrs["cloudwatch_enabled"] is False
    assert fato.attrs["persistent_app_ui"] == "ENABLED"
    assert fato.attrs["persistent_app_ui_declared"] is True
    assert fato.measures["log_destination_count"] == 1


def test_monitoring_ausente_e_zero_destinos_e_nao_silencio():
    # Sem bloco, EMR on EKS nao grava log em lugar nenhum -- ao contrario do
    # Serverless, cujo armazenamento gerenciado tem default LIGADO. Omitir o fact
    # deixaria a regra "nenhum destino de log" sem ingrediente no caso mais comum
    # do estado que ela acusa.
    fato = _um(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json"), "emrc.monitoring")
    assert fato.measures["log_destination_count"] == 0
    assert fato.attrs["monitoring_declared"] is False


def test_persistent_app_ui_ausente_nao_presume_default():
    # O default de persistentAppUI NAO e publicado em lugar nenhum. Presumir
    # seria materializar default sem fonte.
    fato = _um(extract_emr_eks(_PAYLOAD_COMPLETO, "x.json"), "emrc.monitoring")
    assert fato.attrs["persistent_app_ui_declared"] is False
    assert "persistent_app_ui" not in fato.attrs


def test_cloudwatch_conta_como_destino():
    payload = _com_overrides(
        {
            "monitoringConfiguration": {
                "cloudWatchMonitoringConfiguration": {
                    "logGroupName": "/emr-containers/jobs",
                    "logStreamNamePrefix": "etl",
                }
            }
        }
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.attrs["cloudwatch_enabled"] is True
    assert fato.measures["log_destination_count"] == 1


def test_os_dois_destinos_somam_dois():
    payload = _com_overrides(
        {
            "monitoringConfiguration": {
                "s3MonitoringConfiguration": {"logUri": "s3://bucket/logs/"},
                "cloudWatchMonitoringConfiguration": {"logGroupName": "/g"},
            }
        }
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.measures["log_destination_count"] == 2


def test_managed_logs_NAO_conta_como_destino():
    # `managedLogs.allowAWSToRetainLogs` cobre so "system namespace logs when
    # running a job using Native FGAC", sem default declarado e sem retencao
    # publicada. Conta-lo como destino faria a regra silenciar sobre um job que
    # a AWS diz que PRECISA configurar S3 ou CloudWatch.
    payload = _com_overrides(
        {"monitoringConfiguration": {"managedLogs": {"allowAWSToRetainLogs": "ENABLED"}}}
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.measures["log_destination_count"] == 0
    assert fato.attrs["managed_logs_declared"] is True


def test_bloco_de_destino_vazio_nao_conta():
    # `s3MonitoringConfiguration: {}` sem logUri nao e destino.
    payload = _com_overrides(
        {"monitoringConfiguration": {"s3MonitoringConfiguration": {}}}
    )
    fato = _um(extract_emr_eks(payload, "x.json"), "emrc.monitoring")
    assert fato.attrs["s3_log_uri_present"] is False
    assert fato.measures["log_destination_count"] == 0
    assert fato.attrs["monitoring_declared"] is True


def test_a_sentinela_conta_as_configuracoes():
    payload = _com_overrides(
        {
            "applicationConfiguration": [
                {"classification": "spark-defaults", "properties": {"a": "1", "b": "2"}}
            ]
        }
    )
    sentinela = _um(extract_emr_eks(payload, "x.json"), "emrc.analyzed")
    assert sentinela.measures["configuration_count"] == 2
