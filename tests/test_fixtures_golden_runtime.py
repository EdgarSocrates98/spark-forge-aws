"""Golden test do corpus de deteccao de runtime.

Arquivo dedicado por uma razao que nenhum outro corpus tem: aqui o runtime nao
e premissa, e resultado. Todos os outros golden passam `meta["runtime"]` para
`judge`; este detecta o runtime a partir das fontes da fixture e julga com o
que detectou. Julgar com o runtime declarado esconderia o defeito que o corpus
existe para pegar -- uma deteccao que resolve errado continuaria sendo julgada
contra a versao certa, e `runtime_scope` nunca reprovaria nada.

`env.runtime_signal` alimenta SF-ENV-001 (P0) e SF-ENV-004 (P1) e, ate este
corpus existir, era emitido por um extrator com testes unitarios mas sem
NENHUM golden: as duas regras nunca tinham disparado de ponta a ponta.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "runtime"

REQUIRED_FIXTURES = {
    "divergent_sources",
    "pre_aqe_runtime",
    "consistent_sources",
    "glue_40_runtime",
    "glue_51_runtime",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _sources(directory: Path) -> dict:
    sources: dict = {}
    for source_file in sorted((directory / "input").glob("*.json")):
        sources.update(json.loads(source_file.read_text(encoding="utf-8")))
    return sources


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    context, facts = detect_runtime(_sources(directory))
    findings, skipped = judge(facts, load_catalog(), context.to_dict(), return_skipped=True)
    return meta, context, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_rules_all_fire(self, directory):
        meta, _, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, _, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_detected_runtime_matches_the_declared_one(self, directory):
        """O meta declara o runtime ESPERADO da deteccao. Divergir aqui e a
        matriz Glue->Spark/Python/Iceberg ter mudado sem ninguem notar."""
        meta, context, _, _, _ = run_fixture(directory)
        detected = context.to_dict()
        assert {k: detected[k] for k in meta["runtime"]} == meta["runtime"]

    def test_everything_validates_against_schema(self, directory):
        _, _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_detection_is_deterministic(self, directory):
        first = detect_runtime(_sources(directory))
        second = detect_runtime(_sources(directory))
        assert [f.to_dict() for f in first[1]] == [f.to_dict() for f in second[1]]
        assert first[0].to_dict() == second[0].to_dict()


class TestAdversarial:
    def test_divergence_is_recorded_never_silently_resolved(self):
        """Resolver a precedencia e obrigatorio -- ha um so runtime. Esconder
        que houve conflito nao e: o operador precisa saber que o Terraform e o
        run discordam, senao ele corrige o sintoma errado."""
        _, context, facts, findings, _ = run_fixture(FIXTURES / "divergent_sources")
        assert context.spark == "3.3.0"
        assert context.divergences
        assert facts[0].measures["distinct_versions"] == 2
        assert [f.rule_id for f in findings] == ["SF-ENV-001"]
        assert findings[0].severity == "P0"

    def test_agreement_between_two_sources_is_not_divergence(self):
        """`source_count: 2` com `distinct_versions: 1`. Contar fontes em vez
        de valores distintos faria toda deteccao multi-fonte virar um P0."""
        _, _, facts, findings, _ = run_fixture(FIXTURES / "consistent_sources")
        assert facts[0].measures == {"distinct_versions": 1, "source_count": 2}
        assert findings == []

    def test_old_runtime_alone_is_not_a_divergence(self):
        """Spark 3.1.1 dispara SF-ENV-004 (sem AQE por default) e SO ela.
        Confundir 'versao antiga' com 'fontes discordando' inverteria a
        severidade: P1 acionavel viraria P0 falso."""
        _, _, _, findings, _ = run_fixture(FIXTURES / "pre_aqe_runtime")
        assert [f.rule_id for f in findings] == ["SF-ENV-004"]

    def test_current_runtime_fires_nothing(self):
        _, _, _, findings, _ = run_fixture(FIXTURES / "consistent_sources")
        assert findings == []

    def test_aqe_boundary_holds_on_both_sides(self):
        """Spark 3.2 e a fronteira do AQE por default, e no vocabulario de Glue
        isso e `<4.0`. Glue 3.0 dispara SF-ENV-004, Glue 4.0 nao. Um erro de
        `<` para `<=` aqui ou recomenda AQE a quem ja tem, ou cala sobre quem
        nao tem -- as duas metades quebram este teste."""
        _, _, _, before, _ = run_fixture(FIXTURES / "pre_aqe_runtime")
        _, _, _, after, _ = run_fixture(FIXTURES / "glue_40_runtime")
        assert [f.rule_id for f in before] == ["SF-ENV-004"]
        assert [f.rule_id for f in after] == []

    def test_the_three_supported_glue_versions_resolve_to_the_matrix(self):
        """Glue 4.0, 5.0 e 5.1 sao os runtimes correntes. Um erro na matriz
        aqui contamina TODO limiar e toda guarda de versao do relatorio."""
        expected = {
            "glue_40_runtime": ("3.3.0", "3.10", "1.0.0"),
            "consistent_sources": ("3.5.4", "3.11", "1.7.1"),
            "glue_51_runtime": ("3.5.6", "3.11", "1.10.0"),
        }
        for name, (spark, python, iceberg) in expected.items():
            _, context, _, _, _ = run_fixture(FIXTURES / name)
            detected = (context.spark, context.python, context.iceberg)
            assert detected == (spark, python, iceberg), name
