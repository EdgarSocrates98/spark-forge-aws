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
