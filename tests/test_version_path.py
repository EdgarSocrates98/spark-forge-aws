import pytest

from sparkforge.facts import runtime_matrix
from sparkforge.migration import version_path


class TestCaminhoDeVersao:
    def test_expande_os_degraus_intermediarios(self):
        assert version_path.steps("4.0", "5.1") == [("4.0", "5.0"), ("5.0", "5.1")]

    def test_par_adjacente_tem_um_degrau_so(self):
        assert version_path.steps("5.0", "5.1") == [("5.0", "5.1")]

    def test_origem_igual_ao_alvo_nao_tem_degrau(self):
        assert version_path.steps("5.1", "5.1") == []

    def test_alvo_anterior_a_origem_e_erro_nomeado(self):
        with pytest.raises(ValueError, match="alvo anterior"):
            version_path.steps("5.1", "4.0")

    def test_versao_desconhecida_diz_qual_e_o_que_existe(self):
        with pytest.raises(ValueError) as erro:
            version_path.steps("4.0", "9.9")
        assert "9.9" in str(erro.value)
        assert "5.1" in str(erro.value)

    def test_cadeia_completa_bate_com_os_pares_adjacentes_da_matriz(self):
        """Pina o contrato de expansao cumulativa sem citar versao nenhuma.

        Se a YAML ganhar uma versao nova, este teste continua provando que
        `steps` produz exatamente os pares adjacentes de `known_versions()` --
        o teste hardcoded acima e que vai precisar de olhar de novo.
        """
        conhecidas = runtime_matrix.known_versions()
        esperado = [
            (conhecidas[i], conhecidas[i + 1]) for i in range(len(conhecidas) - 1)
        ]
        assert version_path.steps(conhecidas[0], conhecidas[-1]) == esperado
