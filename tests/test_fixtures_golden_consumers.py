"""Golden test do corpus consumers.

Corpus do inventario declarado de consumidores, que desbloqueou
SF-ENV-002.

A fixture carrega DUAS fontes de proposito: o inventario (`*.yaml`) e o
metadata Iceberg da tabela (`*.json`). A regra so existe na interseccao
-- format V3 vem do metadata, quem consome vem do inventario -- e uma
fixture com so uma das metades nao provaria nada sobre ela.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.consumers import extract_consumers_path
from sparkforge.facts.iceberg_metadata import extract_iceberg_metadata_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "consumers"

REQUIRED_FIXTURES = {
    "v3_with_athena_consumer",
    "v2_with_athena_consumer",
    "malformed_inventory",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for inventory in sorted(input_dir.glob("*.yaml")):
        facts.extend(extract_consumers_path(inventory, repo_root=input_dir))
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_iceberg_metadata_path(dump, repo_root=input_dir))
    return facts


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
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
        assert [f.to_dict() for f in _extract(directory)] == [
            f.to_dict() for f in _extract(directory)
        ]


class TestAdversarial:
    def test_v3_with_athena_consumer_is_a_p0(self):
        """O job que migra para V3 continua verde; quem quebra e o consumidor,
        dias depois. P0 e a severidade certa justamente porque o sintoma
        aparece longe da causa."""
        _, _, findings, _ = run_fixture(FIXTURES / "v3_with_athena_consumer")
        assert [(f.rule_id, f.severity) for f in findings] == [("SF-ENV-002", "P0")]

    def test_v2_with_the_same_consumer_fires_nothing(self):
        """A metade negativa: o Athena le V2 sem problema. Uma regra que
        disparasse so por existir consumidor Athena acusaria toda tabela
        Iceberg do lake."""
        _, _, findings, _ = run_fixture(FIXTURES / "v2_with_athena_consumer")
        assert findings == []

    def test_a_non_athena_consumer_is_recorded_without_accusing(self):
        """O QuickSight esta no inventario e vira fact, mas nao satisfaz a
        regra. Fact nao e acusacao."""
        _, facts, _, _ = run_fixture(FIXTURES / "v3_with_athena_consumer")
        services = {f.attrs["service"] for f in facts if f.kind == "env.consumer"}
        assert services == {"athena", "quicksight"}

    def test_duplicate_declaration_produces_one_fact(self):
        """Declarar o mesmo par duas vezes e erro de edicao. Dois facts fariam
        SF-ENV-002 produzir dois findings para um unico problema."""
        _, facts, _, _ = run_fixture(FIXTURES / "malformed_inventory")
        consumers = [f for f in facts if f.kind == "env.consumer"]
        assert len(consumers) == 1

    def test_every_malformed_shape_keeps_its_reason(self):
        _, facts, _, _ = run_fixture(FIXTURES / "malformed_inventory")
        reasons = {f.attrs["reason"] for f in facts if f.kind == "env.unresolved"}
        assert reasons == {"missing_table", "missing_service", "malformed_inventory"}

    def test_the_sentinel_distinguishes_empty_from_never_read(self):
        """Sem `env.consumers_analyzed`, "nenhum consumidor declarado" seria
        indistinguivel de "ninguem leu o inventario"."""
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            sentinel = next(f for f in facts if f.kind == "env.consumers_analyzed")
            counted = sum(1 for f in facts if f.kind == "env.unresolved")
            assert sentinel.measures["unresolved_count"] == counted, directory.name
