"""`sparkforge/knowledge_freshness.py`: o estado de cada fonte citada.

Pares positivo/negativo por estado, com lock sintetico e `as_of` fixo, e a
precedencia entre eles. O lock real nao entra aqui: ele muda a cada refresh, e
a distribuicao real sai datada no STATUS.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from sparkforge.knowledge_freshness import (
    AGING_BASIS,
    AGING_DAYS,
    ESTADOS,
    carregar_lock,
    citacoes_de,
    citacoes_do_doc,
    estado,
    fontes_de_knowledge,
    mapa,
)

AS_OF = date(2026, 9, 11)
U = "https://docs.example.com/latest/pagina.html"


def _lock(**campos):
    return {
        U: {
            "pinned": False,
            "rules": ["SF-X-001"],
            "docs": [],
            "retrieved": ["2026-08-01"],
            **campos,
        }
    }


def _conferida(dias: int, **extra):
    checked = date.fromordinal(AS_OF.toordinal() - dias).isoformat()
    return _lock(sha256="ab" * 32, checked_at=checked, **extra)


class TestEstados:
    def test_fixed(self):
        e = estado(U, "2026-08-01", _lock(pinned=True, changed_at="2026-09-01"), AS_OF)
        assert (e.state, e.reason) == ("fixed", "versao_no_caminho")

    def test_unverified(self):
        e = estado(U, "2026-08-01", _lock(), AS_OF)
        assert (e.state, e.reason) == ("unverified", "nunca_conferida")

    def test_stale_quando_mudou_depois_da_validacao(self):
        e = estado(U, date(2026, 8, 1), _conferida(3, changed_at="2026-09-01"), AS_OF)
        assert e.state == "stale"
        assert (e.validated, e.changed_at) == ("2026-08-01", "2026-09-01")

    def test_nao_stale_quando_revalidou_depois_da_mudanca(self):
        e = estado(U, "2026-09-02", _conferida(3, changed_at="2026-09-01"), AS_OF)
        assert e.state == "fresh"

    def test_mudou_no_mesmo_dia_da_validacao_nao_e_stale(self):
        e = estado(U, "2026-09-01", _conferida(3, changed_at="2026-09-01"), AS_OF)
        assert e.state == "fresh"

    def test_sem_data_de_validacao_e_mudanca_registrada_e_stale(self):
        assert estado(U, None, _conferida(3, changed_at="2026-09-01"), AS_OF).state == "stale"

    def test_fresh(self):
        e = estado(U, "2026-08-01", _conferida(5), AS_OF)
        assert (e.state, e.age_days, e.reason) == ("fresh", 5, "conferida_ha_5_dias")

    def test_aging(self):
        e = estado(U, "2026-08-01", _conferida(20), AS_OF)
        assert (e.state, e.age_days) == ("aging", 20)

    @pytest.mark.parametrize(
        ("dias", "esperado"), [(AGING_DAYS, "fresh"), (AGING_DAYS + 1, "aging")]
    )
    def test_borda_do_limiar(self, dias, esperado):
        assert estado(U, "2026-08-01", _conferida(dias), AS_OF).state == esperado

    def test_checked_at_ilegivel_e_unverified(self):
        lock = _lock(sha256="ab" * 32, checked_at="ontem")
        assert estado(U, "2026-08-01", lock, AS_OF).state == "unverified"


class TestPrecedencia:
    def test_fixed_vence_stale(self):
        lock = _conferida(3, changed_at="2026-09-01")
        lock[U]["pinned"] = True
        assert estado(U, "2026-08-01", lock, AS_OF).state == "fixed"

    def test_stale_vence_aging(self):
        assert (
            estado(U, "2026-08-01", _conferida(40, changed_at="2026-09-01"), AS_OF).state == "stale"
        )

    def test_stale_vence_unverified(self):
        """Hash removido depois de uma mudanca registrada: a mudanca e o sinal."""
        assert estado(U, "2026-08-01", _lock(changed_at="2026-09-01"), AS_OF).state == "stale"


class TestUnresolvedEConflito:
    def test_sem_lock(self):
        e = estado(U, "2026-08-01", None, AS_OF, motivo_sem_lock="lock_ilegivel")
        assert (e.state, e.reason) == ("unresolved", "lock_ilegivel")

    def test_fora_do_lock(self):
        e = estado("https://outra.example.com/x", "2026-08-01", _lock(), AS_OF)
        assert (e.state, e.reason) == ("unresolved", "fora_do_lock")

    def test_conflicted_ao_lado_do_estado(self):
        lock = _conferida(5)
        lock[U]["retrieved"] = ["2026-07-31", "2026-08-03"]
        e = estado(U, "2026-07-31", lock, AS_OF)
        assert e.state == "fresh"
        assert e.conflicted == {"validated": "2026-07-31", "other_readings": ["2026-08-03"]}

    def test_sem_conflito_quando_so_ha_a_mesma_data(self):
        assert estado(U, "2026-08-01", _conferida(5), AS_OF).conflicted is None


class TestMapa:
    def test_validacao_mais_antiga_e_sem_url(self):
        citacoes = [(U, "2026-09-02"), (U, "2026-08-01"), (None, None)]
        saida = mapa(citacoes, _conferida(3, changed_at="2026-09-01"), AS_OF)
        assert saida["source_freshness"][U]["state"] == "stale"
        assert saida["source_freshness"][U]["validated"] == "2026-08-01"
        politica = saida["freshness_policy"]
        assert politica["counts"]["sem_url"] == 1
        assert politica["counts"]["stale"] == 1
        assert set(politica["counts"]) == {*ESTADOS, "sem_url"}
        assert (politica["aging_days"], politica["basis"], politica["as_of"]) == (
            AGING_DAYS,
            AGING_BASIS,
            "2026-09-11",
        )

    def test_citacoes_de_findings_e_regras(self):
        itens = [{"sources": [{"url": U, "retrieved": date(2026, 8, 1)}, {"note": "x"}]}, {}]
        assert citacoes_de(itens) == [(U, date(2026, 8, 1)), (None, None)]


class TestLock:
    def test_ausente(self, tmp_path):
        assert carregar_lock(tmp_path) == (None, "lock_ausente")
        assert carregar_lock(None) == (None, "lock_ausente")

    def test_ilegivel(self, tmp_path):
        (tmp_path / "sources.lock.json").write_text("{nao", encoding="utf-8")
        assert carregar_lock(tmp_path) == (None, "lock_ilegivel")

    def test_lock_avulso_por_variavel_vence_a_raiz(self, tmp_path, monkeypatch):
        """`SPARKFORGE_SOURCES_LOCK` troca so o lock, e nao a raiz de knowledge."""
        avulso = tmp_path / "outro.json"
        avulso.write_text(json.dumps({"sources": _lock(pinned=True)}), encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_SOURCES_LOCK", str(avulso))
        fontes, motivo = carregar_lock(tmp_path / "nao-existe")
        assert motivo is None and fontes[U]["pinned"] is True

    def test_lock_avulso_que_nao_e_json_existente_e_recusado(self, tmp_path, monkeypatch):
        outro = tmp_path / "segredo.txt"
        outro.write_text("nada", encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_SOURCES_LOCK", str(outro))
        assert carregar_lock(tmp_path) == (None, "lock_ilegivel")
        monkeypatch.setenv("SPARKFORGE_SOURCES_LOCK", str(tmp_path / "nao-existe.json"))
        assert carregar_lock(tmp_path) == (None, "lock_ilegivel")

    def test_legivel(self, tmp_path):
        (tmp_path / "sources.lock.json").write_text(
            json.dumps({"schema_version": 1, "sources": _lock()}), encoding="utf-8"
        )
        fontes, motivo = carregar_lock(tmp_path)
        assert motivo is None and U in fontes


class TestFontesDeKnowledge:
    def test_secao_fontes_por_url_e_por_documento(self, tmp_path):
        (tmp_path / "glue").mkdir()
        (tmp_path / "glue" / "a.md").write_text(
            "# A\n\n## Fontes e frescor\nhttps://nao.example.com/1\n\n"
            "## Fontes\n- https://docs.example.com/x (retrieved 2026-08-03)\n"
            "- `https://padrao.example.com/release-<N>.html`\n"
            "### O que estas fontes NAO sustentam\nhttps://docs.example.com/y\n"
            "## Outra\nhttps://fora.example.com/z\n",
            encoding="utf-8",
        )
        por_url, por_doc = fontes_de_knowledge(tmp_path)
        assert set(por_url) == {"https://docs.example.com/x", "https://docs.example.com/y"}
        assert por_url["https://docs.example.com/x"] == {
            "docs": ["knowledge/glue/a.md"],
            "retrieved": ["2026-08-03"],
        }
        assert citacoes_do_doc(por_doc, "knowledge/glue/a.md") == [
            ("https://docs.example.com/x", "2026-08-03"),
            ("https://docs.example.com/y", None),
        ]
        assert citacoes_do_doc(por_doc, "knowledge/nao-existe.md") == []
