"""Golden test do corpus s3.

Corpus da listagem S3, que desbloqueou SF-PQ-001, SF-PQ-003 e SF-PQ-005
-- as tres regras que dependiam de `s3.prefix_summary` e ficavam inertes
com `blocked_on: extrator-de-listagem-s3` desde a Fase 0.

`input/*.json` sao dumps de `aws s3api list-objects-v2`; `input/catalog/`,
quando existe, e o dump do Glue Data Catalog que SF-PQ-005 correlaciona.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.catalog_schema import extract_catalog_schema_tree
from sparkforge.facts.s3_listing import extract_s3_listing_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "s3"

REQUIRED_FIXTURES = {
    "small_files_prefix",
    # Os dois ramos superiores de `severity_by` de SF-PQ-001. `small_files_prefix`
    # tem 1500 arquivos e cai no ramo P2; sem estes dois, P1 e P0 -- a unica P0 da
    # area -- nao apareciam em golden nenhum, e podiam virar qualquer severidade
    # com a suite inteira verde. Cada um tem a contagem no limiar EXATO do proprio
    # ramo, entao eles travam tambem os dois `>=`.
    "small_files_prefix_at_p1_boundary",
    "small_files_prefix_at_p0_boundary",
    "gzip_text_not_splittable",
    "healthy_prefix",
    "truncated_listing",
    "overpartitioned_prefix",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    facts = []
    for listing in sorted(input_dir.glob("*.json")):
        facts.extend(extract_s3_listing_path(listing, repo_root=input_dir))
    catalog = input_dir / "catalog"
    if catalog.is_dir():
        facts.extend(extract_catalog_schema_tree(catalog, repo_root=input_dir))
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
    def test_healthy_prefix_produces_zero_findings(self):
        """Arquivos de ~256 MB sao o alvo, nao um achado. Um erro de sinal no
        limiar de SF-PQ-001 acusaria exatamente este prefixo."""
        _, _, findings, _ = run_fixture(FIXTURES / "healthy_prefix")
        assert findings == []

    def test_control_objects_never_enter_the_average(self):
        """`_SUCCESS` tem 0 byte. Conta-lo como arquivo de dados derrubaria a
        media de QUALQUER prefixo, e SF-PQ-001 passaria a disparar em tabela
        saudavel -- falso positivo sistematico, o pior modo de falha desta
        ferramenta."""
        _, facts, _, _ = run_fixture(FIXTURES / "small_files_prefix")
        summary = next(f for f in facts if f.kind == "s3.prefix_summary")
        sentinel = next(f for f in facts if f.kind == "s3.analyzed")
        assert summary.measures["file_count"] == 1500
        assert sentinel.measures["object_count"] == 1501
        assert sentinel.measures["control_object_count"] == 1
        assert summary.measures["min_file_bytes"] > 0

    def test_every_severity_branch_of_the_small_files_rule_has_a_fixture(self):
        """Os TRES ramos de SF-PQ-001, cada um no limiar do proprio ramo.

        1500 arquivos caem no ultimo ramo, 10000 no do meio, 100000 no primeiro.
        As tres medias estao muito abaixo dos 32 MB do `threshold`, entao o que
        decide a severidade e so a contagem -- e as duas contagens novas sao os
        limiares EXATOS dos dois ramos superiores, onde `>=` e `>` discordam.

        Antes dos dois fixtures novos so o ramo P2 tinha golden: os outros dois,
        incluindo a unica P0 da area de Parquet, podiam virar qualquer
        severidade com a suite inteira verde. Nada no repositorio compara
        severidade de regra contra fixture fora do golden de `findings`.

        As contagens e as severidades vem do CATALOGO, nunca repetidas aqui.
        """
        regra = next(r for r in load_catalog() if r["id"] == "SF-PQ-001")
        ramos = regra["severity_by"]
        limiares = [int(b["when"].rsplit(">=", 1)[1]) for b in ramos]

        fixtures_por_ramo = [
            "small_files_prefix_at_p0_boundary",
            "small_files_prefix_at_p1_boundary",
            "small_files_prefix",
        ]
        assert len(fixtures_por_ramo) == len(ramos)

        vistos = []
        for nome, ramo, limiar in zip(fixtures_por_ramo, ramos, limiares, strict=True):
            _, facts, findings, _ = run_fixture(FIXTURES / nome)
            sumario = next(f for f in facts if f.kind == "s3.prefix_summary")
            achado = next(f for f in findings if f.rule_id == "SF-PQ-001")
            # A media nao pode ser o que decide: se ela subisse acima do limiar
            # o `when` deixaria de casar, e o fixture pararia de provar o ramo.
            assert sumario.measures["avg_file_bytes"] < regra["threshold"]["min_avg_bytes"]
            assert achado.severity == ramo["severity"]
            vistos.append((nome, sumario.measures["file_count"], achado.severity))

        # Os dois ramos superiores estao no limiar EXATO; o de baixo e o corpus
        # que ja existia, e fica onde estava.
        assert vistos[0][1] == limiares[0]
        assert vistos[1][1] == limiares[1]
        assert vistos[2][1] > limiares[2]
        # Tres severidades distintas: um ramo que colidisse com o vizinho nao
        # seria ramo nenhum.
        assert len({s for _, _, s in vistos}) == len(ramos)

    def test_gzip_text_is_kept_apart_from_parquet(self):
        """SF-PQ-003 exige `format: text` e `compression: gzip`. Um sumario
        unico por prefixo diluiria o `.gz` gigante na media do Parquet e a
        regra nunca casaria."""
        _, facts, findings, _ = run_fixture(FIXTURES / "gzip_text_not_splittable")
        summary = next(f for f in facts if f.kind == "s3.prefix_summary")
        assert (summary.attrs["format"], summary.attrs["compression"]) == ("text", "gzip")
        assert [f.rule_id for f in findings] == ["SF-PQ-003"]

    def test_truncated_listing_reports_the_blind_spot_and_no_summary(self):
        """Os numeros da primeira pagina disparariam SF-PQ-001 sobre uma
        amostra apresentada como total. O golden exige as duas metades: o ponto
        cego contado, E nenhum sumario derivado da pagina."""
        _, facts, findings, _ = run_fixture(FIXTURES / "truncated_listing")
        assert not [f for f in facts if f.kind == "s3.prefix_summary"]
        reasons = {f.attrs["reason"] for f in facts if f.kind == "s3.unresolved"}
        assert reasons == {"truncated_listing"}
        assert findings == []

    def test_findings_of_the_same_prefix_are_told_apart(self):
        """Dois grupos do mesmo prefixo nao podem produzir findings com o mesmo
        subject: o operador precisa saber em quais arquivos mexer."""
        _, facts, _, _ = run_fixture(FIXTURES / "small_files_prefix")
        summary = next(f for f in facts if f.kind == "s3.prefix_summary")
        assert "[parquet/snappy]" in summary.subject["symbol"]

    def test_partition_cardinality_needs_both_sources(self):
        """SF-PQ-005 exige listagem E catalogo. Com uma so, o motor pula por
        `requires_facts` em vez de julgar pela metade."""
        _, facts, findings, _ = run_fixture(FIXTURES / "overpartitioned_prefix")
        kinds = {f.kind for f in facts}
        assert {"s3.prefix_summary", "catalog.table_partitions"} <= kinds
        assert [f.rule_id for f in findings] == ["SF-PQ-005"]
