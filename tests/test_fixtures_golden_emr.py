"""Golden test do corpus de cluster EMR on EC2.

Arquivo dedicado, mesma razao de `test_fixtures_golden_athena.py`: a fixture e
um dump `*.json` sob `input/`, extraido por `extract_emr_cluster_path` -- um
dump ja e a uniao das saidas dos seis subcomandos de um cluster, entao nao ha
variante `_tree`.

Nenhuma fixture deste corpus dispara regra: a area `SF-EMR` e a Task 4 desta
fase, e o extrator entra antes dela de proposito (regra sem fact e regra que
nunca foi provada). O que o corpus trava agora e o contrato dos facts -- e
`expects_rules: []` em todas passa a ser um golden negativo real assim que as
regras existirem: se alguma delas disparar sobre um dump que nao a justifica,
o diff aparece aqui.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.emr_cluster import extract_emr_cluster_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "emr"

REQUIRED_FIXTURES = {
    "instance_groups_spot_task",
    "instance_fleets_maximize",
    "configuration_not_applied",
    "missing_instance_model",
    "malformed_sections",
    "empty_dump",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_emr_cluster_path(dump, repo_root=input_dir))
    return facts


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de fixtures
# vazio, o pytest 8.x invoca o callable sobre o sentinela interno NOTSET durante
# a coleta e aborta a sessao INTEIRA, nao so este arquivo. Mesma guarda de
# `test_agent_coverage.py`.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second

    def test_no_two_facts_share_an_id(self, directory):
        """Dois facts com o mesmo id sao dois conteudos diferentes com uma
        rastreabilidade so: o `evidence` de um Finding apontaria para o par, e
        nao para o fact que o justifica. O risco e real aqui porque um dump tem
        muitas propriedades de configuracao sob o mesmo cluster, e `Fact.id` e
        o hash de (kind, subject, measures) -- sem symbol distinto por
        propriedade, todas colidiriam.

        `emr.unresolved` fica de fora, e nao por conveniencia: ele e ancorado
        no ARQUIVO e o que o distingue (`reason`) vive em `attrs`, que por
        contrato de `Fact.id` nao entra no hash. Isso vale para todo extrator
        do pacote (`athena.unresolved`, `tf.unresolved`), e divergir aqui
        seria inventar uma identidade que o resto do projeto nao tem.
        """
        _, facts, _, _ = run_fixture(directory)
        ids = [f.id for f in facts if f.kind != "emr.unresolved"]
        assert len(ids) == len(set(ids))


class TestAdversarial:
    def test_spot_question_has_one_shape_in_both_instance_models(self):
        """O nucleo da decisao de kind unico: `Market == "SPOT"` num grupo e
        `TargetSpotCapacity > 0` num fleet chegam ao MESMO atributo. Se
        virassem kinds distintos, toda regra que pergunta por Spot precisaria
        ser escrita duas vezes -- e a metade esquecida ficaria calada em metade
        dos clusters."""
        _, groups, _, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        _, fleets, _, _ = run_fixture(FIXTURES / "instance_fleets_maximize")

        def spot_roles(facts):
            return {
                f.attrs["role"]
                for f in _by_kind(facts, "emr.instance_capacity")
                if f.attrs["has_spot_capacity"]
            }

        assert spot_roles(groups) == {"TASK"}
        assert spot_roles(fleets) == {"MASTER"}
        assert {f.attrs["collection_type"] for f in _by_kind(groups, "emr.instance_capacity")} == {
            "INSTANCE_GROUP"
        }
        assert {f.attrs["collection_type"] for f in _by_kind(fleets, "emr.instance_capacity")} == {
            "INSTANCE_FLEET"
        }

    def test_group_level_property_records_that_it_overrides_the_cluster(self):
        """Achatar os dois niveis num kind sem discriminante faria uma regra
        afirmar sobre o cluster inteiro o que so vale onde ninguem redefiniu.
        `spark.dynamicAllocation.enabled` esta `false` no cluster e `true` no
        grupo TASK: os dois facts existem, cada um com o seu nivel, e a
        sobreposicao aparece nos dois sentidos."""
        _, facts, _, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        configs = _by_kind(facts, "emr.configuration")
        cluster_level = next(
            f
            for f in configs
            if f.attrs["level"] == "cluster"
            and f.attrs["key"] == "spark.dynamicAllocation.enabled"
        )
        group_level = next(
            f
            for f in configs
            if f.attrs["level"] == "instance_group"
            and f.attrs["key"] == "spark.dynamicAllocation.enabled"
        )
        assert cluster_level.attrs["value"] == "false"
        assert cluster_level.attrs["overridden_in"] == ["ig-TASK"]
        assert cluster_level.measures["overriding_group_count"] == 1
        assert group_level.attrs["value"] == "true"
        assert group_level.attrs["overrides_cluster"] is True
        assert group_level.attrs["cluster_value"] == "false"

    def test_requested_configuration_that_never_applied_becomes_a_guard(self):
        """O fact mais importante do extrator: sem ele, uma regra afirma sobre
        configuracao que NAO esta em vigor. Ele e por grupo, nao por cluster --
        o grupo TASK do mesmo dump tem pedido e aplicado identicos e nao produz
        guard nenhum."""
        _, facts, _, _ = run_fixture(FIXTURES / "configuration_not_applied")
        guards = _by_kind(facts, "emr.configuration.unapplied")
        assert [g.attrs["scope"] for g in guards] == ["ig-CORE"]
        assert guards[0].attrs["pending"] == ["spark-defaults/spark.dynamicAllocation.enabled"]
        assert guards[0].measures["configurations_version"] == 7

    def test_a_clean_dump_produces_no_guard(self):
        """O sentido negativo: `LastSuccessfullyAppliedConfigurations` igual a
        `Configurations` nao pode virar guard. Um guard que dispara sempre e
        um guard que ninguem le, e ele apagaria toda regra de configuracao."""
        _, facts, _, _ = run_fixture(FIXTURES / "instance_groups_spot_task")
        assert _by_kind(facts, "emr.configuration.unapplied") == []

    def test_no_secret_value_survives_into_a_committed_golden(self):
        """Um golden commitado com credencial real seria o analisador causando
        o dano que a regra de segredo existe para prevenir. Vale para os dois
        lugares onde as APIs Describe/List devolvem texto claro: propriedade de
        configuracao e argumento de bootstrap action."""
        directory = FIXTURES / "instance_groups_spot_task"
        raw = (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        assert "AKIAIOSFODNN7EXAMPLE" not in raw
        assert "aB3xY9zQw7Lm2Kd8Rt5N" not in raw

        _, facts, _, _ = run_fixture(directory)
        flagged = [f for f in facts if f.attrs.get("secret_pattern_match")]
        assert {f.kind for f in flagged} == {"emr.configuration", "emr.bootstrap_action"}
        for fact in flagged:
            assert fact.attrs.get("redacted") is True

    def test_missing_instance_dump_is_incomplete_not_a_cluster_without_capacity(self):
        """Lista ausente vira `unresolved`, nunca lista vazia: uma regra que
        perguntasse "ha Spot?" sobre zero facts concluiria "nao ha", que e o
        falso negativo silencioso que o catalogo trata como pior defeito."""
        _, facts, _, _ = run_fixture(FIXTURES / "missing_instance_model")
        assert _by_kind(facts, "emr.instance_capacity") == []
        assert [f.attrs["reason"] for f in _by_kind(facts, "emr.unresolved")] == [
            "missing_instance_model"
        ]

    def test_every_way_the_dump_can_fail_has_its_own_reason(self):
        _, facts, _, _ = run_fixture(FIXTURES / "malformed_sections")
        reasons = {f.attrs["reason"] for f in _by_kind(facts, "emr.unresolved")}
        assert reasons == {
            "malformed_json",
            "conflicting_instance_models",
            "missing_market",
            "missing_instance_role",
            "missing_fleet_capacity",
            "missing_classification",
            "missing_bootstrap_name",
        }
        assert _by_kind(facts, "emr.instance_capacity") == []
        assert _by_kind(facts, "emr.managed_scaling") == []

    def test_sentinel_exists_in_every_fixture_and_counts_what_it_says(self):
        """`emr.analyzed` e o que distingue "analisei e nao ha" de "nunca
        analisei". Sem ela, `absent:` sobre fact de EMR e vacuamente verdadeiro
        num repositorio onde o extrator nunca rodou."""
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            sentinel = next(f for f in facts if f.kind == "emr.analyzed")
            counted = len(_by_kind(facts, "emr.unresolved"))
            assert sentinel.measures["unresolved_count"] == counted, directory.name
            assert sentinel.measures["configuration_count"] == len(
                _by_kind(facts, "emr.configuration")
            ), directory.name

    def test_empty_dump_still_proves_the_extractor_ran(self):
        _, facts, _, _ = run_fixture(FIXTURES / "empty_dump")
        assert {f.kind for f in facts} == {"emr.analyzed", "emr.unresolved"}
        assert facts[0].measures["cluster_count"] == 0
