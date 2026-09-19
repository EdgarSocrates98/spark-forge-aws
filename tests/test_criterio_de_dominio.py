"""Dominio entra por artefato coletavel, nunca por nome.

Uma area so existe com regra que julga fact emitido por extrator, e um coordenador so
existe com area que julga e com rota que um finding ou fact dispara. Criterio escrito
em docs/gates-por-mudanca.md, secao "Criterio de dominio: artefato antes de nome".
"""
import re
from pathlib import Path

import yaml

from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"

SAIRAM_AGENTES = (
    "sf-analytics-specialist",
    "sf-graph-specialist",
    "sf-neptune-specialist",
    "sf-orchestrator",
    "sf-pyspark-specialist",
    "sf-storage-specialist",
    "sf-token-verifier",
)
SAIRAM_SKILLS = (
    "agentic-orchestration",
    "analyze-analytics",
    "analyze-graph-data",
    "design-neptune-graph",
    "token-efficient-agent",
)
SDD_TOOLS = ("sparkforge_sdd_check", "sparkforge_sdd_status", "sparkforge_sdd_stamp")

SECAO = "## Critério de domínio: artefato antes de nome"
VIVOS = (
    "AGENTS.md",
    "docs/guia/05-agents-e-skills.md",
    "docs/guia/usos/iceberg-e-parquet.md",
    "docs/operations-guide.md",
    "docs/teams-catalog.md",
    "docs/vnext/AGENT-CATALOG.md",
    "docs/agentic-evolution.md",
    "knowledge/domain-tool-matrix.md",
    "knowledge/tool-specialization-matrix.md",
    "config/agents.yaml",
)


def _front(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1]) or {}


def _coordenadores() -> list[Path]:
    return sorted(AGENTS.glob("*.md"))


def _area(rule_id: str) -> str:
    return rule_id.rsplit("-", 1)[0]


def _areas_que_julgam() -> set[str]:
    return {
        _area(r["id"])
        for r in load_catalog()
        if r.get("executable", True) and not r.get("blocked_on")
    }


def _chaves(no) -> set[str]:
    if isinstance(no, dict):
        return set(no) | {k for v in no.values() for k in _chaves(v)}
    if isinstance(no, list):
        return {k for v in no for k in _chaves(v)}
    return set()


def _valores_de_caso(no) -> list[str]:
    if isinstance(no, dict):
        proprios = [str(no.get("contains", ""))] if "case" in no else []
        return proprios + [v for x in no.values() for v in _valores_de_caso(x)]
    if isinstance(no, list):
        return [v for x in no for v in _valores_de_caso(x)]
    return []


def _por_artefato(rota: dict) -> bool:
    when = rota.get("when")
    if _chaves(when) & {"findings_area", "fact"}:
        return True
    casos = _valores_de_caso(when)
    return bool(casos) and not any(re.fullmatch(r"__\w+__", c) for c in casos)


def _rotas() -> list[dict]:
    texto = (ROOT / "rules" / "catalog" / "routing.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(texto)["rules"]


def test_catalogo_nao_tem_area_de_coordenacao():
    inertes = [r["id"] for r in load_catalog() if r.get("executable", True) is False]
    assert not inertes, inertes


def test_toda_area_tem_regra_que_julga():
    todas = {_area(r["id"]) for r in load_catalog()}
    sem = sorted(todas - _areas_que_julgam())
    assert not sem, sem


def test_todo_coordenador_declara_area_que_julga():
    julgam = _areas_que_julgam()
    todas = {_area(r["id"]) for r in load_catalog()}
    for path in _coordenadores():
        areas = set(_front(path).get("rule_areas") or [])
        assert areas & julgam, path.name
        assert areas <= todas, (path.name, sorted(areas - todas))


def test_todo_coordenador_tem_rota_por_artefato():
    por_artefato = {rota.get("recommended_agent") for rota in _rotas() if _por_artefato(rota)}
    sem = sorted(p.stem for p in _coordenadores() if p.stem not in por_artefato)
    assert not sem, sem


def test_o_que_so_o_nome_alcancava_saiu():
    presentes = {p.stem for p in _coordenadores()}
    assert presentes.isdisjoint(SAIRAM_AGENTES), sorted(presentes & set(SAIRAM_AGENTES))
    skills = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}
    assert skills.isdisjoint(SAIRAM_SKILLS), sorted(skills & set(SAIRAM_SKILLS))
    arquiteto = (AGENTS / "spark-performance-architect.md").read_text(encoding="utf-8")
    faltam = [t for t in SDD_TOOLS if t not in arquiteto]
    assert not faltam, faltam


def test_criterio_escrito_e_apontado():
    gates = (ROOT / "docs" / "gates-por-mudanca.md").read_text(encoding="utf-8")
    assert SECAO in gates
    inicio = gates.index(SECAO)
    fim = gates.find("\n## ", inicio + 1)
    secao = gates[inicio:fim]
    assert "tests/test_criterio_de_dominio.py" in secao
    for arquivo in ("CLAUDE.md", "AGENTS.md"):
        texto = (ROOT / arquivo).read_text(encoding="utf-8")
        assert "docs/gates-por-mudanca.md" in texto and "artefato" in texto.lower(), arquivo


def test_documento_vivo_nao_cita_o_que_saiu():
    for rel in VIVOS:
        texto = (ROOT / rel).read_text(encoding="utf-8")
        citados = [
            nome
            for nome in SAIRAM_AGENTES + SAIRAM_SKILLS
            if re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", texto)
        ]
        assert not citados, (rel, citados)
