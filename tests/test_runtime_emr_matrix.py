"""EMR_MATRIX: guard de drift contra o knowledge, e as quatro decisoes de desenho.

O guard segue o mecanismo de `test_runtime_detect.py::test_matrix_matches_
committed_knowledge` -- a matriz do codigo tem que espelhar a pagina de
knowledge --, mas nao pode ser o mesmo teste literal: sao 30 releases e quatro
colunas, e transcrever isso a mao no assert produziria uma segunda copia para
manter desatualizada. Aqui a fonte e `knowledge/emr/runtime-matrix.md`, lida e
comparada celula a celula.

As duas paginas oficiais tem perfis de drift OPOSTOS, e por isso as duas metades
do guard sao diferentes:

  6.x  Estavel. A serie nao recebe minors novos; o ultimo e emr-6.15.0. O
       conjunto de releases tem que ser IDENTICO nos dois lados -- linha nova ou
       removida e falha.

  7.x  Churn estrutural garantido: a AWS lanca um minor a cada 90 dias no
       maximo, e cada minor PREPENDE uma coluna. Exigir igualdade de conjunto
       faria o guard falhar ~4x/ano por motivo que nao e drift do que a matriz
       ja conhece, e guard ruidoso e guard ignorado. Entao: toda release que
       EMR_MATRIX conhece tem que casar celula a celula (celula alterada e
       drift, e falha), e release nova so na pagina vira UserWarning
       informativo.
"""
import warnings
from pathlib import Path

import pytest

from sparkforge.facts.runtime_detect import (
    EMR_MATRIX,
    _apache_version,
    _emr_key,
    detect_runtime,
)
from sparkforge.rules.version_scope import _parse, in_scope

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "knowledge" / "emr" / "runtime-matrix.md"

_ABSENT = {"—", "-", ""}


def _committed_matrix() -> dict[str, dict[str, str]]:
    """Le as tabelas das secoes 2 e 3 do documento de knowledge.

    Parsear o markdown em vez de reescrever os valores no teste e o que faz
    deste um guard de DRIFT e nao uma terceira copia: so ha dois lugares onde a
    matriz existe, e este teste e a ponte entre eles.
    """
    rows: dict[str, dict[str, str]] = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| emr-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        release, spark, hadoop, iceberg, installed, pyspark = cells[:6]
        row = {
            "spark": spark,
            "hadoop": hadoop,
            "python_installed": tuple(
                p.strip() for p in installed.split(",") if p.strip()
            ),
        }
        if iceberg not in _ABSENT:
            row["iceberg"] = iceberg
        if pyspark not in _ABSENT:
            row["python"] = pyspark
        rows[_emr_key(release)] = row
    return rows


def _series(releases, major: str) -> set[str]:
    return {r for r in releases if r.startswith(f"{major}.")}


COMMITTED = _committed_matrix()


class TestDocumentIsParseable:
    def test_the_tables_were_actually_found(self):
        """Se o formato da tabela mudar, o parser devolve pouco ou nada e todo
        o resto deste arquivo passaria vazio -- guard que nao guarda nada."""
        assert len(COMMITTED) == len(EMR_MATRIX) >= 30
        assert _series(COMMITTED, "7") and _series(COMMITTED, "6")


class TestDriftGuardSixX:
    """Serie estavel: igualdade estrita nos dois sentidos."""

    def test_release_set_is_identical(self):
        assert _series(EMR_MATRIX, "6") == _series(COMMITTED, "6")

    @pytest.mark.parametrize("release", sorted(_series(EMR_MATRIX, "6")))
    def test_every_cell_matches_the_committed_knowledge(self, release):
        assert EMR_MATRIX[release] == COMMITTED[release]


class TestDriftGuardSevenX:
    """Serie com churn: celula alterada falha, coluna nova so avisa."""

    @pytest.mark.parametrize("release", sorted(_series(EMR_MATRIX, "7")))
    def test_every_known_cell_matches_the_committed_knowledge(self, release):
        assert release in COMMITTED, (
            f"emr-{release} esta em EMR_MATRIX e nao na pagina de knowledge. "
            f"Este sentido E falha: o codigo afirmando o que o documento nao diz."
        )
        assert EMR_MATRIX[release] == COMMITTED[release]

    def test_a_release_only_in_the_document_is_informative_not_a_failure(self):
        extra = sorted(_series(COMMITTED, "7") - _series(EMR_MATRIX, "7"))
        if extra:
            warnings.warn(
                f"EMR_MATRIX desatualizada: a pagina de knowledge ja tem "
                f"{', '.join('emr-' + r for r in extra)}. Considere acrescentar. "
                f"Isto NAO e drift do que a matriz conhece.",
                UserWarning,
                stacklevel=1,
            )


