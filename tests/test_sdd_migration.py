"""SDD_MIGRATION: o processo trocado sem apagar a historia.

Cada teste cobre um criterio de `docs/sdd/SDD_MIGRATION/define.md`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rastreados(prefixo: str) -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", prefixo], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [linha for linha in saida.stdout.splitlines() if linha]


def test_agentspec_desligado_no_projeto():
    config = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert config["enabledPlugins"]["agentspec@agentspec"] is False


def test_historico_agentspec_arquivado():
    assert _rastreados(".claude/sdd") == []
    arquivados = _rastreados("docs/sdd/archive/agentspec")
    assert any(p.endswith("DESIGN_DEBATE_ROI_GATE.md") for p in arquivados)
    assert ".claude/sdd/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_superpowers_congelado():
    texto = (ROOT / "docs" / "superpowers" / "README.md").read_text(encoding="utf-8")
    assert "congelad" in texto
    assert "docs/sdd/" in texto
    assert (ROOT / "docs" / "superpowers" / "STATUS.md").is_file()


def test_documentos_de_entrada_apontam_o_sdd():
    for nome in ("CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md"):
        texto = (ROOT / nome).read_text(encoding="utf-8")
        assert "sdd-define" in texto, nome
        assert "sparkforge sdd check" in texto, nome
        assert "fluxo SDD em `.claude/sdd/`" not in texto, nome
