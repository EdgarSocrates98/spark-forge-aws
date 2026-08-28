"""Golden do corpus de metricas SQL por no do plano.

Dominio proprio, e nao mais cenarios dentro de `fixtures/eventlog/`, pelo mesmo
motivo que `data_quality` e `graph` tem dominio proprio embora leiam o mesmo
`.py` que `pyspark_ast`: o artefato e um, a pergunta e outra.

`test_every_fixture_domain_has_a_golden_module` cobra este arquivo. Sem ele o
corpus existe, parece cobertura, e `scripts/verify_wheel.py` nunca o executa
contra o pacote instalado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.sql_metrics import extract_sql_metrics_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "sql_metrics"

REQUIRED_FIXTURES = {
    "scan_parquet_measured",
    "scan_iceberg_batchscan",
    "aqe_replans_the_scan",
    "unknown_metric",
    "no_sql_events",
    "truncated_log",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    entrada = directory / "input"
    facts = []
    for log in sorted(entrada.glob("*.jsonl")):
        facts.extend(extract_sql_metrics_path(log, repo_root=entrada))
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
        expected = json.loads(
            (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

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


class TestOQueOCorpusInteiroGarante:
    def test_no_scan_carries_a_measure_the_execution_never_published(self):
        """A garantia que separa medido de inferido, sobre o corpus INTEIRO.

        Todo `spark.sql.scan` so pode carregar measure cujo nome de metrica
        aparece no `sparkPlanInfo` daquela execucao E teve valor publicado. Um
        default que preenchesse zero passaria em cada cenario isolado e
        quebraria aqui -- e e disto que depende a confiabilidade do fingerprint
        que vem depois.
        """
        from sparkforge.facts.sql_metric_names import measure_for

        for directory in fixture_dirs():
            publicadas: dict[int, set[str]] = {}
            for log in sorted((directory / "input").glob("*.jsonl")):
                for linha in log.read_text(encoding="utf-8").splitlines():
                    if not linha.strip():
                        continue
                    try:
                        evento = json.loads(linha)
                    except ValueError:
                        continue
                    plano = evento.get("sparkPlanInfo")
                    if not isinstance(plano, dict):
                        continue
                    pilha = [plano]
                    while pilha:
                        no = pilha.pop()
                        pilha.extend(no.get("children") or [])
                        for metrica in no.get("metrics") or []:
                            medida = measure_for(str(metrica.get("name") or ""))
                            if medida:
                                publicadas.setdefault(
                                    evento.get("executionId"), set()
                                ).add(medida)

            for fact in _extract(directory):
                if fact.kind != "spark.sql.scan":
                    continue
                disponiveis = publicadas.get(fact.subject["execution_id"], set())
                assert set(fact.measures) <= disponiveis, (directory.name, fact.measures)
