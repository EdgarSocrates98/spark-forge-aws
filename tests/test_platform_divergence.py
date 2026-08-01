"""Duas plataformas detectadas produzem sinal -- independentemente das versoes.

O criterio 12 da Fase 5 exige sinal quando Glue e EMR sao detectados juntos
**mesmo quando as versoes derivadas coincidem**. A §3.3 do spec registrou que
isso NAO estava coberto, e o motivo e de camada, nao de ajuste:

`SF-ENV-001` dispara sobre `env.runtime_signal` com `measures.distinct_versions
> 1` -- comparacao de VERSAO DE COMPONENTE. `runtime_detect._build_facts` itera
so `observations` (spark, python, iceberg, athena); a plataforma nunca virava
fact. Se Glue 4.0 deriva Spark 3.3.0 e o cluster EMR observado roda o mesmo
3.3.0, nao ha divergencia de versao nenhuma e a dupla deteccao passava muda.

Identidade de plataforma e pergunta diferente de versao de componente: a
pergunta e "quantas plataformas?", nao "quais versoes?". Dai `env.platform`
com `measures.distinct_platforms`, e `SF-ENV-005` sobre ele.

O primeiro caso abaixo -- versoes coincidindo -- e o que nenhum teste anterior
pegava, e o unico que prova o criterio 12.
"""
import pytest

from sparkforge.facts.runtime_detect import EMITTED_KINDS, detect_runtime
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

# Glue 4.0 deriva Spark 3.3.0 pela GLUE_MATRIX. O cluster EMR observado reporta
# o mesmo 3.3.0 -- as versoes derivadas COINCIDEM, entao `distinct_versions` e 1
# e SF-ENV-001 nao tem como disparar. E exatamente esse o caso do criterio 12.
COINCIDENT = {
    "terraform": {"glue_version": "4.0"},
    "event_log": {"spark_version": "3.3.0", "emr_release": "emr-6.10.0"},
}

# As mesmas duas plataformas, agora com as versoes discordando. SF-ENV-001 e
# SF-ENV-005 falam de coisas distintas e podem coexistir: uma diz que as fontes
# discordam sobre a versao, a outra que discordam sobre a propria plataforma.
DIVERGENT = {
    "terraform": {"glue_version": "5.0"},
    "event_log": {"spark_version": "3.3.0", "emr_release": "emr-6.10.0"},
}

# `ids` como lista pre-computada, NUNCA `ids=lambda`: com `parametrize` sobre
# lista vazia o pytest 8.x chama o callable sobre um sentinela interno e estoura
# DENTRO do coletor, abortando a suite inteira em vez de pular.
DUAL_PLATFORM = [("versoes-coincidindo", COINCIDENT), ("versoes-divergindo", DIVERGENT)]
DUAL_PLATFORM_IDS = [nome for nome, _ in DUAL_PLATFORM]


def _fire(sources: dict) -> tuple[list, list]:
    context, facts = detect_runtime(sources)
    findings = judge(facts, load_catalog(), context.to_dict())
    return facts, findings


def _platform_fact(facts: list):
    matching = [f for f in facts if f.kind == "env.platform"]
    return matching[0] if matching else None


class TestTwoPlatformsAlwaysProduceSignal:
    """O invariante da task, nas duas metades do espaco de versoes."""

    @pytest.mark.parametrize("nome,sources", DUAL_PLATFORM, ids=DUAL_PLATFORM_IDS)
    def test_env_platform_counts_two_platforms(self, nome, sources):
        facts, _ = _fire(sources)
        fact = _platform_fact(facts)
        assert fact is not None, (
            f"{nome}: nenhum fact `env.platform`. Glue e EMR foram declarados por "
            f"fontes diferentes e a deteccao nao registrou identidade nenhuma."
        )
        assert fact.measures["distinct_platforms"] == 2
        assert fact.attrs["observed"] == ["emr", "glue"]

    @pytest.mark.parametrize("nome,sources", DUAL_PLATFORM, ids=DUAL_PLATFORM_IDS)
    def test_sf_env_005_fires(self, nome, sources):
        _, findings = _fire(sources)
        assert "SF-ENV-005" in [f.rule_id for f in findings], (
            f"{nome}: SF-ENV-005 nao disparou. Duas plataformas detectadas tem que "
            f"produzir sinal independentemente das versoes."
        )

    @pytest.mark.parametrize("nome,sources", DUAL_PLATFORM, ids=DUAL_PLATFORM_IDS)
    def test_the_finding_is_p0(self, nome, sources):
        _, findings = _fire(sources)
        finding = next(f for f in findings if f.rule_id == "SF-ENV-005")
        assert finding.severity == "P0"
        assert finding.evidence


class TestTheCaseVersionComparisonCouldNeverReach:
    """Criterio 12, isolado: versoes coincidindo."""

    def test_version_comparison_stays_silent(self):
        """SF-ENV-001 NAO dispara aqui, e nao e defeito: nao ha divergencia de
        versao alguma. E a prova de que nenhum ajuste em SF-ENV-001 alcancaria
        este caso -- ele nao e sobre versao."""
        facts, findings = _fire(COINCIDENT)
        signal = [f for f in facts if f.kind == "env.runtime_signal"]
        assert signal, "o fact de versao continua sendo emitido"
        assert all(f.measures["distinct_versions"] == 1 for f in signal)
        assert "SF-ENV-001" not in [f.rule_id for f in findings]

    def test_and_platform_identity_speaks_anyway(self):
        _, findings = _fire(COINCIDENT)
        assert [f.rule_id for f in findings] == ["SF-ENV-005"]


