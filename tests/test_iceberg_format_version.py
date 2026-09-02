"""`iceberg.format_version`: a versao que a tabela E, contra a que foi declarada.

O golden prova que o kind sai nas treze fixtures. Este arquivo prova as coisas
que um golden nao prova bem: as tres razoes de recusa, a diferenca entre
`diverges: false` e `diverges` ausente, e que a propriedade NUNCA supre o topo.
"""

from __future__ import annotations

import pytest

from sparkforge.facts.iceberg_metadata import (
    _VERSOES_DA_SPEC,
    extract_iceberg_metadata,
)


def _versao(payload: dict) -> dict:
    """O fact de versao daquele payload, ou falha dizendo que ele nao saiu."""
    facts = [
        f
        for f in extract_iceberg_metadata(payload, "dump.json")
        if f.kind == "iceberg.format_version"
    ]
    assert len(facts) == 1, (
        f"esperado UM `iceberg.format_version`, saiu {len(facts)}. Ele sai SEMPRE, "
        f"inclusive quando o dump nao traz o campo -- ali como recusa nomeada."
    )
    return dict(facts[0].attrs)


def _base(**extra) -> dict:
    return {"table": "analytics.t", **extra}


class TestAsTresVersoesDaSpec:
    @pytest.mark.parametrize("versao", sorted(_VERSOES_DA_SPEC))
    def test_cada_uma_resolve(self, versao):
        a = _versao(_base(format_version=versao))
        assert a["resolved"] is True
        assert a["declared"] == str(versao)

    def test_v1_nao_e_defeito(self):
        """Uma tabela v1 e valida.

        O defeito so existe quando a matriz diz que o engine do consumidor
        suporta mais E ha motivo para subir -- e isso e julgamento, que mora em
        regra e nao no extrator.
        """
        a = _versao(_base(format_version=1))
        assert a["resolved"] is True
        assert "reason" not in a

    def test_a_constante_daqui_inclui_1_e_a_de_upgrade_nao(self):
        """`feature_support.SPEC_VERSIONS` vale `{2, 3}`, e nao e a mesma coisa.

        Aquela constante governa UPGRADE de spec, e ninguem faz upgrade PARA v1.
        A pergunta aqui e outra -- de que versao a tabela E --, e v1 e resposta
        legitima. Este teste existe para que a "unificacao" obvia das duas
        constantes tenha de passar por cima da distincao.
        """
        from sparkforge.storage import feature_support

        assert 1 in _VERSOES_DA_SPEC
        assert 1 not in feature_support.SPEC_VERSIONS
        assert set(feature_support.SPEC_VERSIONS) < set(_VERSOES_DA_SPEC)


class TestADivergencia:
    def test_topo_e_propriedade_discordando_sai_como_fato(self):
        a = _versao(
            _base(format_version=3, properties={"format-version": "2"})
        )
        assert a["resolved"] is True
        assert a["declared"] == "3"
        assert a["property"] == "2"
        assert a["diverges"] is True

    def test_concordando_sai_false(self):
        a = _versao(_base(format_version=2, properties={"format-version": "2"}))
        assert a["diverges"] is False

    def test_sem_a_propriedade_o_campo_NAO_SAI(self):
        """Ausencia de lado nao e concordancia.

        `diverges: false` sem a propriedade se leria como "conferido e
        concorda", que e afirmacao sobre um lado que nao existe.
        """
        a = _versao(_base(format_version=2, properties={}))
        assert a["resolved"] is True
        assert "diverges" not in a
        assert "property" not in a

    def test_o_espaco_em_branco_da_propriedade_nao_inventa_divergencia(self):
        a = _versao(_base(format_version=2, properties={"format-version": " 2 "}))
        assert a["diverges"] is False


class TestAsTresRecusas:
    def test_ausente_no_dump_nao_e_suprida_pela_propriedade(self):
        """Inferir da propriedade transformaria "o coletor nao me deu" em "a
        tabela e v2" -- e as duas frases mandam o operador a lugares
        diferentes."""
        a = _versao(_base(properties={"format-version": "2"}))
        assert a["resolved"] is False
        assert a["reason"] == "format_version_ausente_no_dump"
        assert "declared" not in a
        assert a["property"] == "2", "a propriedade viaja como evidencia, nao como resposta"
        assert "metadata.json" in a["unblocked_by"]

    def test_nao_numerico(self):
        a = _versao(_base(format_version="dois"))
        assert a["resolved"] is False
        assert a["reason"] == "format_version_nao_numerico"
        assert a["observed"] == "dois"

    def test_booleano_nao_conta_como_inteiro(self):
        """`True` e `int` em Python. Aceita-lo daria `declared: "True"`."""
        a = _versao(_base(format_version=True))
        assert a["resolved"] is False
        assert a["reason"] == "format_version_nao_numerico"

    def test_fora_da_spec(self):
        a = _versao(_base(format_version=9))
        assert a["resolved"] is False
        assert a["reason"] == "format_version_fora_da_spec"
        assert a["observed"] == "9"

    def test_toda_recusa_tem_a_medida_que_a_destrava(self):
        for payload in (
            _base(),
            _base(format_version="dois"),
            _base(format_version=9),
        ):
            a = _versao(payload)
            assert a["resolved"] is False
            assert a["unblocked_by"], f"recusa sem destrava em {a['reason']}"


class TestOFactSaiSempre:
    def test_inclusive_quando_o_dump_nao_traz_o_campo(self):
        """Ausencia do fact se leria como "ninguem perguntou"."""
        a = _versao(_base())
        assert a["reason"] == "format_version_ausente_no_dump"

    def test_o_kind_esta_no_namespace_declarado(self):
        from sparkforge.facts.iceberg_metadata import EMITTED_KINDS

        assert "iceberg.format_version" in EMITTED_KINDS

    def test_dump_malformado_nao_produz_o_fact_e_isso_e_certo(self):
        """Sem nome de tabela nao ha `subject`, e um fact sem subject nao ancora
        nada. A extracao para em `iceberg.unresolved`, que ja e a resposta."""
        facts = extract_iceberg_metadata({"format_version": 2}, "dump.json")
        assert [f.kind for f in facts] == ["iceberg.unresolved"]