class TestAmznSuffixIsKeptAndStillCompares:
    """A decisao mais perigosa da matriz, testada dos dois lados.

    `3.5.6-amzn-2` nao e o `3.5.6` da Apache. Se o valor cru vazasse para a
    comparacao de range, a regra seria pulada e a cobertura apagada em silencio
    -- o modo de falha mais caro deste repositorio. Se o sufixo fosse
    descartado, o relatorio esconderia que o cluster roda um fork.
    """

    def test_the_range_matches_despite_the_vendor_suffix(self):
        assert in_scope({"spark": ">=3.5"}, {"spark": "3.5.6-amzn-2"}) is True
        assert in_scope({"spark": "==3.5.6"}, {"spark": "3.5.6-amzn-2"}) is True
        assert in_scope({"iceberg": ">=1.10.0"}, {"iceberg": "1.10.0-amzn-1"}) is True

    def test_the_two_level_suffix_of_the_six_x_series_also_matches(self):
        """A forma `-amzn-0.1` (emr-6.11.1, 6.10.1, 6.9.1, 6.8.1) era partida em
        quatro segmentos e virava (3,3,2,1) -- MAIOR que (3,3,2). Quatro
        releases inteiras tinham toda regra de range exato pulada em silencio."""
        assert _parse("3.3.2-amzn-0.1") == (3, 3, 2)
        assert in_scope({"spark": "==3.3.2"}, {"spark": "3.3.2-amzn-0.1"}) is True
        assert in_scope({"spark": "<=3.3.2"}, {"spark": "3.3.2-amzn-0.1"}) is True
        assert in_scope({"spark": ">=3.3.2"}, {"spark": "3.3.2-amzn-0.1"}) is True
        assert in_scope({"spark": "<3.4"}, {"spark": "3.3.2-amzn-0.1"}) is True

    def test_the_raw_value_survives_into_the_context_and_the_fact(self):
        context, facts = detect_runtime({"terraform": {"emr_release": "emr-7.13.0"}})
        assert context.spark == "3.5.6-amzn-2"
        assert context.iceberg == "1.10.0-amzn-1"
        signal = next(f for f in facts if f.attrs.get("component") == "spark")
        assert signal.attrs["observed"] == ["3.5.6-amzn-2"]

    @pytest.mark.parametrize("release", sorted(EMR_MATRIX))
    def test_apache_version_agrees_with_version_scope_on_every_cell(self, release):
        """As duas implementacoes do truncamento vivem em modulos que nao se
        importam (`facts/` nao depende de `rules/`). Este teste e o que impede
        elas de divergirem: se uma mudar sozinha, a matriz inteira acusa."""
        for key in ("spark", "hadoop", "iceberg"):
            raw = EMR_MATRIX[release].get(key)
            if raw:
                assert _parse(_apache_version(raw)) == _parse(raw), (release, key)


class TestPythonIsASetNotAValue:
    def test_the_installed_set_is_recorded_for_every_release(self):
        for release, row in EMR_MATRIX.items():
            assert isinstance(row["python_installed"], tuple), release
            assert row["python_installed"], release

    def test_seven_x_resolves_python_because_aws_documents_the_pyspark_default(self):
        context, _ = detect_runtime({"terraform": {"emr_release": "emr-7.5.0"}})
        assert context.python == "3.9"

    def test_seven_thirteen_flipped_the_pyspark_default_to_three_eleven(self):
        """A release note de 7.13.0 declara a virada. Errar isto faz o
        analisador aplicar sintaxe de 3.9 a um runtime 3.11 e vice-versa."""
        assert EMR_MATRIX["7.13.0"]["python"] == "3.11"
        assert EMR_MATRIX["7.12.0"]["python"] == "3.9"

    def test_six_x_does_not_resolve_python_and_that_is_deliberate(self):
        """A AWS nao reafirma o default do PySpark por release em 6.x. Escolher
        `3.7` porque e o maior da lista seria inventar. Fica vazio, e regra com
        `python` em `runtime_scope` e pulada por ausencia -- falha fechada."""
        context, _ = detect_runtime({"terraform": {"emr_release": "emr-6.15.0"}})
        assert context.python == ""
        assert in_scope({"python": ">=3.7"}, context.to_dict()) is False
        assert "python" not in EMR_MATRIX["6.15.0"]

    def test_a_directly_observed_pyspark_python_wins_over_the_matrix(self):
        """`PYSPARK_PYTHON` da classificacao `spark-env` chega como
        `python_version` e resolve a ambiguidade de 6.x."""
        context, _ = detect_runtime(
            {
                "terraform": {"emr_release": "emr-6.15.0"},
                "describe_cluster": {"python_version": "3.7"},
            }
        )
        assert context.python == "3.7"


