"""Carga do Forge Pack: variavel, recusas, catalogo, verbos, knowledge e freshness."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from sparkforge.adapters import _core
from sparkforge.adapters._core import AdapterError
from sparkforge.packs import ENV, load_pack, resolve
from sparkforge.rules.loader import CatalogError, catalog_dir, load_catalog

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "fixtures" / "packs"
ACME = PACKS / "acme-platform"
TIMEOUT_48H = ROOT / "fixtures" / "terraform" / "max_capacity_conflict" / "expected" / "facts.json"


@pytest.fixture
def sem_pack(monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    monkeypatch.delenv("SPARKFORGE_SOURCES_LOCK", raising=False)


@pytest.fixture
def com_acme(monkeypatch, sem_pack):
    monkeypatch.setenv(ENV, str(ACME))


def _ids(regras):
    return [str(r["id"]) for r in regras]


def test_sem_variavel_nao_ha_pack(sem_pack):
    conjunto = resolve()
    assert conjunto.active == () and conjunto.refused == ()


def test_sem_variavel_o_catalogo_e_o_do_core(sem_pack):
    assert _ids(load_catalog()) == _ids(load_catalog(catalog_dir()))


def test_pack_acrescenta_as_regras_dele(com_acme):
    core = _ids(load_catalog(catalog_dir()))
    todas = _ids(load_catalog())
    assert set(todas) - set(core) == {"ACME-GOV-001", "ACME-GOV-002"}
    assert len(todas) == len(core) + 2


@pytest.mark.parametrize(
    "nome, motivo",
    [
        ("recusa_prefixo_reservado", "prefixo_reservado"),
        ("recusa_manifesto_invalido", "manifesto_invalido"),
        ("recusa_core_incompativel", "core_incompativel"),
        ("recusa_id_fora_do_prefixo", "id_fora_do_prefixo"),
        ("recusa_regra_invalida", "regra_invalida"),
        ("recusa_id_duplicado", "id_duplicado"),
    ],
)
def test_cada_recusa(nome, motivo):
    conjunto = resolve([PACKS / nome])
    assert conjunto.active == ()
    assert [r["reason"] for r in conjunto.refused] == [motivo]


def test_prefixo_repetido_e_pack_duplicado():
    conjunto = resolve([ACME, PACKS / "recusa_prefixo_duplicado"])
    assert [p.id for p in conjunto.active] == ["acme-platform"]
    assert conjunto.refused[0]["reason"] == "pack_duplicado"


def test_mesmo_pack_duas_vezes_e_pack_duplicado():
    conjunto = resolve([ACME, ACME])
    assert len(conjunto.active) == 1 and conjunto.refused[0]["reason"] == "pack_duplicado"


def test_pack_recusado_nao_entra_no_catalogo(monkeypatch, sem_pack):
    monkeypatch.setenv(ENV, str(PACKS / "recusa_id_duplicado"))
    assert not [i for i in _ids(load_catalog()) if i.startswith("DUP-")]


def test_diretorio_inexistente_levanta(monkeypatch, sem_pack, tmp_path):
    monkeypatch.setenv(ENV, str(tmp_path / "nao-existe"))
    with pytest.raises(CatalogError, match="nao-existe"):
        load_catalog()
    with pytest.raises(AdapterError) as erro:
        _core.pack_list()
    assert erro.value.exit_code == 2


def test_rules_que_aponta_para_fora_do_pack_e_recusado(tmp_path):
    """`rules/` symlink para fora: a varredura nunca anda fora do pack."""
    pack = tmp_path / "pack"
    shutil.copytree(ACME, pack, ignore=shutil.ignore_patterns("rules"))
    fora = tmp_path / "fora"
    shutil.copytree(ACME / "rules", fora)
    try:
        (pack / "rules").symlink_to(fora, target_is_directory=True)
    except OSError:
        pytest.skip("o sistema nao deixa criar symlink aqui")
    conjunto = resolve([pack])
    assert conjunto.active == ()
    assert conjunto.refused[0]["reason"] == "regra_invalida"
    assert "fora do pack" in conjunto.refused[0]["detail"]


def test_regra_de_pack_carrega_a_origem():
    regra = load_pack(ACME).rules[0]
    assert regra["_pack"] == "acme-platform"
    assert regra["_source_file"] == "packs/acme-platform/rules/plataforma.yaml"


def test_origem_do_finding_pelo_prefixo():
    conjunto = resolve([ACME])
    assert conjunto.pack_of("ACME-GOV-001").id == "acme-platform"
    assert conjunto.pack_of("SF-GLUE-003") is None
    assert conjunto.prefixes() == {"ACME": "acme-platform"}


def _rule_ids(saida):
    return {f["rule_id"] for f in saida["items"]}


def test_judge_ve_o_pack_e_nao_mexe_no_core(monkeypatch, sem_pack):
    sem = _rule_ids(_core.judge_findings(facts_path=str(TIMEOUT_48H), limit=None))
    monkeypatch.setenv(ENV, str(ACME))
    com = _rule_ids(_core.judge_findings(facts_path=str(TIMEOUT_48H), limit=None))
    assert com - sem == {"ACME-GOV-002"}
    assert {r for r in com if r.startswith("SF-")} == sem


def test_root_cause_ve_o_pack(com_acme):
    saida = _core.root_cause(facts_path=str(TIMEOUT_48H))
    assert "ACME-GOV-002" in {c["rule_id"] for c in saida["candidates"]}


def test_rules_lookup_nao_publica_metadado_de_carga(com_acme):
    [regra] = _core.rules_lookup(id=["ACME-GOV-001"])["rules"]
    assert not [chave for chave in regra if chave.startswith("_")]


URL = "https://example.com/acme/padroes-de-plataforma"


def test_fonte_de_pack_sem_lock(com_acme):
    saida = _core.rules_lookup(id=["ACME-GOV-001"], source_freshness=True, as_of="2026-09-12")
    assert saida["source_freshness"][URL] == {"state": "unresolved", "reason": "pack_sem_lock"}


def test_fonte_de_pack_com_lock_do_pack(monkeypatch, sem_pack, tmp_path):
    pack = tmp_path / "acme"
    shutil.copytree(ACME, pack)
    entrada = {"sha256": "x", "checked_at": "2026-09-10", "retrieved": ["2026-09-12"]}
    lock = {"sources": {URL: entrada}}
    (pack / "knowledge" / "sources.lock.json").write_text(json.dumps(lock), encoding="utf-8")
    monkeypatch.setenv(ENV, str(pack))
    saida = _core.rules_lookup(id=["ACME-GOV-001"], source_freshness=True, as_of="2026-09-12")
    assert saida["source_freshness"][URL]["state"] == "fresh"


def test_fonte_do_core_continua_no_lock_do_core(monkeypatch, sem_pack):
    sem = _core.rules_lookup(id=["SF-GLUE-003"], source_freshness=True, as_of="2026-09-12")
    monkeypatch.setenv(ENV, str(ACME))
    com = _core.rules_lookup(id=["SF-GLUE-003"], source_freshness=True, as_of="2026-09-12")
    assert com["source_freshness"] == sem["source_freshness"]


def test_knowledge_do_pack_em_chave_propria(monkeypatch, sem_pack):
    core = _core.knowledge_path()
    assert "packs" not in core
    monkeypatch.setenv(ENV, str(ACME))
    com = _core.knowledge_path(file="packs/acme-platform/padroes-de-plataforma.md")
    assert com["available"] == core["available"]
    assert com["packs"][0]["available"] == ["padroes-de-plataforma.md"]
    assert com["file"].endswith("padroes-de-plataforma.md")


def test_knowledge_do_pack_confinado(com_acme):
    with pytest.raises(AdapterError):
        _core.knowledge_path(file="packs/acme-platform/../pack.yaml")
