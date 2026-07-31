"""Golden test do corpus de workgroups do Athena.

Arquivo dedicado, mesma razao de `test_fixtures_golden_catalog.py`: a fixture
e um dump `*.json` sob `input/`, extraido por `extract_athena_workgroup_path`
-- um dump ja descreve varios workgroups, entao nao ha variante `_tree`.

O corpus existe porque `athena_workgroup` era o unico extrator do pacote sem
teste semantico proprio e sem fixture: os tres kinds dele apareciam em ZERO
golden, e o unico teste que o tocava (`test_adapters_cli.py`) provava que o
verbo respondia, nao que a extracao estava certa.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.athena_workgroup import extract_athena_workgroup_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "athena"

REQUIRED_FIXTURES = {"engine_v3_ok", "engine_v2_outdated", "engine_unresolved"}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for dump in sorted(input_dir.glob("*.json")):
        facts.extend(extract_athena_workgroup_path(dump, repo_root=input_dir))
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
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second


class TestAdversarial:
    def test_current_engine_version_produces_zero_findings(self):
        """Acusar quem ja migrou para a engine 3 manda o operador refazer uma
        migracao concluida. O sentido negativo do golden vale tanto quanto o
        positivo."""
        _, _, findings, _ = run_fixture(FIXTURES / "engine_v3_ok")
        assert findings == []

    def test_outdated_workgroup_is_anchored_and_the_current_one_is_spared(self):
        """Dois workgroups no mesmo dump, um finding so. Se a regra avaliasse
        a lista global de facts em vez de por subject, `primary` (engine 3)
        seria acusado junto."""
        _, _, findings, _ = run_fixture(FIXTURES / "engine_v2_outdated")
        assert [(f.rule_id, f.subject["symbol"]) for f in findings] == [
            ("SF-ATH-004", "legacy-etl")
        ]

    def test_unknown_engine_version_never_becomes_a_workgroup_fact(self):
        """O nucleo do extrator: engine version que nao da para ler NAO pode
        virar `athena.workgroup`. Um `measures.engine_version` adivinhado faria
        SF-ATH-004 julgar uma versao desconhecida -- pior que nao julgar."""
        _, facts, findings, _ = run_fixture(FIXTURES / "engine_unresolved")
        assert not [f for f in facts if f.kind == "athena.workgroup"]
        assert findings == []
        reasons = {f.attrs["reason"] for f in facts if f.kind == "athena.unresolved"}
        assert reasons == {
            "unparseable_engine_version",
            "missing_engine_version",
            "missing_workgroup_name",
            "malformed_json",
        }

    def test_unresolved_is_never_silently_zero_where_it_is_not(self):
        """`athena.analyzed` e a sentinela: sem ela, uma condicao `absent:`
        sobre fact de Athena seria vacuamente verdadeira quando o extrator
        nunca rodou."""
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            sentinel = next(f for f in facts if f.kind == "athena.analyzed")
            counted = sum(1 for f in facts if f.kind == "athena.unresolved")
            assert sentinel.measures["unresolved_count"] == counted, directory.name

    def test_optional_measure_is_absent_not_zero(self):
        """`bytes_scanned_cutoff` ausente no dump nao pode virar 0: zero e um
        limite de scan real e absurdamente restritivo, nao 'sem limite'."""
        _, facts, _, _ = run_fixture(FIXTURES / "engine_v3_ok")
        by_name = {f.attrs["name"]: f for f in facts if f.kind == "athena.workgroup"}
        assert "bytes_scanned_cutoff" in by_name["primary"].measures
        assert "bytes_scanned_cutoff" not in by_name["analytics"].measures
