"""`python -m sparkforge_aws` propaga o exit code do CLI (cycle-16.1.1 wave-03).

Antes `__main__.py` chamava `main()` sem `SystemExit` — recusas governadas
e erros de argparse saíam com `rc=0`, escondendo falhas de hosts que
lançam o pacote via `-m`.
"""
from __future__ import annotations

import subprocess
import sys


def _run_module(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — argv fixo, interpretador atual
        [sys.executable, "-m", "sparkforge_aws", *argv],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_module_help_sai_zero():
    proc = _run_module("--help")
    assert proc.returncode == 0
    assert "sparkforge-aws" in proc.stdout


def test_module_verbo_invalido_nao_sai_zero():
    proc = _run_module("bogus-verb-cycle1611")
    assert proc.returncode == 2
    assert "invalid choice" in proc.stderr


def test_module_flag_invalida_nao_sai_zero():
    """Erro de validação do parser também propaga rc != 0 via `-m`."""
    proc = _run_module("install", "--profile", "bogus-cycle1611")
    assert proc.returncode == 2
