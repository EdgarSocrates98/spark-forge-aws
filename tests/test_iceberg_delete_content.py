"""O censo por `content` em `.delete_files`, e as duas recusas dele.

Antes de 2026-09-02 o extrator contava `delete_file_count` e mais nada: position
delete e equality delete entravam no mesmo numero, e um dump sem a coluna
`content` era indistinguivel de um dump em que todos os deletes fossem do mesmo
tipo.

A distincao importa porque as duas custam coisas diferentes na leitura, e porque
em v3 o DELETION VECTOR chega com `content = 1` -- ele SUBSTITUI o position
delete, e nao se soma a ele.
"""

from __future__ import annotations

import pytest

from sparkforge.facts.iceberg_metadata import (
    _CONTENT_DE_DELETE,
    extract_iceberg_metadata,
)


def _resumo(delete_files: list[dict]) -> dict:
    facts = extract_iceberg_metadata(
        {"table": "a.b", "format_version": 2, "delete_files": delete_files}, "dump.json"
    )
    return dict(
        next(f for f in facts if f.kind == "iceberg.delete_files_summary").measures
    )


class TestOCenso:
    def test_separa_position_de_equality(self):
        m = _resumo([{"content": 1}, {"content": 1}, {"content": 2}])
        assert m["position_delete_count"] == 2
        assert m["equality_delete_count"] == 1
        assert m["delete_file_count"] == 3

    def test_a_soma_do_censo_nunca_excede_o_total(self):
        m = _resumo([{"content": 1}, {"content": 2}, {}, {"content": 9}])
        censo = sum(
            v for k, v in m.items() if k.endswith(("_delete_count", "_unresolved", "_unknown"))
            and k != "delete_file_count"
        )
        assert censo == m["delete_file_count"]

    def test_tabela_sem_delete_nao_inventa_zero_por_tipo(self):
        """Chave ausente diz "nao ha"; `position_delete_count: 0` diria a mesma
        coisa, mas so depois de alguem ter contado -- e aqui nao ha o que
        contar."""
        m = _resumo([])
        assert m["delete_file_count"] == 0
        assert "position_delete_count" not in m
        assert "content_unresolved" not in m


class TestAsDuasRecusas:
    def test_coletor_sem_a_coluna_sai_como_unresolved_e_nunca_zero(self):
        """Zero se leria como "nao ha delete de posicao", quando a verdade e
        "ninguem perguntou". A coluna `content` e OPCIONAL no dump."""
        m = _resumo([{"file_size_in_bytes": 10}, {"file_size_in_bytes": 20}])
        assert m["content_unresolved"] == 2
        assert "position_delete_count" not in m
        assert "equality_delete_count" not in m

    def test_codigo_fora_da_spec_e_nomeado_e_nao_empurrado_para_position(self):
        """Uma spec futura pode acrescentar codigo. Empurra-lo para o tipo mais
        provavel seria adivinhar."""
        m = _resumo([{"content": 7}])
        assert m["content_unknown"] == 1
        assert "position_delete_count" not in m

    def test_content_booleano_nao_conta_como_inteiro(self):
        """`True` e `int` em Python, e `_CONTENT_DE_DELETE[True]` daria
        'position' por acidente de tipagem."""
        m = _resumo([{"content": True}])
        assert m["content_unresolved"] == 1
        assert "position_delete_count" not in m


class TestOsCodigosDaSpec:
    def test_sao_os_que_a_specification_publica(self):
        assert _CONTENT_DE_DELETE == {1: "position", 2: "equality"}

    def test_content_zero_NAO_esta_no_mapa(self):
        """`0` e DATA FILE. Um `0` em `.delete_files` seria o coletor tendo
        misturado as duas tabelas, e chama-lo de delete esconderia esse erro."""
        assert 0 not in _CONTENT_DE_DELETE
        m = _resumo([{"content": 0}])
        assert m["content_unknown"] == 1

    @pytest.mark.parametrize("codigo", [1, 2])
    def test_cada_codigo_produz_sua_chave(self, codigo):
        m = _resumo([{"content": codigo}])
        assert f"{_CONTENT_DE_DELETE[codigo]}_delete_count" in m


def test_o_deletion_vector_de_v3_conta_como_position_e_a_razao_esta_escrita():
    """Em v3 o DV chega com `content = 1` -- ele SUBSTITUI o position delete.

    Contar os dois juntos e o que a spec sustenta. Separa-los exigiria ler
    `content_offset` / `content_size_in_bytes` do Puffin, que o dump nao traz --
    e e a mesma lacuna de coletor que `docs/harness/ICEBERG-GAP.md` registra
    para a camada `Puffin`.
    """
    m = _resumo([{"content": 1}])
    assert m["position_delete_count"] == 1
    assert "deletion_vector_count" not in m, (
        "separar DV de position delete exige o Puffin, que o coletor nao traz"
    )
