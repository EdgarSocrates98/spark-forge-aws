"""Testes semanticos do extrator de cluster EMR on EC2.

`fixtures/emr/` prova o comportamento de ponta a ponta contra o catalogo; este
modulo prova as decisoes do extrator isoladamente, sobre payloads construidos
na mao -- em especial as que NAO chegam a virar Fact e por isso nao aparecem
num golden de facts: grupo sem `Market`, fleet sem capacidade alvo, secao
ausente contra secao malformada, forma embutida contra forma de nivel raiz.

O invariante central, e a razao de o modulo existir: NENHUM caminho pode
produzir uma resposta que o dump nao afirme. Um `has_spot_capacity: false`
fabricado num grupo sem `Market` apagaria em silencio as regras que perguntam
por Spot; um `emr.instance_capacity` ausente porque a lista nao foi coletada
seria lido como "nao ha capacidade Spot aqui". As duas sao a resposta
autoritativa-porem-errada que este pacote existe para evitar.
"""
import json

import pytest

from sparkforge.facts.emr_cluster import (
    EMITTED_KINDS,
    extract_emr_cluster,
    extract_emr_cluster_path,
    extract_emr_cluster_tree,
)


def _extract(payload, path="cluster.json"):
    return extract_emr_cluster(payload, path)


def _of(facts, kind):
    return [f for f in facts if f.kind == kind]


def _reasons(facts):
    return [f.attrs["reason"] for f in _of(facts, "emr.unresolved")]


def _sentinel(facts):
    return next(f for f in facts if f.kind == "emr.analyzed")


def _cluster(**overrides):
    base = {
        "Id": "j-1",
        "ReleaseLabel": "emr-7.5.0",
        "InstanceCollectionType": "INSTANCE_GROUP",
        "Status": {"State": "RUNNING"},
    }
    base.update(overrides)
    return base


def _dump(cluster_overrides=None, **sections):
    payload = {"Cluster": _cluster(**(cluster_overrides or {}))}
    payload.update(sections)
    return payload


def _group(**overrides):
    base = {
        "Id": "ig-1",
        "InstanceGroupType": "CORE",
        "Market": "ON_DEMAND",
        "InstanceType": "r5.xlarge",
        "RequestedInstanceCount": 2,
    }
    base.update(overrides)
    return base


def _fleet(**overrides):
    base = {
        "Id": "if-1",
        "InstanceFleetType": "TASK",
        "TargetSpotCapacity": 4,
        "TargetOnDemandCapacity": 0,
    }
    base.update(overrides)
    return base


