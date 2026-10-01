"""`ReleaseDescriptor`: o que uma release E, com a recusa NOMEADA.

A invariante central desta area, e a razao de ela existir: as quatro
plataformas publicam conjuntos DIFERENTES de componente, e um descritor que
apagasse essa diferenca mentiria por omissao. Por isso todo teste aqui roda
sobre as 95 releases das quatro plataformas, nunca sobre amostra.
"""
from __future__ import annotations

import pytest

from sparkforge.migration import release_descriptor as rd

# Contagem MEDIDA das quatro matrizes em 2026-08-31. Nao e alvo: e o numero
# que `knowledge/<plataforma>/runtime-matrix.yaml` carrega hoje, e ele muda
# quando a AWS publica release nova. Se este teste reprovar depois de uma
# atualizacao de knowledge, o numero e que muda -- nunca a invariante.
RELEASES_POR_PLATAFORMA = {
    "glue": 5,
    "emr_ec2": 30,
    "emr_serverless": 26,
    "emr_eks": 34,
}


def todos_os_descritores() -> tuple[rd.ReleaseDescriptor, ...]:
    return rd.describe_all()


class TestCoberturaDasQuatroMatrizes:
    def test_sao_noventa_e_cinco_releases_nas_quatro_plataformas(self):
        medido = {p: len(rd.known_releases(p)) for p in rd.PLATFORMS}
        assert medido == RELEASES_POR_PLATAFORMA
        assert sum(medido.values()) == 95

    def test_todo_componente_ou_resolve_com_fonte_ou_esta_em_unresolved(self):
        """Nunca vazio em silencio -- a §20 do CLAUDE.md, sobre 95 releases."""
        for descritor in todos_os_descritores():
            onde = f"{descritor.platform}/{descritor.release}"
            resolvidos = set(descritor.components)
            recusados = set(descritor.unresolved)
            assert resolvidos.isdisjoint(recusados), onde
            assert resolvidos | recusados == set(rd.COMPONENT_UNIVERSE), onde
            for nome, componente in descritor.components.items():
                assert componente.version, f"{onde}.{nome}: versao vazia"
                assert componente.sources, f"{onde}.{nome}: valor sem fonte"
            for nome in recusados:
                detalhe = descritor.refused[nome]
                assert detalhe.kind in rd.UNRESOLVED_KINDS, f"{onde}.{nome}"
                assert detalhe.reason.strip(), f"{onde}.{nome}: recusa sem razao"

    def test_nenhum_descritor_fica_sem_procedencia_de_release(self):
        for descritor in todos_os_descritores():
            onde = f"{descritor.platform}/{descritor.release}"
            assert descritor.sources, onde
            assert descritor.retrieved, onde


class TestOQueCadaFontePublica:
    def test_emr_on_eks_nomeia_hadoop_e_python_como_nao_publicados(self):
        """0 de 34 paginas para hadoop, 2 de 34 (em prosa) para python."""
        descritor = rd.describe("emr_eks", "emr-7.7.0")
        for componente in ("hadoop", "python", "python_installed", "scala", "java"):
            assert componente in descritor.unresolved
            assert descritor.refused[componente].kind == rd.PLATFORM_DOES_NOT_PUBLISH
        assert set(descritor.components) == {"spark", "iceberg", "hudi", "delta"}

    def test_emr_serverless_publica_iceberg_so_nas_duas_spark_8(self):
        com_iceberg = rd.describe("emr_serverless", "spark-8.0.0")
        assert "iceberg" in com_iceberg.components
        sem_iceberg = rd.describe("emr_serverless", "7.7.0")
        assert "iceberg" in sem_iceberg.unresolved
        assert sem_iceberg.refused["iceberg"].kind == rd.RELEASE_CELL_ABSENT

    def test_glue_5_1_nomeia_java_como_celula_ausente_nao_como_eixo_inexistente(self):
        """A fonte do Glue PUBLICA java (4 de 5 releases); a celula de 5.1 e que
        nao foi lida. As duas recusas sao diferentes e tem nomes diferentes."""
        descritor = rd.describe("glue", "5.1")
        assert "java" in descritor.unresolved
        assert descritor.refused["java"].kind == rd.RELEASE_CELL_ABSENT
        assert "hadoop" in descritor.unresolved
        assert descritor.refused["hadoop"].kind == rd.PLATFORM_DOES_NOT_PUBLISH

    def test_iceberg_ausente_em_emr_6_4_0_e_celula_vazia_da_pagina(self):
        descritor = rd.describe("emr_ec2", "6.4.0")
        assert "iceberg" in descritor.unresolved
        assert descritor.refused["iceberg"].kind == rd.RELEASE_CELL_ABSENT

    def test_python_da_serie_6_x_de_ec2_nao_e_reafirmado_por_release(self):
        assert "python" in rd.describe("emr_ec2", "6.15.0").unresolved
        assert "python" in rd.describe("emr_ec2", "7.0.0").components


