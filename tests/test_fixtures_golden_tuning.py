"""Golden test do corpus tuning: sete cenarios da configuracao derivada.

`sparkforge tune` NAO extrai de artefato -- deriva de facts JA extraidos
(`spark.stage.shuffle`, `spark.conf_effective`, `pyspark.conf_set`,
`tf.spark_conf`, `spark.runtime_version`) -- mesmo molde de `fixtures/finops/` e
`fixtures/capacity/`.

Os pares importam mais que os cenarios isolados:

  shuffle_medido_com_aqe / shuffle_medido_sem_aqe
      o MESMO shuffle, e o mesmo numero derivado, com significado diferente:
      a versao decide se o numero e piso inicial ou numero final.

  valor_atual_vem_do_codigo / valor_atual_vem_do_terraform
      o MESMO valor efetivo, e a classe de procedencia vem da FONTE que pediu.

  default_escrito_a_mao
      o sintoma da seccao 36: configuracao que alguem escreveu e nao muda nada.

`TestOQueOCorpusInteiroGarante` verifica as quatro garantias que valem sobre o
corpus INTEIRO, cada uma contra um erro que passaria despercebido cenario a
cenario.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.findings.models import Fact
from sparkforge.tuning import build_conf_advice

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "tuning"

REQUIRED_FIXTURES = {
    "shuffle_medido_com_aqe",
    "shuffle_medido_sem_aqe",
    "alvo_declarado_pelo_operador",
    "valor_atual_vem_do_codigo",
    "valor_atual_vem_do_terraform",
    "default_escrito_a_mao",
    "sem_shuffle_medido",
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


def run_fixture(directory: Path) -> dict:
    return build_conf_advice(_input_facts(directory), runtime=_meta(directory)["runtime"])


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_report_matches_golden(self, directory):
        relatorio = run_fixture(directory)
        expected = json.loads((directory / "expected" / "report.json").read_text(encoding="utf-8"))
        assert relatorio == expected

    def test_meta_declares_what_the_scenario_proves(self, directory):
        meta = _meta(directory)
        assert meta["name"] == directory.name
        assert meta["proves"].strip()


class TestOQueOCorpusInteiroGarante:
    def test_every_proposal_carries_formula_and_basis(self):
        """Numero sem a conta que o produziu e numero magico com outra roupa."""
        vistos = 0
        for directory in fixture_dirs():
            for propriedade in run_fixture(directory)["properties"]:
                derivado = propriedade["derived"]
                assert derivado["formula"].strip(), directory.name
                assert derivado["basis"]["shuffle_write_bytes"] > 0, directory.name
                assert derivado["basis"]["target_partition_bytes"] > 0, directory.name
                vistos += 1
        assert vistos >= 5

    def test_no_proposal_without_measured_shuffle(self):
        for directory in fixture_dirs():
            entradas = _input_facts(directory)
            mediu = any(
                f.kind == "spark.stage.shuffle" and float(f.measures.get("write_bytes") or 0) > 0
                for f in entradas
            )
            if run_fixture(directory)["properties"]:
                assert mediu, directory.name

    def test_every_proposal_carries_a_safety_level(self):
        for directory in fixture_dirs():
            for propriedade in run_fixture(directory)["properties"]:
                assert propriedade["safety"] in {"SAFE", "REVIEW", "EXPERIMENTAL"}, directory.name

    def test_nothing_applies_and_nothing_is_ranked_by_estimated_gain(self):
        """Sem esta garantia, a proxima pessoa vai achar que aplicar era o fim."""
        for directory in fixture_dirs():
            blob = str(run_fixture(directory)).lower()
            for palavra in ("applied", "estimated_saving", "expected_gain", "economia"):
                assert palavra not in blob, (directory.name, palavra)

    def test_every_refusal_says_what_would_unlock_it(self):
        for directory in fixture_dirs():
            recusas = run_fixture(directory)["refused"]
            assert recusas, directory.name
            for recusa in recusas:
                assert recusa["detail"].strip(), (directory.name, recusa["reason"])
