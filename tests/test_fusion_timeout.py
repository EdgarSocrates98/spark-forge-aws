"""Passo 0 do simulate (§19): a derivacao de timeout ganha porta de producao.

Ate 2026-09-12 `extract_timeout_diagnosis` so era chamada por teste, e
`spark.timeout.*` so existia nos goldens. Agora `fusion.fuse()` a chama -- mas
so quando o pool tem um kind que ela le (`SOURCE_KINDS`), para que o `fuse` de
quem nao tem artefato de timeout continue igual.
"""
from __future__ import annotations

import json
from pathlib import Path

from sparkforge.facts import timeout_diagnosis
from sparkforge.facts.fusion import fuse
from sparkforge.findings.models import Fact

ROOT = Path(__file__).resolve().parents[1]
BROADCAST = ROOT / "fixtures" / "eventlog" / "broadcast_timeout_stage_failure" / "expected"
SQL = ROOT / "fixtures" / "fusion"


def _facts(caminho: Path) -> list[Fact]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return [Fact(**{k: v for k, v in d.items() if k != "id"}) for d in dados]


def _timeout(facts) -> list[Fact]:
    return [f for f in facts if f.kind.startswith("spark.timeout.")]


def test_fuse_produz_o_mesmo_timeout_que_o_extrator():
    pool = _facts(BROADCAST / "facts.json")
    esperado = timeout_diagnosis.extract_timeout_diagnosis(pool, "")
    produzido = _timeout(fuse(pool))
    assert esperado, "o caso de broadcast precisa produzir timeout"
    assert sorted(f.id for f in produzido) == sorted(f.id for f in esperado)


def test_pool_sem_kind_de_origem_nao_ganha_timeout():
    caminhos = sorted(SQL.glob("*/input/facts.json")) or sorted(SQL.glob("*/expected/facts.json"))
    for caminho in caminhos:
        pool = [f for f in _facts(caminho) if not f.kind.startswith("spark.timeout.")]
        assert not any(f.kind in timeout_diagnosis.SOURCE_KINDS for f in pool)
        assert _timeout(fuse(pool)) == [], caminho


def test_source_kinds_cobre_o_que_o_extrator_le():
    assert set(timeout_diagnosis._BASIS_POR_KIND) <= timeout_diagnosis.SOURCE_KINDS
    assert {"glue.job_run", "spark.conf_effective"} <= timeout_diagnosis.SOURCE_KINDS