class TestConjuntoNaoEValor:
    def test_python_installed_de_ec2_permanece_conjunto(self):
        """A pagina declara interpretadores INSTALADOS. Achatar num valor so
        escolheria por conta propria qual deles o PySpark usa."""
        componente = rd.describe("emr_ec2", "emr-7.7.0").components["python_installed"]
        assert componente.version == ("3.9", "3.11")
        assert componente.is_set is True
        assert rd.describe("emr_ec2", "emr-7.7.0").components["python"].is_set is False

    def test_conjunto_sobrevive_ao_to_dict_como_lista(self):
        saida = rd.describe("emr_ec2", "emr-7.7.0").to_dict()
        assert saida["components"]["python_installed"]["version"] == ["3.9", "3.11"]


class TestNuncaHerdarDeOutraPlataforma:
    def test_o_mesmo_rotulo_publica_iceberg_diferente_no_ec2_e_no_eks(self):
        """O achado do sub-projeto 1. Se a normalizacao da frente A tivesse
        apagado isso, este teste cai."""
        assert rd.describe("emr_ec2", "emr-7.7.0").components["iceberg"].version == (
            "1.7.1-amzn-0"
        )
        assert rd.describe("emr_eks", "emr-7.7.0").components["iceberg"].version == (
            "1.6.1-amzn-2"
        )

    def test_o_spark_tambem_diverge_no_sufixo_do_fork(self):
        assert rd.describe("emr_ec2", "emr-7.7.0").components["spark"].version == (
            "3.5.3-amzn-1"
        )
        assert rd.describe("emr_eks", "emr-7.7.0").components["spark"].version == (
            "3.5.3-amzn-0"
        )


class TestErroNomeado:
    def test_release_desconhecida_traz_a_lista_do_que_a_plataforma_conhece(self):
        with pytest.raises(rd.UnknownRelease) as excecao:
            rd.describe("emr_eks", "emr-9.9.9")
        mensagem = str(excecao.value)
        assert "9.9.9" in mensagem
        assert "emr_eks" in mensagem
        assert "7.7.0" in mensagem

    def test_release_de_outra_plataforma_nao_vira_keyerror(self):
        """`6.3.0` existe no EKS e nao no EC2 -- a fronteira das duas matrizes."""
        assert "6.3.0" in rd.known_releases("emr_eks")
        with pytest.raises(rd.UnknownRelease):
            rd.describe("emr_ec2", "6.3.0")

    def test_plataforma_desconhecida_traz_a_lista_das_quatro(self):
        with pytest.raises(rd.UnknownPlatform) as excecao:
            rd.describe("databricks", "1.0")
        assert "emr_serverless" in str(excecao.value)


class TestNormalizacaoDeRotulo:
    def test_prefixo_emr_e_aceito_e_a_chave_e_a_da_matriz(self):
        com_prefixo = rd.describe("emr_ec2", "emr-7.7.0")
        sem_prefixo = rd.describe("emr_ec2", "7.7.0")
        assert com_prefixo == sem_prefixo
        assert com_prefixo.release == "7.7.0"

    def test_rotulo_de_glue_nao_leva_prefixo(self):
        assert rd.describe("glue", "5.0").release == "5.0"


class TestDeterminismo:
    def test_duas_chamadas_produzem_o_mesmo_dicionario(self):
        assert rd.describe("emr_eks", "7.7.0").to_dict() == (
            rd.describe("emr_eks", "emr-7.7.0").to_dict()
        )

    def test_listas_saem_ordenadas(self):
        for descritor in todos_os_descritores():
            assert list(descritor.unresolved) == sorted(descritor.unresolved)
            assert list(descritor.components) == sorted(descritor.components)


class TestChavesReservadasNaoSaoComponente:
    def test_sources_e_retrieved_nunca_aparecem_como_componente(self):
        """`runtime_matrix.load()` (Glue) devolve `sources` e `retrieved` DENTRO
        da linha resolvida -- as reservadas so sao filtradas nas tres matrizes
        fechadas. Descritor que as tratasse como componente inventaria dois
        eixos em todas as cinco releases de Glue."""
        for release in rd.known_releases("glue"):
            componentes = set(rd.describe("glue", release).components)
            assert "sources" not in componentes
            assert "retrieved" not in componentes


class TestVocabularioBateComOsDados:
    def test_o_publicado_por_plataforma_cobre_o_que_o_yaml_traz(self):
        from sparkforge.facts import runtime_matrix as rm

        medido = {
            "glue": rm.load(),
            "emr_ec2": rm.load_emr(),
            "emr_serverless": rm.load_emr_serverless(),
            "emr_eks": rm.load_emr_eks(),
        }
        for plataforma, matriz in medido.items():
            presentes = {
                chave
                for linha in matriz.values()
                for chave in linha
                if chave not in {"sources", "retrieved"}
            }
            assert presentes == rd.published_components(plataforma), plataforma

    def test_o_universo_e_a_uniao_das_quatro_e_nada_alem(self):
        uniao: set[str] = set()
        for plataforma in rd.PLATFORMS:
            uniao |= rd.published_components(plataforma)
        assert set(rd.COMPONENT_UNIVERSE) == uniao
