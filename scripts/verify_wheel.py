#!/usr/bin/env python3
"""Gate do artefato: o pacote instalado reproduz os goldens byte a byte?

Constroi sdist e wheel, instala o wheel num venv limpo, e roda os modulos de
golden ja existentes SOB O PYTHON DO VENV. Se o pacote instalado produz os
mesmos facts e findings que o repositorio, o canal pip esta em paridade.

Por que reaproveitar os modulos de golden em vez de reimplementar a comparacao:
as 74 fixtures ja sao o contrato, verificado no CI a cada commit. Um comparador
proprio seria um segundo contrato para manter divergir do primeiro -- e o
primeiro a divergir seria o novo, porque ninguem o le.

A guarda que sustenta tudo esta em `tests/test_installed_provenance.py`, ligada
aqui por `SPARKFORGE_VERIFY_INSTALLED=1`. Sem ela, um `sys.path` errado faria o
pytest importar o repositorio e comparar o codigo-fonte consigo mesmo.

Uso:
    python scripts/verify_wheel.py                # constroi, instala e verifica
    python scripts/verify_wheel.py --keep         # nao apaga o diretorio temporario
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GOLDEN_MODULES = sorted(p.name for p in (ROOT / "tests").glob("test_fixtures_golden*.py"))
PROVENANCE_MODULE = "test_installed_provenance.py"


def venv_python(venv: Path) -> Path:
    """Interpretador do venv, nos dois layouts."""
    windows = venv / "Scripts" / "python.exe"
    return windows if windows.exists() else venv / "bin" / "python"


def pytest_command(python: Path, root: Path) -> list[str]:
    """Comando do gate.

    `-o pythonpath=` sobrescreve o `pythonpath = ["."]` do pyproject. Sem isso o
    repositorio entra no sys.path e vence o site-packages -- e o gate passaria
    comparando o repo consigo mesmo.

    A procedencia vem PRIMEIRO: se o import veio do lugar errado, comparar
    golden nao significa nada.
    """
    modules = [str(root / "tests" / PROVENANCE_MODULE)]
    modules += [str(root / "tests" / name) for name in GOLDEN_MODULES]
    return [str(python), "-m", "pytest", "-q", "-o", "pythonpath=", *modules]


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    printable = " ".join(str(c) for c in command)
    print(f"$ {printable}", flush=True)
    return subprocess.run(command, check=False, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--keep", action="store_true", help="Nao apaga o diretorio temporario.")
    args = parser.parse_args(argv)

    workdir = Path(tempfile.mkdtemp(prefix="sparkforge-gate-"))
    dist = workdir / "dist"
    venv = workdir / "venv"

    try:
        if _run([sys.executable, "-m", "build", "--outdir", str(dist), str(ROOT)]).returncode:
            print("build falhou", file=sys.stderr)
            return 1

        wheels = sorted(dist.glob("*.whl"))
        sdists = sorted(dist.glob("*.tar.gz"))
        if not wheels or not sdists:
            print(f"esperava wheel e sdist em {dist}, achei {[p.name for p in dist.iterdir()]}",
                  file=sys.stderr)
            return 1

        if _run([sys.executable, "-m", "venv", str(venv)]).returncode:
            return 1

        python = venv_python(venv)
        install = [str(python), "-m", "pip", "install", "--quiet", str(wheels[0]), "pytest"]
        if _run(install).returncode:
            return 1

        # `cwd` fora do repositorio e a primeira guarda; a assercao de
        # procedencia e a que sustenta. As duas, porque configuracao se perde.
        env = dict(os.environ)
        env["SPARKFORGE_VERIFY_INSTALLED"] = "1"
        env["PYTHONSAFEPATH"] = "1"
        env.pop("SPARKFORGE_CATALOG", None)
        env.pop("SPARKFORGE_KNOWLEDGE", None)

        result = _run(pytest_command(python, ROOT), cwd=str(workdir), env=env)
        if result.returncode:
            print("gate de paridade REPROVOU", file=sys.stderr)
            return 1

        if _run([str(python), "-m", "pip", "install", "--quiet", "twine"]).returncode:
            return 1
        if _run([str(python), "-m", "twine", "check", str(wheels[0]), str(sdists[0])]).returncode:
            print("twine check reprovou", file=sys.stderr)
            return 1

        print(f"\nOK: {wheels[0].name} e {sdists[0].name} em paridade com os goldens.")
        return 0
    finally:
        if args.keep:
            print(f"artefatos preservados em {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
