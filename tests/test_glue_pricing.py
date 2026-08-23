"""Preco como dado com data e regiao -- e o que a fonte NAO sustenta.

O defeito que estes testes existem para impedir nao e um numero errado: e um
numero certo que envelhece em silencio, ou um numero calculado a partir de duas
fontes que nao falam da mesma coisa.
"""
import pytest
import yaml

from sparkforge.facts import pricing
from sparkforge.facts.runtime_matrix import SOURCE_TYPES


class TestTodaEntradaCarregaProcedencia:
    def test_todo_preco_tem_fonte_tipo_e_data(self):
        for entrada in pricing.load()["prices"]:
            assert entrada["source"].startswith("https://")
            assert entrada["source_type"] in SOURCE_TYPES
            assert entrada["retrieved"]

    def test_todo_anuncio_tem_fonte_tipo_e_data(self):
        for entrada in pricing.load()["announcements"]:
            assert entrada["source"].startswith("https://")
            assert entrada["source_type"] in SOURCE_TYPES
            assert entrada["retrieved"]

    def test_o_vocabulario_de_source_type_nao_e_redeclarado(self):
        """Mesma disciplina da matriz de feature: importado, nunca copiado."""
        import inspect

        fonte = inspect.getsource(pricing)
        assert "from sparkforge.facts.runtime_matrix import SOURCE_TYPES" in fonte
        assert "SOURCE_TYPES = " not in fonte


class TestEixoDeclaradoAindaQuandoDesconhecido:
    def test_regiao_e_versao_sao_sempre_declaradas(self):
        for entrada in pricing.load()["prices"]:
            # `UNQUALIFIED` conta: a fonte foi lida e nao qualificou. O que nao
            # pode e o campo faltar, que diria "ninguem leu".
            assert entrada["region"]
            assert entrada["runtime_version"]


class TestNaoInfereCustoPorVersao:
    def test_a_fonte_nao_diferencia_preco_por_versao_de_runtime(self):
        """O resultado, nao a lacuna.

        Se um dia uma fonte publicar preco por versao, este teste falha e alguem
        precisa decidir conscientemente o que muda -- que e o ponto.
        """
        assert pricing.differentiates_by_runtime_version() is False

    def test_o_modulo_nao_expoe_nenhum_calculo_de_desconto(self):
        import inspect

        fonte = inspect.getsource(pricing)
        for proibido in ("0.30", "0.7", "* 0.", "discount", "desconto"):
            assert proibido not in fonte, proibido

    def test_anuncio_sem_baseline_nao_permite_derivar_preco_anterior(self):
        for anuncio in pricing.announcements():
            if not anuncio.get("baseline"):
                # Sem base declarada, nao ha o que calcular -- e o modulo nao
                # oferece nenhuma funcao que finja que ha.
                assert not hasattr(pricing, "price_for_version")


class TestFiltro:
    def test_filtrar_por_versao_devolve_tambem_o_preco_nao_qualificado(self):
        seis = pricing.prices("6.0")
        assert seis, "esconder o preco do servico responderia 'nao ha preco' quando ha"
        assert all(p["runtime_version"] in ("6.0", pricing.UNQUALIFIED) for p in seis)


class TestFailClosed:
    @pytest.mark.parametrize(
        "mutacao",
        [
            {"source": ""},
            {"source_type": "BLOG_QUALQUER"},
            {"retrieved": ""},
            {"region": ""},
        ],
    )
    def test_entrada_sem_evidencia_estoura_na_carga(self, mutacao, tmp_path, monkeypatch):
        base = pricing.load()["prices"][0].copy()
        base.update(mutacao)
        arquivo = tmp_path / "pricing.yaml"
        arquivo.write_text(
            yaml.safe_dump({"unit": "DPU-hour", "prices": [base]}), encoding="utf-8"
        )
        monkeypatch.setattr(pricing, "safe_knowledge_file", lambda *_: arquivo)
        pricing.load.cache_clear()
        try:
            with pytest.raises(pricing.PricingError):
                pricing.load()
        finally:
            pricing.load.cache_clear()

    def test_tabela_vazia_estoura_em_vez_de_responder_zero(self, tmp_path, monkeypatch):
        arquivo = tmp_path / "pricing.yaml"
        arquivo.write_text(yaml.safe_dump({"prices": []}), encoding="utf-8")
        monkeypatch.setattr(pricing, "safe_knowledge_file", lambda *_: arquivo)
        pricing.load.cache_clear()
        try:
            with pytest.raises(pricing.PricingError):
                pricing.load()
        finally:
            pricing.load.cache_clear()
