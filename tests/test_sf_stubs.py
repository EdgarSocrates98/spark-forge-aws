"""A camada sf-* sem area oca: o catalogo so julga, e o conteudo real mudou de dono."""
from pathlib import Path

import yaml

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
