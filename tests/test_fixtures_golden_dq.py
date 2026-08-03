"""Golden test do corpus de validacao de dados.

Arquivo dedicado, mesma razao de `test_fixtures_golden_callgraph.py`: o golden
guarda SO os facts `dq.*`. Os de `pyspark_ast` sobre os mesmos `.py` ja tem o
corpus `fixtures/pyspark/` -- repetidos aqui, uma mudanca em `pyspark_ast`
quebraria dois goldens pelo mesmo motivo, escondendo qual dos dois contratos
regrediu.

Todo `expects_rules` nasce vazio nesta task, e isso e o correto e nao uma
pendencia: o catalogo `SF-DQ` so existe a partir da Task 7. Ate la, os oito
goldens de findings sao NEGATIVOS -- se alguma regra ja existente disparar
sobre um `dq.*`, o diff aparece aqui. Depois das Tasks 7 e 8, sete deles ganham
regra e `validated_correctly` continua vazio de proposito.

Sete das oito fixtures tem defeito; `validated_correctly` e a metade negativa,
e e ela que separa "a regra reconhece o defeito" de "a regra dispara sobre
qualquer validacao". `TestAdversarial` abaixo trava, fixture a fixture, o
atributo que cada uma existe para provar -- o golden sozinho prova que a saida
nao mudou, mas nao prova que ela diz o que o nome da fixture promete.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.data_quality import EMITTED_KINDS, extract_data_quality_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "dq"

REQUIRED_FIXTURES = {
    # Os quatro positivos, um por regra da area.
    "validation_after_write",
    "suite_without_enforcement",
    "check_recomputes_lineage",
    "repeated_checks_same_target",
    # A metade negativa das quatro.
    "validated_correctly",
    # Os dois frameworks, cada um pelo que o `.py` PERMITE afirmar sobre a
    # varredura: `shares_scan: true` num, chave ausente no outro.
    "pydeequ_suite",
    "great_expectations_suite",
    # A maquinaria de ponto cego, que e a que apodrece em silencio.
    "unresolved_helper",
    # A guarda contra o falso positivo de D-5c-11: alvo que chega por parametro
    # sai SEM `target_persisted`, e `SF-DQ-003` nao avalia o check. Nenhuma das
    # oito acima tem check sobre parametro, entao sem esta fixture remover a
    # omissao no extrator passaria por `fixtures/dq/` inteiro sem quebrar nada.
    "helper_validates_cached_param",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_data_quality_tree(directory / "input", repo_root=directory / "input")
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def _only_check(directory: Path):
    _, facts, _, _ = run_fixture(FIXTURES / directory)
    checks = _by_kind(facts, "dq.check")
    assert len(checks) == 1, [f.attrs for f in checks]
    return checks[0]


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

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = extract_data_quality_tree(directory / "input", repo_root=directory / "input")
        second = extract_data_quality_tree(directory / "input", repo_root=directory / "input")
        assert [f.to_dict() for f in first] == [f.to_dict() for f in second]

    def test_module_analyzed_counts_agree_with_the_emitted_facts(self, directory):
        """A sumarizacao nao pode divergir dos facts que ela resume.

        `unresolved_count` e a medida que um agente le para saber quanto do
        arquivo o extrator NAO enxergou. Se ela deixar de bater com os facts,
        o ponto cego passa a ser subnotificado -- e subnotificar ponto cego e
        indistinguivel de nao ter nenhum.
        """
        _, facts, _, _ = run_fixture(directory)
        modules = _by_kind(facts, "dq.module_analyzed")
        assert len(modules) == len(sorted((directory / "input").rglob("*.py")))
        assert sum(m.measures["check_count"] for m in modules) == len(_by_kind(facts, "dq.check"))
        assert sum(m.measures["unresolved_count"] for m in modules) == len(
            _by_kind(facts, "dq.unresolved")
        )


class TestAdversarial:
    """Cada fixture prova o que o nome dela diz -- conferido, nunca presumido.

    O golden prova que a saida nao mudou; ele nao prova que a saida esta certa.
    Uma fixture chamada `validation_after_write` cujo check saisse com
    `position_vs_write: before_write` continuaria com golden verde, e a Task 7
    escreveria SF-DQ-001 contra um corpus que nao a exercita.
    """

    def test_validation_after_write_validates_after_the_write(self):
        check = _only_check("validation_after_write")
        assert check.attrs["position_vs_write"] == "after_write"
        assert check.attrs["target"] == "vendas"

    def test_suite_without_enforcement_has_a_check_and_no_consequence(self):
        """A prova e uma AUSENCIA, e ausencia e o que some sem ninguem notar."""
        _, facts, _, _ = run_fixture(FIXTURES / "suite_without_enforcement")
        assert _by_kind(facts, "dq.check")
        assert _by_kind(facts, "dq.enforcement") == []

    def test_check_recomputes_lineage_needs_both_attributes(self):
        check = _only_check("check_recomputes_lineage")
        assert check.attrs["target_persisted"] is False
        assert check.attrs["action_after_check"] is True

    def test_repeated_checks_counts_two_scans_over_the_same_target(self):
        _, facts, _, _ = run_fixture(FIXTURES / "repeated_checks_same_target")
        checks = _by_kind(facts, "dq.check")
        assert len(checks) == 2
        assert {c.attrs["target"] for c in checks} == {"pagamentos"}
        for check in checks:
            assert check.measures["checks_on_target"] == 2
            assert check.attrs["shares_scan"] is False

    def test_validated_correctly_is_clean_on_all_four_axes(self):
        """A metade negativa das quatro regras, num fact so.

        `action_after_check` e `true` aqui e isso e CORRETO -- o write reusa o
        alvo. Com `cache()` no meio, o reuso nao recomputa: e a prova de que
        SF-DQ-003 precisa dos dois atributos, e nao so deste.
        """
        check = _only_check("validated_correctly")
        assert check.attrs["position_vs_write"] == "before_write"
        assert check.attrs["target_persisted"] is True
        assert check.measures["checks_on_target"] == 1
        _, facts, _, _ = run_fixture(FIXTURES / "validated_correctly")
        assert [f.attrs["form"] for f in _by_kind(facts, "dq.enforcement")] == ["raise"]

    def test_pydeequ_suite_shares_scan_and_names_neither_vetoed_key(self):
        """D-5c-1 e D-5c-2: `single_pass` e `declared_checks` sao proibidos.

        Os dois seriam afirmacoes que o `.py` nao sustenta -- a suite custa uma
        passada POR AGRUPAMENTO, e contar `addCheck` no fonte nao diz quantos
        agrupamentos sao.
        """
        check = _only_check("pydeequ_suite")
        assert check.attrs["framework"] == "pydeequ"
        assert check.attrs["shares_scan"] is True
        assert "single_pass" not in check.attrs
        assert "declared_checks" not in check.attrs
        assert check.attrs["target"] == "assinaturas", "o alvo e o argumento de onData"

    def test_great_expectations_omits_shares_scan_entirely(self):
        """D-5c-3: chave AUSENTE, nunca `false`.

        `engine._where_matches` reprova caminho ausente, entao SF-DQ-004 nao
        avalia este check -- que e o correto. `false` afirmaria que a validacao
        nao compartilha varredura, e o `.py` nao diz isso.
        """
        check = _only_check("great_expectations_suite")
        assert check.attrs["framework"] == "great_expectations"
        assert check.attrs["check_type"] == "batch_parameters_dataframe"
        assert "shares_scan" not in check.attrs
        assert check.attrs["target"] == "faturas"

    def test_unresolved_helper_guesses_no_target(self):
        """Alvo nao resolvido e CONTADO, e nunca adivinhado.

        `spark` como alvo dataria este check contra o write de qualquer outro
        dado que tambem saia de `spark`, e SF-DQ-001 afirmaria "validou depois
        de publicar" sobre dados que nunca se tocaram.
        """
        _, facts, _, _ = run_fixture(FIXTURES / "unresolved_helper")
        unresolved = _by_kind(facts, "dq.unresolved")
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "unresolved_target"
        assert "target" not in unresolved[0].attrs
        assert _by_kind(facts, "dq.check") == []
        # Sem `dq.check` nao ha subject a proteger: o `raise` do helper existe,
        # e ainda assim nao vira enforcement solto.
        assert _by_kind(facts, "dq.enforcement") == []

    def test_the_corpus_covers_every_kind_the_extractor_emits(self):
        """Recorte local do invariante global de `test_fixtures_kind_coverage`.

        Aqui a falha aponta para a fixture que falta neste corpus, em vez de
        para "algum golden do repositorio inteiro".
        """
        covered = set()
        for directory in fixture_dirs():
            _, facts, _, _ = run_fixture(directory)
            covered.update(f.kind for f in facts)
        assert set(EMITTED_KINDS) - covered == set()

    def test_the_two_frameworks_disagree_only_where_the_source_allows(self):
        """PyDeequ e Great Expectations produzem o MESMO kind.

        O que muda entre eles nao e a correlacao -- os quatro atributos saem do
        mesmo `_check` --, e sim o que o `.py` permite afirmar sobre a
        varredura. Se um dia os dois divergirem em `target_persisted` ou em
        `position_vs_write`, alguem duplicou o caminho de construcao.
        """
        deequ = _only_check("pydeequ_suite")
        gx = _only_check("great_expectations_suite")
        correlacao = {"target", "target_persisted", "action_after_check", "position_vs_write"}
        assert correlacao <= set(deequ.attrs)
        assert correlacao <= set(gx.attrs)
        assert set(deequ.attrs) - set(gx.attrs) == {"shares_scan"}
