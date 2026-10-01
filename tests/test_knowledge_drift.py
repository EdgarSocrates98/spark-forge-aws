"""Knowledge Drift Radar: estados, saltos, sem repositorio e a secao do refresh."""
from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

from sparkforge.knowledge_drift import RepoIndex, build_index, drift, render_markdown, repo_root

ROOT = Path(__file__).resolve().parents[1]
URL = "https://exemplo.invalid/doc"
OUTRA = "https://exemplo.invalid/outra"
DIA = date(2026, 9, 13)
ENTRADA = {"changed_at": "2026-09-09", "checked_at": "2026-09-09", "sha256": "x", "pinned": False}
LOCK = {URL: ENTRADA}
INDICE = RepoIndex(
    goldens={"SF-LF-001": frozenset({"infra_code/a"})},
    evals={"SF-LF-001": frozenset({"evals/x.yaml"})},
    agent_areas={"agents/lf.md": frozenset({"SF-LF"}), "agents/outro.md": frozenset({"SF-PY"})},
    agent_citations={"SF-ERR-017": frozenset({"agents/y.md"})},
)


def _regra(rule_id, retrieved, url=URL):
    fonte = {"url": url} if retrieved is None else {"url": url, "retrieved": retrieved}
    return {"id": rule_id, "sources": [fonte]}


def _unica(saida):
    [fonte] = saida["changed_sources"]
    return fonte


def test_lida_antes_da_mudanca_e_stale_e_entra_no_impacto():
    fonte = _unica(drift(LOCK, None, [_regra("SF-LF-001", "2026-08-22")], {}, INDICE, DIA))
    assert fonte["citations"][0]["state"] == "stale"
    assert fonte["impact"] == {
        "rules": ["SF-LF-001"],
        "docs": [],
        "goldens": ["infra_code/a"],
        "evals": ["evals/x.yaml"],
        "agents": ["agents/lf.md"],
    }


def test_lida_depois_e_revalidada_e_fica_fora_do_impacto():
    fonte = _unica(drift(LOCK, None, [_regra("SF-LF-001", "2026-09-10")], {}, INDICE, DIA))
    assert fonte["impact"]["rules"] == [] and fonte["revalidated"] == ["SF-LF-001"]


def test_lida_no_dia_da_mudanca_ja_e_revalidada():
    fonte = _unica(drift(LOCK, None, [_regra("SF-LF-001", "2026-09-09")], {}, INDICE, DIA))
    assert fonte["revalidated"] == ["SF-LF-001"]


def test_regra_sem_data_de_leitura_e_stale():
    fonte = _unica(drift(LOCK, None, [_regra("SF-LF-001", None)], {}, INDICE, DIA))
    assert fonte["citations"][0]["retrieved"] is None and fonte["impact"]["rules"] == ["SF-LF-001"]


def test_fonte_fixa_por_versao_nunca_entra():
    lock = {URL: {**LOCK[URL], "pinned": True}}
    saida = drift(lock, None, [_regra("SF-LF-001", "2026-08-22")], {}, INDICE, DIA)
    assert saida["changed_sources"] == [] and saida["lock"]["changed"] == 0


def test_documento_e_citacao_e_entra_no_impacto():
    docs = {"knowledge/glue/x.md": {URL: ["2026-08-01", "2026-09-10"]}}
    fonte = _unica(drift(LOCK, None, [], docs, INDICE, DIA))
    assert fonte["citations"] == [
        {"kind": "doc", "id": "knowledge/glue/x.md", "retrieved": "2026-08-01",
         "state": "stale", "reason": "mudou_depois_da_validacao"}
    ]
    assert fonte["impact"]["docs"] == ["knowledge/glue/x.md"]


def test_agente_por_citacao_e_por_area():
    fonte = _unica(drift(LOCK, None, [_regra("SF-ERR-017", "2026-08-22")], {}, INDICE, DIA))
    assert fonte["impact"]["agents"] == ["agents/y.md"]


def test_sem_repositorio_os_tres_saltos_sao_unresolved():
    saida = drift(LOCK, None, [_regra("SF-LF-001", "2026-08-22")], {}, None, DIA)
    fonte = _unica(saida)
    assert fonte["impact"]["rules"] == ["SF-LF-001"]
    assert fonte["impact"]["goldens"] is None and fonte["impact"]["agents"] is None
    assert saida["unresolved"] == [
        {"field": campo, "reason": "sem_repositorio"} for campo in ("goldens", "evals", "agents")
    ]


def test_lock_ausente_nao_derruba():
    saida = drift(None, "lock_ausente", [], {}, INDICE, DIA)
    assert saida["changed_sources"] == []
    assert saida["unresolved"] == [{"field": "lock", "reason": "lock_ausente"}]


def test_filtro_por_url():
    lock = {**LOCK, OUTRA: LOCK[URL]}
    regras = [_regra("SF-LF-001", "2026-08-22"), _regra("SF-PY-001", "2026-08-22", OUTRA)]
    saida = drift(lock, None, regras, {}, INDICE, DIA, url=OUTRA)
    assert [f["url"] for f in saida["changed_sources"]] == [OUTRA]


def test_recusa_sempre_presente():
    saida = drift({}, None, [], {}, INDICE, DIA)
    assert saida["refused"] == [
        {"field": "conteudo_da_mudanca", "reason": "exige_leitura_humana_da_fonte"}
    ]


def test_totais_sao_distintos_entre_fontes():
    lock = {**LOCK, OUTRA: LOCK[URL]}
    regras = [
        {"id": "SF-LF-001", "sources": [
            {"url": URL, "retrieved": "2026-08-22"}, {"url": OUTRA, "retrieved": "2026-08-22"}]}
    ]
    saida = drift(lock, None, regras, {}, INDICE, DIA)
    assert saida["totals"]["rules"] == 1 and saida["totals"]["goldens"] == 1


def test_repo_root_e_a_raiz_do_checkout():
    assert repo_root() == ROOT


def test_indice_do_repositorio_bate_com_os_findings_esperados():
    """Ida e volta contra uma varredura independente dos `expected/findings.json`."""
    indice = build_index(ROOT)
    esperado: dict[str, set[str]] = {}
    for caminho in (ROOT / "fixtures").rglob("expected/findings.json"):
        caso = caminho.parent.parent.relative_to(ROOT / "fixtures").as_posix()
        for achado in json.loads(caminho.read_text(encoding="utf-8")):
            esperado.setdefault(achado["rule_id"], set()).add(caso)
    assert {r: set(c) for r, c in indice.goldens.items()} == esperado


def test_agentes_do_repositorio_declaram_a_area():
    indice = build_index(ROOT)
    for agente in indice.agents_of("SF-LF-001"):
        texto = (ROOT / agente).read_text(encoding="utf-8")
        assert "SF-LF" in texto


def _script_refresh():
    spec = importlib.util.spec_from_file_location(
        "refresh_knowledge", ROOT / "scripts" / "refresh_knowledge.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_relatorio_do_refresh_traz_a_mesma_secao():
    payload = drift(LOCK, None, [_regra("SF-LF-001", "2026-08-22")], {}, INDICE, DIA)
    relatorio = _script_refresh().render_report([], {}, "2026-09-13", payload)
    assert render_markdown(payload) in relatorio
    assert "1 rules" in relatorio and "1 goldens" in relatorio


def test_relatorio_sem_impacto_e_o_de_antes():
    modulo = _script_refresh()
    assert "## Impacto" not in modulo.render_report([], {}, "2026-09-13")
