"""`ReleaseDiff`: o que mudou, com o EIXO declarado e o resto recusado por nome.

O teste que carrega esta area e o contrafactual de plataforma: `emr-7.7.0` no
EC2 contra o MESMO rotulo no EKS. Ele prova duas coisas de uma vez -- que a
normalizacao da frente A nao apagou a divergencia que o sub-projeto 1 mediu, e
que o diff nao apresenta essa divergencia como se fosse mudanca de release.
"""
from __future__ import annotations

import pytest

from sparkforge.migration import release_descriptor as rd
from sparkforge.migration import release_diff as rdiff


def mudanca(diferenca: rdiff.ReleaseDiff, componente: str) -> rdiff.ComponentChange:
    for entrada in diferenca.changed:
        if entrada.component == componente:
            return entrada
    raise AssertionError(f"{componente} nao esta em changed: {diferenca.changed}")


class TestContrafactualDePlataforma:
    """`emr-7.7.0` EC2 x `emr-7.7.0` EKS. O achado do sub-projeto 1."""

    @pytest.fixture
    def diferenca(self) -> rdiff.ReleaseDiff:
        return rdiff.diff(
            rd.describe("emr_ec2", "emr-7.7.0"),
            rd.describe("emr_eks", "emr-7.7.0"),
        )

    def test_o_diff_nao_e_vazio(self, diferenca):
        assert diferenca.changed

    def test_o_eixo_e_plataforma_e_so_plataforma(self, diferenca):
        assert diferenca.axis == ("platform",)

    def test_a_divergencia_de_iceberg_aparece_com_os_dois_valores(self, diferenca):
        entrada = mudanca(diferenca, "iceberg")
        assert entrada.from_value == "1.7.1-amzn-0"
        assert entrada.to_value == "1.6.1-amzn-2"

    def test_o_sufixo_do_fork_do_spark_tambem_diverge(self, diferenca):
        entrada = mudanca(diferenca, "spark")
        assert (entrada.from_value, entrada.to_value) == ("3.5.3-amzn-1", "3.5.3-amzn-0")

    def test_hadoop_nao_vira_removed_porque_a_fonte_do_eks_nao_o_publica(self, diferenca):
        """Dizer "o EKS removeu o Hadoop" seria a mentira por omissao que o
        campo `unresolved` existe para nao contar."""
        assert "hadoop" not in diferenca.removed
        assert "hadoop" not in diferenca.added
        razao = diferenca.unresolved["component.hadoop"]
        assert "emr_eks" in razao

    def test_hudi_e_delta_nao_viram_added_porque_a_fonte_do_ec2_nao_os_publica(
        self, diferenca
    ):
        for componente in ("hudi", "delta"):
            assert componente not in diferenca.added
            assert f"component.{componente}" in diferenca.unresolved

    def test_o_dicionario_carrega_o_eixo(self, diferenca):
        assert diferenca.to_dict()["axis"] == ["platform"]


class TestEixoRelease:
    def test_dentro_da_mesma_plataforma_o_eixo_e_release(self):
        diferenca = rdiff.diff(
            rd.describe("emr_ec2", "emr-6.15.0"),
            rd.describe("emr_ec2", "emr-7.5.0"),
        )
        assert diferenca.axis == ("release",)
        assert diferenca.changed

    def test_componente_que_a_fonte_passa_a_publicar_entra_em_added(self):
        """`python` (o default do PySpark) e ausente na serie 6.x de EC2 e
        presente na 7.x -- a fonte passou a reafirma-lo por release."""
        diferenca = rdiff.diff(
            rd.describe("emr_ec2", "6.15.0"), rd.describe("emr_ec2", "7.0.0")
        )
        assert diferenca.added == ("python",)
        assert diferenca.removed == ()

    def test_componente_que_a_fonte_deixa_de_publicar_entra_em_removed(self):
        """A celula `iceberg` de `6.4.0` e vazia na pagina oficial."""
        diferenca = rdiff.diff(
            rd.describe("emr_ec2", "6.5.0"), rd.describe("emr_ec2", "6.4.0")
        )
        assert diferenca.removed == ("iceberg",)
        assert diferenca.added == ()


class TestDoisEixos:
    """Plataformas diferentes E releases diferentes: emitir declarando os dois,
    e recusar a ATRIBUICAO -- que e a parte que nao tem base."""

    @pytest.fixture
    def diferenca(self) -> rdiff.ReleaseDiff:
        return rdiff.diff(
            rd.describe("emr_ec2", "emr-6.15.0"),
            rd.describe("emr_eks", "emr-7.5.0"),
        )

    def test_os_dois_eixos_saem_declarados_e_em_ordem_fixa(self, diferenca):
        assert diferenca.axis == ("platform", "release")

    def test_a_atribuicao_sai_em_unresolved_com_a_medida_que_a_destravaria(
        self, diferenca
    ):
        razao = diferenca.unresolved["attribution"]
        assert "platform" in razao
        assert "release" in razao

    def test_um_eixo_so_nao_recusa_atribuicao(self):
        um_eixo = rdiff.diff(
            rd.describe("emr_ec2", "6.15.0"), rd.describe("emr_ec2", "7.5.0")
        )
        assert "attribution" not in um_eixo.unresolved