class TestIcebergDoesNotExistBeforeSixFive:
    def test_the_key_is_absent_not_a_sentinel(self):
        assert "iceberg" not in EMR_MATRIX["6.4.0"]
        assert "iceberg" in EMR_MATRIX["6.5.0"]

    def test_a_rule_scoped_on_iceberg_is_skipped_by_absence(self):
        context, _ = detect_runtime({"terraform": {"emr_release": "emr-6.4.0"}})
        assert context.iceberg == ""
        assert in_scope({"iceberg": ">=1.0"}, context.to_dict()) is False
        assert in_scope({"iceberg": "*"}, context.to_dict()) is False

    def test_six_five_does_derive_iceberg(self):
        context, _ = detect_runtime({"terraform": {"emr_release": "emr-6.5.0"}})
        assert context.iceberg == "0.12.0"


class TestHadoopStaysInTheMatrixAndOutOfTheContext:
    def test_every_release_records_hadoop(self):
        for release, row in EMR_MATRIX.items():
            assert row["hadoop"], release

    def test_it_never_becomes_a_runtime_context_field(self):
        """Nenhuma regra do catalogo tem `hadoop` em `runtime_scope`, e
        `_DIRECT_KEYS` nao o le de fonte nenhuma: o campo so poderia receber
        valor de matriz, e `to_dict()` passaria a emiti-lo em todo golden com
        `runtime` no payload. Custo sem consumidor."""
        context, _ = detect_runtime({"terraform": {"emr_release": "emr-7.13.0"}})
        assert "hadoop" not in context.to_dict()

    def test_no_catalog_rule_scopes_on_hadoop(self):
        from sparkforge.rules.loader import load_catalog

        assert not [
            r["id"] for r in load_catalog() if "hadoop" in (r.get("runtime_scope") or {})
        ]


class TestObservationBeatsTheMatrix:
    def test_describe_cluster_is_declared_in_the_precedence(self):
        from sparkforge.facts.runtime_detect import _PRECEDENCE

        assert "describe_cluster" in _PRECEDENCE
        assert _PRECEDENCE.index("event_log") < _PRECEDENCE.index("describe_cluster")
        assert _PRECEDENCE.index("describe_cluster") < _PRECEDENCE.index("cli")

    def test_a_directly_observed_version_beats_the_derived_one(self):
        context, _ = detect_runtime(
            {
                "terraform": {"emr_release": "emr-7.5.0"},
                "describe_cluster": {"spark_version": "3.5.2-amzn-1"},
            }
        )
        assert context.spark == "3.5.2-amzn-1"
        assert context.detected_from == ["describe_cluster", "terraform"]

    def test_the_event_log_still_beats_describe_cluster(self):
        context, _ = detect_runtime(
            {
                "describe_cluster": {"spark_version": "3.5.2-amzn-1"},
                "event_log": {"spark_version": "3.5.3-amzn-0"},
            }
        )
        assert context.spark == "3.5.3-amzn-0"

    def test_drift_between_the_dump_and_the_matrix_is_a_divergence(self):
        """A matriz e guard de drift: `describe_cluster` dizendo uma versao que
        a release label nao embarca significa que uma das duas descreve outro
        cluster."""
        context, facts = detect_runtime(
            {
                "describe_cluster": {
                    "emr_release": "emr-7.5.0",
                    "spark_version": "3.3.0",
                }
            }
        )
        assert context.divergences
        signal = next(f for f in facts if f.attrs.get("component") == "spark")
        assert signal.measures["distinct_versions"] == 2


