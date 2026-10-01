"""O cruzamento que faltava: inventario de consumidores CONTRA a matriz.

`env.consumer` existia. `knowledge/storage/iceberg-feature-support.yaml`
existia. Nada cruzava os dois, e por isso nada impedia recomendar format v3
para quem tem Athena consumindo.
"""
import pytest

from sparkforge.storage import upgrade


class TestVeredito:
    def test_engine_com_celula_unsupported_bloqueia(self):
        # A matriz declara `variant` UNSUPPORTED no Athena, com fonte.
        resultado = upgrade.assess_upgrade(["athena"], target_spec_version=3)
        assert resultado.verdict == "BLOCKED"
        bloqueios = [c for c in resultado.cells if c.status == "UNSUPPORTED"]
        assert bloqueios, "esperava ao menos uma celula UNSUPPORTED"
        assert all(c.source for c in bloqueios), (
            "celula que BLOQUEIA precisa carregar a fonte que a sustenta"
        )

    def test_engine_so_com_celula_unknown_nao_bloqueia_nem_libera(self):
        # PyIceberg: nenhuma fonte foi lida nesta coleta.
        resultado = upgrade.assess_upgrade(["pyiceberg"], target_spec_version=3)
        assert resultado.verdict == "UNRESOLVED"
        assert resultado.unresolved, "UNRESOLVED sem dizer o que falta e inutil"

    def test_bloqueio_vence_desconhecimento(self):
        # Um consumidor que bloqueia e outro que ninguem conhece: o veredito e
        # BLOCKED. Nao ha o que resolver -- ja ha fonte dizendo nao.
        resultado = upgrade.assess_upgrade(["athena", "pyiceberg"], target_spec_version=3)
        assert resultado.verdict == "BLOCKED"

    def test_sem_consumidor_declarado_nao_inventa_veredito(self):
        resultado = upgrade.assess_upgrade([], target_spec_version=3)
        assert resultado.verdict == "UNRESOLVED"
        assert resultado.unresolved


class TestNuncaExecuta:
    def test_o_modulo_nao_tem_superficie_de_escrita(self):
        """Secao 94 do prompt: assess-upgrade NUNCA executa o upgrade.

        Medido pelo que o modulo IMPORTA, nao por substring na fonte: prosa
        que menciona "subprocesso" numa explicacao nao e uma chamada, e um
        teste que confunde as duas quebra na primeira frase honesta.
        """
        import ast
        import inspect

        arvore = ast.parse(inspect.getsource(upgrade))
        importados: set[str] = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                importados.update(a.name.split(".")[0] for a in no.names)
            elif isinstance(no, ast.ImportFrom) and no.module:
                importados.add(no.module.split(".")[0])
        for proibido in ("boto3", "botocore", "subprocess", "os", "pyspark"):
            assert proibido not in importados, proibido


class TestVocabularioFechado:
    def test_todo_veredito_esta_no_vocabulario(self):
        for engines in ([], ["athena"], ["glue"], ["pyiceberg"], ["athena", "glue"]):
            resultado = upgrade.assess_upgrade(engines, target_spec_version=3)
            assert resultado.verdict in upgrade.VERDICTS

    def test_versao_de_spec_fora_do_vocabulario_estoura(self):
        with pytest.raises(ValueError):
            upgrade.assess_upgrade(["athena"], target_spec_version=9)


class TestSerializacao:
    def test_to_dict_carrega_a_evidencia_de_cada_celula(self):
        payload = upgrade.assess_upgrade(["athena"], target_spec_version=3).to_dict()
        assert payload["verdict"] == "BLOCKED"
        assert payload["target_spec_version"] == 3
        assert payload["consumers"] == ["athena"]
        for celula in payload["cells"]:
            assert {"feature", "engine", "engine_version", "status"} <= set(celula)