class TestClusterIdentity:
    def test_release_label_and_numeric_release_coexist(self):
        """O label e o que a API devolve; a release numerica e o que
        `RuntimeContext.emr` guarda e o que uma comparacao de versao consegue
        ler. Guardar so o label faria todo `runtime_scope` com range falhar em
        silencio -- o defeito que a Task 2 desta fase corrigiu."""
        fact = _of(_extract(_dump()), "emr.cluster")[0]
        assert fact.attrs["release_label"] == "emr-7.5.0"
        assert fact.attrs["release"] == "7.5.0"
        assert fact.measures["release_major"] == 7
        assert fact.measures["release_minor"] == 5

    @pytest.mark.parametrize(
        ("label", "release"),
        [("emr-6.15.0", "6.15.0"), ("EMR-7.0.0", "7.0.0"), ("7.5.0", "7.5.0")],
    )
    def test_both_spellings_of_the_release_resolve_to_the_same_number(self, label, release):
        fact = _of(_extract(_dump({"ReleaseLabel": label})), "emr.cluster")[0]
        assert fact.attrs["release"] == release

    def test_release_without_a_readable_number_keeps_the_label_and_omits_the_measure(self):
        """Serie sem numero nao vira `0`: uma regra que perguntasse
        `measures.release_major == 6` acertaria por acidente sobre uma release
        desconhecida."""
        fact = _of(_extract(_dump({"ReleaseLabel": "emr-preview"})), "emr.cluster")[0]
        assert fact.attrs["release_label"] == "emr-preview"
        assert "release_major" not in fact.measures

    def test_missing_cluster_section_is_an_incomplete_dump(self):
        facts = _extract({"InstanceGroups": [_group()]})
        assert _reasons(facts) == ["missing_cluster"]
        assert _of(facts, "emr.instance_capacity") == []

    def test_cluster_without_id_anchors_nothing(self):
        """Toda entidade e ancorada em `<cluster>/...`. Sem o id, dois dumps
        diferentes colidiriam no mesmo subject."""
        facts = _extract({"Cluster": {"ReleaseLabel": "emr-7.5.0"}})
        assert _reasons(facts) == ["missing_cluster_id"]
        assert _of(facts, "emr.cluster") == []

    @pytest.mark.parametrize("payload", [[], "texto", 3, None])
    def test_payload_that_is_not_an_object_is_unresolved(self, payload):
        assert _reasons(_extract(payload)) == ["malformed_json"]

    def test_log_uri_present_distinguishes_absent_from_unknown(self):
        """`where:` do catalogo so compara igualdade: `attrs.log_uri: null`
        casaria tambem um dump que nao coletou o campo. O booleano diz "o dump
        respondeu, e a resposta e nao ha destino de log"."""
        with_uri = _of(_extract(_dump({"LogUri": "s3://b/logs/"})), "emr.cluster")[0]
        without = _of(_extract(_dump()), "emr.cluster")[0]
        assert with_uri.attrs["log_uri_present"] is True
        assert without.attrs["log_uri_present"] is False
        assert without.attrs["log_uri"] is None

    @pytest.mark.parametrize("value", [None, "true", 1, {}])
    def test_auto_terminate_that_is_not_a_boolean_stays_none(self, value):
        """`AutoTerminate` decide a severidade da regra de LogUri. Um `false`
        default mudaria a severidade a partir de um campo nao lido."""
        fact = _of(_extract(_dump({"AutoTerminate": value})), "emr.cluster")[0]
        assert fact.attrs["auto_terminate"] is None

    def test_idle_timeout_becomes_a_cluster_measure_only_when_collected(self):
        """`get-auto-termination-policy` e um dump proprio, mas o unico dado que
        traz e propriedade do cluster e nenhuma regra o consulta sozinho: kind
        proprio seria capacidade sem consumidor."""
        with_policy = _extract(_dump(AutoTerminationPolicy={"IdleTimeout": 900}))
        without = _extract(_dump())
        assert _of(with_policy, "emr.cluster")[0].measures["idle_timeout_seconds"] == 900
        assert "idle_timeout_seconds" not in _of(without, "emr.cluster")[0].measures

    def test_state_change_reason_code_survives_for_post_mortem(self):
        """`ListBootstrapActions` nao traz status nem exit code; `Status.
        StateChangeReason.Code` e a UNICA evidencia de bootstrap com problema
        que a API devolve."""
        payload = _dump(
            {"Status": {"State": "TERMINATED", "StateChangeReason": {"Code": "BOOTSTRAP_FAILURE"}}}
        )
        fact = _of(_extract(payload), "emr.cluster")[0]
        assert fact.attrs["state_change_reason_code"] == "BOOTSTRAP_FAILURE"


class TestApplications:
    def test_observed_version_becomes_a_fact_per_application(self):
        payload = _dump(
            {"Applications": [{"Name": "Spark", "Version": "3.5.2-amzn-1"}, {"Name": "Hive"}]}
        )
        facts = _of(_extract(payload), "emr.application")
        assert [(f.attrs["name"], f.attrs["version"]) for f in facts] == [
            ("Hive", None),
            ("Spark", "3.5.2-amzn-1"),
        ]

    def test_application_without_a_name_is_unresolved(self):
        payload = _dump({"Applications": [{"Version": "3.5.2"}]}, InstanceGroups=[_group()])
        assert _reasons(_extract(payload)) == ["missing_application_name"]

    def test_applications_of_the_wrong_type_reports_the_section(self):
        facts = _extract(_dump({"Applications": {"Spark": "3.5.2"}}))
        unresolved = _of(facts, "emr.unresolved")[0]
        assert unresolved.attrs["section"] == "Applications"


