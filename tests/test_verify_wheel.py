# tests/test_verify_wheel.py
"""Testes do orquestrador do gate.

O gate em si constroi artefato e cria venv -- caro demais para a suite. Aqui se
prova a MONTAGEM do comando, que e onde os erros silenciosos moram: um
`-o pythonpath=` esquecido faz o pytest do venv importar o repositorio, e o gate
inteiro vira teatro.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_wheel import GOLDEN_MODULES, pytest_command  # noqa: E402


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