class TestBothRulesCoexistWhenBothAreTrue:
    def test_divergent_versions_fire_both(self):
        """Versao divergente E plataforma dupla sao dois defeitos, nao um.
        Reportar so um faria o operador corrigir metade e achar que acabou."""
        _, findings = _fire(DIVERGENT)
        assert sorted({f.rule_id for f in findings}) == ["SF-ENV-001", "SF-ENV-005"]


class TestOnePlatformIsNotDivergence:
    """A contraparte negativa. `env.platform` e emitido com UMA plataforma de
    proposito: a regra passa a ser avaliada e explicitamente nao dispara, em vez
    de sumir por `requires_facts` -- que e a ausencia muda que esta fase existe
    para eliminar."""

    @pytest.mark.parametrize(
        "nome,sources",
        [
            ("so-glue", {"terraform": {"glue_version": "5.0"}}),
            ("so-emr", {"event_log": {"emr_release": "emr-7.5.0", "spark_version": "3.5.1"}}),
        ],
        ids=["so-glue", "so-emr"],
    )
    def test_single_platform_emits_the_fact_and_fires_nothing(self, nome, sources):
        facts, findings = _fire(sources)
        fact = _platform_fact(facts)
        assert fact is not None, f"{nome}: uma plataforma detectada tem que virar fact"
        assert fact.measures["distinct_platforms"] == 1
        assert "SF-ENV-005" not in [f.rule_id for f in findings]

    def test_two_sources_agreeing_on_one_platform_is_not_divergence(self):
        """`source_count: 2` com `distinct_platforms: 1`. Contar fontes em vez de
        identidades distintas faria toda deteccao multi-fonte virar um P0 -- o
        mesmo defeito que `test_agreement_between_two_sources_is_not_divergence`
        ja trava para versoes."""
        facts, findings = _fire(
            {"terraform": {"glue_version": "5.0"}, "cli": {"glue_version": "5.0"}}
        )
        fact = _platform_fact(facts)
        assert fact.measures == {"distinct_platforms": 1, "source_count": 2}
        assert "SF-ENV-005" not in [f.rule_id for f in findings]

    def test_no_platform_observed_emits_no_fact(self):
        """Nenhuma plataforma observada nao e "uma plataforma": e ausencia de
        observacao. Emitir o fact aqui afirmaria identidade que ninguem viu."""
        facts, _ = _fire({"event_log": {"spark_version": "3.5.4"}})
        assert _platform_fact(facts) is None


class TestTheFactSaysWhereEachPlatformCameFrom:
    def test_origins_name_the_sources(self):
        """`origins` e o que torna o achado acionavel: o operador precisa saber
        QUAL fonte descreve outra coisa, senao o P0 nao tem onde ser corrigido."""
        facts, _ = _fire(COINCIDENT)
        fact = _platform_fact(facts)
        assert fact.attrs["origins"] == {"emr": ["event_log"], "glue": ["terraform"]}

    def test_resolved_follows_the_declared_precedence(self):
        """Precedencia de fonte, a mesma de `_PRECEDENCE`: o event log observou o
        run, o Terraform declarou intencao. Resolver NAO descarta a outra --
        `observed` continua com as duas, e e sobre ela que a regra dispara."""
        facts, _ = _fire(COINCIDENT)
        fact = _platform_fact(facts)
        assert fact.attrs["resolved"] == "emr"
        assert fact.attrs["observed"] == ["emr", "glue"]


class TestTheContractAroundTheNewKind:
    def test_env_platform_is_in_the_declared_vocabulary(self):
        """`EMITTED_KINDS` e a fonte unica de
        `tests/test_rules_catalog_reachability.py`: kind fora dela faz a regra
        que o exige parecer inalcancavel."""
        assert "env.platform" in EMITTED_KINDS

    def test_the_fact_validates_against_the_schema(self):
        from sparkforge.findings.validate import validate_fact

        facts, _ = _fire(COINCIDENT)
        for fact in facts:
            validate_fact(fact.to_dict())

    def test_detection_is_deterministic(self):
        first = detect_runtime(COINCIDENT)
        second = detect_runtime(COINCIDENT)
        assert [f.to_dict() for f in first[1]] == [f.to_dict() for f in second[1]]
        assert first[0].to_dict() == second[0].to_dict()


class TestRuntimeContextKnowsEmr:
    def test_emr_is_a_field_with_an_empty_default(self):
        from sparkforge.findings.models import RuntimeContext

        assert RuntimeContext().emr == ""
        assert "emr" in RuntimeContext().to_dict()

    def test_the_detected_release_label_reaches_the_context(self):
        context, _ = detect_runtime(
            {"event_log": {"emr_release": "emr-7.5.0", "spark_version": "3.5.1"}}
        )
        assert context.emr == "emr-7.5.0"
        assert context.glue == ""

    def test_platform_divergence_is_recorded_in_the_context_too(self):
        """`divergences` e o canal que um humano le no relatorio. Deixar a
        plataforma de fora dele reproduziria, no contexto, o mesmo silencio que
        esta task remove do catalogo."""
        context, _ = detect_runtime(COINCIDENT)
        assert any(d.startswith("platform:") for d in context.divergences)
