"""A camada sf-* sem area oca: o catalogo so julga, e o conteudo real mudou de dono."""
import re
from pathlib import Path

import yaml

from sparkforge.rules.loader import load_catalog

# Importadas, nao recopiadas: a feature CONFIG_OCA declara as duas tuplas no teste que
# guarda a remocao, e uma segunda copia aqui divergiria no primeiro nome que voltasse.
from tests.test_config_declarado_existe import SUBAGENTS_QUE_SAIRAM, TOOLS_QUE_SAIRAM

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"

OCOS = (
    "sf-agent-builder",
    "sf-agent-evaluation-specialist",
    "sf-airflow-specialist",
    "sf-athena-specialist",
    "sf-context-engineer",
    "sf-cost-reviewer",
    "sf-data-architect",
    "sf-dynamodb-specialist",
    "sf-evidence-verifier",
    "sf-functional-rules-specialist",
    "sf-iceberg-specialist",
    "sf-kinesis-specialist",
    "sf-lambda-serverless-specialist",
    "sf-lineage-specialist",
    "sf-memory-engineer",
    "sf-parquet-specialist",
    "sf-s3-specialist",
    "sf-schema-registry-specialist",
    "sf-step-functions-specialist",
)
SKILLS_QUE_SAIRAM = (
    "design-agent-systems",
    "design-airflow-pipelines",
    "design-dynamodb-model",
    "design-lambda-serverless",
    "design-step-functions-orchestration",
    "engineer-agent-context",
    "engineer-agent-memory",
    "optimize-athena-queries",
    "optimize-iceberg-tables",
    "verify-agent-evidence",
)
CODE_TOOLS = (
    "sparkforge_code_status",
    "sparkforge_code_sync",
    "sparkforge_code_search",
    "sparkforge_code_symbol",
    "sparkforge_code_export",
    "sparkforge_code_shape",
    "sparkforge_code_path",
    "sparkforge_code_context",
    "sparkforge_code_read",
)


def _front(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1]) or {}


def test_conteudo_real_muda_de_dono():
    revisor = (AGENTS / "pyspark-code-reviewer.md").read_text(encoding="utf-8")
    faltam = [t for t in CODE_TOOLS if t not in revisor]
    assert not faltam, faltam
    iceberg = AGENTS / "iceberg-performance-engineer.md"
    assert "sparkforge_iceberg_assess_upgrade" in iceberg.read_text(encoding="utf-8")
    assert "iceberg-v3-readiness" in (_front(iceberg).get("skills") or [])
    dq = _front(AGENTS / "data-quality-reviewer.md")
    assert "analyze-functional-rules" in (dq.get("skills") or [])


def _areas_que_julgam() -> set[str]:
    return {r["id"].rsplit("-", 1)[0] for r in load_catalog() if r.get("executable", True)}


def _findings_areas(no) -> list[str]:
    if isinstance(no, dict):
        achadas = [no["findings_area"]] if "findings_area" in no else []
        return achadas + [a for v in no.values() for a in _findings_areas(v)]
    if isinstance(no, list):
        return [a for v in no for a in _findings_areas(v)]
    return []


def test_catalogo_so_tem_regra_que_julga():
    catalogo = load_catalog()
    assert not list((ROOT / "rules" / "catalog").glob("agentic-sf-*.yaml"))
    assert [r["id"] for r in catalogo if r.get("executable", True) is False] == []
    # A contagem (157) era a foto do SF_STUBS, e cada area nova a derrubava sem medir
    # nada do que este teste guarda. Quem publica a contagem e o STATUS, pelo gate.


def test_todo_sf_declara_area_que_julga():
    presentes = {p.stem for p in AGENTS.glob("sf-*.md")}
    assert presentes.isdisjoint(OCOS), sorted(presentes & set(OCOS))
    julgam = _areas_que_julgam()
    for path in sorted(AGENTS.glob("sf-*.md")):
        areas = set(_front(path).get("rule_areas") or [])
        assert areas & julgam, path.name
        assert areas <= julgam, (path.name, sorted(areas - julgam))


VIVOS = (
    "AGENTS.md",
    "docs/agentic-expansion.md",
    "docs/guia/05-agents-e-skills.md",
    "docs/guia/usos/athena-e-sql.md",
    "docs/guia/usos/iceberg-e-parquet.md",
    "docs/guia/usos/custo-e-capacidade.md",
    "docs/teams-catalog.md",
    "docs/operations-guide.md",
    "docs/vnext/AGENT-CATALOG.md",
    "docs/vnext/DEMOS.md",
    "knowledge/domain-tool-matrix.md",
    "config/teams-expansion.yaml",
    "config/agentic-expansion.yaml",
    "skills/aws-database/SKILL.md",
    "skills/aws-messaging-and-streaming/SKILL.md",
    "skills/aws-serverless/SKILL.md",
    "skills/aws-storage/SKILL.md",
    "skills/provision-s3-tables-table/SKILL.md",
    "sparkforge/findings/validate.py",
)


def test_documento_vivo_nao_cita_o_que_saiu():
    for rel in VIVOS:
        texto = (ROOT / rel).read_text(encoding="utf-8")
        citados = [
            nome
            for nome in OCOS + SKILLS_QUE_SAIRAM + TOOLS_QUE_SAIRAM + SUBAGENTS_QUE_SAIRAM
            if re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", texto)
        ]
        assert not citados, (rel, citados)


def test_rota_aponta_para_agente_e_area_que_existem():
    rotas = yaml.safe_load(
        (ROOT / "rules" / "catalog" / "routing.yaml").read_text(encoding="utf-8")
    )["rules"]
    agentes = {p.stem for p in AGENTS.glob("*.md")}
    julgam = _areas_que_julgam()
    for rota in rotas:
        agente = rota.get("recommended_agent")
        if agente is not None:
            assert agente in agentes, (rota["id"], agente)
        fora = [a for a in _findings_areas(rota.get("when")) if a not in julgam]
        assert not fora, (rota["id"], fora)
