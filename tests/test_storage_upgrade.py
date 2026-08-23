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
