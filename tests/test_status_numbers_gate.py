"""O gate de lastro do `STATUS.md` reprova quando o numero publicado diverge.

Gate sem teste e promessa. Estes casos provam as tres coisas que
`scripts/check_status_numbers.py` afirma fazer: acusar divergencia, acusar linha
publicada sem produtor, e acusar medida orfa.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_status_numbers", ROOT / "scripts" / "check_status_numbers.py"
)
gate = importlib.util.module_from_spec(_spec)
sys.modules["check_status_numbers"] = gate
_spec.loader.exec_module(gate)


def _status_falso(tmp_path: Path, filas: str) -> Path:
    caminho = tmp_path / "STATUS.md"
    caminho.write_text(
        "# t\n\n## Números correntes\n\n"
        "| Dimensão | Valor | Onde conferir |\n|---|---|---|\n"
        f"{filas}\n"
        "## Fases\n",
        encoding="utf-8",
    )
    return caminho


def test_o_repositorio_de_verdade_passa():
    """O gate roda no corpo real e sai limpo, inclusive em `--strict`."""
    assert gate.auditar(strict=True) == []


def test_reprova_quando_o_numero_publicado_diverge(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "STATUS", _status_falso(tmp_path, "| Coisas | **7** | x |"))
    monkeypatch.setattr(gate, "MEDIDAS", {"Coisas": lambda: 9})
    monkeypatch.setattr(gate, "SEM_MEDIDA", {})
    problemas = gate.auditar()
    assert len(problemas) == 1
    assert "publica 7, medido 9" in problemas[0]


def test_nao_reprova_quando_bate(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "STATUS", _status_falso(tmp_path, "| Coisas | **9** | x |"))
    monkeypatch.setattr(gate, "MEDIDAS", {"Coisas": lambda: 9})
    monkeypatch.setattr(gate, "SEM_MEDIDA", {})
    assert gate.auditar() == []


def test_strict_reprova_linha_publicada_sem_produtor(tmp_path, monkeypatch):
    """O defeito que motivou o gate: `62 de 116` estava publicado apontando um
    teste que nunca contou nem 62 nem 116."""
    monkeypatch.setattr(gate, "STATUS", _status_falso(tmp_path, "| Orfa | **3** | prosa |"))
    monkeypatch.setattr(gate, "MEDIDAS", {})
    monkeypatch.setattr(gate, "SEM_MEDIDA", {})
    assert gate.auditar(strict=False) == []
    problemas = gate.auditar(strict=True)
    assert len(problemas) == 1
    assert "sem medida" in problemas[0]


def test_recusa_declarada_nao_reprova_em_strict(tmp_path, monkeypatch):
    """Recusa tem nome: dimensao em `SEM_MEDIDA` passa, e a razao fica escrita."""
    monkeypatch.setattr(gate, "STATUS", _status_falso(tmp_path, "| Cara | **3** | prosa |"))
    monkeypatch.setattr(gate, "MEDIDAS", {})
    monkeypatch.setattr(gate, "SEM_MEDIDA", {"Cara": "roda a suite inteira"})
    assert gate.auditar(strict=True) == []


def test_reprova_medida_sem_linha_na_tabela(tmp_path, monkeypatch):
    """Fail-closed nos dois sentidos, como `check_vnext_claims.py`: a dimensao
    sumiu do documento e a medida ficou."""
    monkeypatch.setattr(gate, "STATUS", _status_falso(tmp_path, "| Coisas | **9** | x |"))
    monkeypatch.setattr(gate, "MEDIDAS", {"Coisas": lambda: 9, "Sumida": lambda: 1})
    monkeypatch.setattr(gate, "SEM_MEDIDA", {})
    problemas = gate.auditar()
    assert len(problemas) == 1
    assert "Sumida" in problemas[0]


def test_le_o_primeiro_numero_da_coluna_valor():
    """O resto da celula e argumento, e argumento nao e alegacao. A celula de
    `Testes` carrega 8660, 7, 90, 8662 e 8572 -- so o primeiro e a alegacao."""
    assert gate._publicado("**8660** passando, **7** skipped, e antes eram 8572") == 8660
    assert gate._publicado("**105 de 140** têm `validation`") == 105
    assert gate._publicado("sem numero nenhum") is None


@pytest.mark.parametrize("dimensao", sorted(gate.MEDIDAS))
def test_toda_medida_tem_linha_no_status(dimensao):
    publicadas = {d for _, d, _ in gate.linhas_da_tabela()}
    assert dimensao in publicadas, f"`{dimensao}` mede algo que o STATUS.md nao publica"


@pytest.mark.parametrize("dimensao", sorted(gate.SEM_MEDIDA))
def test_toda_recusa_tem_linha_no_status(dimensao):
    """Recusa para dimensao que nao existe mais e recusa que envelheceu."""
    publicadas = {d for _, d, _ in gate.linhas_da_tabela()}
    assert dimensao in publicadas, f"`{dimensao}` esta em SEM_MEDIDA e nao esta no STATUS.md"


def test_toda_recusa_carrega_razao():
    vazias = [d for d, razao in gate.SEM_MEDIDA.items() if not (razao or "").strip()]
    assert not vazias, f"recusa sem razao escrita: {vazias}"
