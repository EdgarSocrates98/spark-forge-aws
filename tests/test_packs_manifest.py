"""Manifesto do Forge Pack: faixa de versao e recusas do `pack.yaml`."""
from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.packs.manifest import (
    PackRefused,
    check_core,
    dentro_da_faixa,
    installed_version,
    read_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "instalada, faixa, ok",
    [
        ("0.5.0", ">=0.5,<1.0", True),
        ("1.0.0", ">=0.5,<1.0", False),
        ("0.5", ">=0.5.0", True),
        ("0.4.9", ">0.4.9", False),
        ("2.0", "==2", True),
        ("0.5.1", "<=0.5", False),
    ],
)
def test_faixa(instalada, faixa, ok):
    assert dentro_da_faixa(instalada, faixa) is ok


def _pack(tmp_path: Path, texto: str) -> Path:
    (tmp_path / "pack.yaml").write_text(texto, encoding="utf-8")
    return tmp_path


BOM = "pack:\n  id: acme\n  version: 1.0.0\n  prefix: ACME\n  core: '>=0.5'\n"


def test_manifesto_bom(tmp_path):
    manifesto = read_manifest(_pack(tmp_path, BOM))
    assert (manifesto.id, manifesto.prefix, manifesto.core) == ("acme", "ACME", ">=0.5")


@pytest.mark.parametrize(
    "texto, motivo",
    [
        (BOM.replace("  prefix: ACME\n", ""), "manifesto_invalido"),
        (BOM.replace("id: acme", "id: Acme"), "manifesto_invalido"),
        (BOM.replace("1.0.0", "1.0.0rc1"), "manifesto_invalido"),
        (BOM.replace("'>=0.5'", "'~=0.5'"), "manifesto_invalido"),
        (BOM.replace("prefix: ACME", "prefix: acme"), "manifesto_invalido"),
        ("pack: [lista]\n", "manifesto_invalido"),
        ("pack: {id: [\n", "manifesto_invalido"),
        (BOM.replace("prefix: ACME", "prefix: SF"), "prefixo_reservado"),
    ],
)
def test_manifesto_recusado(tmp_path, texto, motivo):
    with pytest.raises(PackRefused) as erro:
        read_manifest(_pack(tmp_path, texto))
    assert erro.value.reason == motivo


def test_sem_pack_yaml_e_manifesto_invalido(tmp_path):
    with pytest.raises(PackRefused) as erro:
        read_manifest(tmp_path)
    assert erro.value.reason == "manifesto_invalido"


def test_core_incompativel_nomeia_a_versao(tmp_path):
    manifesto = read_manifest(_pack(tmp_path, BOM.replace("'>=0.5'", "'>=9.0'")))
    with pytest.raises(PackRefused) as erro:
        check_core(manifesto, "0.5.0")
    assert erro.value.reason == "core_incompativel" and "0.5.0" in erro.value.detail


def test_versao_desconhecida_e_incompativel(tmp_path):
    with pytest.raises(PackRefused) as erro:
        check_core(read_manifest(_pack(tmp_path, BOM)), None)
    assert "desconhecida" in erro.value.detail


def test_versao_e_a_do_codigo_carregado():
    """No repositorio, a versao vem do `pyproject.toml` do mesmo codigo, e nao de
    uma dist-info que o `sys.path` achar primeiro (medido: 0.4.0 velha)."""
    texto = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{installed_version()}"' in texto
