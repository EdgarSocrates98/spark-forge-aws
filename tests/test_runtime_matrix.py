from pathlib import Path

from sparkforge.facts import runtime_matrix

ROOT = Path(__file__).resolve().parents[1]


class TestMatrizDeVersoes:
    def test_carrega_as_versoes_que_o_codigo_conhecia(self):
        matriz = runtime_matrix.load()
        # As quatro que `GLUE_MATRIX` trazia. Nao asserta o total: versao nova
        # entra por dado, e um total copiado quebraria com numero para bumpar.
        for versao in ("3.0", "4.0", "5.0", "5.1"):
            assert versao in matriz, versao

    def test_cada_versao_declara_runtime_e_procedencia(self):
        for versao, linha in runtime_matrix.load().items():
            assert linha["spark"], versao
            assert linha["python"], versao
            assert linha["sources"], f"{versao} sem fonte"
            assert linha["retrieved"], f"{versao} sem data de consulta"

    def test_toda_fonte_esta_no_lock_de_fontes(self):
        vigiadas = runtime_matrix.watched_sources()
        for versao, linha in runtime_matrix.load().items():
            for fonte in linha["sources"]:
                assert fonte in vigiadas, f"{versao}: {fonte} fora do sources.lock.json"

    def test_versoes_conhecidas_saem_ordenadas(self):
        conhecidas = runtime_matrix.known_versions()
        assert list(conhecidas) == sorted(
            conhecidas, key=lambda v: tuple(int(p) for p in v.split("."))
        )
        assert conhecidas.index("4.0") < conhecidas.index("5.1")
