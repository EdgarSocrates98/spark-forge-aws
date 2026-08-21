from pathlib import Path

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
