"""Golden test do corpus waste: cinco cenarios do desperdicio de capacidade.

A seccao 37 do documento de origem pede as duas regras juntas, e o corpus existe
para provar que elas sao um PAR: `folga_medida_sem_skew` e `ocioso_por_skew` tem
a MESMA utilizacao de worker e razao de skew diferente, e so isso decide qual
das duas dispara.

  folga_medida_sem_skew         -- `SF-WASTE-001`
  ocioso_por_skew               -- `SF-WASTE-002`, e a outra calada
  utilizacao_alta_nada_dispara  -- nenhuma das duas
  memoria_alta_com_worker_ocioso -- por que as quatro condicoes sao um `all`
  sem_cloudwatch                -- a lacuna nomeada

`TestOQueOCorpusInteiroGarante` verifica o que vale sobre o corpus inteiro, e a
garantia central e a que o subprojeto E estabeleceu: nada aqui quantifica
economia.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.utilization import extract_utilization
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import validate_fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "waste"

REQUIRED_FIXTURES = {
    "folga_medida_sem_skew",
    "ocioso_por_skew",
    "utilizacao_alta_nada_dispara",
    "memoria_alta_com_worker_ocioso",
    "sem_cloudwatch",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _meta(directory: Path) -> dict:
    return yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))


def _input_facts(directory: Path) -> list[Fact]:
    data = json.loads((directory / "input" / "facts.json").read_text(encoding="utf-8"))
    return [
        Fact(
            kind=d["kind"],
            subject=d["subject"],
            measures=d.get("measures", {}),
            attrs=d.get("attrs", {}),
            provenance=d.get("provenance", {}),
        )
        for d in data
    ]


def _derived_facts(directory: Path) -> list[Fact]:
    return extract_utilization(_input_facts(directory), "<facts>")


def _facts(directory: Path) -> list[Fact]:
    return sort_facts([*_input_facts(directory), *_derived_facts(directory)])


def run_fixture(directory: Path):
    return judge(_facts(directory), load_catalog(), _meta(directory)["runtime"])


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_derived_facts_match_golden(self, directory):
        derivados = _derived_facts(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in derivados] == expected

    def test_findings_match_golden(self, directory):
        achados = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in achados] == expected

    def test_every_fact_validates_against_schema(self, directory):
        for fact in _derived_facts(directory):
            validate_fact(fact.to_dict())

    def test_meta_declares_what_the_scenario_proves(self, directory):
        meta = _meta(directory)
        assert meta["name"] == directory.name
        assert meta["proves"].strip()


class TestOQueOCorpusInteiroGarante:
    def test_the_two_rules_never_fire_together(self):
        """A ausencia de skew e condicao de uma, e a presenca e condicao da outra."""
        for directory in fixture_dirs():
            ids = {f.rule_id for f in run_fixture(directory)}
            assert not {"SF-WASTE-001", "SF-WASTE-002"} <= ids, directory.name

    def test_both_rules_are_reached_by_the_corpus(self):
        """Regra sem golden que dispara e regra que ninguem exercita."""
        disparadas = set()
        for directory in fixture_dirs():
            disparadas.update(f.rule_id for f in run_fixture(directory))

        assert {"SF-WASTE-001", "SF-WASTE-002"} <= disparadas

    def test_nothing_quantifies_a_saving(self):
        """A garantia que o subprojeto E estabeleceu, aplicada aqui.

        "Voce economizaria X" exige o custo do run que NAO aconteceu, e nenhuma
        fonte mede contrafactual.
        """
        for directory in fixture_dirs():
            blob = str([f.to_dict() for f in _derived_facts(directory)]).lower()
            for palavra in ("saving", "economia", "estimated"):
                assert palavra not in blob, (directory.name, palavra)

    def test_no_summary_without_measured_utilization(self):
        for directory in fixture_dirs():
            tem_metrica = any(
                f.kind == "glue.metric"
                and f.attrs.get("name") == "glue.driver.workerUtilization"
                for f in _input_facts(directory)
            )
            resumos = [
                f for f in _derived_facts(directory) if f.kind == "glue.utilization.summary"
            ]
            if resumos:
                assert tem_metrica, directory.name
