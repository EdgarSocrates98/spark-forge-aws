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
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import verify_wheel  # noqa: E402
from scripts.verify_wheel import GOLDEN_MODULES, main, pytest_command  # noqa: E402


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
        on_disk = {p.name for p in (ROOT / "tests").glob("test_fixtures_golden*.py")}
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


def _prep_fake_workdir(tmp_path: Path, monkeypatch) -> Path:
    """Prepara um workdir com wheel e sdist ja presentes, e faz
    `tempfile.mkdtemp` devolve-lo.

    O passo de build e sempre mockado por `_FakeRun` (nunca roda de verdade),
    entao os artefatos que `main()` procura via glob apos o build precisam
    existir de antemao -- senao todo teste alem do build cairia na checagem
    "esperava wheel e sdist em ..." em vez de exercitar o caminho pretendido.
    """
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "sparkforge_aws-0.0.0-py3-none-any.whl").write_bytes(b"")
    (dist / "sparkforge_aws-0.0.0.tar.gz").write_bytes(b"")
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix="": str(tmp_path))
    return tmp_path


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
    desta classe, isso so tinha sido observado rodando o gate de verdade."""

    def test_build_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=0))
        assert main([]) == 1

    def test_venv_creation_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=1))
        assert main([]) == 1

    def test_wheel_install_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=2))
        assert main([]) == 1

    def test_golden_pytest_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=3))
        assert main([]) == 1

    def test_twine_install_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=4))
        assert main([]) == 1

    def test_twine_check_failure_returns_1(self, monkeypatch, tmp_path):
        _prep_fake_workdir(tmp_path, monkeypatch)
        monkeypatch.setattr(verify_wheel, "_run", _FakeRun(fail_at=5))
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


class TestOutdir:
    """`--outdir` e a correcao do buraco apontado na revisao da Task 8: sem
    ele, o unico exemplar provado pelos 539 testes de golden e apagado no
    `finally` (o workdir e temporario), e quem publica reconstroi do zero --
    um IRMAO do artefato provado, nunca comprovadamente o mesmo, porque nada
    neste repositorio fixa `SOURCE_DATE_EPOCH`."""

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
