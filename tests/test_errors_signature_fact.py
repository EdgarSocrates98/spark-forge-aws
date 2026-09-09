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


# ---------------------------------------------------------------------------
# A PROCEDENCIA DO CATALOGO DE ASSINATURAS (2026-09-09)
#
# Estes testes existem por causa de um defeito que passou por TODA a suite e
# so caiu no `Artifact parity gate` do CI, que roda o corpus contra o WHEEL
# instalado.
#
# `DeterministicErrorMatcher` resolvia o diretorio por
# `Path(__file__).parent.parent.parent / "knowledge" / "errors"`. No
# repositorio isso da `<raiz>/knowledge/errors` e funciona; instalado por pip,
# da `site-packages/knowledge/errors`, que NAO EXISTE -- o `force-include` do
# `pyproject.toml` poe o diretorio em `sparkforge/knowledge`.
#
# O modo de falha era SILENCIOSO: `_load_signatures` devolve cedo quando o
# diretorio nao existe, `signatures` fica vazia, e `build_signature_matches`
# passa a emitir `error.signature.unresolved` para TUDO. Um operador com o
# pacote instalado veria "nenhuma assinatura conhecida cobre isto" sobre um
# `NoSuchMethodError` que o catalogo conhece ha meses.
#
# A correcao e usar `sparkforge/knowledge_ref.py::knowledge_dir()`, que ja
# existia e ja resolvia as tres origens na ordem certa. Estes testes o prendem.
# ---------------------------------------------------------------------------


class TestProcedenciaDoCatalogoDeAssinaturas:
    def test_o_diretorio_default_vem_de_knowledge_dir(self):
        """Amarra o CAMINHO, e nao so o resultado: no repositorio os dois
        caminhos coincidem, entao um teste que so contasse assinaturas passaria
        com o bug de volta."""
        from sparkforge.errors.matcher import DeterministicErrorMatcher
        from sparkforge.knowledge_ref import knowledge_dir

        assert DeterministicErrorMatcher().errors_dir == knowledge_dir() / "errors"

    def test_o_catalogo_default_nao_esta_vazio(self):
        """Guarda contra a regressao pelo lado do efeito: catalogo vazio faz
        TODA excecao cair em `nenhuma_assinatura_casou`, e o relatorio fica
        limpo justamente onde deveria acusar."""
        from sparkforge.errors.matcher import DeterministicErrorMatcher
        from sparkforge.knowledge_ref import knowledge_dir

        # Contagem DERIVADA do disco, e nao fixada: acrescentar assinatura nao
        # pode quebrar este teste, cujo assunto e a PROCEDENCIA do diretorio.
        # Quem cobra o NUMERO e `tests/test_rules_errors.py`, e la o numero e a
        # afirmacao.
        no_disco = len(list((knowledge_dir() / "errors").rglob("*.json")))
        assert no_disco > 0, "o catalogo de assinaturas nao pode estar vazio"
        assert len(DeterministicErrorMatcher().signatures) == no_disco

    def test_SPARKFORGE_KNOWLEDGE_redireciona_o_catalogo(self, tmp_path, monkeypatch):
        """A consequencia de usar `knowledge_dir()`: o override de ambiente
        passa a valer tambem para as assinaturas, como ja valia para o resto de
        `knowledge/`."""
        from sparkforge.errors.matcher import DeterministicErrorMatcher

        vazio = tmp_path / "knowledge"
        (vazio / "errors").mkdir(parents=True)
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(vazio))
        assert DeterministicErrorMatcher().signatures == []
