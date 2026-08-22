"""Golden test do corpus de compatibilidade de migracao entre versoes de Glue.

Arquivo dedicado, mesma razao dos demais `test_fixtures_golden_*.py`: o golden
guarda os facts `mig.*` (extrator `sparkforge/facts/migration.py`, Tasks 4-6
desta fase) e os findings de `rules/catalog/glue-migration.yaml` (`SF-MIG`,
Task 7). `sparkforge/facts/migration.py` documenta por que `migration` so
entrou em `tests/test_fixtures_kind_coverage.py::EXTRACTORS` no MESMO commit
em que ganhou catalogo -- e essa entrada e o que deixava
`test_every_kind_of_every_extractor_appears_in_some_golden[migration]`
vermelho de proposito ate esta Task 9 escrever o corpus.

A extracao usa `extract_migration_tree`, e nao um laco sobre `*.py`/`*.jar`/
`requirements*.txt`, pela mesma razao de `regen_graph`
(`scripts/regen_fixtures.py`): e a funcao que `adapters/_core.py` chama
quando o `--path` e diretorio, e ela ordena GLOBALMENTE por (kind, subject,
id) -- um laco por arquivo concatenaria blocos ja ordenados por arquivo e o
golden descreveria uma ordenacao que nenhuma superficie do produto emite.

O corpus e desenhado por eixo, uma fixture por kind (nove fixtures para oito
kinds, porque `cast_sem_guarda` carrega dois papeis: prova `mig.ansi_risk` E
prova que SF-MIG-003 fica muda):

  * `sdk_v1_import` -- dispara SF-MIG-001 (`com.amazonaws.*` sobrevivendo no
    Glue 5.0+).
  * `emrfs_config` -- dispara SF-MIG-002 (chave exclusiva do EMRFS sobrevivendo
    no S3A do Glue 5.0+).
  * `cast_sem_guarda` -- emite `mig.ansi_risk`, mas SF-MIG-003 e `blocked_on`
    (nenhuma fonte confirma a versao do Glue em que o Spark liga ANSI mode por
    default -- ver comentario acima da regra em
    `rules/catalog/glue-migration.yaml`). O ponto da fixture e o NEGATIVO: o
    fact existe, a regra fica muda.
  * `legacy_conf`, `deprecated_api`, `table_format`, `jar_binary`,
    `python_dep` -- os cinco kinds que a Task 5/6 emitiu sem regra
    correspondente ainda (observacao pura). Cada um prova so o vocabulario do
    fact, `expects_rules` vazio de proposito.
  * `clean_job` -- o negativo de referencia: job escrito do jeito atual (SDK
    v2, sem config de EMRFS, sem API depreciada, sem cast sem guarda). Zero
    facts, zero findings -- se algum kind `mig.*` disparar aqui, e falso
    positivo do extrator.

`SF-MIG-003` e o motivo de `test_every_rule_has_a_fixture_that_fires_it` e
`test_every_severity_branch_has_a_golden_that_produces_it`
(`tests/test_fixtures_kind_coverage.py`) continuarem vermelhos para essa regra
especifica mesmo depois deste corpus: `blocked_on` faz `judge()` pular a regra
incondicionalmente (`sparkforge/rules/engine.py`, antes mesmo de checar
`runtime_scope` ou `requires_facts`), entao NENHUMA fixture pode faze-la
disparar enquanto o bloqueio existir -- e o bloqueio e uma decisao consciente
registrada no catalogo, nao uma lacuna de corpus. Essa e exatamente a garantia
que `TestRegraBloqueadaNuncaAparece` em `tests/test_migration_assessment.py`
ja fixa no nivel do assessment multi-degrau; aqui ela e fixada no nivel do
`judge()` de um runtime unico.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.migration import EMITTED_KINDS, extract_migration_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "migration"

REQUIRED_FIXTURES = {
    "sdk_v1_import",
    "emrfs_config",
    "cast_sem_guarda",
    "legacy_conf",
    "deprecated_api",
    "table_format",
    "jar_binary",
    "python_dep",
    "clean_job",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    return extract_migration_tree(input_dir, repo_root=input_dir)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de
# fixtures vazio, o pytest 8.x invoca o callable sobre o sentinela interno
# NOTSET durante a coleta e aborta a sessao INTEIRA, nao so este arquivo.
# Mesma guarda de `test_fixtures_golden_emr_serverless.py` e
# `test_fixtures_golden_graph.py`.
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
        fact_ids = {f.id for f in facts}
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict(), fact_ids=fact_ids)

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second

    def test_no_two_facts_share_an_id(self, directory):
        _, facts, _, _ = run_fixture(directory)
        ids = [f.id for f in facts]
        assert len(ids) == len(set(ids))


class TestAdversarial:
    def test_every_emitted_kind_appears_in_this_corpus(self):
        """Recorte local do invariante global de
        `test_fixtures_kind_coverage.py`. Aqui ele falha com a mensagem certa:
        kind de migracao sem fixture de migracao."""
        vistos: set[str] = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            vistos.update(f.kind for f in facts)
        assert set(EMITTED_KINDS) - vistos == set()

    def test_sf_mig_003_never_fires_despite_the_evidence_it_needs(self):
        """`cast_sem_guarda` carrega o fact que SF-MIG-003 exige
        (`mig.ansi_risk` com `attrs.form == "cast"`), e mesmo assim a regra
        fica muda: `blocked_on` faz o motor pular ANTES de avaliar `when`
        (`sparkforge/rules/engine.py::judge`). O skip precisa ter o motivo
        certo -- `blocked_on`, nunca `requires_facts` -- senao um operador
        que leia `skipped` esperaria o fact que ja esta la.
        """
        _, facts, findings, skipped = run_fixture(FIXTURES / "cast_sem_guarda")
        assert _by_kind(facts, "mig.ansi_risk"), "a fixture perdeu o fact que a justifica"
        assert "SF-MIG-003" not in {f.rule_id for f in findings}
        bloqueio = next(s for s in skipped if s["rule_id"] == "SF-MIG-003")
        assert bloqueio["reason"] == "blocked_on"

    def test_the_clean_job_is_never_accused(self):
        """O sentido negativo do golden vale tanto quanto o positivo: um job
        escrito com SDK v2, sem config de EMRFS, sem API depreciada e sem cast
        sem guarda nao pode emitir fact nenhum -- se emitir, o extrator esta
        capturando alem do que o proprio vocabulario declara."""
        _, facts, findings, _ = run_fixture(FIXTURES / "clean_job")
        assert facts == []
        assert findings == []

    def test_python_dep_ignores_comment_blank_and_unpinned_package(self):
        """`boto3` sem `==` e o comentario da fixture nao fixam versao
        nenhuma -- nenhum dos dois e o vocabulario que `mig.python_dep`
        observa. Recorte local do que `tests/test_facts_migration.py`
        (`TestNegativoDependenciaPython`) ja prova por unidade, preso a este
        golden especifico para que uma regressao apareca nos dois lugares."""
        _, facts, _, _ = run_fixture(FIXTURES / "python_dep")
        deps = {f.attrs["package"]: f.attrs["version"] for f in _by_kind(facts, "mig.python_dep")}
        assert deps == {"pandas": "2.0.3", "pyarrow": "14.0.1"}

    def test_jar_binary_reads_scala_from_the_file_name_not_the_content(self):
        """`.jar` e observacao de ARQUIVO INTEIRO, ancorada em `line: 0`: nao
        ha linha de fonte para apontar, so o arquivo (docstring de
        `_jar_facts` em `sparkforge/facts/migration.py`)."""
        _, facts, _, _ = run_fixture(FIXTURES / "jar_binary")
        jar = _by_kind(facts, "mig.jar_binary")
        assert len(jar) == 1
        assert jar[0].attrs["scala"] == "2.12"
        assert jar[0].subject["line"] == 0

    def test_no_fact_carries_judgement(self):
        """Recorte do corpus inteiro do invariante que
        `tests/test_facts_migration.py::test_o_fact_nao_carrega_juizo` ja
        prova por unidade: o extrator OBSERVA, nunca julga. Preso ao golden
        para que uma regressao apareca no diff do corpus tambem, nao so no
        teste de unidade."""
        palavras = ("severidade", "risco", "deve", "incompativel")
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            for fact in facts:
                texto = (str(fact.attrs) + str(fact.measures)).lower()
                for palavra in palavras:
                    assert palavra not in texto, f"{directory.name}/{fact.kind} julga: {texto}"
