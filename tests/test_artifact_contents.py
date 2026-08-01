"""O artefato tem que carregar catalogo e knowledge.

Sem isto, `pip install` entrega `analyze` sem `judge` -- a camada `facts/`
embarca e a camada `rules/` nao. O teste constroi o wheel de verdade porque
inspecionar `pyproject.toml` provaria a intencao, nao o resultado: e o backend
que decide o que entra no zip.
"""
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> zipfile.ZipFile:
    out = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"`python -m build` indisponivel ou falhou: {result.stderr[-400:]}")
    built = sorted(out.glob("*.whl"))
    assert built, "build terminou com sucesso e nao produziu wheel"
    return zipfile.ZipFile(built[0])


def _names(wheel: zipfile.ZipFile, prefix: str) -> list[str]:
    return [n for n in wheel.namelist() if n.startswith(prefix)]


class TestWheelCarriesTheKnowledgeLayer:
    def test_catalog_yaml_is_inside_the_package(self, wheel):
        found = _names(wheel, "sparkforge/rules/catalog/")
        assert [n for n in found if n.endswith(".yaml")], sorted(wheel.namelist())[:20]

    def test_routing_is_included_too(self, wheel):
        """`next_step` fica inerte sem routing.yaml, e o sintoma seria um
        roteamento vazio em vez de um erro."""
        assert "sparkforge/rules/catalog/routing.yaml" in wheel.namelist()

    def test_knowledge_is_inside_the_package(self, wheel):
        assert _names(wheel, "sparkforge/knowledge/")

    def test_schemas_survived_the_backend_swap(self, wheel):
        """`package-data` do setuptools embarcava os JSON Schemas. Se a troca de
        backend os perder, `validate_output` quebra no pacote instalado -- e a
        secao 5.2 da Fase 0 diz que finding sem schema nao e recusado."""
        assert _names(wheel, "sparkforge/findings/schemas/")

    def test_the_counts_are_not_zero(self, wheel):
        """Asserção de contagem: `force-include` sumindo num upgrade do
        hatchling nao quebraria import nenhum -- so devolveria catalogo
        vazio."""
        assert len(_names(wheel, "sparkforge/rules/catalog/")) >= 8
        assert len(_names(wheel, "sparkforge/knowledge/")) >= 15


# A constante que o hatchling usa como `SOURCE_DATE_EPOCH` quando a variavel
# nao esta no ambiente: 2020-02-02T00:00:00Z. O `datetime` deriva a tupla em vez
# de repeti-la para que as duas nunca possam divergir na leitura.
HATCHLING_DEFAULT_EPOCH = 1580601600
_utc = datetime.fromtimestamp(HATCHLING_DEFAULT_EPOCH, timezone.utc)
HATCHLING_DEFAULT_TIME_TUPLE = (
    _utc.year,
    _utc.month,
    _utc.day,
    _utc.hour,
    _utc.minute,
    _utc.second,
)


class TestTheWheelIsBuiltReproducibly:
    """Os invariantes que `reproducible = true` produz, medidos no wheel.

    A prova FORTE da reprodutibilidade -- construir duas vezes e comparar por
    sha256 -- mora em `scripts/verify_wheel.py`, porque custa uma segunda build
    inteira e a suite roda a cada commit; o `ci.yml` executa aquele gate em
    ubuntu e windows a cada push e PR. O que sobra aqui e barato e roda sempre:
    o wheel que a fixture ja construiu carrega, em cada entrada do zip, a marca
    de cada eixo que a flag fecha. Um `reproducible = false` colado em
    `pyproject.toml` quebraria estes testes em segundos, sem esperar o gate.
    """

    def test_every_entry_shares_one_timestamp(self, wheel):
        """O eixo do `SOURCE_DATE_EPOCH`. A assercao e "um so valor", nao um
        valor especifico, porque um construtor pode legitimamente exportar
        `SOURCE_DATE_EPOCH` -- o que nao pode e o timestamp vir do relogio, que
        daria valores diferentes entre as entradas do mesmo zip."""
        stamps = {info.date_time for info in wheel.infolist()}
        assert len(stamps) == 1, sorted(stamps)

    @pytest.mark.skipif(
        "SOURCE_DATE_EPOCH" in os.environ,
        reason="ambiente fixa SOURCE_DATE_EPOCH; o default do hatchling nao se aplica",
    )
    def test_without_the_env_var_the_epoch_is_the_fixed_constant(self, wheel):
        """Sem `SOURCE_DATE_EPOCH` no ambiente, o timestamp e uma CONSTANTE --
        nao o commit, nao o relogio.

        Derivar o epoch do commit (`git log -1 --format=%ct`) e o que a maioria
        dos projetos faz, e aqui seria errado: `python -m build` constroi o
        wheel A PARTIR do sdist, onde nao existe `.git`. O epoch mudaria entre
        o caminho direto e o caminho via sdist, e os dois wheels divergiriam --
        exatamente o defeito que se quer impedir.
        """
        assert {info.date_time for info in wheel.infolist()} == {HATCHLING_DEFAULT_TIME_TUPLE}

    def test_permissions_are_normalized(self, wheel):
        """O eixo do umask e do sistema de arquivos. `st_mode` cru faria o
        mesmo wheel sair diferente de um checkout com umask diferente, e
        diferente entre Windows (0o666) e Linux (0o644)."""
        modes = {(info.external_attr >> 16) & 0o777 for info in wheel.infolist()}
        assert modes <= {0o644, 0o755}, [oct(m) for m in sorted(modes)]

    def test_one_compression_method_for_every_entry(self, wheel):
        methods = {info.compress_type for info in wheel.infolist()}
        assert methods == {zipfile.ZIP_DEFLATED}, methods

    def test_the_entries_follow_a_sorted_walk(self, wheel):
        """O eixo da ordem de caminhada do sistema de arquivos.

        O zip NAO e globalmente ordenado, e nao deveria ser: `os.walk` e
        top-down, entao os arquivos da raiz de um diretorio vem antes dos das
        subpastas (`knowledge/INDEX.md` antes de `knowledge/athena/...`), e o
        `force-include` entra depois dos arquivos do projeto. O invariante que
        a reprodutibilidade exige e outro, e mais fraco: dentro de cada
        diretorio a ordem vem de `sorted()`, e as entradas de um mesmo
        diretorio saem contiguas. Uma listagem crua de `os.scandir` -- que
        varia entre sistemas de arquivos e entre maquinas -- quebraria os dois.

        `.dist-info` fica FORA da checagem: nada ali e caminhado. Sao arquivos
        gerados em memoria, e `RECORD` sai por ultimo por construcao (ele
        indexa os outros), depois de `licenses/LICENSE` -- o que parte o bloco
        do `.dist-info` em dois sem que isso diga nada sobre ordem de
        caminhada.
        """
        walked = [n for n in wheel.namelist() if ".dist-info/" not in n]
        assert walked, wheel.namelist()

        runs: list[str] = []
        by_directory: dict[str, list[str]] = {}
        for name in walked:
            parent = name.rsplit("/", 1)[0] if "/" in name else ""
            if not runs or runs[-1] != parent:
                runs.append(parent)
            by_directory.setdefault(parent, []).append(name)

        assert len(runs) == len(set(runs)), f"diretorio visitado em blocos separados: {runs}"
        for parent, names in by_directory.items():
            assert names == sorted(names), parent
