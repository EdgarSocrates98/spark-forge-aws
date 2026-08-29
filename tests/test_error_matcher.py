"""Tests for Deterministic Error Matcher and Reliability RCA."""

from sparkforge.errors.matcher import DeterministicErrorMatcher
from sparkforge.reliability.rca import ReliabilityAnalyzer


def test_error_matcher_oom():
    matcher = DeterministicErrorMatcher()
    log = (
        "ERROR YarnClusterScheduler: Container killed by YARN for exceeding memory limits. 5.5 "
        "GB of 5.0 GB physical memory used."
    )
    matches = matcher.match_log(log)
    assert len(matches) > 0
    assert matches[0].error_id == "ERR-GLUE-001"
    assert matches[0].service == "glue"
    assert matches[0].confidence > 0.90


def test_reliability_rca():
    analyzer = ReliabilityAnalyzer()
    events = [
        {
            "timestamp": "2026-08-20T10:00:00Z",
            "source": "cloudwatch",
            "event": "Task failure",
            "resource": "glue_job_1",
            "severity": "info",
        },
        {
            "timestamp": "2026-08-20T10:05:00Z",
            "source": "spark_eventlog",
            "event": "Container killed for exceeding memory limits (OOM)",
            "resource": "executor-2",
            "severity": "critical",
        },
    ]
    report = analyzer.analyze_incident("INC-001", events)
    assert "Out of Memory" in report.primary_root_cause
    assert report.confidence >= 0.90
    assert len(report.immediate_mitigations) > 0


class TestConhecimentoDeErroDeGlue6:
    """Secao 79: so erro OBSERVADO em fonte oficial entra.

    Os tres abaixo tem texto exato no Developer Guide de migracao para o Glue
    6.0. Erro hipotetico -- "provavelmente da NoClassDefFound" -- nao entra:
    conhecimento inventado com forma de conhecimento conhecido e pior que
    lacuna, porque o operador o trata como observacao.
    """

    def test_jar_de_scala_212_sob_spark_4(self):
        matcher = DeterministicErrorMatcher()
        achados = matcher.match_log("java.lang.NoSuchMethodError: scala.Predef$.refArrayOps(...)")
        assert "ERR-GLUE-002" in {a.error_id for a in achados}

    def test_sdk_v2_antigo_com_user_jars_first(self):
        matcher = DeterministicErrorMatcher()
        achados = matcher.match_log("Caused by: java.lang.NoSuchFieldError: SDK_VERSION")
        assert "ERR-GLUE-003" in {a.error_id for a in achados}

    def test_athena_sobre_tabela_iceberg_v3(self):
        matcher = DeterministicErrorMatcher()
        achados = matcher.match_log("GENERIC_USER_ERROR: Cannot read unsupported version 3")
        achado = next(a for a in achados if a.error_id == "ERR-ATH-001")
        assert achado.service == "athena"
        assert achado.fixes, "erro sem correcao nomeada nao ajuda ninguem"

    def test_toda_entrada_declara_fonte_e_data(self):
        import json
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1] / "knowledge" / "errors"
        for arquivo in raiz.glob("**/*.json"):
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            assert dados.get("sources"), f"{arquivo.name}: sem fonte"
            assert dados.get("last_verified"), f"{arquivo.name}: sem data de verificacao"