class TestConsumidorSemLinhaNaMatriz:
    """A diferenca entre "a matriz tem a linha e nao ha fonte" e "ninguem abriu
    a linha". As duas saem `UNKNOWN` numa celula, e so a segunda uma pessoa
    consegue consertar -- por isso ela precisa ser NOMEADA."""

    def test_emr_e_ambiguo_e_a_frase_diz_o_que_declarar(self):
        resultado = upgrade.assess_upgrade(["emr"], target_spec_version=3)
        assert resultado.unevaluated_consumers == ["emr"]
        assert resultado.verdict == "UNRESOLVED"
        frase = " ".join(resultado.unresolved)
        assert "AMBIGUO" in frase
        for plataforma in ("emr_ec2", "emr_serverless", "emr_eks"):
            assert plataforma in frase

    def test_servico_desconhecido_sai_nomeado_e_nao_em_silencio(self):
        resultado = upgrade.assess_upgrade(["quicksight"], target_spec_version=3)
        assert resultado.unevaluated_consumers == ["quicksight"]
        assert resultado.verdict == "UNRESOLVED"
        assert any("AUSENTE da matriz" in linha for linha in resultado.unresolved)

    def test_engine_com_linha_na_matriz_nao_cai_aqui(self):
        """PyIceberg tem linha e toda celula `UNKNOWN`. Ele NAO e um consumidor
        nao avaliado: ele foi avaliado, e nao ha fonte. Confundir os dois
        apagaria a unica lista que uma pessoa consegue fechar."""
        resultado = upgrade.assess_upgrade(["pyiceberg"], target_spec_version=3)
        assert resultado.unevaluated_consumers == []
        assert resultado.verdict == "UNRESOLVED"

    def test_o_campo_sai_no_payload(self):
        payload = upgrade.assess_upgrade(["emr"], target_spec_version=3).to_dict()
        assert payload["unevaluated_consumers"] == ["emr"]


class TestCruzamentoPorRelease:
    """`releases` e OPCIONAL, e a ausencia dele nao inventa nada. Com release,
    a resposta e a da plataforma naquela release -- que e o unico jeito de
    `emr_ec2` e `emr_eks` diferirem na MESMA release, como as fontes dizem que
    diferem."""

    def test_sem_release_a_resposta_e_a_da_engine(self):
        resultado = upgrade.assess_upgrade(["emr_eks"], target_spec_version=3)
        assert {c.status for c in resultado.cells} == {"UNKNOWN"}
        assert all(c.engine_version == "*" for c in resultado.cells)
        assert all(c.reason == "" for c in resultado.cells)

    def test_com_release_as_duas_plataformas_divergem(self):
        ec2 = upgrade.assess_upgrade(
            ["emr_ec2"], target_spec_version=3, releases={"emr_ec2": "emr-7.7.0"}
        )
        eks = upgrade.assess_upgrade(
            ["emr_eks"], target_spec_version=3, releases={"emr_eks": "emr-7.7.0"}
        )

        def status(resultado, feature):
            return next(c.status for c in resultado.cells if c.feature == feature)

        assert status(ec2, "nanosecond_timestamp") == "UNKNOWN"
        assert status(eks, "nanosecond_timestamp") == "UNSUPPORTED"

    def test_a_celula_carrega_a_medida_que_a_sustenta(self):
        resultado = upgrade.assess_upgrade(
            ["emr_eks"], target_spec_version=3, releases={"emr_eks": "emr-7.7.0"}
        )
        celula = next(
            c for c in resultado.cells if c.feature == "nanosecond_timestamp"
        )
        assert celula.library_version == "1.6.1-amzn-2"
        assert celula.min_library_version == "1.7.0"
        assert celula.reason == "biblioteca_anterior_ao_minimo"
        assert celula.to_dict()["reason"] == "biblioteca_anterior_ao_minimo"

    def test_iceberg_ausente_na_release_nao_bloqueia(self):
        """`emr-6.5.0` no EKS nao publica Iceberg. Isso e `UNRESOLVED`, nunca
        `BLOCKED`: nao saber que versao roda e diferente de saber que nao
        suporta, e transformar o primeiro no segundo mataria uma migracao que
        talvez estivesse liberada."""
        resultado = upgrade.assess_upgrade(
            ["emr_eks"], target_spec_version=3, releases={"emr_eks": "emr-6.5.0"}
        )
        assert resultado.verdict == "UNRESOLVED"
        assert {c.reason for c in resultado.cells} == {"iceberg_ausente_na_release"}
