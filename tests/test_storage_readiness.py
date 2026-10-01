"""O cruzamento por release, e o contrafactual que prova que ele nao e cosmetico.

`emr` era UMA engine na matriz de feature e UM servico no `ConsumerGraph`. As
tres plataformas publicam Iceberg DIFERENTE -- 6 de 26 releases comparaveis
divergem entre EC2 e EKS. Enquanto a linha era uma so, essa diferenca era
INEXPRIMIVEL: nao havia duas coisas para comparar.

O teste que decide esta arquivo e `TestContrafactualDaGranularidade`. Ele nao
pergunta "as tres engines existem?" -- existir e cosmetico. Ele pergunta "elas
respondem DIFERENTE para a mesma release?", e a resposta so pode ser sim se a
versao de biblioteca de cada plataforma tiver sido lida da matriz DAQUELA
plataforma.
"""
import pytest

from sparkforge.facts import runtime_matrix
from sparkforge.storage import feature_support, readiness


class TestContrafactualDaGranularidade:
    """`emr-7.7.0` responde diferente para `emr_ec2` e `emr_eks`.

    A feature e `nanosecond_timestamp`, com `min_library_version` = 1.7.0 --
    um valor que cai EXATAMENTE entre as duas plataformas nesta release. Nao e
    coincidencia escolhida a posteriori: 1.7.0 e a primeira release cujas notas
    curadas do Iceberg nomeiam `timestamp_ns`, e emr-7.7.0 e a release que o
    sub-projeto de EMR on EKS mediu divergindo.
    """

    FEATURE = "nanosecond_timestamp"
    RELEASE = "emr-7.7.0"

    def test_as_duas_plataformas_publicam_iceberg_diferente(self):
        """O fato medido, lido das DUAS matrizes de runtime -- nunca de uma so.
        Se um dia as duas convergirem, este teste falha ANTES dos outros e
        explica por que eles pararam de provar o que provam."""
        ec2 = runtime_matrix.load_emr()["7.7.0"]["iceberg"]
        eks = runtime_matrix.load_emr_eks()["7.7.0"]["iceberg"]
        assert ec2 == "1.7.1-amzn-0"
        assert eks == "1.6.1-amzn-2"
        assert ec2 != eks

    def test_a_prontidao_diverge_entre_ec2_e_eks(self):
        ec2 = readiness.readiness(self.FEATURE, "emr_ec2", self.RELEASE)
        eks = readiness.readiness(self.FEATURE, "emr_eks", self.RELEASE)

        assert ec2["status"] == "UNKNOWN"
        assert ec2["reason"] == "biblioteca_atende_o_minimo"
        assert ec2["library_version"] == "1.7.1-amzn-0"

        assert eks["status"] == "UNSUPPORTED"
        assert eks["reason"] == "biblioteca_anterior_ao_minimo"
        assert eks["library_version"] == "1.6.1-amzn-2"

        assert ec2["status"] != eks["status"], (
            "se as duas responderem igual, a separacao de `emr` em tres engines "
            "foi cosmetica -- e uma resposta dada para 'EMR' volta a estar "
            "errada para pelo menos uma das tres"
        )

    def test_a_terceira_plataforma_tambem_responde_por_si(self):
        """EMR Serverless publica `spark` em emr-7.7.0 e NAO publica `iceberg`.
        A resposta dele nao e a do EC2 nem a do EKS: e a recusa nomeada."""
        serverless = readiness.readiness(self.FEATURE, "emr_serverless", self.RELEASE)
        assert serverless["status"] == "UNKNOWN"
        assert serverless["reason"] == "iceberg_ausente_na_release"
        assert serverless["library_version"] == ""

    def test_diverges_ve_a_divergencia(self):
        assert readiness.diverges(self.FEATURE, self.RELEASE)

    def test_a_divergencia_nao_e_generalizada(self):
        """O contrafactual so vale se ele distinguir. `deletion_vectors` tem
        minimo 1.8.0, e AS DUAS bibliotecas de emr-7.7.0 estao abaixo dele --
        entao as duas respondem `UNSUPPORTED`, pela mesma razao. Um mecanismo
        que fizesse tudo divergir nao estaria medindo nada."""
        ec2 = readiness.readiness("deletion_vectors", "emr_ec2", self.RELEASE)
        eks = readiness.readiness("deletion_vectors", "emr_eks", self.RELEASE)
        assert ec2["status"] == eks["status"] == "UNSUPPORTED"
        assert ec2["reason"] == eks["reason"] == "biblioteca_anterior_ao_minimo"