class TestIdentidade:
    def test_uma_release_contra_ela_mesma_nao_muda_nada(self):
        descritor = rd.describe("emr_eks", "emr-7.7.0")
        diferenca = rdiff.diff(descritor, descritor)
        assert diferenca.changed == ()
        assert diferenca.added == ()
        assert diferenca.removed == ()
        assert set(diferenca.unchanged) == set(descritor.components)

    def test_sem_eixo_variando_o_diff_declara_eixo_vazio(self):
        descritor = rd.describe("glue", "5.0")
        assert rdiff.diff(descritor, descritor).axis == ()

    def test_identidade_em_todas_as_95_releases(self):
        for plataforma in rd.PLATFORMS:
            for release in rd.known_releases(plataforma):
                descritor = rd.describe(plataforma, release)
                diferenca = rdiff.diff(descritor, descritor)
                onde = f"{plataforma}/{release}"
                assert diferenca.changed == (), onde
                assert set(diferenca.unchanged) == set(descritor.components), onde


class TestAsSeteDimensoesDo82:
    """Duas tem lastro na matriz; cinco nao, e cada uma sai NOMEADA com a
    medida que a destravaria. Lista vazia seria lida como "nao mudou nada"."""

    @pytest.fixture
    def diferenca(self) -> rdiff.ReleaseDiff:
        return rdiff.diff(
            rd.describe("emr_ec2", "6.15.0"), rd.describe("emr_ec2", "7.5.0")
        )

    def test_as_cinco_sem_lastro_saem_em_unresolved(self, diferenca):
        for dimensao in rdiff.DIMENSOES_SEM_LASTRO:
            assert dimensao in diferenca.unresolved, dimensao
            razao = diferenca.unresolved[dimensao]
            assert len(razao) > 40, f"{dimensao}: razao curta demais para destravar"

    def test_added_e_removed_nao_saem_em_unresolved_porque_tem_lastro(self, diferenca):
        assert "added" not in diferenca.unresolved
        assert "removed" not in diferenca.unresolved

    def test_a_razao_de_cada_uma_nomeia_a_medida_e_nao_so_a_falta(self, diferenca):
        for dimensao in rdiff.DIMENSOES_SEM_LASTRO:
            assert "knowledge/" in diferenca.unresolved[dimensao], dimensao

    def test_as_sete_dimensoes_estao_todas_enderecadas(self, diferenca):
        enderecadas = set(rdiff.DIMENSOES_SEM_LASTRO) | set(rdiff.DIMENSOES_COM_LASTRO)
        assert enderecadas == set(rdiff.DIMENSOES_DO_82)


class TestDeterminismo:
    def test_mesma_entrada_mesma_saida(self):
        primeiro = rdiff.diff(
            rd.describe("emr_ec2", "emr-7.7.0"), rd.describe("emr_eks", "emr-7.7.0")
        ).to_dict()
        segundo = rdiff.diff(
            rd.describe("emr_ec2", "7.7.0"), rd.describe("emr_eks", "7.7.0")
        ).to_dict()
        assert primeiro == segundo

    def test_toda_lista_sai_ordenada(self):
        diferenca = rdiff.diff(
            rd.describe("emr_ec2", "emr-7.7.0"), rd.describe("emr_eks", "emr-7.7.0")
        )
        assert list(diferenca.added) == sorted(diferenca.added)
        assert list(diferenca.removed) == sorted(diferenca.removed)
        assert list(diferenca.unchanged) == sorted(diferenca.unchanged)
        nomes = [entrada.component for entrada in diferenca.changed]
        assert nomes == sorted(nomes)

    def test_o_universo_de_componente_e_particionado_sem_sobra(self):
        """Todo componente do universo cai em exatamente um balde. Componente
        que sumisse entre os baldes seria o vazio em silencio de novo."""
        for esquerda, direita in (
            (("emr_ec2", "7.7.0"), ("emr_eks", "7.7.0")),
            (("glue", "3.0"), ("glue", "6.0")),
            (("emr_serverless", "7.7.0"), ("emr_ec2", "7.7.0")),
        ):
            diferenca = rdiff.diff(rd.describe(*esquerda), rd.describe(*direita))
            baldes = (
                {entrada.component for entrada in diferenca.changed}
                | set(diferenca.added)
                | set(diferenca.removed)
                | set(diferenca.unchanged)
                | {
                    chave.removeprefix("component.")
                    for chave in diferenca.unresolved
                    if chave.startswith("component.")
                }
            )
            assert baldes == set(rd.COMPONENT_UNIVERSE), (esquerda, direita)


class TestConjuntoNoDiff:
    def test_python_installed_muda_como_conjunto_e_nao_como_string(self):
        diferenca = rdiff.diff(
            rd.describe("emr_ec2", "6.4.0"), rd.describe("emr_ec2", "7.13.0")
        )
        entrada = mudanca(diferenca, "python_installed")
        assert entrada.from_value == ("2.7", "3.7")
        assert entrada.to_value == ("3.9", "3.11")
        saida = diferenca.to_dict()
        registro = next(
            r for r in saida["changed"] if r["component"] == "python_installed"
        )
        assert registro["from"] == ["2.7", "3.7"]
        assert registro["to"] == ["3.9", "3.11"]