class TestInstanceModels:
    def test_group_market_answers_the_spot_question(self):
        facts = _extract(_dump(InstanceGroups=[_group(InstanceGroupType="TASK", Market="SPOT")]))
        capacity = _of(facts, "emr.instance_capacity")[0]
        assert capacity.attrs["has_spot_capacity"] is True
        assert capacity.attrs["has_on_demand_capacity"] is False
        assert capacity.attrs["collection_type"] == "INSTANCE_GROUP"

    def test_fleet_target_capacity_answers_the_same_question(self):
        facts = _extract(
            _dump(InstanceFleets=[_fleet(TargetSpotCapacity=6, TargetOnDemandCapacity=2)])
        )
        capacity = _of(facts, "emr.instance_capacity")[0]
        assert capacity.attrs["has_spot_capacity"] is True
        assert capacity.attrs["has_on_demand_capacity"] is True
        assert capacity.attrs["collection_type"] == "INSTANCE_FLEET"
        assert capacity.measures["target_spot_capacity"] == 6

    def test_fleet_market_is_none_because_the_question_does_not_apply(self):
        """Um fleet pode ter as duas capacidades ao mesmo tempo, o que nao tem
        equivalente no modelo de grupo. `None` diz "nao se aplica", nunca
        "nao sei" -- e por isso `has_*_capacity` existe separado."""
        facts = _extract(_dump(InstanceFleets=[_fleet()]))
        assert _of(facts, "emr.instance_capacity")[0].attrs["market"] is None

    @pytest.mark.parametrize("market", [None, "", "ondemand", 3])
    def test_group_without_a_readable_market_never_becomes_capacity(self, market):
        facts = _extract(_dump(InstanceGroups=[_group(Market=market)]))
        assert _of(facts, "emr.instance_capacity") == []
        assert _reasons(facts) == ["missing_market"]

    @pytest.mark.parametrize(
        "fleet",
        [
            {"TargetSpotCapacity": 4},
            {"TargetOnDemandCapacity": 4},
            {"TargetSpotCapacity": "4", "TargetOnDemandCapacity": 0},
        ],
    )
    def test_fleet_missing_a_target_capacity_never_becomes_capacity(self, fleet):
        payload = _dump(InstanceFleets=[{"Id": "if-1", "InstanceFleetType": "TASK", **fleet}])
        facts = _extract(payload)
        assert _of(facts, "emr.instance_capacity") == []
        assert _reasons(facts) == ["missing_fleet_capacity"]

    @pytest.mark.parametrize("role", [None, "", "PRIMARY", "CORE_NODE", 7])
    def test_unknown_role_never_becomes_capacity(self, role):
        """`PRIMARY` esta na lista porque e como a AWS chama o papel na
        documentacao recente, e NAO e o que a API devolve (`MASTER`). Aceitar
        o vocabulario da doc seria adivinhar o contrato."""
        facts = _extract(_dump(InstanceGroups=[_group(InstanceGroupType=role)]))
        assert _of(facts, "emr.instance_capacity") == []
        assert _reasons(facts) == ["missing_instance_role"]

    @pytest.mark.parametrize("role", ["task", "TASK", " task "])
    def test_role_is_read_case_insensitively_and_trimmed(self, role):
        facts = _extract(_dump(InstanceGroups=[_group(InstanceGroupType=role)]))
        assert _of(facts, "emr.instance_capacity")[0].attrs["role"] == "TASK"

    def test_neither_model_is_an_incomplete_dump(self):
        facts = _extract(_dump())
        assert _reasons(facts) == ["missing_instance_model"]

    def test_both_models_is_a_cluster_that_cannot_exist(self):
        facts = _extract(_dump(InstanceGroups=[_group()], InstanceFleets=[_fleet()]))
        assert "conflicting_instance_models" in _reasons(facts)
        assert len(_of(facts, "emr.instance_capacity")) == 2

    def test_embedded_and_top_level_shapes_are_both_read(self):
        """O CLI parece embutir as listas dentro de `Cluster`, o que contradiz
        a documentacao da API. Depender de uma das formas quebraria metade dos
        dumps reais."""
        embedded = _extract({"Cluster": _cluster(InstanceGroups=[_group()])})
        top_level = _extract(_dump(InstanceGroups=[_group()]))
        assert [f.to_dict() for f in embedded] == [f.to_dict() for f in top_level]

    def test_ebs_block_device_count_is_a_measure_only_when_the_list_exists(self):
        """`EbsBlockDevices: []` significa "nenhum volume ADICIONAL", nao
        "sem EBS" -- o EMR aloca gp2/gp3 por default. O extrator conta o que o
        dump traz e nao interpreta; a leitura fica com a regra."""
        with_list = _extract(_dump(InstanceGroups=[_group(EbsBlockDevices=[])]))
        without = _extract(_dump(InstanceGroups=[_group()]))
        assert _of(with_list, "emr.instance_capacity")[0].measures["ebs_block_device_count"] == 0
        assert "ebs_block_device_count" not in _of(without, "emr.instance_capacity")[0].measures

    def test_one_bad_group_never_discards_the_good_ones(self):
        payload = _dump(InstanceGroups=["lixo", _group(Id="ig-ok")])
        facts = _extract(payload)
        assert [f.attrs["id"] for f in _of(facts, "emr.instance_capacity")] == ["ig-ok"]
        assert _reasons(facts) == ["malformed_json"]