class TestRecusaNomeada:
    def test_iceberg_ausente_na_release_nao_vira_unsupported(self):
        """`emr-6.5.0` no EKS: a plataforma publica a release e NAO publica
        Iceberg nela. Nao saber que versao roda e diferente de saber que nao
        suporta -- e a diferenca decide uma migracao."""
        resultado = readiness.readiness("variant", "emr_eks", "emr-6.5.0")
        assert resultado["status"] == "UNKNOWN"
        assert resultado["reason"] == "iceberg_ausente_na_release"

    def test_a_mesma_release_no_ec2_tem_versao_e_por_isso_responde(self):
        """E o par que mostra que a recusa acima e da PLATAFORMA e nao da
        release: no EC2, `emr-6.5.0` publica Iceberg 0.12.0, e ai a resposta e
        um `UNSUPPORTED` com fonte -- 0.12.0 e anterior a qualquer minimo."""
        resultado = readiness.readiness("variant", "emr_ec2", "emr-6.5.0")
        assert resultado["status"] == "UNSUPPORTED"
        assert resultado["reason"] == "biblioteca_anterior_ao_minimo"
        assert resultado["library_version"] == "0.12.0"

    def test_variante_de_imagem_nao_responde_pela_familia(self):
        """O limite da granularidade, declarado e enforcado. A fonte diz que
        `emr-7.7.0-java8-latest` NAO tem Iceberg enquanto `emr-7.7.0` tem;
        responder pela familia erraria essa celula."""
        resultado = readiness.readiness(
            "nanosecond_timestamp", "emr_eks", "emr-7.7.0-java8-latest"
        )
        assert resultado["reason"] == "variante_de_imagem_fora_da_matriz"
        assert resultado["status"] == "UNKNOWN"
        assert readiness._family("7.7.0-java8-latest") == "7.7.0"

    def test_release_desconhecida_e_diferente_de_variante(self):
        resultado = readiness.readiness("variant", "emr_eks", "emr-99.0.0")
        assert resultado["reason"] == "release_desconhecida"

    def test_engine_sem_matriz_de_runtime_recusa_por_nome(self):
        """Athena, Trino, Flink e companhia nao tem versao de biblioteca
        publicada por release num formato que este repositorio leia. A recusa
        e nomeada em vez de silenciosa."""
        resultado = readiness.readiness("variant", "athena", "engine-v3")
        assert resultado["reason"] == "engine_sem_matriz_de_runtime"

    def test_feature_sem_minimo_recusa_por_nome(self):
        resultado = readiness.readiness("variant_shredding", "emr_ec2", "emr-7.13.0")
        assert resultado["reason"] == "min_library_version_ausente"
        assert resultado["status"] == "UNKNOWN"


