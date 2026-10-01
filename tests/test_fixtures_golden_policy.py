"""Golden do hook `PreToolUse` da policy (§16), por subprocess.

Cada caso de `fixtures/policy/` e uma raiz (`CLAUDE_PROJECT_DIR`) com
`.sparkforge/policy.yaml` (ou sem ela), o `input.json` que o Claude Code manda
no stdin e o `expected.json` com o codigo de saida e o que o stderr diz.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "policy"
CASOS = sorted(p.name for p in FIXTURES.iterdir() if (p / "input.json").is_file())


def _rodar(caso: str) -> tuple[subprocess.CompletedProcess, float]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(FIXTURES / caso)}
    inicio = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "sparkforge.policy.hook"],
        input=(FIXTURES / caso / "input.json").read_text(encoding="utf-8"),
        capture_output=True, text=True, env=env, cwd=str(FIXTURES / caso), timeout=60,
    )
    return proc, time.perf_counter() - inicio


@pytest.mark.parametrize("caso", CASOS)
def test_golden(caso):
    esperado = json.loads((FIXTURES / caso / "expected.json").read_text(encoding="utf-8"))
    proc, _ = _rodar(caso)
    assert proc.returncode == esperado["exit_code"], proc.stderr
    assert proc.stdout == ""
    for trecho in esperado["stderr_contains"]:
        assert trecho in proc.stderr, (trecho, proc.stderr)
    if esperado["exit_code"] == 0:
        assert proc.stderr == ""


def test_hook_nao_importa_o_catalogo_de_tools():
    """O hook roda em todo Bash; importar `sparkforge.adapters` custa ~0,5 s."""
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys, sparkforge.policy.hook as h, sparkforge.policy.decide, "
         "sparkforge.policy.load; print(any(m.startswith('sparkforge.adapters') "
         "for m in sys.modules))"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.stdout.strip() == "False", proc.stderr


def test_hook_e_rapido():
    """SC3 mede < 0,2 s por chamada; o teste folga para maquina de CI lenta."""
    tempos = sorted(_rodar(caso)[1] for caso in CASOS)
    assert tempos[len(tempos) // 2] < 1.0, tempos
