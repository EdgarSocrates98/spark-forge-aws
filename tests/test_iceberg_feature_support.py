"""Matriz de compatibilidade feature de Iceberg x engine.

Espelha `tests/test_runtime_matrix.py`: a mesma tecnica de matriz sintetica em
`tmp_path` via monkeypatch de `knowledge_ref.__file__`, pelo mesmo motivo --
os casos de erro precisam de uma celula defeituosa, e inventar celula
defeituosa no dado PUBLICADO e exatamente o que o carregador existe para
recusar.
"""
import pytest

import sparkforge.knowledge_ref as kr
from sparkforge.facts import runtime_matrix
from sparkforge.storage import feature_support


def _limpa_caches():
    feature_support.load.cache_clear()
    runtime_matrix.watched_sources.cache_clear()


@pytest.fixture(autouse=True)
def _restaura_a_matriz_real():
    """A matriz do repositorio precisa voltar a ser o que o resto da suite ve.
    `autouse` porque esquecer a limpeza num teste novo contamina os seguintes
    com uma matriz de `tmp_path` que ja nem existe mais em disco."""
    yield
    _limpa_caches()


def _matriz_sintetica(tmp_path, monkeypatch, corpo: str):
    pacote = tmp_path / "site-packages" / "sparkforge"
    conhecimento = pacote / "knowledge"
    (conhecimento / "storage").mkdir(parents=True)
    (conhecimento / "storage" / "iceberg-feature-support.yaml").write_text(corpo, encoding="utf-8")
    (conhecimento / "sources.lock.json").write_text('{"sources": {}}', encoding="utf-8")
    modulo = pacote / "knowledge_ref.py"
    modulo.touch()
    monkeypatch.delenv("SPARKFORGE_KNOWLEDGE", raising=False)
    monkeypatch.setattr(kr, "__file__", str(modulo))
    _limpa_caches()


def _celula(status: str, *, fonte: bool = True, tipo: str = "OFFICIAL_TECHNICAL_DOC") -> str:
    linhas = [f"          status: {status}\n"]
    if fonte:
        linhas.append('          source: "https://exemplo.invalido/fonte"\n')
        linhas.append(f"          source_type: {tipo}\n")
        linhas.append('          retrieved: "2026-01-01"\n')
    return "".join(linhas)


def _corpo(celula: str, spec_version: int = 3) -> str:
    return (
        "schema_version: 1\n"
        "features:\n"
        "  feature_sintetica:\n"
        f"    spec_version: {spec_version}\n"
        "    engines:\n"
        "      glue:\n"
        '        "9.9":\n'
        f"{celula}"
    )


class TestCelulaReal:
    """A matriz publicada, nas duas celulas que a fonte do Glue 6.0 sustenta
    textualmente -- uma afirmativa e uma negativa, em engines diferentes."""

    def test_variant_no_glue_6_0_e_suportado(self):
        assert feature_support.support("variant", "glue", "6.0") == "SUPPORTED"

    def test_athena_nao_le_tabela_v3(self):
        assert feature_support.support("variant", "athena") == "UNSUPPORTED"

    def test_celula_afirmativa_carrega_a_fonte_que_a_sustenta(self):
        celula = feature_support.cell("variant", "glue", "6.0")
        assert celula["source"] == (
            "https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html"
        )
        assert celula["source_type"] in runtime_matrix.SOURCE_TYPES
        assert celula["retrieved"]


class TestCelulaAusente:
    """Celula ausente e celula desconhecida sao coisas diferentes -- mas
    NENHUMA das duas e excecao. `KeyError` vazando daqui viraria `try/except`
    no chamador, e `except KeyError` engole tambem o defeito de digitacao."""

    def test_engine_que_a_matriz_nao_lista_devolve_unknown(self):
        assert feature_support.support("variant", "duckdb", "1.0") == "UNKNOWN"

    def test_feature_que_a_matriz_nao_lista_devolve_unknown(self):
        assert feature_support.support("nao_existe", "glue", "6.0") == "UNKNOWN"

    def test_versao_que_a_matriz_nao_lista_devolve_unknown(self):
        assert feature_support.support("variant", "glue", "1.0") == "UNKNOWN"