class TestConfigurationLevels:
    def test_cluster_and_group_levels_are_distinguishable(self):
        payload = _dump(
            {"Configurations": [{"Classification": "spark", "Properties": {"k": "cluster"}}]},
            InstanceGroups=[
                _group(
                    Configurations=[{"Classification": "spark", "Properties": {"k": "grupo"}}]
                )
            ],
        )
        by_level = {f.attrs["level"]: f for f in _of(_extract(payload), "emr.configuration")}
        assert by_level["cluster"].attrs["value"] == "cluster"
        assert by_level["cluster"].attrs["overridden_in"] == ["ig-1"]
        assert by_level["cluster"].measures["overriding_group_count"] == 1
        assert by_level["instance_group"].attrs["value"] == "grupo"
        assert by_level["instance_group"].attrs["overrides_cluster"] is True
        assert by_level["instance_group"].attrs["cluster_value"] == "cluster"

    def test_a_property_only_at_group_level_does_not_claim_to_override(self):
        payload = _dump(
            InstanceGroups=[
                _group(Configurations=[{"Classification": "spark", "Properties": {"k": "v"}}])
            ]
        )
        fact = _of(_extract(payload), "emr.configuration")[0]
        assert fact.attrs["overrides_cluster"] is False
        assert fact.attrs["cluster_value"] is None

    def test_fleet_properties_come_from_instance_type_specifications(self):
        payload = _dump(
            InstanceFleets=[
                _fleet(
                    InstanceTypeSpecifications=[
                        {
                            "InstanceType": "r5.xlarge",
                            "Configurations": [
                                {"Classification": "spark", "Properties": {"k": "v"}}
                            ],
                        }
                    ]
                )
            ]
        )
        fact = _of(_extract(payload), "emr.configuration")[0]
        assert fact.attrs["level"] == "instance_fleet"
        assert fact.attrs["instance_type"] == "r5.xlarge"
        assert fact.attrs["scope"] == "if-1"

    def test_nested_configurations_keep_the_child_classification(self):
        """`spark-env` carrega as variaveis num `Configurations` aninhado com
        classificacao `export`. Ignorar o aninhamento perderia
        `PYSPARK_PYTHON`, que e o unico lugar onde o Python efetivo aparece."""
        payload = _dump(
            {
                "Configurations": [
                    {
                        "Classification": "spark-env",
                        "Properties": {},
                        "Configurations": [
                            {
                                "Classification": "export",
                                "Properties": {"PYSPARK_PYTHON": "/usr/bin/python3.11"},
                            }
                        ],
                    }
                ]
            },
            InstanceGroups=[_group()],
        )
        fact = _of(_extract(payload), "emr.configuration")[0]
        assert fact.attrs["classification"] == "export"
        assert fact.attrs["key"] == "PYSPARK_PYTHON"

    @pytest.mark.parametrize("value", [True, 4, 4.5])
    def test_non_string_property_values_are_stringified_not_dropped(self, value):
        payload = _dump(
            {"Configurations": [{"Classification": "spark", "Properties": {"k": value}}]},
            InstanceGroups=[_group()],
        )
        fact = _of(_extract(payload), "emr.configuration")[0]
        assert isinstance(fact.attrs["value"], str)

    def test_configuration_without_classification_is_unresolved(self):
        payload = _dump({"Configurations": [{"Properties": {"k": "v"}}]}, InstanceGroups=[_group()])
        assert _reasons(_extract(payload)) == ["missing_classification"]

    def test_properties_of_the_wrong_type_reports_the_classification(self):
        payload = _dump(
            {"Configurations": [{"Classification": "spark", "Properties": "nao-e-objeto"}]},
            InstanceGroups=[_group()],
        )
        unresolved = _of(_extract(payload), "emr.unresolved")[0]
        assert unresolved.attrs["section"] == "spark.Properties"

    def test_two_entries_with_the_same_classification_and_key_do_not_collide(self):
        """Dado contraditorio, mas possivel. Dois facts com o mesmo id seriam
        dois conteudos diferentes com uma rastreabilidade so."""
        payload = _dump(
            {
                "Configurations": [
                    {"Classification": "spark", "Properties": {"k": "a"}},
                    {"Classification": "spark", "Properties": {"k": "b"}},
                ]
            },
            InstanceGroups=[_group()],
        )
        facts = _of(_extract(payload), "emr.configuration")
        assert len({f.id for f in facts}) == 2
        assert sorted(f.attrs["value"] for f in facts) == ["a", "b"]


