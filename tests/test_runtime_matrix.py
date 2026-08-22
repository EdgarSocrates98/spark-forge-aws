from pathlib import Path

import pytest

import sparkforge.knowledge_ref as kr
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

    def test_toda_fonte_de_claim_tambem_esta_no_lock(self):
        """A forma longa carrega fonte por claim, e nao pela lista `sources` da
        linha -- sem esta metade, uma URL citada dentro de `claims` ficaria sem
        `retrieved` revalidado por `scripts/refresh_knowledge.py`, que e o unico
        mecanismo que percebe fonte oficial mudando de conteudo."""
        vigiadas = runtime_matrix.watched_sources()
        for versao, componentes in runtime_matrix.evidence().items():
            for componente, registro in componentes.items():
                for claim in registro["claims"]:
                    assert claim["source"] in vigiadas, (
                        f"{versao}.{componente}: {claim['source']} fora do sources.lock.json"
                    )

    def test_versoes_conhecidas_saem_ordenadas(self):
        conhecidas = runtime_matrix.known_versions()
        assert list(conhecidas) == sorted(
            conhecidas, key=lambda v: tuple(int(p) for p in v.split("."))
        )
        assert conhecidas.index("4.0") < conhecidas.index("5.1")


class TestResolucaoDeCaminhoNoPacoteInstalado:
    """Espelha `test_knowledge_ref.py::
    test_falls_back_to_the_package_dir_when_no_repo_root_exists`.

    A Task 1 desta fase escrevia a propria conta de `parents[N]` para achar
    `knowledge/glue/runtime-matrix.yaml`, e essa conta so foi verificada no
    checkout de desenvolvimento -- onde `knowledge/` mora dois niveis acima
    deste arquivo. `pyproject.toml` empacota `knowledge/` DENTRO do pacote
    (`sparkforge/knowledge`), um nivel mais fundo do que a conta original
    alcancava; instalado por pip, `import sparkforge.facts.runtime_detect`
    quebrava com `FileNotFoundError` -- reproduzido e confirmado instalando o
    wheel de verdade num venv limpo. A correcao trocou a conta propria por
    `sparkforge.knowledge_ref.knowledge_dir()`, que ja resolve exatamente
    este caso desde a Fase 3a e ja tem o teste que este espelha.

    Sem este teste, nada aqui pinaria que `runtime_matrix` continua
    delegando para `knowledge_ref` em vez de reintroduzir a propria conta de
    path -- o mesmo desvio que causou o bug, e o unico caminho que os outros
    tres testes desta classe nunca exercitam (raiz do repo sempre existe no
    ambiente de teste).
    """

    def test_le_a_matriz_do_layout_de_pacote_instalado(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SPARKFORGE_KNOWLEDGE", raising=False)

        fake_package_dir = tmp_path / "site-packages" / "sparkforge"
        fake_knowledge_dir = fake_package_dir / "knowledge"
        (fake_knowledge_dir / "glue").mkdir(parents=True)
        (fake_knowledge_dir / "glue" / "runtime-matrix.yaml").write_text(
            "schema_version: 1\n"
            "versions:\n"
            '  "9.9":\n'
            '    spark: "9.9.9"\n'
            '    python: "9.9"\n'
            '    iceberg: "9.9.9"\n'
            "    sources: []\n"
            '    retrieved: "2026-01-01"\n',
            encoding="utf-8",
        )
        (fake_knowledge_dir / "sources.lock.json").write_text(
            '{"sources": {}}', encoding="utf-8"
        )
        fake_module_file = fake_package_dir / "knowledge_ref.py"
        fake_module_file.touch()

        # `knowledge_dir()` le o proprio `__file__` de `knowledge_ref`, nao o
        # de `runtime_matrix` -- e o de `runtime_matrix` que importaria a
        # funcao errado se a resolucao fosse reescrita ad-hoc de novo.
        monkeypatch.setattr(kr, "__file__", str(fake_module_file))

        runtime_matrix.load.cache_clear()
        runtime_matrix.watched_sources.cache_clear()
        try:
            assert runtime_matrix.load() == {
                "9.9": {
                    "spark": "9.9.9",
                    "python": "9.9",
                    "iceberg": "9.9.9",
                    "sources": [],
                    "retrieved": "2026-01-01",
                }
            }
            assert runtime_matrix.watched_sources() == frozenset()
        finally:
            # A matriz real do repositorio tem que voltar a ser o que os
            # demais testes deste arquivo (e o resto da suite) enxergam.
            runtime_matrix.load.cache_clear()
            runtime_matrix.watched_sources.cache_clear()


class TestSemVersaoNoCodigo:
    def test_matriz_de_glue_nao_volta_para_o_codigo(self):
        import re

        # A matriz e dado. Se uma versao de Glue voltar a ser constante em
        # Python, ela volta a envelhecer sem fonte e sem data -- o arranjo que a
        # Task 1 desfez. O padrao procura entrada de dicionario com chave de
        # versao, que e a forma que `GLUE_MATRIX` tinha.
        alvo = re.compile(r'"[0-9]+\.[0-9]+"\s*:\s*\{\s*"spark"')
        ofensores = []
        for arquivo in (ROOT / "sparkforge").rglob("*.py"):
            if arquivo.name == "runtime_matrix.py":
                continue
            if alvo.search(arquivo.read_text(encoding="utf-8")):
                ofensores.append(str(arquivo.relative_to(ROOT)))
        assert ofensores == [], f"matriz de versao em codigo: {ofensores}"


def _limpa_caches():
    runtime_matrix.load.cache_clear()
    runtime_matrix.evidence.cache_clear()
    runtime_matrix.watched_sources.cache_clear()


def _matriz_sintetica(tmp_path, monkeypatch, corpo: str):
    """Aponta o resolvedor de `knowledge/` para uma matriz escrita pelo teste.

    Mesmo mecanismo de `TestResolucaoDeCaminhoNoPacoteInstalado`: `knowledge_dir()`
    resolve a partir do `__file__` de `knowledge_ref`, entao trocar esse atributo
    e a unica forma de isolar o corpo real do repositorio. Sem isso todo teste
    abaixo estaria medindo a matriz de verdade, e um `CONFLICTING` sintetico
    exigiria inventar um conflito no dado publicado -- que e justamente o que o
    carregador recusa.
    """
    pacote = tmp_path / "site-packages" / "sparkforge"
    conhecimento = pacote / "knowledge"
    (conhecimento / "glue").mkdir(parents=True)
    (conhecimento / "glue" / "runtime-matrix.yaml").write_text(corpo, encoding="utf-8")
    (conhecimento / "sources.lock.json").write_text('{"sources": {}}', encoding="utf-8")
    modulo = pacote / "knowledge_ref.py"
    modulo.touch()
    monkeypatch.delenv("SPARKFORGE_KNOWLEDGE", raising=False)
    monkeypatch.setattr(kr, "__file__", str(modulo))
    _limpa_caches()


@pytest.fixture(autouse=True)
def _restaura_a_matriz_real():
    """A matriz do repositorio precisa voltar a ser o que o resto da suite ve.
    `autouse` porque esquecer a limpeza num teste novo contamina os seguintes
    com uma matriz de `tmp_path` que ja nem existe mais em disco."""
    yield
    _limpa_caches()


def _matriz(componente: str) -> str:
    return (
        "schema_version: 1\n"
        "versions:\n"
        '  "9.9":\n'
        '    spark: "9.9.9"\n'
        f"{componente}"
        "    sources: []\n"
        '    retrieved: "2026-01-01"\n'
    )


def _longa(status: str, *valores: str) -> str:
    linhas = [f"    python:\n      status: {status}\n      claims:\n"]
    for indice, valor in enumerate(valores):
        linhas.append(
            f'        - value: "{valor}"\n'
            f'          source: "https://exemplo.invalido/fonte-{indice}"\n'
            "          source_type: OFFICIAL_TECHNICAL_DOC\n"
            '          retrieved: "2026-01-01"\n'
        )
    return "".join(linhas)


class TestEvidenciaPorFonte:
    def test_fonte_unica_resolve_para_o_valor(self, tmp_path, monkeypatch):
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("VERIFIED", "3.13")))
        assert runtime_matrix.load()["9.9"]["python"] == "3.13"

    def test_fontes_concordantes_resolvem_para_o_valor(self, tmp_path, monkeypatch):
        _matriz_sintetica(
            tmp_path, monkeypatch, _matriz(_longa("VERIFIED", "3.13", "3.13", "3.13"))
        )
        assert runtime_matrix.load()["9.9"]["python"] == "3.13"

    def test_verified_com_fontes_discordantes_estoura(self, tmp_path, monkeypatch):
        """A invariante central da secao 1 do prompt -- "nunca transformar
        CONFLICTING em VERIFIED". A forma pratica de violar nao e mentir: e
        editar o valor de uma claim e esquecer a outra."""
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("VERIFIED", "3.12", "3.13")))
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="nunca vira VERIFIED"):
            runtime_matrix.load()

    def test_conflicting_retem_o_valor_em_vez_de_escolher_um(self, tmp_path, monkeypatch):
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("CONFLICTING", "3.12", "3.13")))
        linha = runtime_matrix.load()["9.9"]
        assert "python" not in linha
        assert linha["spark"] == "9.9.9"
        assert runtime_matrix.conflicting() == [("9.9", "python")]

    def test_unresolved_tambem_retem(self, tmp_path, monkeypatch):
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("UNRESOLVED", "3.12", "3.13")))
        assert "python" not in runtime_matrix.load()["9.9"]

    def test_conflito_inventado_estoura(self, tmp_path, monkeypatch):
        """Conflito falso apaga em silencio toda regra guardada pelo componente
        -- o mesmo estrago do conflito escondido, na direcao oposta."""
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("CONFLICTING", "3.13", "3.13")))
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="conflito inventado"):
            runtime_matrix.load()

    def test_status_sem_mecanismo_que_o_produza_e_recusado(self, tmp_path, monkeypatch):
        """`STALE` e `UNVERIFIED` afirmam frescor, e frescor depende de um TTL
        por dominio que este repositorio ainda nao tem como dado."""
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("STALE", "3.13")))
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="STALE e UNVERIFIED"):
            runtime_matrix.load()

    def test_source_type_fora_do_vocabulario_estoura(self, tmp_path, monkeypatch):
        corpo = _matriz(
            "    python:\n"
            "      status: VERIFIED\n"
            "      claims:\n"
            '        - value: "3.13"\n'
            '          source: "https://exemplo.invalido/fonte"\n'
            "          source_type: ALGUM_BLOG_QUALQUER\n"
            '          retrieved: "2026-01-01"\n'
        )
        _matriz_sintetica(tmp_path, monkeypatch, corpo)
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="source_type"):
            runtime_matrix.load()

    def test_claim_sem_procedencia_estoura(self, tmp_path, monkeypatch):
        corpo = _matriz(
            "    python:\n"
            "      status: VERIFIED\n"
            "      claims:\n"
            '        - value: "3.13"\n'
            "          source_type: OFFICIAL_TECHNICAL_DOC\n"
            '          retrieved: "2026-01-01"\n'
        )
        _matriz_sintetica(tmp_path, monkeypatch, corpo)
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="claim sem `source`"):
            runtime_matrix.load()

    def test_status_sem_claims_estoura(self, tmp_path, monkeypatch):
        corpo = _matriz("    python:\n      status: VERIFIED\n      claims: []\n")
        _matriz_sintetica(tmp_path, monkeypatch, corpo)
        with pytest.raises(runtime_matrix.RuntimeMatrixError, match="sem `claims`"):
            runtime_matrix.load()

    def test_forma_curta_nao_aparece_na_evidencia(self, tmp_path, monkeypatch):
        """`evidence()` relata disputa. Componente escalar nao tem disputa a
        relatar, e lista-lo ali daria a impressao de que tem."""
        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("VERIFIED", "3.13")))
        assert set(runtime_matrix.evidence()["9.9"]) == {"python"}


