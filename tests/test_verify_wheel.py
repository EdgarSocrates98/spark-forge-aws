# tests/test_verify_wheel.py
"""Testes do orquestrador do gate.

O gate em si constroi artefato e cria venv -- caro demais para a suite. Aqui se
prova a MONTAGEM do comando, que e onde os erros silenciosos moram: um
`-o pythonpath=` esquecido faz o pytest do venv importar o repositorio, e o gate
inteiro vira teatro. As classes de baixo tambem provam `main()` inteiro com
`_run` e `shutil.rmtree` trocados por dublês -- sem isso, cada caminho de
retorno de `main()` (build falhou, venv falhou, golden reprovou, etc.) so
tinha sido verificado rodando o gate de verdade, a ~95s por execucao.
"""
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import verify_wheel  # noqa: E402
from scripts.verify_wheel import (  # noqa: E402
    GOLDEN_MODULES,
    compare_builds,
    main,
    pytest_command,
    sha256_of,
    zip_divergence,
)


class TestPytestCommand:
    def test_overrides_pythonpath_to_empty(self):
        """`pyproject.toml` declara `pythonpath = ["."]`. Sem sobrescrever, o
        repositorio entra no sys.path e vence o site-packages."""
        cmd = pytest_command(Path("/venv/bin/python"), ROOT)
        assert "-o" in cmd
        assert "pythonpath=" in cmd

    def test_runs_the_provenance_module_first(self):
        """Se a procedencia falha, comparar golden nao tem sentido."""
        cmd = pytest_command(Path("/venv/bin/python"), ROOT)
        modules = [c for c in cmd if "test_" in str(c)]
        assert "provenance" in str(modules[0])

    def test_runs_every_golden_module(self):
        cmd = " ".join(str(c) for c in pytest_command(Path("/venv/bin/python"), ROOT))
        for module in GOLDEN_MODULES:
            assert module in cmd, module

    def test_uses_the_venv_python_not_the_current_one(self):
        cmd = pytest_command(Path("/venv/bin/python"), ROOT)
        assert str(cmd[0]) == str(Path("/venv/bin/python"))


class TestGoldenModuleDiscovery:
    def test_discovers_every_golden_module_on_disk(self):
        """Corpus novo sem entrada aqui sairia do gate em silencio."""
        on_disk = {p.name for p in (ROOT / "tests").glob("test_fixtures_*.py")}
        assert set(GOLDEN_MODULES) == on_disk

    def test_there_is_more_than_one(self):
        assert len(GOLDEN_MODULES) >= 15


class _FakeRun:
    """Dublê de `_run`: registra cada chamada e devolve sucesso, exceto na
    posicao `fail_at` (0-based, na ordem em que `main()` chama `_run`)."""

    def __init__(self, fail_at: int | None = None):
        self.calls: list[list] = []
        self.fail_at = fail_at

    def __call__(self, command, **kwargs):
        idx = len(self.calls)
        self.calls.append(command)
        returncode = 1 if idx == self.fail_at else 0
        return subprocess.CompletedProcess(command, returncode)


def _prep_fake_workdir(tmp_path: Path, monkeypatch, *, rebuild_bytes: bytes = b"") -> Path:
    """Prepara um workdir com wheel e sdist ja presentes, e faz
    `tempfile.mkdtemp` devolve-lo.

    O passo de build e sempre mockado por `_FakeRun` (nunca roda de verdade),
    entao os artefatos que `main()` procura via glob apos o build precisam
    existir de antemao -- senao todo teste alem do build cairia na checagem
    "esperava wheel e sdist em ..." em vez de exercitar o caminho pretendido.

    `rebuild/` recebe os mesmos nomes, e por padrao o mesmo conteudo, para que
    a checagem de reprodutibilidade passe. `rebuild_bytes` diferente simula uma
    build nao-reproduzivel.
    """
    dist = tmp_path / "dist"
    dist.mkdir()
    rebuild = tmp_path / "rebuild"
    rebuild.mkdir()
    for name in ("sparkforge_aws-0.0.0-py3-none-any.whl", "sparkforge_aws-0.0.0.tar.gz"):
        (dist / name).write_bytes(b"")
        (rebuild / name).write_bytes(rebuild_bytes)
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": str(tmp_path))
    return tmp_path