class TestUnappliedConfiguration:
    def _payload(self, requested, applied):
        group = _group(
            Configurations=[{"Classification": "spark", "Properties": requested}],
            LastSuccessfullyAppliedConfigurations=[
                {"Classification": "spark", "Properties": applied}
            ],
            ConfigurationsVersion=4,
        )
        return _dump(InstanceGroups=[group])

    def test_divergence_becomes_the_guard(self):
        facts = _extract(self._payload({"k": "novo"}, {"k": "antigo"}))
        guard = _of(facts, "emr.configuration.unapplied")[0]
        assert guard.attrs["pending"] == ["spark/k"]
        assert guard.attrs["scope"] == "ig-1"
        assert guard.measures["configurations_version"] == 4

    def test_identical_content_produces_no_guard(self):
        facts = _extract(self._payload({"k": "v"}, {"k": "v"}))
        assert _of(facts, "emr.configuration.unapplied") == []

    def test_property_that_the_request_removes_is_reported_as_dropped(self):
        """A divergencia tem dois lados: o que foi pedido e nao vigora, e o que
        vigora e o pedido tiraria. Contar so o primeiro esconderia uma
        reconfiguracao que REMOVE uma propriedade ainda ativa."""
        facts = _extract(self._payload({"k": "v"}, {"k": "v", "outro": "ainda-ativo"}))
        guard = _of(facts, "emr.configuration.unapplied")[0]
        assert guard.attrs["pending"] == []
        assert guard.attrs["dropped"] == ["spark/outro"]

    def test_missing_last_applied_makes_no_claim(self):
        """A API so devolve `LastSuccessfullyAppliedConfigurations` quando houve
        reconfiguracao. Ausencia nao pode virar guard: um guard que dispara em
        todo cluster nunca reconfigurado apagaria toda regra de configuracao."""
        payload = _dump(
            InstanceGroups=[
                _group(Configurations=[{"Classification": "spark", "Properties": {"k": "v"}}])
            ]
        )
        assert _of(_extract(payload), "emr.configuration.unapplied") == []

    def test_the_facts_still_come_from_what_was_requested(self):
        """O guard diz que a intencao nao virou realidade; ele nao substitui os
        facts pelo que esta aplicado. Trocar a fonte esconderia do operador o
        que alguem pediu e nunca entrou em vigor."""
        facts = _extract(self._payload({"k": "novo"}, {"k": "antigo"}))
        assert [f.attrs["value"] for f in _of(facts, "emr.configuration")] == ["novo"]