class TestTheReleaseLabelIsAcceptedInBothSpellings:
    @pytest.mark.parametrize("value", ["emr-7.13.0", "EMR-7.13.0", "7.13.0"])
    def test_every_spelling_finds_the_same_row(self, value):
        context, _ = detect_runtime({"terraform": {"emr_release": value}})
        assert context.spark == "3.5.6-amzn-2"

    @pytest.mark.parametrize("key", ["emr_release", "emr_version", "emr"])
    def test_every_declared_key_derives(self, key):
        context, _ = detect_runtime({"terraform": {key: "emr-7.13.0"}})
        assert context.spark == "3.5.6-amzn-2"

    def test_an_unknown_release_derives_nothing_and_does_not_raise(self):
        context, _ = detect_runtime({"terraform": {"emr_release": "emr-9.9.9"}})
        assert context.emr == "emr-9.9.9"
        assert context.spark == ""

    def test_the_label_form_is_not_comparable_by_in_scope(self):
        """ARMADILHA CONHECIDA, fixada aqui de proposito em vez de deixada muda.

        `RuntimeContext.emr` guarda o release label (`emr-7.5.0`), decisao da
        Task 1 e documentada no campo. Mas `version_scope._parse` le o primeiro
        segmento como `emr` -> 0, e um `runtime_scope: {"emr": ">=7.0"}` nunca
        casaria -- perda de cobertura muda, o modo de falha que as Fases 5a e
        5a.2 fecharam. Nenhuma regra do catalogo usa `emr` em `runtime_scope`
        hoje, entao nada esta quebrado; a primeira que usar precisa decidir
        entre normalizar o campo ou ensinar `_parse` a ignorar o prefixo."""
        assert _parse("emr-7.5.0") == (0,)
        assert in_scope({"emr": ">=7.0"}, {"emr": "emr-7.5.0"}) is False
        assert in_scope({"emr": ">=7.0"}, {"emr": "7.5.0"}) is True


class TestTwoPlatformsDoNotProduceAVersionDivergence:
    """A consequencia de plataforma dupla nao vira um segundo P0.

    Nao ha release de EMR que case com Glue 4.0 em Spark E Iceberg ao mesmo
    tempo. Contar essa discordancia como divergencia de versao mandaria o
    operador "alinhar o Terraform a versao efetiva" quando o remedio e remover
    o artefato que nao e deste job -- que e o que SF-ENV-005 ja diz.
    """

    SOURCES = {
        "terraform": {"glue_version": "4.0"},
        "event_log": {"emr_release": "emr-6.9.0", "spark_version": "3.3.0"},
    }

    def test_the_two_matrices_really_do_disagree_on_iceberg(self):
        from sparkforge.facts.runtime_detect import GLUE_MATRIX

        assert GLUE_MATRIX["4.0"]["iceberg"] != EMR_MATRIX["6.9.0"]["iceberg"]

    def test_and_it_does_not_become_sf_env_001(self):
        from sparkforge.rules.engine import judge
        from sparkforge.rules.loader import load_catalog

        context, facts = detect_runtime(self.SOURCES)
        findings = judge(facts, load_catalog(), context.to_dict())
        assert [f.rule_id for f in findings] == ["SF-ENV-005"]

    def test_a_direct_observation_still_diverges_against_a_matrix(self):
        """A exclusao vale so entre derivacoes de plataformas diferentes.
        Observacao direta nunca e excluida da contagem -- senao a guarda
        inteira viraria uma forma elegante de calar SF-ENV-001."""
        context, _ = detect_runtime(
            {
                "terraform": {"glue_version": "5.0"},
                "event_log": {"spark_version": "3.3.0"},
            }
        )
        assert any("spark" in d for d in context.divergences)

    def test_the_build_suffix_alone_is_not_a_version_divergence(self):
        """Glue 4.0 deriva `3.3.0`; emr-6.9.0 deriva `3.3.0-amzn-1`. Mesma
        versao Apache, patches diferentes. `observed` mostra as duas cruas."""
        _, facts = detect_runtime(self.SOURCES)
        signal = next(f for f in facts if f.attrs.get("component") == "spark")
        assert signal.measures["distinct_versions"] == 1
        assert signal.attrs["observed"] == ["3.3.0", "3.3.0-amzn-1"]