def _whl(path: Path, entries: list[tuple[str, bytes]], *, date_time=(2020, 2, 2, 0, 0, 0)) -> Path:
    """Escreve um zip minimo com metadado de entrada controlado."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in entries:
            info = zipfile.ZipInfo(name, date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            archive.writestr(info, payload)
    return path


class TestGoldenCorpusGuard:
    """O Critico da revisao: corpus vazio nao pode passar como paridade."""

    def test_empty_corpus_fails_the_gate_before_touching_anything(self, monkeypatch):
        monkeypatch.setattr(verify_wheel, "GOLDEN_MODULES", [])
        fake = _FakeRun()
        monkeypatch.setattr(verify_wheel, "_run", fake)
        assert main([]) == 1
        # A guarda morre ANTES de construir wheel algum -- nao so reprova,
        # reprova cedo, sem gastar os ~95s de build+venv+instalacao a toa.
        assert fake.calls == []

    def test_corpus_below_the_floor_fails_the_gate(self, monkeypatch):
        """Nao precisa estar vazio: um corpus truncado (renomeacao parcial,
        merge quebrado) tambem tem que reprovar, nao so o caso extremo `[]`."""
        monkeypatch.setattr(verify_wheel, "GOLDEN_MODULES", ["test_fixtures_golden.py"] * 3)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        assert main([]) == 1

    def test_full_corpus_does_not_trip_the_guard(self, monkeypatch, tmp_path):
        """O guard nao pode reprovar o caso normal -- senao o gate nunca passa."""
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        assert main([]) == 0


class TestMainReturnCodes:
    """Cada ponto de falha de `main()` tem que devolver 1; sucesso, 0. Antes
    desta classe, isso so tinha sido observado rodando o gate de verdade.

    Os indices de `fail_at` sao a ORDEM das chamadas a `_run` dentro de
    `main()`: 0 build, 1 rebuild, 2 venv, 3 pip install, 4 pytest, 5 pip
    install twine, 6 twine check. Inserir um passo novo no meio desloca todos
    os que vem depois -- por isso cada teste nomeia o passo que exercita.
    """

    def test_build_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=0))
        assert main([]) == 1

    def test_rebuild_failure_returns_1(self, monkeypatch, tmp_path):
        """A segunda build (checagem de reprodutibilidade) falhando reprova o
        gate como qualquer outro passo -- nao e um aviso."""
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=1))
        assert main([]) == 1

    def test_venv_creation_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=2))
        assert main([]) == 1

    def test_wheel_install_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=3))
        assert main([]) == 1

    def test_golden_pytest_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=4))
        assert main([]) == 1

    def test_twine_install_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=5))
        assert main([]) == 1

    def test_twine_check_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=6))
        assert main([]) == 1

    def test_all_steps_succeeding_returns_0(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        assert main([]) == 0


class TestWorkdirCleanup:
    def test_rmtree_runs_without_keep(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        calls = []
        monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: calls.append(a))
        main([])
        assert calls, "sem --keep, rmtree tem que rodar no finally"

    def test_rmtree_is_skipped_with_keep(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        calls = []
        monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: calls.append(a))
        main(["--keep"])
        assert not calls, "com --keep, rmtree nao pode rodar"

    def test_rmtree_runs_even_when_a_step_fails(self, monkeypatch, tmp_path):
        """O `finally` tem que limpar mesmo em reprovacao -- e o caminho mais
        comum na pratica, ja que um gate que reprova toda hora e o normal
        durante o desenvolvimento desta task."""
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=3))
        calls = []
        monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: calls.append(a))
        assert main([]) == 1
        assert calls


class TestReproducibility:
    """A build tem que ser funcao da arvore, nao do instante.

    A construcao dupla de verdade roda dentro do gate (`ci.yml`, job `wheel`,
    em ubuntu e windows). Aqui se prova a LOGICA da comparacao, que e onde o
    erro silencioso mora: um comparador que devolve `[]` para tudo faria o
    gate imprimir "reprodutibilidade OK" sem ter comparado nada -- o mesmo
    antipadrao que a guarda de `GOLDEN_MODULES` existe para evitar.
    """

    def test_identical_directories_have_no_divergence(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        for d in (a, b):
            d.mkdir()
            _whl(d / "p-1.0-py3-none-any.whl", [("m.py", b"x = 1")])
            (d / "p-1.0.tar.gz").write_bytes(b"same")
        assert compare_builds(a, b) == []

    def test_differing_bytes_are_reported_with_both_hashes(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        _whl(a / "p-1.0-py3-none-any.whl", [("m.py", b"x = 1")])
        _whl(b / "p-1.0-py3-none-any.whl", [("m.py", b"x = 2")])
        report = "\n".join(compare_builds(a, b))
        assert "sha256=" in report
        # Nomeia o arquivo DENTRO do zip, nao so o zip -- e a diferenca entre
        # "diverge" e "diverge aqui".
        assert "m.py" in report

    def test_an_empty_directory_never_passes_as_reproducible(self, tmp_path):
        """Sem esta guarda, um build que nao produziu nada e um build que
        produziu artefatos identicos dariam a mesma resposta: `[]`."""
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        assert compare_builds(a, b)

    def test_a_missing_artifact_is_reported(self, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        _whl(a / "p-1.0-py3-none-any.whl", [("m.py", b"x = 1")])
        (a / "p-1.0.tar.gz").write_bytes(b"s")
        _whl(b / "p-1.0-py3-none-any.whl", [("m.py", b"x = 1")])
        assert "p-1.0.tar.gz" in "\n".join(compare_builds(a, b))

    def test_timestamp_divergence_names_the_date_time_field(self, tmp_path):
        """O eixo classico: mesmo conteudo, `date_time` diferente. O relatorio
        tem que mostrar os dois valores, senao quem le nao sabe qual eixo
        fechar."""
        a = _whl(tmp_path / "a.whl", [("m.py", b"x = 1")])
        b = _whl(tmp_path / "b.whl", [("m.py", b"x = 1")], date_time=(2024, 6, 1, 12, 0, 0))
        report = "\n".join(zip_divergence(a, b))
        assert "2020" in report and "2024" in report

    def test_entry_order_divergence_is_named_as_such(self, tmp_path):
        """Mesmas entradas em ordem diferente e um eixo proprio -- ordem de
        caminhada do sistema de arquivos -- e nao se ve olhando entrada por
        entrada, so comparando as listas."""
        a = _whl(tmp_path / "a.whl", [("x.py", b"1"), ("y.py", b"2")])
        b = _whl(tmp_path / "b.whl", [("y.py", b"2"), ("x.py", b"1")])
        assert any("ORDEM" in line for line in zip_divergence(a, b))

    def test_the_tarball_is_not_decomposed(self, tmp_path):
        """`zip_divergence` so entende `.whl`; para o sdist o gate para no
        sha256, o que e deliberado (ver docstring)."""
        (tmp_path / "a.tar.gz").write_bytes(b"a")
        (tmp_path / "b.tar.gz").write_bytes(b"b")
        assert zip_divergence(tmp_path / "a.tar.gz", tmp_path / "b.tar.gz") == []

    def test_sha256_matches_hashlib(self, tmp_path):
        import hashlib

        payload = b"conteudo qualquer" * 5000  # maior que o chunk de leitura
        target = tmp_path / "f.bin"
        target.write_bytes(payload)
        assert sha256_of(target) == hashlib.sha256(payload).hexdigest()

    def test_a_non_reproducible_build_fails_the_gate(self, monkeypatch, tmp_path):
        """O teste que fecha a divida: artefatos diferentes entre as duas
        builds reprovam `main()`, e reprovam ANTES de instalar o venv."""
        _prep_fake_workdir(tmp_path, monkeypatch, rebuild_bytes=b"bytes diferentes")
        fake = _FakeRun()
        monkeypatch.setattr(verify_wheel, "_run", fake)
        assert main([]) == 1
        assert len(fake.calls) == 2, "so as duas builds; nada depois da reprovacao"

    def test_a_non_reproducible_build_never_reaches_outdir(
        self, monkeypatch, tmp_path, tmp_path_factory
    ):
        _prep_fake_workdir(tmp_path, monkeypatch, rebuild_bytes=b"diferente")
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        outdir = tmp_path_factory.mktemp("released") / "nao-deve-existir"
        assert main(["--outdir", str(outdir)]) == 1
        assert not outdir.exists()


class TestOutdir:
    """`--outdir` e a correcao do buraco apontado na revisao da Task 8: sem
    ele, o unico exemplar provado pelos testes de golden e apagado no
    `finally` (o workdir e temporario), e o passo de publicacao teria que
    reconstruir para ter o que anexar.

    A build hoje E reproduzivel bit-a-bit (o gate prova isso a cada execucao),
    entao reconstruir daria o mesmo arquivo. `--outdir` fica assim mesmo: a
    igualdade vale sob condicoes (mesmo hatchling, mesmo zlib, mesmo
    `SOURCE_DATE_EPOCH`), e a versao do backend nao esta pinada -- copiar torna
    "o byte publicado e o byte testado" estrutural em vez de inferido."""

    def test_outdir_receives_the_verified_wheel_and_sdist(
        self, monkeypatch, tmp_path, tmp_path_factory
    ):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        # `tmp_path_factory` porque `outdir` precisa viver FORA do workdir
        # falso (que e o proprio `tmp_path` aqui, via `_prep_fake_workdir`) --
        # senao o `rmtree` do `finally` apagaria `outdir` junto.
        outdir = tmp_path_factory.mktemp("released")
        assert main(["--outdir", str(outdir)]) == 0
        names = {p.name for p in outdir.iterdir()}
        assert names == {
            "sparkforge_aws-0.0.0-py3-none-any.whl",
            "sparkforge_aws-0.0.0.tar.gz",
        }

    def test_outdir_is_not_created_when_the_gate_fails(
        self, monkeypatch, tmp_path, tmp_path_factory
    ):
        """Um artefato reprovado nunca pode aparecer num diretorio de onde
        alguem poderia publicar por engano -- a copia so roda depois do twine
        check, o ultimo portao do gate."""
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=3))  # golden reprova
        outdir = tmp_path_factory.mktemp("released")
        empty_before = list(outdir.iterdir())
        assert main(["--outdir", str(outdir)]) == 1
        assert list(outdir.iterdir()) == empty_before

    def test_without_outdir_no_extra_directory_is_created(self, monkeypatch, tmp_path):
        """Comportamento default nao muda: sem `--outdir`, so o workdir
        temporario existe, e ele e apagado no `finally`."""
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        assert main([]) == 0

    def test_outdir_with_dotdot_still_lands_at_the_resolved_path(
        self, monkeypatch, tmp_path, tmp_path_factory
    ):
        """Achado de seguranca: `--outdir` vem de argv e chegava a `mkdir`/
        `copy2` sem normalizacao -- caminho classico de CWE-22. `safe_outdir`
        resolve `..` ANTES de qualquer acesso a disco; este teste prova que o
        `..` some e os artefatos pousam no diretorio real, nao num escape."""
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun())
        base = tmp_path_factory.mktemp("released")
        (base / "sibling").mkdir()
        raw = base / "sibling" / ".." / "target"
        assert main(["--outdir", str(raw)]) == 0
        target = (base / "target").resolve()
        assert target.is_dir()
        names = {p.name for p in target.iterdir()}
        assert names == {
            "sparkforge_aws-0.0.0-py3-none-any.whl",
            "sparkforge_aws-0.0.0.tar.gz",
        }
        # Nao vazou nada para o diretorio intermediario que o `..` atravessou.
        assert list((base / "sibling").iterdir()) == []


class TestSafeOutdir:
    """`safe_outdir` e o unico ponto de entrada para `--outdir`: resolve uma
    vez, aqui, antes de qualquer `mkdir` ou `copy2`. Nenhum valor cru de argv
    deve sobreviver alem desta funcao."""

    def test_resolves_dotdot_components(self, tmp_path):
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        raw = tmp_path / "a" / "b" / ".." / "b"
        resolved = verify_wheel.safe_outdir(raw)
        assert resolved == nested.resolve()
        assert ".." not in resolved.parts

    def test_result_is_always_absolute(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        resolved = verify_wheel.safe_outdir(Path("relative_dir"))
        assert resolved.is_absolute()

    def test_rejects_a_file_in_place_of_a_directory(self, tmp_path):
        f = tmp_path / "not_a_dir"
        f.write_text("x")
        with pytest.raises(SystemExit):
            verify_wheel.safe_outdir(f)

    def test_follows_a_symlink_to_its_real_target(self, tmp_path):
        """Decisao: SEGUIR o symlink, nao recusar.

        `install_dest` (scripts/install_skills.py) recusa symlink que escape
        de uma raiz de contencao -- mas aqui nao ha raiz: o proposito de
        `--outdir` e depositar onde o operador mandar, e um symlink e so mais
        uma forma legitima de nomear esse lugar. `resolve()` converte para o
        caminho real; e esse caminho real, nao o link, que recebe os arquivos
        e aparece na mensagem "artefatos provados copiados para ..." -- o
        operador nunca fica sem saber onde os artefatos foram parar."""
        target = tmp_path / "real_target"
        target.mkdir()
        link = tmp_path / "link_to_target"
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks exigem privilegio neste ambiente Windows")
        resolved = verify_wheel.safe_outdir(link)
        assert resolved == target.resolve()


class TestArtifactDest:
    """`_artifact_dest` e a segunda metade da guarda: o unico componente
    concatenado ao `outdir` ja resolvido e um basename provado. Os testes
    abaixo usam um `SimpleNamespace` no lugar de `Path` para poder forjar um
    `.name` malicioso -- um `Path` de verdade nunca produziria `.name` com
    separador, mas a funcao nao confia nisso, e o teste prova exatamente essa
    desconfianca."""

    def test_joins_outdir_and_basename(self, tmp_path):
        outdir = tmp_path / "out"
        artifact = Path("/build/dist/sparkforge_aws-0.5.0-py3-none-any.whl")
        dest = verify_wheel._artifact_dest(outdir, artifact)
        assert dest == outdir / "sparkforge_aws-0.5.0-py3-none-any.whl"

    def test_refuses_a_name_containing_a_forward_slash(self):
        fake = SimpleNamespace(name="sub/evil.whl")
        with pytest.raises(SystemExit):
            verify_wheel._artifact_dest(Path("/out"), fake)

    def test_refuses_a_name_containing_a_backslash(self):
        fake = SimpleNamespace(name="sub\\evil.whl")
        with pytest.raises(SystemExit):
            verify_wheel._artifact_dest(Path("/out"), fake)

    def test_refuses_dotdot_as_a_name(self):
        fake = SimpleNamespace(name="..")
        with pytest.raises(SystemExit):
            verify_wheel._artifact_dest(Path("/out"), fake)

    def test_refuses_an_empty_name(self):
        fake = SimpleNamespace(name="")
        with pytest.raises(SystemExit):
            verify_wheel._artifact_dest(Path("/out"), fake)