class TestSecrets:
    def test_access_key_in_a_property_is_redacted(self):
        payload = _dump(
            {
                "Configurations": [
                    {"Classification": "emrfs-site", "Properties": {"k": "AKIAIOSFODNN7EXAMPLE"}}
                ]
            },
            InstanceGroups=[_group()],
        )
        fact = _of(_extract(payload), "emr.configuration")[0]
        assert fact.attrs["value"] == "<redigido>"
        assert fact.attrs["secret_pattern_match"] is True
        assert fact.attrs["redacted"] is True

    @pytest.mark.parametrize(
        "args",
        [
            ["--password=aB3xY9zQw7Lm2Kd8Rt5N"],
            ["--password", "aB3xY9zQw7Lm2Kd8Rt5N"],
            ["https://user:senha@host/repo"],
        ],
    )
    def test_secret_in_bootstrap_args_is_redacted_in_both_forms(self, args):
        """`--flag=valor` e `--flag valor` sao as duas formas que aparecem em
        bootstrap script; olhar so uma perderia metade dos casos."""
        payload = _dump(
            InstanceGroups=[_group()],
            BootstrapActions=[
                {"Name": "b", "ScriptBootstrapAction": {"Path": "s3://b/x.sh", "Args": args}}
            ],
        )
        fact = _of(_extract(payload), "emr.bootstrap_action")[0]
        assert "<redigido>" in fact.attrs["args"]
        assert fact.attrs["secret_pattern_match"] is True

    def test_ordinary_args_are_not_flagged(self):
        """Marcar argumento comum como segredo faria o operador rotacionar uma
        credencial que nao existe -- acusar configuracao correta queima a
        confianca no relatorio inteiro."""
        payload = _dump(
            InstanceGroups=[_group()],
            BootstrapActions=[
                {
                    "Name": "b",
                    "ScriptBootstrapAction": {"Path": "s3://b/x.sh", "Args": ["--repo", "interno"]},
                }
            ],
        )
        fact = _of(_extract(payload), "emr.bootstrap_action")[0]
        assert fact.attrs["args"] == ["--repo", "interno"]
        assert "secret_pattern_match" not in fact.attrs


class TestBootstrapAndManagedScaling:
    def test_bootstrap_actions_keep_their_order_as_identity(self):
        """Bootstrap actions rodam em sequencia: a posicao e identidade real, e
        e o que impede duas acoes homonimas de colidirem num fact so."""
        payload = _dump(
            InstanceGroups=[_group()],
            BootstrapActions=[
                {"Name": "mesma", "ScriptBootstrapAction": {"Path": "s3://b/1.sh"}},
                {"Name": "mesma", "ScriptBootstrapAction": {"Path": "s3://b/2.sh"}},
            ],
        )
        facts = _of(_extract(payload), "emr.bootstrap_action")
        assert [f.measures["position"] for f in facts] == [0, 1]
        assert len({f.id for f in facts}) == 2

    def test_bootstrap_without_a_name_is_unresolved(self):
        payload = _dump(
            InstanceGroups=[_group()],
            BootstrapActions=[{"ScriptBootstrapAction": {"Path": "s3://b/x.sh"}}],
        )
        assert _reasons(_extract(payload)) == ["missing_bootstrap_name"]

    def test_managed_scaling_is_its_own_fact_because_describe_cluster_lacks_it(self):
        payload = _dump(
            InstanceGroups=[_group()],
            ManagedScalingPolicy={
                "ComputeLimits": {
                    "UnitType": "InstanceFleetUnits",
                    "MinimumCapacityUnits": 2,
                    "MaximumCapacityUnits": 40,
                }
            },
        )
        fact = _of(_extract(payload), "emr.managed_scaling")[0]
        assert fact.attrs["unit_type"] == "InstanceFleetUnits"
        assert fact.measures == {"minimum_capacity_units": 2, "maximum_capacity_units": 40}

    def test_no_managed_scaling_section_emits_no_fact(self):
        """A ausencia da politica e o que a regra de alocacao dinamica le como
        "nao ha managed scaling". Emitir um fact vazio inverteria a leitura."""
        assert _of(_extract(_dump(InstanceGroups=[_group()])), "emr.managed_scaling") == []

    def test_policy_without_compute_limits_is_malformed_not_absent(self):
        payload = _dump(InstanceGroups=[_group()], ManagedScalingPolicy={"PolicyType": "MANAGED"})
        facts = _extract(payload)
        assert _of(facts, "emr.managed_scaling") == []
        assert _reasons(facts) == ["malformed_json"]


