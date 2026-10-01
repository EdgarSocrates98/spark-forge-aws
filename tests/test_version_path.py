import pytest

from sparkforge.facts import runtime_matrix
from sparkforge.migration import release_descriptor, version_path


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


class TestAsQuatroPlataformas:
    """D-1 da spec de EMR: a ordem vem da MATRIZ, nunca de lista em codigo."""

    def test_a_ordem_de_cada_plataforma_e_a_da_matriz_dela(self):
        """Ordenar as releases ORDENAVEIS da matriz e reordenar a lista que
        `known_releases` devolve -- nada e acrescentado nem retirado alem dos
        rotulos que nao sao versao. Se alguem escrever uma lista nova em codigo,
        este teste a pega."""
        for plataforma in version_path.platforms():
            conhecidas = set(release_descriptor.known_releases(plataforma))
            ordenadas = version_path.ordered_releases(plataforma)
            fora = set(version_path.out_of_pattern(plataforma))
            assert set(ordenadas) | fora == conhecidas
            assert set(ordenadas) & fora == set()

    def test_a_ordem_e_crescente_por_segmento_numerico(self):
        for plataforma in version_path.platforms():
            ordenadas = version_path.ordered_releases(plataforma)
            chaves = [tuple(int(p) for p in r.split(".")) for r in ordenadas]
            assert chaves == sorted(chaves)

    def test_caminho_de_emr_entre_series_segue_a_matriz(self):
        """O caso que a §5 da spec cobra: `6.15.0 -> 7.5.0` atravessa as duas
        series vivas do EMR, e isso e legitimo. Os degraus precisam ser os
        pares ADJACENTES da matriz de EC2, sem inventar degrau nem pular."""
        degraus = version_path.steps("6.15.0", "7.5.0", platform="emr_ec2")
        ordenadas = version_path.ordered_releases("emr_ec2")
        inicio, fim = ordenadas.index("6.15.0"), ordenadas.index("7.5.0")
        assert degraus == [
            (ordenadas[i], ordenadas[i + 1]) for i in range(inicio, fim)
        ]
        assert degraus[0][0] == "6.15.0"
        assert degraus[-1][1] == "7.5.0"
        # A troca de serie acontece DENTRO do caminho, e nao no fim: se ela nao
        # aparecer, o caminho nao atravessou as duas series e o teste nao mede
        # o que diz medir.
        assert any(a.startswith("6.") and b.startswith("7.") for a, b in degraus)

    def test_rotulo_fora_do_padrao_e_recusado_pelo_nome(self):
        """`spark-8.0.0` e `spark-8.0-preview` nao sao versao e nao tem posicao.
        A recusa precisa NOMEAR o rotulo -- ordenar alfabeticamente colocaria a
        previa antes da release por acidente de escrita."""
        for plataforma in version_path.platforms():
            for rotulo in version_path.out_of_pattern(plataforma):
                alguma = version_path.ordered_releases(plataforma)[0]
                with pytest.raises(ValueError) as erro:
                    version_path.steps(alguma, rotulo, platform=plataforma)
                assert rotulo in str(erro.value)
                assert "fora do padrao de versao" in str(erro.value)

    def test_rotulo_fora_do_padrao_tambem_e_recusado_como_origem(self):
        with pytest.raises(ValueError, match="fora do padrao de versao"):
            version_path.steps("spark-8.0.0", "7.13.0", platform="emr_eks")

    def test_as_duas_grafias_da_fonte_produzem_o_mesmo_caminho(self):
        """A pagina do EMR escreve `emr-7.7.0` no titulo e `7.7.0` na tabela.
        As duas entram; a chave da matriz e a unica que sai."""
        com_prefixo = version_path.steps("emr-7.0.0", "emr-7.2.0", platform="emr_ec2")
        sem_prefixo = version_path.steps("7.0.0", "7.2.0", platform="emr_ec2")
        assert com_prefixo == sem_prefixo
        conhecidas = set(release_descriptor.known_releases("emr_ec2"))
        for origem, alvo in com_prefixo:
            assert origem in conhecidas and alvo in conhecidas

    def test_plataforma_desconhecida_e_erro_nomeado_com_as_quatro(self):
        with pytest.raises(ValueError) as erro:
            version_path.steps("7.0.0", "7.1.0", platform="emr")
        for plataforma in version_path.platforms():
            assert plataforma in str(erro.value)

    def test_release_de_uma_plataforma_nao_vale_na_outra(self):
        """As fronteiras das quatro matrizes NAO coincidem: `6.3.0` existe no
        EMR on EKS (que desce ate `5.32.0`) e nao no EC2 (que comeca em
        `6.4.0`). O erro precisa dizer de qual matriz se trata."""
        assert "6.3.0" in version_path.ordered_releases("emr_eks")
        assert "6.3.0" not in version_path.ordered_releases("emr_ec2")
        with pytest.raises(ValueError, match="fora da matriz de emr_ec2"):
            version_path.steps("6.3.0", "7.0.0", platform="emr_ec2")

    def test_o_default_continua_sendo_glue(self):
        assert version_path.DEFAULT_PLATFORM == "glue"
        assert version_path.steps("4.0", "5.1") == version_path.steps(
            "4.0", "5.1", platform="glue"
        )