class TestNuncaPromove:
    def test_atender_o_minimo_nao_vira_supported(self):
        """A inferencia proibida por uma porta nova: a versao da biblioteca no
        lugar da spec. `emr-7.13.0` traz Iceberg 1.10.0-amzn-1, que atende o
        minimo de `row_lineage` (1.8.0) com folga -- e a resposta continua
        `UNKNOWN`, porque nenhuma pagina da AWS nomeia row lineage para EMR."""
        resultado = readiness.readiness("row_lineage", "emr_ec2", "emr-7.13.0")
        assert resultado["library_version"] == "1.10.0-amzn-1"
        assert resultado["reason"] == "biblioteca_atende_o_minimo"
        assert resultado["status"] == "UNKNOWN"
        assert resultado["cell_status"] == "UNKNOWN"

    def test_a_celula_da_engine_vence_quando_ela_existe(self):
        """Glue tem celula afirmativa por nome. Com release declarada, o
        cruzamento nao a apaga: o minimo so decide quando a biblioteca esta
        ABAIXO dele."""
        resultado = readiness.readiness("deletion_vectors", "glue", "5.1")
        assert resultado["reason"] == "biblioteca_atende_o_minimo"
        assert resultado["status"] == "SUPPORTED"


class TestVocabularioFechado:
    def test_toda_razao_produzida_esta_declarada(self):
        casos = [
            ("variant", "athena", "x"),
            ("variant", "emr_eks", "emr-99.0.0"),
            ("variant", "emr_eks", "emr-7.7.0-java8-latest"),
            ("variant", "emr_eks", "emr-6.5.0"),
            ("variant_shredding", "emr_ec2", "emr-7.13.0"),
            ("variant", "emr_ec2", "emr-6.5.0"),
            ("row_lineage", "emr_ec2", "emr-7.13.0"),
        ]
        produzidas = {readiness.readiness(*c)["reason"] for c in casos}
        assert produzidas == readiness.REASONS, (
            "toda razao do vocabulario precisa de um caso que a produza, e todo "
            "caso precisa cair numa razao declarada"
        )

    def test_todo_status_produzido_esta_no_vocabulario_da_matriz(self):
        for engine in readiness.PLATFORM_LOADERS:
            for feature in feature_support.load():
                resultado = readiness.readiness(feature, engine, "emr-7.7.0")
                assert resultado["status"] in feature_support.SUPPORT_STATUS

    def test_as_tres_plataformas_de_emr_estao_declaradas_juntas(self):
        assert readiness.EMR_PLATFORMS == ("emr_ec2", "emr_serverless", "emr_eks")
        for plataforma in readiness.EMR_PLATFORMS:
            assert plataforma in readiness.PLATFORM_LOADERS
            assert plataforma in feature_support.engines()


class TestNuncaExecuta:
    def test_o_modulo_nao_tem_superficie_de_escrita(self):
        """Mesma garantia estrutural de `sparkforge/storage/upgrade.py`, medida
        pelos IMPORTS e nao por substring na fonte: prosa que menciona
        "subprocesso" numa explicacao nao e uma chamada."""
        import ast
        import inspect

        arvore = ast.parse(inspect.getsource(readiness))
        importados: set[str] = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados.update(a.name.split(".")[0] for a in no.names)
            elif isinstance(no, ast.ImportFrom) and no.module:
                importados.add(no.module.split(".")[0])
        for proibido in ("boto3", "botocore", "subprocess", "os", "pyspark"):
            assert proibido not in importados, proibido


class TestComparacaoDeVersao:
    @pytest.mark.parametrize(
        "cru,esperado",
        [
            ("1.7.1-amzn-0", (1, 7, 1)),
            ("1.6.1-amzn-2", (1, 6, 1)),
            ("0.12.0", (0, 12, 0)),
            ("1.10.0-amzn-1", (1, 10, 0)),
        ],
    )
    def test_o_sufixo_da_aws_nao_ordena(self, cru, esperado):
        assert readiness._comparavel(cru) == esperado

    def test_dez_e_maior_que_nove(self):
        """Comparacao por tupla de inteiros, nunca por string: `"1.10.0"` e
        MENOR que `"1.9.0"` em ordem lexicografica, e essa e a forma classica
        de o cruzamento errar em silencio."""
        assert readiness._comparavel("1.10.0") > readiness._comparavel("1.9.0")
