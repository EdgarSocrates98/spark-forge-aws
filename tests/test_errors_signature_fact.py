"""O matcher emite FATO, nao juizo.

Ele constata que a excecao casa com uma assinatura. O que fazer a respeito e
regra do catalogo -- e por isso `confidence`, `fixes` e `likely_causes` nao
viajam neste caminho.
"""

from __future__ import annotations

from sparkforge.errors.matcher import build_signature_matches
from sparkforge.findings.models import Fact


def _exc(classe: str, caused_by: list[str] | None = None) -> Fact:
    return Fact(
        kind="spark.exception",
        subject={"stage_id": 1},
        measures={},
        attrs={
            "exception_class": classe,
            "message_head": "x",
            "is_chained": bool(caused_by),
            "caused_by": caused_by or [],
        },
    )


class TestMatcherEmiteFato:
    def test_casa_por_classe_de_excecao(self):
        facts = build_signature_matches([_exc("java.lang.NoSuchMethodError")])
        m = [f for f in facts if f.kind == "error.signature_match"]
        assert m, "NoSuchMethodError tem assinatura no catalogo"
        assert m[0].attrs["signature_id"].startswith("ERR-")
        assert m[0].attrs["matched_on"] == "exception_class"

    def test_casa_pelo_encadeamento(self):
        facts = build_signature_matches(
            [_exc("org.apache.spark.SparkException", ["java.lang.NoSuchMethodError"])]
        )
        m = [f for f in facts if f.kind == "error.signature_match"]
        assert m and m[0].attrs["matched_on"] == "caused_by"

    def test_nao_carrega_juizo_nem_confidence(self):
        facts = build_signature_matches([_exc("java.lang.NoSuchMethodError")])
        for f in facts:
            for proibido in (
                "confidence",
                "fixes",
                "likely_causes",
                "diagnostic_steps",
                "unsafe_fixes",
            ):
                assert proibido not in f.attrs

    def test_sem_assinatura_sai_unresolved(self):
        facts = build_signature_matches([_exc("com.exemplo.ErroInedito")])
        un = [f for f in facts if f.kind == "error.signature.unresolved"]
        assert un and un[0].attrs["reason"] == "nenhuma_assinatura_casou"

    def test_sem_excecao_no_case_nao_emite_nada(self):
        assert build_signature_matches([]) == []