class TestComponenteEmDisputaNaoJulgaRegra:
    """O golden que a secao 78 do prompt torna obrigatorio, no nivel em que ele
    tem consequencia: com o valor retido, a regra guardada por aquele componente
    e PULADA, nunca julgada contra um numero escolhido a dedo."""

    def test_regra_guardada_pelo_componente_em_disputa_e_pulada(self, tmp_path, monkeypatch):
        from sparkforge.rules.version_scope import in_scope

        _matriz_sintetica(tmp_path, monkeypatch, _matriz(_longa("CONFLICTING", "3.12", "3.13")))
        runtime = dict(runtime_matrix.load()["9.9"])
        runtime["glue"] = "9.9"

        # A guarda por Python reprova -- e por AUSENCIA da chave, que e o
        # caminho fail-closed de `in_scope`, nao por comparacao de versao.
        assert in_scope({"python": ">=3.13"}, runtime) is False
        # E a guarda por um componente que NAO esta em disputa continua valendo:
        # o valor retido nao contamina o resto da linha.
        assert in_scope({"spark": ">=9.0"}, runtime) is True


class TestOCasoRealDoGlue6:
    def test_python_do_glue_6_declara_evidencia_de_tres_fontes(self):
        registro = runtime_matrix.evidence()["6.0"]["python"]
        assert registro["status"] == "VERIFIED"
        tipos = {c["source_type"] for c in registro["claims"]}
        # Tres NATUREZAS de fonte distintas, nao tres URLs quaisquer: e o que
        # torna a concordancia informativa. Doc tecnica, release doc e blog
        # oficial sao exatamente as tres que a secao 2 do prompt poe em duvida.
        assert tipos == {"OFFICIAL_TECHNICAL_DOC", "OFFICIAL_RELEASE_DOC", "OFFICIAL_BLOG"}
        assert {c["value"] for c in registro["claims"]} == {"3.13"}

    def test_a_matriz_publicada_nao_tem_componente_em_disputa(self):
        """Se um dia tiver, este teste vira o alarme: componente retido apaga as
        regras guardadas por ele, e isso precisa ser decisao consciente de quem
        editou a matriz, com a linha aparecendo aqui."""
        assert runtime_matrix.conflicting() == []