class TestInvariantesDoCarregador:
    def test_status_fora_do_vocabulario_estoura(self, tmp_path, monkeypatch):
        _matriz_sintetica(tmp_path, monkeypatch, _corpo(_celula("MAIS_OU_MENOS")))
        with pytest.raises(feature_support.FeatureSupportError, match="status"):
            feature_support.load()

    def test_source_type_fora_do_vocabulario_estoura(self, tmp_path, monkeypatch):
        _matriz_sintetica(
            tmp_path, monkeypatch, _corpo(_celula("SUPPORTED", tipo="ALGUM_BLOG_QUALQUER"))
        )
        with pytest.raises(feature_support.FeatureSupportError, match="source_type"):
            feature_support.load()

    def test_status_afirmativo_sem_fonte_estoura(self, tmp_path, monkeypatch):
        """A regra da secao 20 em codigo: celula afirmativa sem evidencia e
        opiniao com cara de fato."""
        _matriz_sintetica(tmp_path, monkeypatch, _corpo(_celula("SUPPORTED", fonte=False)))
        with pytest.raises(feature_support.FeatureSupportError, match="sem `source`"):
            feature_support.load()

    def test_spec_version_fora_do_formato_conhecido_estoura(self, tmp_path, monkeypatch):
        _matriz_sintetica(tmp_path, monkeypatch, _corpo(_celula("SUPPORTED"), spec_version=4))
        with pytest.raises(feature_support.FeatureSupportError, match="spec_version"):
            feature_support.load()

    def test_unknown_sem_fonte_e_aceito(self, tmp_path, monkeypatch):
        """Desconhecimento nao precisa de prova; afirmacao precisa. Exigir fonte
        de `UNKNOWN` empurraria quem edita a inventar uma -- ou, pior, a apagar
        a celula, e celula apagada mente dizendo que a pergunta nunca foi
        feita."""
        _matriz_sintetica(tmp_path, monkeypatch, _corpo(_celula("UNKNOWN", fonte=False)))
        assert feature_support.support("feature_sintetica", "glue", "9.9") == "UNKNOWN"

    def test_forma_curta_afirmativa_tambem_exige_fonte(self, tmp_path, monkeypatch):
        """A forma escalar (`"9.9": UNKNOWN`) existe para deixar as dezenas de
        celulas desconhecidas legiveis. Ela nao pode virar a porta dos fundos
        por onde um `SUPPORTED` sem fonte entra."""
        corpo = (
            "schema_version: 1\n"
            "features:\n"
            "  feature_sintetica:\n"
            "    engines:\n"
            "      glue:\n"
            '        "9.9": SUPPORTED\n'
        )
        _matriz_sintetica(tmp_path, monkeypatch, corpo)
        with pytest.raises(feature_support.FeatureSupportError, match="sem `source`"):
            feature_support.load()


class TestMatrizPublicada:
    def test_toda_celula_afirmativa_tem_fonte_vigiada_no_lock(self):
        """URL solta na matriz, sem entrada no lock, nao teria hash nem data
        revalidados por `scripts/refresh_knowledge.py` -- que e o unico
        mecanismo que percebe fonte oficial mudando de conteudo."""
        vigiadas = runtime_matrix.watched_sources()
        for feature, engine, versao, celula in feature_support.cells():
            if celula["status"] == "UNKNOWN":
                continue
            assert celula["source"] in vigiadas, (
                f"{feature}.{engine}.{versao}: {celula['source']} fora do sources.lock.json"
            )

    def test_unknown_cells_relata_o_que_a_matriz_nao_sabe(self):
        """Relatorio honesto MOSTRA o desconhecido em vez de omitir. Se um dia
        esta lista esvaziar, ou a cobertura ficou completa (com fonte por
        celula) ou alguem preencheu por chute -- e as duas merecem ser vistas."""
        desconhecidas = feature_support.unknown_cells()
        assert desconhecidas
        assert ("default_values", "pyiceberg", "*") in desconhecidas
        assert ("variant", "glue", "6.0") not in desconhecidas

    def test_athena_tem_exatamente_uma_celula_afirmativa(self):
        """A fonte diz que tabela `format-version = 3` nao e lida pelo Athena --
        uma afirmacao sobre o FORMATO, nao sobre feature. Estende-la para as
        outras seis features da v3 preencheria celula por raciocinio, que e o
        mesmo defeito da inferencia entre engines na direcao negativa. Este
        teste existe porque a proxima pessoa a editar a matriz vai achar a
        assimetria estranha e "consertar" -- e ai o gate precisa aparecer antes
        do commit, com a explicacao em `engines.athena.note`."""
        afirmativas = [
            (feature, versao)
            for feature, engine, versao, celula in feature_support.cells()
            if engine == "athena" and celula["status"] != "UNKNOWN"
        ]
        assert afirmativas == [("variant", "*")]

    def test_suporte_nao_se_propaga_entre_engines(self):
        """A inferencia proibida da secao 20: "o Iceberg suporta, logo o Athena
        suporta". O dado nao propaga -- e este teste falha no dia em que alguem
        preencher uma linha inteira a partir de uma unica fonte de uma engine."""
        for feature, dados in feature_support.load().items():
            engines = dados["engines"]
            suportado = {
                engine
                for engine, versoes in engines.items()
                if any(c["status"] == "SUPPORTED" for c in versoes.values())
            }
            if not suportado:
                continue
            outras = {
                c["status"]
                for engine, versoes in engines.items()
                if engine not in suportado
                for c in versoes.values()
            }
            assert outras <= {"UNKNOWN", "UNSUPPORTED", "PARTIAL"}, feature
        # E o caso concreto, para que o laco acima nao passe por vacuidade.
        assert feature_support.support("variant", "glue", "6.0") == "SUPPORTED"
        assert feature_support.support("variant", "emr") == "UNKNOWN"
        assert feature_support.support("variant", "athena") == "UNSUPPORTED"


class TestResolucaoDeCaminhoNoPacoteInstalado:
    """Modulo novo que le dado do disco repete o bug de path da Fase SF-MIG se
    escrever a propria conta de `parents[N]`: `pyproject.toml` empacota
    `knowledge/` DENTRO do pacote, um nivel mais fundo do que a conta do
    checkout alcanca. Ver a docstring de `sparkforge/facts/runtime_matrix.py`.
    """

    def test_le_a_matriz_do_layout_de_pacote_instalado(self, tmp_path, monkeypatch):
        _matriz_sintetica(tmp_path, monkeypatch, _corpo(_celula("UNKNOWN", fonte=False)))
        assert feature_support.support("feature_sintetica", "glue", "9.9") == "UNKNOWN"
        assert feature_support.unknown_cells() == [("feature_sintetica", "glue", "9.9")]
