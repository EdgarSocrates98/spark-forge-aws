"""Gate da matriz de conformidade MCP — `evals/mcp-conformance/matrix.yaml`.

A matriz afirma, por requisito do protocolo, um status do vocabulario
fechado. Toda linha `covered` precisa nomear evidencia REAL: `arquivo::teste`
que existe em `tests/` — afirmacao sem prova reprova aqui, que e o motivo da
matriz existir.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "evals" / "mcp-conformance" / "matrix.yaml"

STATUSES = {"covered", "delegated_to_sdk", "unresolved", "not_applicable"}
EVIDENCIA = re.compile(r"^(?P<arquivo>tests/[^:]+)::(?P<teste>[A-Za-z0-9_:.\[\]-]+)$")


@pytest.fixture(scope="module")
def matriz() -> dict:
    return yaml.safe_load(MATRIX.read_text(encoding="utf-8"))


def test_matrix_bem_formada(matriz: dict) -> None:
    assert matriz["schema_version"] == 1
    assert matriz["protocol_eras"]
    reqs = matriz["requirements"]
    assert reqs, "matriz sem requisitos"
    ids = [r["id"] for r in reqs]
    assert len(ids) == len(set(ids)), "id duplicado"
    for r in reqs:
        assert set(r) >= {"id", "requirement", "status", "evidence"}, r["id"]
        assert r["status"] in STATUSES, r["id"]
        assert isinstance(r["evidence"], list), r["id"]


def _teste_existe(arquivo: str, teste: str) -> bool:
    path = ROOT / arquivo
    if not path.is_file():
        return False
    texto = path.read_text(encoding="utf-8")
    # `Classe::teste` ou `teste` direto; parametrizacao `[x]` nao entra.
    partes = teste.split("::")
    nome = partes[-1].split("[")[0]
    if len(partes) > 1:
        classe = partes[-2]
        if re.search(rf"^class {re.escape(classe)}\b", texto, re.M) is None:
            return False
    return re.search(rf"def {re.escape(nome)}\b", texto) is not None


def test_toda_evidencia_aponta_teste_real(matriz: dict) -> None:
    for r in matriz["requirements"]:
        for ref in r["evidence"]:
            m = EVIDENCIA.match(ref)
            assert m, f"{r['id']}: evidencia malformada {ref!r}"
            assert _teste_existe(m["arquivo"], m["teste"]), (
                f"{r['id']}: {ref} nao existe"
            )


def test_covered_sempre_tem_evidencia(matriz: dict) -> None:
    for r in matriz["requirements"]:
        if r["status"] == "covered":
            assert r["evidence"], f"{r['id']}: covered sem evidencia"


def test_status_nao_covered_declara_motivo(matriz: dict) -> None:
    for r in matriz["requirements"]:
        if r["status"] != "covered":
            assert r.get("note"), f"{r['id']}: {r['status']} sem nota"


def test_matriz_nao_e_tudo_covered_nem_tudo_delegado(matriz: dict) -> None:
    """Uma matriz 100% covered ou 0% seria suspeita — declaracao honesta mistura."""
    statuses = {r["status"] for r in matriz["requirements"]}
    assert "covered" in statuses
    assert statuses - {"covered"}, "sem nenhuma lacuna/delegacao declarada"