class TestSentinelAndContract:
    def test_sentinel_counts_what_the_dump_produced(self):
        payload = _dump(
            {"Configurations": [{"Classification": "spark", "Properties": {"a": "1", "b": "2"}}]},
            InstanceGroups=[_group()],
            BootstrapActions=[{"Name": "b", "ScriptBootstrapAction": {"Path": "s3://b/x.sh"}}],
        )
        assert _sentinel(_extract(payload)).measures == {
            "cluster_count": 1,
            "instance_capacity_count": 1,
            "configuration_count": 2,
            "bootstrap_action_count": 1,
            "unapplied_count": 0,
            "unresolved_count": 0,
        }

    def test_sentinel_exists_even_when_nothing_could_be_read(self):
        facts = _extract("texto")
        assert _sentinel(facts).measures["cluster_count"] == 0
        assert _sentinel(facts).measures["unresolved_count"] == 1

    def test_no_fact_escapes_the_declared_namespace(self):
        facts = (
            _extract(_dump(InstanceGroups=[_group()]))
            + _extract("texto")
            + _extract({"Cluster": {}})
        )
        assert {f.kind for f in facts} <= EMITTED_KINDS

    def test_facts_come_back_sorted_by_kind(self):
        kinds = [f.kind for f in _extract(_dump(InstanceGroups=[_group()]))]
        assert kinds == sorted(kinds)

    def test_extraction_is_deterministic(self):
        payload = _dump(InstanceGroups=[_group()])
        assert [f.to_dict() for f in _extract(payload)] == [
            f.to_dict() for f in _extract(payload)
        ]


class TestPathEntryPoints:
    def test_reads_a_file_and_anchors_relative_to_the_repo_root(self, tmp_path):
        dump = tmp_path / "sub" / "cluster.json"
        dump.parent.mkdir()
        dump.write_text(json.dumps(_dump(InstanceGroups=[_group()])), encoding="utf-8")

        facts = extract_emr_cluster_path(dump, repo_root=tmp_path)
        assert _sentinel(facts).provenance["artifact"] == "sub/cluster.json"
        assert _sentinel(facts).provenance["artifact_sha256"]

    def test_invalid_json_becomes_unresolved_instead_of_raising(self, tmp_path):
        dump = tmp_path / "cluster.json"
        dump.write_text("{ nao e json", encoding="utf-8")
        assert _reasons(extract_emr_cluster_path(dump, repo_root=tmp_path)) == ["malformed_json"]

    def test_unreadable_path_becomes_unresolved_instead_of_raising(self, tmp_path):
        facts = extract_emr_cluster_path(tmp_path / "nao-existe.json", repo_root=tmp_path)
        assert _reasons(facts) == ["read_error"]

    def test_bom_prefixed_file_still_parses(self, tmp_path):
        """Dump salvo por PowerShell no Windows vem com BOM. Sem `utf-8-sig`
        isso viraria `malformed_json` num arquivo perfeito."""
        dump = tmp_path / "cluster.json"
        dump.write_text(json.dumps(_dump(InstanceGroups=[_group()])), encoding="utf-8-sig")
        assert len(_of(extract_emr_cluster_path(dump, repo_root=tmp_path), "emr.cluster")) == 1

    def test_tree_reads_every_dump_and_one_bad_file_is_not_fatal(self, tmp_path):
        (tmp_path / "a.json").write_text(
            json.dumps(_dump(InstanceGroups=[_group()])), encoding="utf-8"
        )
        (tmp_path / "b.json").write_text("{ quebrado", encoding="utf-8")

        facts = extract_emr_cluster_tree(tmp_path, repo_root=tmp_path)
        assert len(_of(facts, "emr.cluster")) == 1
        assert "malformed_json" in _reasons(facts)
        assert len(_of(facts, "emr.analyzed")) == 2
