# SparkForge Fase 0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic extraction and judgment layer for SparkForge — anchored Facts from PySpark source, Findings from a version-guarded YAML rule catalog, a case file with deterministic routing, and CLI + MCP adapters — so that two operators on different models in different tools produce identical evidence and identical next steps.

**Architecture:** Six layers with negative boundaries. `facts/` extractors emit anchored observations with no judgment. `rules/` applies a YAML catalog (already committed, 59 rules) via a whitelist-only expression evaluator to produce Findings. `case/` holds investigation state in `.sparkforge/case.yaml` and routes deterministically. `adapters/` are thin CLI and MCP shells with zero domain logic. Knowledge stays outside the code in `rules/catalog/` and `knowledge/`.

**Tech Stack:** Python (stdlib `ast`, `hashlib`, `json`), PyYAML, jsonschema, pytest. Optional extras: boto3 (`[aws]`), MCP Python SDK (`[mcp]`). No mandatory dependency beyond PyYAML + jsonschema.

---

## Environment facts verified before writing this plan

- Local Python: **3.14.6**. `pyproject.toml` declares `requires-python = ">=3.10"`. Core code must avoid syntax newer than 3.10 so the package can run under Glue 4.0 if executed inside a job.
- Available: `PyYAML 6.0.2`, `jsonschema 4.23.0`, `pytest 8.3.4`.
- **Not** available: `ruff`. Lint tasks install it as a dev extra; do not assume it is present.
- 77 existing tests pass. `tests/` uses plain `pathlib` assertions with `ROOT = Path(__file__).resolve().parents[1]`. Follow that convention.
- `scripts/sync_skills.py` mirrors `skills/` to `.claude/skills/` and `.agents/skills/` with `--check` for CI. It does **not** yet handle `agents/`.
- Run tests with `python -m pytest`, never bare `pytest`.

## Two deviations from the spec, decided deliberately

**1. Catalog location.** Spec §14 places the catalog at `sparkforge/rules/catalog/`. It is already committed at repo root `rules/catalog/`, and it stays there: it is consultable data, it is the third rung of the portability ladder (an agent with no Python reads it directly), and burying it inside the package hurts discovery. `loader.py` resolves the path in order: `SPARKFORGE_CATALOG` env var → repo root `rules/catalog/` → package-relative fallback. Task 5 implements this.

**2. Routing predicates are declarative, not expressions.** The committed `routing.yaml` uses `len(value) > 1`, `any(h.status == 'open')` and `'athena' in value`. All three require `ast.Call` or `ast.In`, which the spec's whitelist forbids — and weakening the evaluator is not acceptable because the catalog is editable data and therefore an execution surface. Task 13 converts routing predicates to declarative operators (`count_gt`, `equals`, `contains`, `any_where`, `absent`) and updates `rules/catalog/README.md`.

---

## File Structure

**New package:**

| File | Responsibility |
|---|---|
| `sparkforge/__init__.py` | Version constant only |
| `sparkforge/findings/models.py` | `Fact`, `Finding`, `RuntimeContext`; canonical ids, deterministic ordering, `to_dict` |
| `sparkforge/findings/schemas/fact.schema.json` | JSON Schema for Fact |
| `sparkforge/findings/schemas/finding.schema.json` | JSON Schema for Finding; `evidence` `minItems: 1`; forbids percent in `expected_effect` without `benchmark_ref` |
| `sparkforge/findings/validate.py` | Schema loading and validation helpers |
| `sparkforge/rules/expr.py` | Whitelist-only AST expression evaluator. Security boundary |
| `sparkforge/rules/loader.py` | Catalog discovery, parsing, structural validation |
| `sparkforge/rules/engine.py` | Facts + RuntimeContext + catalog → Findings; version-scope skipping |
| `sparkforge/rules/version_scope.py` | `runtime_scope` range matching |
| `sparkforge/facts/pyspark_ast.py` | Static AST extractor. Three passes: parent map, chain reconstruction, emission |
| `sparkforge/case/store.py` | Read/write `.sparkforge/case.yaml` |
| `sparkforge/case/router.py` | `next_step(case)` pure function over `routing.yaml` |
| `sparkforge/case/resume.py` | Rehydration payload and `handoff.md` rendering |
| `sparkforge/collect/base.py` | Artifact manifest and optional-collector interface. Offline-first |
| `sparkforge/adapters/cli.py` | `sparkforge` entry point. Zero domain logic |
| `sparkforge/adapters/mcp.py` | MCP tools, stdio + HTTP. Zero domain logic |

**New non-code:**

| Path | Responsibility |
|---|---|
| `fixtures/pyspark/<name>/` | `input/`, `expected/facts.json`, `expected/findings.json`, `meta.yaml` |
| `parity.yaml` | Capability × platform × mechanism manifest |
| `evals/fase0.xml` | 10 verifiable QA pairs |
| `AGENT_PROTOCOL.md` | Hard rules injected into every agent and skill |
| `agents/` | Single source for the three agents |
| `.claude-plugin/plugin.json`, `.mcp.json` | Claude Code plugin |
| `commands/` | `/sf-open`, `/sf-next`, `/sf-resume`, `/sf-handoff` |

**Modified:**

| Path | Change |
|---|---|
| `pyproject.toml` | Package discovery, entry point, extras, pytest config |
| `scripts/sync_skills.py` | Extend to `agents/` and protocol injection |
| `rules/catalog/routing.yaml` | Declarative predicates (Task 13) |
| `rules/catalog/README.md` | Document declarative routing operators |

---

## Task 1: Package skeleton and packaging metadata

**Files:**
- Create: `sparkforge/__init__.py`, `sparkforge/findings/__init__.py`, `sparkforge/rules/__init__.py`, `sparkforge/facts/__init__.py`, `sparkforge/case/__init__.py`, `sparkforge/adapters/__init__.py`
- Modify: `pyproject.toml`
- Test: `tests/test_package_importable.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_package_importable.py
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_version_exposed():
    import sparkforge

    assert sparkforge.__version__ == "0.4.0"


def test_core_imports_without_optional_extras():
    """Core must not import boto3 or the MCP SDK. Devin CLI and CI run without them."""
    code = (
        "import sys;"
        "sys.modules['boto3'] = None;"
        "sys.modules['mcp'] = None;"
        "import sparkforge.findings.models, sparkforge.rules.expr;"
        "print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_package_importable.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge'`

- [ ] **Step 3: Create the package files**

```python
# sparkforge/__init__.py
"""SparkForge AWS — camada determinística de extração e julgamento."""

__version__ = "0.4.0"
```

Create these five files with exactly this one-line content each — `sparkforge/findings/__init__.py`, `sparkforge/rules/__init__.py`, `sparkforge/facts/__init__.py`, `sparkforge/case/__init__.py`, `sparkforge/adapters/__init__.py`:

```python
"""Subpacote SparkForge."""
```

- [ ] **Step 4: Update `pyproject.toml`**

Replace the entire file with:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sparkforge-aws"
version = "0.4.0"
description = "Agent skills and deterministic analyzers for AWS Glue PySpark, Parquet, Iceberg and Athena performance engineering"
requires-python = ">=3.10"
dependencies = [
    "PyYAML>=6.0",
    "jsonschema>=4.0",
]

[project.optional-dependencies]
aws = ["boto3>=1.34"]
mcp = ["mcp>=1.0"]
dev = ["pytest>=8.0", "ruff>=0.6"]

[project.scripts]
sparkforge = "sparkforge.adapters.cli:main"

[tool.setuptools.packages.find]
include = ["sparkforge*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_package_importable.py -v`
Expected: PASS, 2 tests

- [ ] **Step 6: Confirm the existing suite still passes**

Run: `python -m pytest -q`
Expected: 79 passed

- [ ] **Step 7: Commit**

```bash
git add sparkforge pyproject.toml tests/test_package_importable.py
git commit -m "feat(pkg): add sparkforge package skeleton and packaging metadata"
```

---

## Task 2: The expression evaluator — security boundary first

Built before anything that uses it, because the catalog is editable data and therefore an execution surface. The tests that matter most here are the rejection tests.

**Files:**
- Create: `sparkforge/rules/expr.py`
- Test: `tests/test_rules_expr.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rules_expr.py
import pytest

from sparkforge.rules.expr import ExprError, evaluate

CTX = {
    "measures": {"max_ms": 41000, "p50_ms": 1200, "run_length": 12},
    "attrs": {"bounded": False, "udf_type": "python"},
    "threshold": {"ratio": 3.0, "run_length": 10},
}


class TestArithmeticAndComparison:
    def test_ratio_comparison_true(self):
        assert evaluate("measures.max_ms / measures.p50_ms >= threshold.ratio", CTX) is True

    def test_ratio_comparison_false(self):
        ctx = {"measures": {"max_ms": 1000, "p50_ms": 1000}, "threshold": {"ratio": 3.0}}
        assert evaluate("measures.max_ms / measures.p50_ms >= threshold.ratio", ctx) is False

    def test_boundary_exact_threshold_is_inclusive(self):
        ctx = {"measures": {"a": 3.0}, "threshold": {"ratio": 3.0}}
        assert evaluate("measures.a >= threshold.ratio", ctx) is True

    def test_boundary_just_below_is_false(self):
        ctx = {"measures": {"a": 2.99}, "threshold": {"ratio": 3.0}}
        assert evaluate("measures.a >= threshold.ratio", ctx) is False

    def test_boolean_and(self):
        expr = "measures.run_length >= threshold.run_length and attrs.bounded == False"
        assert evaluate(expr, CTX) is True

    def test_equality_on_string_attr(self):
        assert evaluate("attrs.udf_type == 'python'", CTX) is True


class TestRejections:
    """These are the tests that matter. Catalog YAML is editable data."""

    @pytest.mark.parametrize(
        "expr",
        [
            "__import__('os').system('echo pwned')",
            "len(measures)",
            "measures.__class__",
            "measures.__class__.__mro__",
            "open('/etc/passwd').read()",
            "[x for x in measures]",
            "lambda: 1",
            "measures['max_ms']",
            "os.getcwd()",
            "measures.max_ms if True else 0",
            "{'a': 1}",
            "(1, 2)",
        ],
    )
    def test_disallowed_constructs_raise(self, expr):
        with pytest.raises(ExprError):
            evaluate(expr, CTX)

    def test_unknown_root_rejected(self):
        with pytest.raises(ExprError, match="raiz"):
            evaluate("secrets.token == 'x'", CTX)

    def test_missing_path_rejected(self):
        with pytest.raises(ExprError, match="ausente"):
            evaluate("measures.does_not_exist > 1", CTX)

    def test_syntax_error_rejected(self):
        with pytest.raises(ExprError, match="invalida"):
            evaluate("measures.a >>>", CTX)

    def test_division_by_zero_is_expr_error_not_crash(self):
        ctx = {"measures": {"a": 1, "b": 0}, "threshold": {}}
        with pytest.raises(ExprError, match="divis"):
            evaluate("measures.a / measures.b > 1", ctx)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rules_expr.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.rules.expr'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/rules/expr.py
"""Avaliador de expressões do catálogo de regras.

Fronteira de segurança. O catálogo é dado editável, portanto é superfície de
execução. Whitelist de nós AST; nunca `eval`. Ver
docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md secao 5.3.
"""
from __future__ import annotations

import ast
import operator
from typing import Any, Dict

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

ALLOWED_ROOTS = frozenset({"measures", "attrs", "threshold"})


class ExprError(ValueError):
    """Expressão inválida, insegura, ou com caminho ausente no contexto."""


def evaluate(expr: str, context: Dict[str, Any]) -> Any:
    """Avalia `expr` contra `context`. Levanta ExprError em qualquer desvio."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise ExprError("expressao invalida: {0!r}: {1}".format(expr, exc)) from exc
    return _eval(tree.body, context)


def _eval(node: ast.AST, ctx: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, str, bool)) or node.value is None:
            return node.value
        raise ExprError("constante nao permitida: {0!r}".format(node.value))

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not _eval(node.operand, ctx)
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand, ctx)
        if isinstance(node.op, ast.UAdd):
            return +_eval(node.operand, ctx)
        raise ExprError("operador unario nao permitido")

    if isinstance(node, ast.BoolOp):
        values = [_eval(v, ctx) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)

    if isinstance(node, ast.BinOp):
        func = _BIN_OPS.get(type(node.op))
        if func is None:
            raise ExprError("operador binario nao permitido: {0}".format(type(node.op).__name__))
        left = _eval(node.left, ctx)
        right = _eval(node.right, ctx)
        try:
            return func(left, right)
        except ZeroDivisionError as exc:
            raise ExprError("divisao por zero em: {0}".format(ast.dump(node))) from exc

    if isinstance(node, ast.Compare):
        left = _eval(node.left, ctx)
        for op_node, comparator in zip(node.ops, node.comparators):
            func = _CMP_OPS.get(type(op_node))
            if func is None:
                raise ExprError("comparador nao permitido: {0}".format(type(op_node).__name__))
            right = _eval(comparator, ctx)
            if not func(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Attribute):
        return _resolve_path(node, ctx)

    raise ExprError("no nao permitido: {0}".format(type(node).__name__))


def _resolve_path(node: ast.Attribute, ctx: Dict[str, Any]) -> Any:
    parts = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        if current.attr.startswith("__"):
            raise ExprError("atributo dunder proibido: {0}".format(current.attr))
        parts.append(current.attr)
        current = current.value

    if not isinstance(current, ast.Name):
        raise ExprError("base de atributo nao permitida: {0}".format(type(current).__name__))
    if current.id not in ALLOWED_ROOTS:
        raise ExprError(
            "raiz nao permitida: {0} (permitidas: {1})".format(
                current.id, ", ".join(sorted(ALLOWED_ROOTS))
            )
        )

    parts.append(current.id)
    parts.reverse()

    value: Any = ctx
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            raise ExprError("caminho ausente no contexto: {0}".format(".".join(parts)))
        value = value[part]
    return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rules_expr.py -v`
Expected: PASS, 22 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/rules/expr.py tests/test_rules_expr.py
git commit -m "feat(rules): add whitelist-only expression evaluator with rejection tests"
```

---

## Task 3: Fact and Finding contracts

**Files:**
- Create: `sparkforge/findings/models.py`
- Test: `tests/test_findings_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_findings_models.py
import pytest

from sparkforge.findings.models import Fact, Finding, SEVERITY_ORDER, sort_facts, sort_findings


def make_fact(**over):
    base = dict(
        kind="pyspark.partitioning",
        subject={"type": "source_location", "file": "lib/loader.py", "line": 142, "col": 8},
        measures={"target_count": 1},
        attrs={"method": "coalesce", "literal_arg": True},
        provenance={"artifact": "artifacts/src/lib/loader.py", "extractor": "pyspark_ast@0.1.0"},
    )
    base.update(over)
    return Fact(**base)


class TestFactId:
    def test_id_is_stable_across_instances(self):
        assert make_fact().id == make_fact().id

    def test_id_has_expected_shape(self):
        fid = make_fact().id
        assert fid.startswith("f_")
        assert len(fid) == 8

    def test_id_changes_with_kind(self):
        assert make_fact().id != make_fact(kind="pyspark.action").id

    def test_id_changes_with_subject(self):
        other = {"type": "source_location", "file": "lib/loader.py", "line": 999, "col": 8}
        assert make_fact().id != make_fact(subject=other).id

    def test_id_changes_with_measures(self):
        assert make_fact().id != make_fact(measures={"target_count": 2}).id

    def test_id_ignores_provenance(self):
        """Provenance records where the fact came from, not what it asserts."""
        assert make_fact().id == make_fact(provenance={"artifact": "other", "extractor": "x@9"}).id

    def test_id_ignores_key_order_in_subject(self):
        reordered = {"col": 8, "line": 142, "file": "lib/loader.py", "type": "source_location"}
        assert make_fact().id == make_fact(subject=reordered).id


class TestFactSerialization:
    def test_to_dict_includes_id_and_schema_version(self):
        data = make_fact().to_dict()
        assert data["id"] == make_fact().id
        assert data["schema_version"] == 1
        assert data["kind"] == "pyspark.partitioning"

    def test_sort_facts_is_deterministic(self):
        a = make_fact(kind="pyspark.action")
        b = make_fact(kind="pyspark.partitioning")
        assert [f.kind for f in sort_facts([b, a])] == ["pyspark.action", "pyspark.partitioning"]


class TestFinding:
    def test_evidence_must_not_be_empty(self):
        with pytest.raises(ValueError, match="evidence"):
            Finding(
                rule_id="SF-PY-005",
                title="coalesce(1)",
                severity="P0",
                confidence="high",
                status="structural",
                subject={"type": "source_location", "file": "a.py", "line": 1},
                evidence=[],
            )

    def test_severity_must_be_known(self):
        with pytest.raises(ValueError, match="severity"):
            Finding(
                rule_id="SF-PY-005",
                title="x",
                severity="CRITICAL",
                confidence="high",
                status="structural",
                subject={"type": "source_location"},
                evidence=["f_abc123"],
            )

    def test_status_must_be_known(self):
        with pytest.raises(ValueError, match="status"):
            Finding(
                rule_id="SF-PY-005",
                title="x",
                severity="P0",
                confidence="high",
                status="probable",
                subject={"type": "source_location"},
                evidence=["f_abc123"],
            )

    def test_sort_findings_orders_by_severity_then_rule_id(self):
        def mk(rule_id, severity):
            return Finding(
                rule_id=rule_id,
                title="t",
                severity=severity,
                confidence="high",
                status="structural",
                subject={"type": "source_location", "file": "a.py", "line": 1},
                evidence=["f_abc123"],
            )

        items = [mk("SF-PY-009", "P2"), mk("SF-PY-005", "P0"), mk("SF-PY-002", "P2")]
        ordered = [(f.severity, f.rule_id) for f in sort_findings(items)]
        assert ordered == [("P0", "SF-PY-005"), ("P2", "SF-PY-002"), ("P2", "SF-PY-009")]

    def test_severity_order_covers_p0_to_p4(self):
        assert SEVERITY_ORDER == ("P0", "P1", "P2", "P3", "P4")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_findings_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.findings.models'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/findings/models.py
"""Contratos de dados: Fact, Finding, RuntimeContext.

Fact é observação crua ancorada, sem juízo. Finding é juízo, sempre lastreado por
pelo menos um Fact. Ordenação é determinística para golden test não flakar.
Ver docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md secao 5.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence, Tuple

SCHEMA_VERSION = 1
SEVERITY_ORDER: Tuple[str, ...] = ("P0", "P1", "P2", "P3", "P4")
CONFIDENCE_VALUES = frozenset({"high", "medium", "low"})
STATUS_VALUES = frozenset({"structural", "confirmed"})


def _canonical(value: Any) -> str:
    """JSON canônico: chaves ordenadas, sem espaços. Base do id estável."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _subject_key(subject: Dict[str, Any]) -> str:
    return _canonical(subject)


@dataclass(frozen=True)
class Fact:
    """Observação determinística ancorada. Nunca contém juízo nem limiar."""

    kind: str
    subject: Dict[str, Any]
    measures: Dict[str, Any] = field(default_factory=dict)
    attrs: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    @property
    def id(self) -> str:
        """sha1[:6] de (kind + subject + measures). Provenance não entra: ela
        registra de onde o fact veio, não o que ele afirma."""
        payload = _canonical(
            {"kind": self.kind, "subject": self.subject, "measures": self.measures}
        )
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
        return "f_" + digest[:6]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "schema_version": self.schema_version,
            "kind": self.kind,
            "subject": self.subject,
            "measures": self.measures,
            "attrs": self.attrs,
            "provenance": self.provenance,
        }


@dataclass
class Finding:
    """Juízo sobre o sistema analisado. `evidence` nunca vazio."""

    rule_id: str
    title: str
    severity: str
    confidence: str
    status: str
    subject: Dict[str, Any]
    evidence: List[str]
    measured: Dict[str, Any] = field(default_factory=dict)
    threshold: Dict[str, Any] = field(default_factory=dict)
    runtime_scope: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    proposed_change: List[str] = field(default_factory=list)
    expected_effect: str = ""
    benchmark_ref: str = ""
    risks: List[str] = field(default_factory=list)
    tradeoffs: List[str] = field(default_factory=list)
    validation: List[str] = field(default_factory=list)
    rollback: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    catalog_version: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError(
                "Finding {0}: evidence vazio. Finding sem Fact e invalido.".format(self.rule_id)
            )
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(
                "Finding {0}: severity {1!r} desconhecida (esperado: {2})".format(
                    self.rule_id, self.severity, ", ".join(SEVERITY_ORDER)
                )
            )
        if self.confidence not in CONFIDENCE_VALUES:
            raise ValueError(
                "Finding {0}: confidence {1!r} desconhecida".format(self.rule_id, self.confidence)
            )
        if self.status not in STATUS_VALUES:
            raise ValueError(
                "Finding {0}: status {1!r} desconhecido (esperado: {2})".format(
                    self.rule_id, self.status, ", ".join(sorted(STATUS_VALUES))
                )
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "schema_version": self.schema_version,
            "catalog_version": self.catalog_version,
            "title": self.title,
            "severity": self.severity,
            "confidence": self.confidence,
            "status": self.status,
            "subject": self.subject,
            "evidence": list(self.evidence),
            "measured": self.measured,
            "threshold": self.threshold,
            "runtime_scope": self.runtime_scope,
            "explanation": self.explanation,
            "proposed_change": list(self.proposed_change),
            "expected_effect": self.expected_effect,
            "benchmark_ref": self.benchmark_ref,
            "risks": list(self.risks),
            "tradeoffs": list(self.tradeoffs),
            "validation": list(self.validation),
            "rollback": list(self.rollback),
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class RuntimeContext:
    """Versões detectadas. `divergences` não vazio significa detecção conflitante."""

    glue: str = ""
    spark: str = ""
    python: str = ""
    iceberg: str = ""
    athena: str = ""
    detected_from: Sequence[str] = ()
    divergences: Sequence[str] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "glue": self.glue,
            "spark": self.spark,
            "python": self.python,
            "iceberg": self.iceberg,
            "athena": self.athena,
            "detected_from": list(self.detected_from),
            "divergences": list(self.divergences),
        }


def sort_facts(facts: Iterable[Fact]) -> List[Fact]:
    """Ordem determinística: (kind, subject canônico, id)."""
    return sorted(facts, key=lambda f: (f.kind, _subject_key(f.subject), f.id))


def sort_findings(findings: Iterable[Finding]) -> List[Finding]:
    """Ordem determinística: (severidade, rule_id, subject canônico)."""
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_ORDER.index(f.severity),
            f.rule_id,
            _subject_key(f.subject),
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_findings_models.py -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/findings/models.py tests/test_findings_models.py
git commit -m "feat(findings): add Fact and Finding contracts with deterministic ordering"
```

---

## Task 4: Extractor — first kind (`pyspark.partitioning`)

Vertical slice starts here. One kind, one rule, end to end, before broadening. `pyspark.partitioning` is chosen because `SF-PY-005` (`coalesce(1)`, P0) needs only method name plus literal arg — no chain analysis yet.

**Files:**
- Create: `sparkforge/facts/pyspark_ast.py`
- Test: `tests/test_facts_pyspark_ast.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_facts_pyspark_ast.py
import textwrap

from sparkforge.facts.pyspark_ast import EXTRACTOR_ID, extract_source


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


class TestPartitioning:
    def test_detects_coalesce_with_literal_one(self):
        src = textwrap.dedent(
            """
            def run(df):
                df.coalesce(1).write.parquet("s3://b/p")
            """
        )
        facts = extract_source(src, "lib/loader.py")
        got = facts_of("pyspark.partitioning", facts)
        assert len(got) == 1
        fact = got[0]
        assert fact.attrs["method"] == "coalesce"
        assert fact.attrs["literal_arg"] is True
        assert fact.measures["target_count"] == 1
        assert fact.subject["file"] == "lib/loader.py"
        assert fact.subject["line"] == 3
        assert fact.subject["symbol"] == "run"
        assert "coalesce" in fact.subject["snippet"]

    def test_detects_repartition_with_literal(self):
        src = "df.repartition(200)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["method"] == "repartition"
        assert facts[0].measures["target_count"] == 200
        assert facts[0].attrs["has_partition_expr"] is False

    def test_repartition_by_column_marks_partition_expr(self):
        src = 'df.repartition(200, "cliente_id")\n'
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["has_partition_expr"] is True

    def test_non_literal_arg_is_marked_and_has_no_measure(self):
        src = "df.repartition(n_particoes)\n"
        facts = facts_of("pyspark.partitioning", extract_source(src, "a.py"))
        assert facts[0].attrs["literal_arg"] is False
        assert "target_count" not in facts[0].measures

    def test_clean_code_yields_no_partitioning_facts(self):
        src = 'df.select("a").filter("a > 1").write.parquet("s3://b/p")\n'
        assert facts_of("pyspark.partitioning", extract_source(src, "a.py")) == []


class TestProvenanceAndDeterminism:
    def test_provenance_records_extractor_and_artifact(self):
        facts = extract_source("df.coalesce(1)\n", "lib/x.py")
        prov = facts[0].provenance
        assert prov["extractor"] == EXTRACTOR_ID
        assert prov["artifact"] == "lib/x.py"
        assert len(prov["artifact_sha256"]) == 64

    def test_same_input_twice_yields_identical_dicts(self):
        src = "df.coalesce(1)\ndf.repartition(10)\n"
        first = [f.to_dict() for f in extract_source(src, "a.py")]
        second = [f.to_dict() for f in extract_source(src, "a.py")]
        assert first == second


class TestUnresolved:
    def test_dynamic_dispatch_emits_unresolved_not_a_finding_candidate(self):
        src = "getattr(df, metodo)(1)\n"
        facts = extract_source(src, "a.py")
        assert facts_of("pyspark.unresolved", facts)
        assert facts_of("pyspark.partitioning", facts) == []

    def test_unresolved_records_reason_and_location(self):
        src = "getattr(df, metodo)(1)\n"
        fact = facts_of("pyspark.unresolved", extract_source(src, "a.py"))[0]
        assert fact.attrs["reason"] == "getattr"
        assert fact.subject["line"] == 1


class TestSyntaxError:
    def test_unparseable_file_yields_single_unresolved_fact(self):
        facts = extract_source("def broken(:\n", "bad.py")
        assert len(facts) == 1
        assert facts[0].kind == "pyspark.unresolved"
        assert facts[0].attrs["reason"] == "syntax_error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_facts_pyspark_ast.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.facts.pyspark_ast'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/facts/pyspark_ast.py
"""Extrator estatico de codigo PySpark.

NUNCA importa nem executa o codigo do alvo: `ast` da stdlib apenas. Importar um
modulo de job para inspecionar executaria codigo arbitrario do repositorio
analisado.

Tres passes: (1) mapa pai/escopo, (2) reconstrucao de cadeia, (3) emissao.
Nao aplica limiar, nao atribui severidade, nao ordena por importancia.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "pyspark_ast@0.1.0"

_PARTITION_METHODS = frozenset({"coalesce", "repartition", "repartitionByRange"})


class _Context:
    """Passe 1: mapa filho -> pai, escopo de funcao, profundidade de loop."""

    def __init__(self, tree: ast.AST) -> None:
        self.parent: Dict[int, Any] = {}
        self.function: Dict[int, str] = {}
        self.loop_depth: Dict[int, int] = {}
        self._walk(tree, None, "", 0)

    def _walk(self, node: ast.AST, parent: Optional[ast.AST], symbol: str, depth: int) -> None:
        self.parent[id(node)] = parent
        self.function[id(node)] = symbol
        self.loop_depth[id(node)] = depth

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol = node.name
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            depth += 1

        for child in ast.iter_child_nodes(node):
            self._walk(child, node, symbol, depth)


def _snippet(lines: List[str], node: ast.AST) -> str:
    lineno = getattr(node, "lineno", None)
    if lineno is None or lineno - 1 >= len(lines):
        return ""
    return lines[lineno - 1].strip()


def _subject(node: ast.AST, path: str, ctx: _Context, lines: List[str]) -> Dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": getattr(node, "lineno", 0),
        "col": getattr(node, "col_offset", 0),
        "end_line": getattr(node, "end_lineno", getattr(node, "lineno", 0)),
        "symbol": ctx.function.get(id(node), ""),
        "snippet": _snippet(lines, node),
    }


def _literal(node: ast.AST) -> Optional[Any]:
    """Valor se o no e literal constante; None caso contrario."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str, bool)):
        return node.value
    return None


def extract_source(source: str, path: str) -> List[Fact]:
    """Extrai Facts de `source`. `path` e usado como ancora e procedencia."""
    sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    provenance = {"artifact": path, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}
    lines = source.splitlines()

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [
            Fact(
                kind="pyspark.unresolved",
                subject={
                    "type": "source_location",
                    "file": path,
                    "line": exc.lineno or 0,
                    "col": exc.offset or 0,
                    "symbol": "",
                    "snippet": "",
                },
                attrs={"reason": "syntax_error", "detail": str(exc.msg)},
                provenance=provenance,
            )
        ]

    ctx = _Context(tree)
    facts: List[Fact] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Dispatch dinamico: cobertura honesta em vez de silencio.
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            facts.append(
                Fact(
                    kind="pyspark.unresolved",
                    subject=_subject(node, path, ctx, lines),
                    attrs={"reason": "getattr"},
                    provenance=provenance,
                )
            )
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        method = node.func.attr
        if method in _PARTITION_METHODS:
            facts.append(_partitioning_fact(node, method, path, ctx, lines, provenance))

    return sort_facts(facts)


def _partitioning_fact(
    node: ast.Call,
    method: str,
    path: str,
    ctx: _Context,
    lines: List[str],
    provenance: Dict[str, Any],
) -> Fact:
    first = node.args[0] if node.args else None
    target = _literal(first) if first is not None else None
    literal_arg = isinstance(target, int) and not isinstance(target, bool)

    # repartition(200, "col") ou repartition("col"): ha expressao de particao.
    has_partition_expr = len(node.args) > 1 or (first is not None and not literal_arg)

    measures: Dict[str, Any] = {}
    if literal_arg:
        measures["target_count"] = target

    return Fact(
        kind="pyspark.partitioning",
        subject=_subject(node, path, ctx, lines),
        measures=measures,
        attrs={
            "method": method,
            "literal_arg": literal_arg,
            "has_partition_expr": has_partition_expr,
            "inside_loop": ctx.loop_depth.get(id(node), 0) > 0,
        },
        provenance=provenance,
    )


def extract_path(path: Path, repo_root: Optional[Path] = None) -> List[Fact]:
    """Extrai de um arquivo, ancorando o path relativo a `repo_root`."""
    text = path.read_text(encoding="utf-8")
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    return extract_source(text, rel.replace("\\", "/"))


def extract_tree(root: Path, repo_root: Optional[Path] = None) -> List[Fact]:
    """Extrai de todos os .py sob `root`, em ordem deterministica de path."""
    facts: List[Fact] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        facts.extend(extract_path(py, repo_root))
    return sort_facts(facts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_facts_pyspark_ast.py -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/pyspark_ast.py tests/test_facts_pyspark_ast.py
git commit -m "feat(facts): add static PySpark AST extractor"
```

---

## Task 5: Catalog loader and version scope guard

**Files:**
- Create: `sparkforge/rules/loader.py`, `sparkforge/rules/version_scope.py`
- Test: `tests/test_rules_loader.py`, `tests/test_rules_version_scope.py`

- [ ] **Step 1: Write the failing version-scope test**

```python
# tests/test_rules_version_scope.py
import pytest

from sparkforge.rules.version_scope import in_scope


class TestInScope:
    def test_wildcard_always_matches(self):
        assert in_scope({"glue": "*"}, {"glue": "5.0"}) is True

    def test_empty_scope_always_matches(self):
        assert in_scope({}, {"glue": "5.0"}) is True

    def test_gte_matches_equal(self):
        assert in_scope({"spark": ">=3.5"}, {"spark": "3.5.4"}) is True

    def test_gte_matches_greater(self):
        assert in_scope({"spark": ">=3.2"}, {"spark": "3.5.4"}) is True

    def test_gte_rejects_lower(self):
        assert in_scope({"spark": ">=3.2"}, {"spark": "3.1.1"}) is False

    def test_lt_rejects_equal(self):
        assert in_scope({"glue": "<4.0"}, {"glue": "4.0"}) is False

    def test_lt_matches_lower(self):
        assert in_scope({"glue": "<4.0"}, {"glue": "3.0"}) is True

    def test_multiple_keys_all_must_match(self):
        scope = {"glue": ">=5.1", "iceberg": ">=1.10.0"}
        assert in_scope(scope, {"glue": "5.1", "iceberg": "1.10.0"}) is True
        assert in_scope(scope, {"glue": "5.1", "iceberg": "1.7.1"}) is False

    def test_unknown_runtime_key_does_not_match(self):
        """Sem versao detectada a regra nao dispara. Falha fechada por versao."""
        assert in_scope({"iceberg": ">=1.7.0"}, {"glue": "5.0"}) is False

    def test_exact_version_pin(self):
        assert in_scope({"glue": "5.0"}, {"glue": "5.0"}) is True
        assert in_scope({"glue": "5.0"}, {"glue": "5.1"}) is False

    def test_malformed_spec_raises(self):
        with pytest.raises(ValueError, match="runtime_scope"):
            in_scope({"glue": "~>5.0"}, {"glue": "5.0"})
```

- [ ] **Step 2: Write the failing loader test**

```python
# tests/test_rules_loader.py
from pathlib import Path

import pytest

from sparkforge.rules.loader import CatalogError, catalog_dir, load_catalog

ROOT = Path(__file__).resolve().parents[1]


class TestCatalogDiscovery:
    def test_finds_repo_root_catalog(self):
        assert catalog_dir() == ROOT / "rules" / "catalog"

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))
        assert catalog_dir() == tmp_path


class TestLoadCommittedCatalog:
    def test_loads_all_non_routing_rules(self):
        assert len(load_catalog()) == 43

    def test_routing_is_excluded(self):
        assert not [r for r in load_catalog() if r["id"].startswith("ROUTE-")]

    def test_every_rule_id_is_unique(self):
        ids = [r["id"] for r in load_catalog()]
        assert len(ids) == len(set(ids))

    def test_every_rule_has_required_fields(self):
        required = (
            "id",
            "category",
            "title",
            "requires_facts",
            "when",
            "status",
            "runtime_scope",
            "sources",
        )
        for rule in load_catalog():
            for key in required:
                assert key in rule, "{0} sem {1}".format(rule.get("id"), key)

    def test_every_rule_has_a_severity(self):
        for rule in load_catalog():
            assert "severity_default" in rule or "severity_by" in rule, rule["id"]

    def test_every_source_has_url_or_origin(self):
        for rule in load_catalog():
            for src in rule["sources"]:
                assert "url" in src or "origin" in src, rule["id"]

    def test_every_expr_is_accepted_by_the_safe_evaluator(self):
        """Expressao invalida no catalogo falha na carga, nao em producao."""
        load_catalog(validate_exprs=True)

    def test_catalog_version_is_stamped(self):
        for rule in load_catalog():
            assert isinstance(rule["catalog_version"], int)


class TestRejections:
    def _write(self, tmp_path, monkeypatch, name, body):
        (tmp_path / name).write_text(body, encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))

    def test_duplicate_id_raises(self, tmp_path, monkeypatch):
        one = (
            "{id: SF-X-001, category: c, title: t, requires_facts: [k], "
            "when: {all: []}, status: structural, severity_default: P2, "
            'runtime_scope: {glue: "*"}, sources: [{origin: field-heuristic}]}'
        )
        body = "catalog_version: 1\narea: SF-X\nrules:\n  - " + one + "\n  - " + one + "\n"
        self._write(tmp_path, monkeypatch, "dup.yaml", body)
        with pytest.raises(CatalogError, match="duplicado"):
            load_catalog()

    def test_missing_required_field_raises(self, tmp_path, monkeypatch):
        body = "catalog_version: 1\narea: SF-X\nrules:\n  - {id: SF-X-002, title: t}\n"
        self._write(tmp_path, monkeypatch, "bad.yaml", body)
        with pytest.raises(CatalogError, match="SF-X-002"):
            load_catalog()

    def test_unsafe_expr_raises_at_load_time(self, tmp_path, monkeypatch):
        body = (
            "catalog_version: 1\n"
            "area: SF-X\n"
            "rules:\n"
            "  - id: SF-X-003\n"
            "    category: c\n"
            "    title: t\n"
            "    requires_facts: [k]\n"
            "    when:\n"
            "      all:\n"
            "        - {fact: k, expr: \"__import__('os').system('x')\"}\n"
            "    status: structural\n"
            "    severity_default: P2\n"
            '    runtime_scope: {glue: "*"}\n'
            "    sources: [{origin: field-heuristic}]\n"
        )
        self._write(tmp_path, monkeypatch, "unsafe.yaml", body)
        with pytest.raises(CatalogError, match="SF-X-003"):
            load_catalog(validate_exprs=True)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_rules_loader.py tests/test_rules_version_scope.py -v`
Expected: FAIL with `ModuleNotFoundError` for both modules

- [ ] **Step 4: Write `version_scope.py`**

```python
# sparkforge/rules/version_scope.py
"""Guarda de versao do catalogo.

Regra fora do range nao dispara. Falha fechada: versao nao detectada significa
nao aplicar, porque aplicar limiar de versao errada invalida a recomendacao.
"""
from __future__ import annotations

from typing import Dict, Tuple

_OPERATORS = (">=", "<=", ">", "<", "==")


def _parse(version: str) -> Tuple[int, ...]:
    parts = []
    for chunk in str(version).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _compare(left: Tuple[int, ...], right: Tuple[int, ...]) -> int:
    size = max(len(left), len(right))
    padded_left = left + (0,) * (size - len(left))
    padded_right = right + (0,) * (size - len(right))
    if padded_left < padded_right:
        return -1
    return 1 if padded_left > padded_right else 0


def in_scope(scope: Dict[str, str], runtime: Dict[str, str]) -> bool:
    """True se todas as restricoes de `scope` casam com `runtime`."""
    for key, raw_spec in (scope or {}).items():
        spec = str(raw_spec).strip()
        if spec == "*":
            continue

        actual = runtime.get(key)
        if not actual:
            return False

        found = None
        for candidate in _OPERATORS:
            if spec.startswith(candidate):
                found = candidate
                break

        target = spec[len(found):].strip() if found else spec
        if not target or not target[0].isdigit():
            raise ValueError("runtime_scope invalido para {0}: {1!r}".format(key, spec))

        result = _compare(_parse(actual), _parse(target))
        op = found or "=="

        if op == ">=" and result < 0:
            return False
        if op == "<=" and result > 0:
            return False
        if op == ">" and result <= 0:
            return False
        if op == "<" and result >= 0:
            return False
        if op == "==" and result != 0:
            return False

    return True
```

- [ ] **Step 5: Write `loader.py`**

```python
# sparkforge/rules/loader.py
"""Descoberta, parsing e validacao estrutural do catalogo de regras.

Resolucao de path, em ordem: env var SPARKFORGE_CATALOG -> raiz do repo
(rules/catalog) -> fallback relativo ao pacote. Desvio deliberado da spec secao
14: o catalogo e dado consultavel e e o terceiro degrau da escada de
portabilidade, entao fica na raiz e nao enterrado no pacote.

routing.yaml tem schema proprio e e carregado por sparkforge.case.router.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from sparkforge.rules.expr import ExprError, evaluate

ROUTING_FILE = "routing.yaml"

_REQUIRED = (
    "id",
    "category",
    "title",
    "requires_facts",
    "when",
    "status",
    "runtime_scope",
    "sources",
)


class CatalogError(ValueError):
    """Catalogo malformado. Falha na carga, nunca em producao."""


def catalog_dir() -> Path:
    override = os.environ.get("SPARKFORGE_CATALOG")
    if override:
        return Path(override)

    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "rules" / "catalog"
    if candidate.is_dir():
        return candidate

    return Path(__file__).resolve().parent / "catalog"


def _validate_expr(rule_id: str, expr: str) -> None:
    probe = {"measures": {}, "attrs": {}, "threshold": {}}
    try:
        evaluate(expr, probe)
    except ExprError as exc:
        message = str(exc)
        # Caminho ausente e esperado com contexto vazio; o que importa e a forma.
        if "ausente" not in message:
            raise CatalogError(
                "{0}: expressao rejeitada pelo avaliador: {1}".format(rule_id, message)
            ) from exc


def _collect_exprs(rule: Dict[str, Any]) -> List[str]:
    found: List[str] = []
    when = rule.get("when") or {}
    for group in ("all", "any"):
        for condition in when.get(group) or []:
            if isinstance(condition, dict) and "expr" in condition:
                found.append(condition["expr"])
    for entry in rule.get("severity_by") or []:
        if isinstance(entry, dict) and "when" in entry:
            found.append(entry["when"])
    return found


def load_catalog(
    directory: Optional[Path] = None, validate_exprs: bool = False
) -> List[Dict[str, Any]]:
    """Carrega todas as regras exceto routing. Levanta CatalogError se invalido."""
    base = directory or catalog_dir()
    if not base.is_dir():
        raise CatalogError("diretorio de catalogo inexistente: {0}".format(base))

    rules: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}

    for path in sorted(base.glob("*.yaml")):
        if path.name == ROUTING_FILE:
            continue

        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise CatalogError("{0}: YAML invalido: {1}".format(path.name, exc)) from exc

        version = document.get("catalog_version", 1)

        for rule in document.get("rules") or []:
            rule_id = rule.get("id", "<sem id>")

            missing = [key for key in _REQUIRED if key not in rule]
            if missing:
                raise CatalogError(
                    "{0}: campos obrigatorios ausentes: {1}".format(rule_id, ", ".join(missing))
                )
            if "severity_default" not in rule and "severity_by" not in rule:
                raise CatalogError(
                    "{0}: precisa de severity_default ou severity_by".format(rule_id)
                )
            for source in rule["sources"]:
                if "url" not in source and "origin" not in source:
                    raise CatalogError("{0}: source sem url nem origin".format(rule_id))
            if rule_id in seen:
                raise CatalogError(
                    "id duplicado: {0} em {1} e {2}".format(rule_id, seen[rule_id], path.name)
                )

            if validate_exprs:
                for expr in _collect_exprs(rule):
                    _validate_expr(rule_id, expr)

            seen[rule_id] = path.name
            rule["catalog_version"] = version
            rule["_source_file"] = path.name
            rules.append(rule)

    return sorted(rules, key=lambda r: r["id"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_rules_loader.py tests/test_rules_version_scope.py -v`
Expected: PASS, 22 tests. This also proves the 43 committed non-routing rules are structurally valid and every `expr` is accepted by the evaluator.

- [ ] **Step 7: Commit**

```bash
git add sparkforge/rules/loader.py sparkforge/rules/version_scope.py tests/test_rules_loader.py tests/test_rules_version_scope.py
git commit -m "feat(rules): add catalog loader and version guard"
```

---

## Task 6: Rules engine — closes the vertical slice

After this task, `coalesce(1)` in source produces a `SF-PY-005` Finding with anchored evidence, end to end. Everything after Task 6 broadens what already works.

**Files:**
- Create: `sparkforge/rules/engine.py`
- Test: `tests/test_rules_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rules_engine.py
import pytest

from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge

GLUE_50 = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def rule(**over):
    base = {
        "id": "SF-T-001",
        "category": "test",
        "title": "titulo",
        "requires_facts": ["k"],
        "when": {"all": [{"fact": "k", "where": {"attrs.flag": True}}]},
        "status": "structural",
        "severity_default": "P2",
        "runtime_scope": {"glue": "*"},
        "sources": [{"origin": "field-heuristic"}],
        "catalog_version": 1,
        "explanation": "porque custa",
        "proposed_change": ["mudar"],
        "risks": ["risco"],
        "validation": ["contagem total"],
        "rollback": ["reverter"],
    }
    base.update(over)
    return base


def fact(**over):
    base = {
        "kind": "k",
        "subject": {"type": "source_location", "file": "a.py", "line": 1},
        "measures": {},
        "attrs": {"flag": True},
    }
    base.update(over)
    return Fact(**base)


class TestWhereMatching:
    def test_matching_where_produces_finding(self):
        found = judge([fact()], [rule()], GLUE_50)
        assert [f.rule_id for f in found] == ["SF-T-001"]

    def test_non_matching_where_produces_nothing(self):
        assert judge([fact(attrs={"flag": False})], [rule()], GLUE_50) == []

    def test_finding_evidence_points_at_the_fact(self):
        the_fact = fact()
        found = judge([the_fact], [rule()], GLUE_50)
        assert found[0].evidence == [the_fact.id]

    def test_finding_inherits_subject_from_primary_fact(self):
        found = judge([fact()], [rule()], GLUE_50)
        assert found[0].subject == {"type": "source_location", "file": "a.py", "line": 1}

    def test_finding_carries_rule_narrative_fields(self):
        found = judge([fact()], [rule()], GLUE_50)[0]
        assert found.explanation == "porque custa"
        assert found.proposed_change == ["mudar"]
        assert found.validation == ["contagem total"]
        assert found.rollback == ["reverter"]
        assert found.sources == [{"origin": "field-heuristic"}]


class TestRequiresFacts:
    def test_rule_is_skipped_when_required_kind_absent(self):
        """Kind nao extraido nao gera falso negativo silencioso: a regra e reportada
        como skipped, nao avaliada."""
        found, skipped = judge([], [rule()], GLUE_50, return_skipped=True)
        assert found == []
        assert skipped[0]["rule_id"] == "SF-T-001"
        assert skipped[0]["reason"] == "requires_facts"


class TestVersionScope:
    def test_out_of_scope_rule_is_skipped_with_reason(self):
        scoped = rule(runtime_scope={"iceberg": ">=1.10.0"})
        found, skipped = judge([fact()], [scoped], GLUE_50, return_skipped=True)
        assert found == []
        assert skipped[0]["reason"] == "runtime_scope"
        assert skipped[0]["scope"] == {"iceberg": ">=1.10.0"}

    def test_in_scope_rule_fires(self):
        scoped = rule(runtime_scope={"iceberg": ">=1.7.0"})
        assert len(judge([fact()], [scoped], GLUE_50)) == 1


class TestExprAndThreshold:
    def test_expr_with_threshold_fires_above_limit(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        assert len(judge([fact(measures={"n": 12})], [r], GLUE_50)) == 1

    def test_expr_with_threshold_does_not_fire_below_limit(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        assert judge([fact(measures={"n": 9})], [r], GLUE_50) == []

    def test_threshold_and_measured_appear_on_the_finding(self):
        r = rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 10},
        )
        found = judge([fact(measures={"n": 12})], [r], GLUE_50)[0]
        assert found.threshold == {"n": 10}
        assert found.measured == {"n": 12}


class TestSeverityBy:
    def _rule(self):
        return rule(
            when={"all": [{"fact": "k", "expr": "measures.n >= threshold.n"}]},
            threshold={"n": 3},
            severity_by=[
                {"when": "measures.n >= 10", "severity": "P0"},
                {"when": "measures.n >= 3", "severity": "P2"},
            ],
        )

    def test_first_matching_branch_wins(self):
        assert judge([fact(measures={"n": 12})], [self._rule()], GLUE_50)[0].severity == "P0"

    def test_second_branch_when_first_does_not_match(self):
        assert judge([fact(measures={"n": 5})], [self._rule()], GLUE_50)[0].severity == "P2"


class TestAnyAndAbsent:
    def test_any_group_fires_on_one_match(self):
        r = rule(
            when={
                "any": [
                    {"fact": "k", "where": {"attrs.flag": False}},
                    {"fact": "k", "where": {"attrs.flag": True}},
                ]
            }
        )
        assert len(judge([fact()], [r], GLUE_50)) == 1

    def test_absent_condition_fires_when_kind_missing(self):
        r = rule(
            requires_facts=["k"],
            when={"all": [{"fact": "k"}, {"absent": "other.kind"}]},
        )
        assert len(judge([fact()], [r], GLUE_50)) == 1

    def test_absent_condition_blocks_when_kind_present(self):
        r = rule(
            requires_facts=["k"],
            when={"all": [{"fact": "k"}, {"absent": "other.kind"}]},
        )
        facts = [fact(), fact(kind="other.kind")]
        assert judge(facts, [r], GLUE_50) == []


class TestDeterminism:
    def test_findings_are_sorted_and_stable(self):
        r_a = rule(id="SF-T-009", severity_default="P2")
        r_b = rule(id="SF-T-002", severity_default="P0")
        first = [f.to_dict() for f in judge([fact()], [r_a, r_b], GLUE_50)]
        second = [f.to_dict() for f in judge([fact()], [r_b, r_a], GLUE_50)]
        assert first == second
        assert [f["rule_id"] for f in first] == ["SF-T-002", "SF-T-009"]


class TestVerticalSliceEndToEnd:
    """A prova da Fase 0: codigo-fonte entra, Finding ancorado sai."""

    def test_coalesce_one_yields_sf_py_005_at_the_right_line(self):
        from sparkforge.rules.loader import load_catalog

        source = 'df.select("a").coalesce(1).write.parquet("s3://b/p")\n'
        facts = extract_source(source, "lib/loader.py")
        catalog = [r for r in load_catalog() if r["id"] == "SF-PY-005"]
        assert catalog, "SF-PY-005 ausente do catalogo"

        found = judge(facts, catalog, GLUE_50)
        assert len(found) == 1
        finding = found[0]
        assert finding.rule_id == "SF-PY-005"
        assert finding.severity == "P0"
        assert finding.status == "structural"
        assert finding.subject["file"] == "lib/loader.py"
        assert finding.subject["line"] == 1
        assert len(finding.evidence) == 1
        assert finding.evidence[0].startswith("f_")

    def test_repartition_200_does_not_trigger_coalesce_rule(self):
        from sparkforge.rules.loader import load_catalog

        facts = extract_source("df.repartition(200)\n", "lib/loader.py")
        catalog = [r for r in load_catalog() if r["id"] == "SF-PY-005"]
        assert judge(facts, catalog, GLUE_50) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_rules_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.rules.engine'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/rules/engine.py
"""Motor de regras: Facts + RuntimeContext + catalogo -> Findings.

Nao le artefato bruto. So ve Facts. Regra fora do runtime_scope, ou cujo kind
nao foi extraido, e reportada como skipped com motivo, nunca silenciosamente
descartada: skip silencioso e falso negativo disfarcado.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sparkforge.findings.models import Fact, Finding, sort_findings
from sparkforge.rules.expr import ExprError, evaluate
from sparkforge.rules.version_scope import in_scope


def _dotted(container: Dict[str, Any], path: str) -> Tuple[bool, Any]:
    """Resolve 'attrs.udf_type' em {'attrs': {'udf_type': ...}}."""
    current: Any = container
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _fact_context(fact: Fact, threshold: Dict[str, Any]) -> Dict[str, Any]:
    return {"measures": fact.measures, "attrs": fact.attrs, "threshold": threshold}


def _where_matches(fact: Fact, where: Dict[str, Any]) -> bool:
    payload = {"measures": fact.measures, "attrs": fact.attrs, "subject": fact.subject}
    for path, expected in (where or {}).items():
        present, actual = _dotted(payload, path)
        if not present or actual != expected:
            return False
    return True


def _expr_matches(fact: Fact, expr: str, threshold: Dict[str, Any]) -> bool:
    try:
        return bool(evaluate(expr, _fact_context(fact, threshold)))
    except ExprError:
        # Caminho ausente significa que este fact nao tem a measure exigida.
        return False


def _condition_candidates(
    condition: Dict[str, Any], facts: Sequence[Fact], threshold: Dict[str, Any]
) -> List[Fact]:
    """Facts que satisfazem uma condicao. Lista vazia = condicao nao satisfeita."""
    kind = condition.get("fact")
    if kind is None:
        return []

    matched = []
    for fact in facts:
        if fact.kind != kind:
            continue
        if "where" in condition and not _where_matches(fact, condition["where"]):
            continue
        if "expr" in condition and not _expr_matches(fact, condition["expr"], threshold):
            continue
        matched.append(fact)
    return matched


def _absent_satisfied(condition: Dict[str, Any], facts: Sequence[Fact]) -> bool:
    kind = condition.get("absent")
    return not any(f.kind == kind for f in facts)


def _evaluate_when(
    when: Dict[str, Any], facts: Sequence[Fact], threshold: Dict[str, Any]
) -> Optional[List[Fact]]:
    """Retorna os facts de evidencia se `when` casa; None caso contrario."""
    for group, require_all in (("all", True), ("any", False)):
        conditions = when.get(group)
        if not conditions:
            continue

        evidence: List[Fact] = []
        satisfied_count = 0

        for condition in conditions:
            if "absent" in condition:
                if _absent_satisfied(condition, facts):
                    satisfied_count += 1
                elif require_all:
                    return None
                continue

            matched = _condition_candidates(condition, facts, threshold)
            if matched:
                satisfied_count += 1
                evidence.extend(matched)
            elif require_all:
                return None

        if require_all:
            return evidence
        if satisfied_count:
            return evidence
        return None

    return None


def _severity_for(rule: Dict[str, Any], fact: Fact) -> str:
    branches = rule.get("severity_by")
    if not branches:
        return rule["severity_default"]

    context = _fact_context(fact, rule.get("threshold") or {})
    for branch in branches:
        try:
            if evaluate(branch["when"], context):
                return branch["severity"]
        except ExprError:
            continue
    return rule.get("severity_default", "P3")


def _measured_for(rule: Dict[str, Any], fact: Fact) -> Dict[str, Any]:
    """Somente as measures relevantes ao limiar da regra, para a saida ser legivel."""
    threshold = rule.get("threshold") or {}
    if not threshold:
        return dict(fact.measures)
    return dict(fact.measures)


def _build_finding(rule: Dict[str, Any], evidence: Sequence[Fact]) -> Finding:
    primary = evidence[0]
    return Finding(
        rule_id=rule["id"],
        catalog_version=rule.get("catalog_version", 1),
        title=rule["title"],
        severity=_severity_for(rule, primary),
        confidence=rule.get("confidence", "high"),
        status=rule["status"],
        subject=primary.subject,
        evidence=[f.id for f in evidence],
        measured=_measured_for(rule, primary),
        threshold=dict(rule.get("threshold") or {}),
        runtime_scope=dict(rule.get("runtime_scope") or {}),
        explanation=(rule.get("explanation") or "").strip(),
        proposed_change=list(rule.get("proposed_change") or []),
        expected_effect=(rule.get("expected_effect") or "").strip(),
        benchmark_ref=rule.get("benchmark_ref", ""),
        risks=list(rule.get("risks") or []),
        tradeoffs=list(rule.get("tradeoffs") or []),
        validation=list(rule.get("validation") or []),
        rollback=list(rule.get("rollback") or []),
        sources=list(rule.get("sources") or []),
    )


def judge(
    facts: Iterable[Fact],
    rules: Iterable[Dict[str, Any]],
    runtime: Dict[str, str],
    return_skipped: bool = False,
):
    """Aplica `rules` sobre `facts`. Ordem de saida deterministica.

    Com return_skipped=True devolve (findings, skipped), onde skipped explica por
    que cada regra nao foi avaliada.
    """
    fact_list = list(facts)
    present_kinds = {f.kind for f in fact_list}
    findings: List[Finding] = []
    skipped: List[Dict[str, Any]] = []

    for rule in rules:
        scope = rule.get("runtime_scope") or {}
        if not in_scope(scope, runtime):
            skipped.append(
                {"rule_id": rule["id"], "reason": "runtime_scope", "scope": scope}
            )
            continue

        required = set(rule.get("requires_facts") or [])
        if required and not required.issubset(present_kinds):
            skipped.append(
                {
                    "rule_id": rule["id"],
                    "reason": "requires_facts",
                    "missing": sorted(required - present_kinds),
                }
            )
            continue

        threshold = rule.get("threshold") or {}
        evidence = _evaluate_when(rule.get("when") or {}, fact_list, threshold)
        if not evidence:
            continue

        findings.append(_build_finding(rule, evidence))

    ordered = sort_findings(findings)
    return (ordered, skipped) if return_skipped else ordered
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_rules_engine.py -v`
Expected: PASS, 20 tests. The two `TestVerticalSliceEndToEnd` tests are the Phase 0 proof: source in, anchored Finding out.

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -q`
Expected: all pass, no regressions in the 77 existing tests

- [ ] **Step 6: Commit**

```bash
git add sparkforge/rules/engine.py tests/test_rules_engine.py
git commit -m "feat(rules): add engine, close vertical slice"
```

---

## Task 7: JSON Schemas and output validation

The schema is what stops a weak model inventing a gain figure. It rejects a percentage in `expected_effect` when `benchmark_ref` is empty.

**Files:**
- Create: `sparkforge/findings/schemas/fact.schema.json`, `sparkforge/findings/schemas/finding.schema.json`, `sparkforge/findings/validate.py`
- Modify: `pyproject.toml` (ship schemas as package data)
- Test: `tests/test_findings_validate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_findings_validate.py
import pytest

from sparkforge.facts.pyspark_ast import extract_source
from sparkforge.findings.validate import ValidationFailed, validate_fact, validate_finding


def good_finding(**over):
    base = {
        "rule_id": "SF-PY-005",
        "schema_version": 1,
        "catalog_version": 1,
        "title": "coalesce(1)",
        "severity": "P0",
        "confidence": "high",
        "status": "structural",
        "subject": {"type": "source_location", "file": "a.py", "line": 1},
        "evidence": ["f_abc123"],
        "measured": {},
        "threshold": {},
        "runtime_scope": {"glue": "*"},
        "explanation": "explica",
        "proposed_change": ["mudar"],
        "expected_effect": "",
        "benchmark_ref": "",
        "risks": [],
        "tradeoffs": [],
        "validation": ["contagem total"],
        "rollback": ["reverter"],
        "sources": [{"origin": "field-heuristic"}],
    }
    base.update(over)
    return base


class TestFactSchema:
    def test_extracted_facts_validate(self):
        for fact in extract_source("df.coalesce(1)\n", "a.py"):
            validate_fact(fact.to_dict())

    def test_fact_without_kind_is_rejected(self):
        with pytest.raises(ValidationFailed):
            validate_fact({"id": "f_a", "schema_version": 1, "subject": {}})

    def test_fact_with_non_numeric_measure_is_rejected(self):
        bad = {
            "id": "f_a",
            "schema_version": 1,
            "kind": "k",
            "subject": {"type": "source_location"},
            "measures": {"n": "doze"},
            "attrs": {},
            "provenance": {},
        }
        with pytest.raises(ValidationFailed, match="measures"):
            validate_fact(bad)


class TestFindingSchema:
    def test_good_finding_validates(self):
        validate_finding(good_finding())

    def test_empty_evidence_rejected(self):
        with pytest.raises(ValidationFailed, match="evidence"):
            validate_finding(good_finding(evidence=[]))

    def test_unknown_severity_rejected(self):
        with pytest.raises(ValidationFailed):
            validate_finding(good_finding(severity="BLOCKER"))

    def test_unknown_status_rejected(self):
        with pytest.raises(ValidationFailed):
            validate_finding(good_finding(status="maybe"))


class TestNoInventedGains:
    """A regra que mata 'ganho de 40%' na origem."""

    @pytest.mark.parametrize(
        "effect",
        [
            "reduz o runtime em 40%",
            "ganho de 2x no tempo",
            "corta 30 % do custo",
            "melhora ~15%",
        ],
    )
    def test_quantified_effect_without_benchmark_is_rejected(self, effect):
        with pytest.raises(ValidationFailed, match="benchmark_ref"):
            validate_finding(good_finding(expected_effect=effect))

    def test_quantified_effect_with_benchmark_is_accepted(self):
        validate_finding(
            good_finding(
                expected_effect="reduz o runtime em 40%",
                benchmark_ref="bench/2026-07-29-coalesce.json",
            )
        )

    def test_qualitative_effect_without_benchmark_is_accepted(self):
        validate_finding(
            good_finding(expected_effect="hipotese: reduz o tempo do stage dominante")
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_findings_validate.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.findings.validate'`

- [ ] **Step 3: Write `fact.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sparkforge.dev/schemas/fact.schema.json",
  "title": "Fact",
  "type": "object",
  "required": ["id", "schema_version", "kind", "subject"],
  "additionalProperties": false,
  "properties": {
    "id": {"type": "string", "pattern": "^f_[0-9a-f]{6}$"},
    "schema_version": {"type": "integer", "const": 1},
    "kind": {"type": "string", "pattern": "^[a-z0-9_]+(\\.[a-z0-9_]+)+$"},
    "subject": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["source_location", "stage", "task", "tf_resource", "table", "job_run"]
        },
        "file": {"type": "string"},
        "line": {"type": "integer", "minimum": 0},
        "col": {"type": "integer", "minimum": 0},
        "end_line": {"type": "integer", "minimum": 0},
        "symbol": {"type": "string"},
        "snippet": {"type": "string"}
      }
    },
    "measures": {
      "type": "object",
      "description": "Somente numerico. Unidade no nome da chave.",
      "additionalProperties": {"type": "number"}
    },
    "attrs": {"type": "object"},
    "provenance": {
      "type": "object",
      "properties": {
        "artifact": {"type": "string"},
        "artifact_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "extractor": {"type": "string", "pattern": "^[a-z0-9_]+@[0-9]+\\.[0-9]+\\.[0-9]+$"}
      }
    }
  }
}
```

- [ ] **Step 4: Write `finding.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://sparkforge.dev/schemas/finding.schema.json",
  "title": "Finding",
  "type": "object",
  "required": [
    "rule_id",
    "schema_version",
    "title",
    "severity",
    "confidence",
    "status",
    "subject",
    "evidence"
  ],
  "properties": {
    "rule_id": {"type": "string", "pattern": "^(SF-[A-Z]+-[0-9]{3})$"},
    "schema_version": {"type": "integer", "const": 1},
    "catalog_version": {"type": "integer", "minimum": 1},
    "title": {"type": "string", "minLength": 1},
    "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3", "P4"]},
    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    "status": {"type": "string", "enum": ["structural", "confirmed"]},
    "subject": {"type": "object", "required": ["type"]},
    "evidence": {
      "type": "array",
      "minItems": 1,
      "description": "Finding sem Fact e invalido.",
      "items": {"type": "string", "pattern": "^f_[0-9a-f]{6}$"}
    },
    "measured": {"type": "object"},
    "threshold": {"type": "object"},
    "runtime_scope": {"type": "object"},
    "explanation": {"type": "string"},
    "proposed_change": {"type": "array", "items": {"type": "string"}},
    "expected_effect": {"type": "string"},
    "benchmark_ref": {"type": "string"},
    "risks": {"type": "array", "items": {"type": "string"}},
    "tradeoffs": {"type": "array", "items": {"type": "string"}},
    "validation": {"type": "array", "items": {"type": "string"}},
    "rollback": {"type": "array", "items": {"type": "string"}},
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "anyOf": [{"required": ["url"]}, {"required": ["origin"]}]
      }
    }
  }
}
```

- [ ] **Step 5: Write `validate.py`**

```python
# sparkforge/findings/validate.py
"""Validacao de saida contra JSON Schema.

Gate de saida, rigido. Nao trava investigacao; trava alucinacao. A regra que
mais importa nao e expressavel em JSON Schema puro: efeito quantificado sem
benchmark_ref e rejeitado por _reject_unbacked_gain.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import jsonschema

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"

# "40%", "40 %", "2x", "2 x" -- numero seguido de unidade de ganho.
_QUANTIFIED = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|x\b|vezes\b)", re.IGNORECASE)


class ValidationFailed(ValueError):
    """Payload rejeitado pelo schema ou pela regra de ganho sem benchmark."""


@lru_cache(maxsize=8)
def _schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / name
    if not path.is_file():
        raise ValidationFailed("schema ausente: {0}".format(path))
    return json.loads(path.read_text(encoding="utf-8"))


def _check(payload: Dict[str, Any], schema_name: str) -> None:
    try:
        jsonschema.validate(payload, _schema(schema_name))
    except jsonschema.ValidationError as exc:
        location = "/".join(str(p) for p in exc.absolute_path) or "<raiz>"
        raise ValidationFailed("{0}: {1}".format(location, exc.message)) from exc


def validate_fact(payload: Dict[str, Any]) -> None:
    _check(payload, "fact.schema.json")


def _reject_unbacked_gain(payload: Dict[str, Any]) -> None:
    effect = payload.get("expected_effect") or ""
    if not effect:
        return
    if not _QUANTIFIED.search(effect):
        return
    if payload.get("benchmark_ref"):
        return
    raise ValidationFailed(
        "expected_effect quantifica ganho ({0!r}) sem benchmark_ref. "
        "Ganho previsto sem benchmark e invencao.".format(effect)
    )


def validate_finding(payload: Dict[str, Any]) -> None:
    _check(payload, "finding.schema.json")
    _reject_unbacked_gain(payload)
```

- [ ] **Step 6: Ship the schemas as package data**

In `pyproject.toml`, add below `[tool.setuptools.packages.find]`:

```toml
[tool.setuptools.package-data]
sparkforge = ["findings/schemas/*.json"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m pytest tests/test_findings_validate.py -v`
Expected: PASS, 13 tests

- [ ] **Step 8: Commit**

```bash
git add sparkforge/findings/schemas sparkforge/findings/validate.py pyproject.toml tests/test_findings_validate.py
git commit -m "feat(findings): add JSON Schemas and reject unbacked gain claims"
```

---

## Task 8: Extractor — chain reconstruction (pass 2)

This is what makes "line by line" real. With the ordered method chain, "join before select/filter" stops being a subjective reading and becomes a predicate on indices. `SF-PY-003` depends on it.

**Files:**
- Modify: `sparkforge/facts/pyspark_ast.py`
- Test: `tests/test_facts_chain.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_facts_chain.py
from sparkforge.facts.pyspark_ast import extract_source


def only(kind, facts):
    got = [f for f in facts if f.kind == kind]
    assert len(got) == 1, "esperado 1 fact {0}, veio {1}".format(kind, len(got))
    return got[0]


class TestChainOrder:
    def test_records_ordered_methods(self):
        src = 'df.select("a").join(o, "k").filter("a > 1").write.parquet("s3://b/p")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.attrs["methods"] == ["select", "join", "filter", "write", "parquet"]

    def test_join_index_and_first_reduction_index_when_join_is_late(self):
        src = 'df.select("a").filter("a > 1").join(o, "k")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.measures["join_index"] == 2
        assert chain.measures["first_reduction_index"] == 0

    def test_join_before_reduction_is_visible_in_measures(self):
        src = 'df.join(o, "k").select("a").filter("a > 1")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.measures["join_index"] == 0
        assert chain.measures["first_reduction_index"] == 1

    def test_chain_without_join_has_no_join_index(self):
        src = 'df.select("a").filter("a > 1")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert "join_index" not in chain.measures

    def test_chain_span_covers_multiline(self):
        src = 'df.select("a") \\\n  .join(o, "k") \\\n  .filter("a > 1")\n'
        chain = only("pyspark.chain", extract_source(src, "a.py"))
        assert chain.subject["line"] == 1
        assert chain.subject["end_line"] >= 3

    def test_single_call_is_not_a_chain(self):
        assert [f for f in extract_source("df.count()\n", "a.py") if f.kind == "pyspark.chain"] == []


class TestBoundedDetection:
    def test_collect_after_limit_is_bounded(self):
        src = "rows = df.limit(10).collect()\n"
        fact = only("pyspark.driver_collect", extract_source(src, "a.py"))
        assert fact.attrs["bounded"] is True

    def test_collect_without_limit_is_unbounded(self):
        src = "rows = df.collect()\n"
        fact = only("pyspark.driver_collect", extract_source(src, "a.py"))
        assert fact.attrs["bounded"] is False

    def test_topandas_without_limit_is_unbounded(self):
        src = "pdf = df.toPandas()\n"
        fact = only("pyspark.driver_collect", extract_source(src, "a.py"))
        assert fact.attrs["bounded"] is False


class TestWithColumnRun:
    def test_counts_consecutive_withcolumn(self):
        calls = "".join('.withColumn("c{0}", lit(1))'.format(i) for i in range(12))
        fact = only("pyspark.withcolumn_run", extract_source("df" + calls + "\n", "a.py"))
        assert fact.measures["run_length"] == 12

    def test_below_threshold_still_emits_the_fact(self):
        """Extrator nao aplica limiar. Emite a contagem; a regra decide."""
        calls = "".join('.withColumn("c{0}", lit(1))'.format(i) for i in range(9))
        fact = only("pyspark.withcolumn_run", extract_source("df" + calls + "\n", "a.py"))
        assert fact.measures["run_length"] == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_facts_chain.py -v`
Expected: FAIL — `pyspark.chain`, `pyspark.driver_collect` and `pyspark.withcolumn_run` are not emitted yet

- [ ] **Step 3: Add chain reconstruction to `pyspark_ast.py`**

Insert these constants after `_PARTITION_METHODS`:

```python
_REDUCTION_METHODS = frozenset({"select", "filter", "where", "drop", "selectExpr"})
_DRIVER_COLLECT = frozenset({"collect", "toPandas", "toLocalIterator"})
_BOUNDING_METHODS = frozenset({"limit", "take", "head", "first"})
```

Add the chain walker:

```python
def _chain_methods(node: ast.Call) -> Tuple[List[str], ast.AST]:
    """Caminha a espinha Attribute/Call e devolve os metodos em ordem de escrita.

    Passe 2. A ordem e o que permite transformar 'join antes de filter' em
    predicado sobre indices, em vez de leitura subjetiva.
    """
    methods: List[str] = []
    current: ast.AST = node

    while True:
        if isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
            methods.append(current.func.attr)
            current = current.func.value
        elif isinstance(current, ast.Attribute):
            methods.append(current.attr)
            current = current.value
        else:
            break

    methods.reverse()
    return methods, current


def _chain_root_call(node: ast.Call, ctx: _Context) -> bool:
    """True se `node` e o topo da cadeia, para nao emitir um fact por elo."""
    parent = ctx.parent.get(id(node))
    if isinstance(parent, ast.Attribute):
        return False
    if isinstance(parent, ast.Call) and parent.func is node:
        return False
    return True
```

- [ ] **Step 4: Emit the three new kinds**

Inside `extract_source`, replace the `if method in _PARTITION_METHODS:` block with:

```python
        if method in _PARTITION_METHODS:
            facts.append(_partitioning_fact(node, method, path, ctx, lines, provenance))

        if method in _DRIVER_COLLECT:
            methods, _ = _chain_methods(node)
            bounded = any(m in _BOUNDING_METHODS for m in methods[:-1])
            facts.append(
                Fact(
                    kind="pyspark.driver_collect",
                    subject=_subject(node, path, ctx, lines),
                    attrs={
                        "method": method,
                        "bounded": bounded,
                        "inside_loop": ctx.loop_depth.get(id(node), 0) > 0,
                    },
                    provenance=provenance,
                )
            )

        if not _chain_root_call(node, ctx):
            continue

        methods, _ = _chain_methods(node)
        if len(methods) < 2:
            continue

        facts.append(_chain_fact(node, methods, path, ctx, lines, provenance))

        run = _longest_withcolumn_run(methods)
        if run >= 2:
            facts.append(
                Fact(
                    kind="pyspark.withcolumn_run",
                    subject=_subject(node, path, ctx, lines),
                    measures={"run_length": run},
                    attrs={"inside_loop": ctx.loop_depth.get(id(node), 0) > 0},
                    provenance=provenance,
                )
            )
```

Add the two helpers:

```python
def _chain_fact(
    node: ast.Call,
    methods: List[str],
    path: str,
    ctx: _Context,
    lines: List[str],
    provenance: Dict[str, Any],
) -> Fact:
    measures: Dict[str, Any] = {"length": len(methods)}

    join_index = next((i for i, m in enumerate(methods) if m == "join"), None)
    if join_index is not None:
        measures["join_index"] = join_index

    reduction_index = next(
        (i for i, m in enumerate(methods) if m in _REDUCTION_METHODS), None
    )
    if reduction_index is not None:
        measures["first_reduction_index"] = reduction_index

    return Fact(
        kind="pyspark.chain",
        subject=_subject(node, path, ctx, lines),
        measures=measures,
        attrs={"methods": methods},
        provenance=provenance,
    )


def _longest_withcolumn_run(methods: List[str]) -> int:
    best = 0
    current = 0
    for method in methods:
        current = current + 1 if method == "withColumn" else 0
        best = max(best, current)
    return best
```

Add `Tuple` to the `typing` import at the top of the file.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_facts_chain.py tests/test_facts_pyspark_ast.py -v`
Expected: PASS, 21 tests

- [ ] **Step 6: Commit**

```bash
git add sparkforge/facts/pyspark_ast.py tests/test_facts_chain.py
git commit -m "feat(facts): add chain reconstruction and bounded detection"
```

---

## Task 9: Extractor — remaining kinds

Completes the 17 kinds from spec §6.2. `pyspark.callgraph_edge` is emitted but consumed only in Phase 1.

**Files:**
- Modify: `sparkforge/facts/pyspark_ast.py`
- Test: `tests/test_facts_kinds.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_facts_kinds.py
import textwrap

from sparkforge.facts.pyspark_ast import extract_source

EXPECTED_KINDS = {
    "pyspark.read",
    "pyspark.write",
    "pyspark.action",
    "pyspark.driver_collect",
    "pyspark.udf",
    "pyspark.cache",
    "pyspark.partitioning",
    "pyspark.join",
    "pyspark.explode",
    "pyspark.window",
    "pyspark.chain",
    "pyspark.loop",
    "pyspark.withcolumn_run",
    "pyspark.conf_set",
    "pyspark.dedup",
    "pyspark.callgraph_edge",
    "pyspark.unresolved",
}


def kinds(src):
    return {f.kind for f in extract_source(src, "a.py")}


def one(kind, src):
    got = [f for f in extract_source(src, "a.py") if f.kind == kind]
    assert got, "nenhum fact {0}".format(kind)
    return got[0]


def test_kind_namespace_is_complete_and_documented():
    """Garante que as 17 kinds da spec secao 6.2 existem como constante."""
    from sparkforge.facts.pyspark_ast import EMITTED_KINDS

    assert EMITTED_KINDS == EXPECTED_KINDS


class TestReadWriteAction:
    def test_read_parquet(self):
        fact = one("pyspark.read", 'spark.read.parquet("s3://b/p")\n')
        assert fact.attrs["format"] == "parquet"

    def test_read_table(self):
        fact = one("pyspark.read", 'spark.table("db.tbl")\n')
        assert fact.attrs["target"] == "db.tbl"

    def test_spark_sql_is_a_read(self):
        fact = one("pyspark.read", 'spark.sql("SELECT 1")\n')
        assert fact.attrs["format"] == "sql"

    def test_write_records_mode(self):
        fact = one("pyspark.write", 'df.write.mode("append").parquet("s3://b/p")\n')
        assert fact.attrs["mode"] == "append"

    def test_writeto_append_is_a_write(self):
        fact = one("pyspark.write", 'df.writeTo("db.tbl").append()\n')
        assert fact.attrs["mode"] == "append"

    def test_count_is_an_action(self):
        assert one("pyspark.action", "df.count()\n").attrs["method"] == "count"


class TestUdf:
    def test_python_udf_decorator(self):
        src = textwrap.dedent(
            """
            @udf(returnType=StringType())
            def normaliza(x):
                return x.strip()
            """
        )
        assert one("pyspark.udf", src).attrs["udf_type"] == "python"

    def test_pandas_udf_decorator_is_distinguished(self):
        src = textwrap.dedent(
            """
            @pandas_udf("string")
            def normaliza(s):
                return s
            """
        )
        assert one("pyspark.udf", src).attrs["udf_type"] == "pandas"

    def test_udf_call_form(self):
        assert one("pyspark.udf", "f = udf(minha_funcao, StringType())\n").attrs[
            "udf_type"
        ] == "python"


class TestCache:
    def test_cache_without_unpersist_in_scope(self):
        src = textwrap.dedent(
            """
            def run(df):
                d = df.cache()
                return d.count()
            """
        )
        assert one("pyspark.cache", src).attrs["has_unpersist_in_scope"] is False

    def test_cache_with_unpersist_in_same_function(self):
        src = textwrap.dedent(
            """
            def run(df):
                d = df.cache()
                n = d.count()
                d.unpersist()
                return n
            """
        )
        assert one("pyspark.cache", src).attrs["has_unpersist_in_scope"] is True


class TestJoinExplodeWindowDedup:
    def test_join_records_how_and_broadcast_hint(self):
        fact = one("pyspark.join", 'a.join(broadcast(b), "k", how="left")\n')
        assert fact.attrs["how"] == "left"
        assert fact.attrs["has_broadcast_hint"] is True

    def test_join_without_hint(self):
        assert one("pyspark.join", 'a.join(b, "k")\n').attrs["has_broadcast_hint"] is False

    def test_explode_without_prior_reduction(self):
        fact = one("pyspark.explode", 'df.select(explode(col("arr")))\n')
        assert fact.attrs["variant"] == "explode"

    def test_window_partition_by(self):
        fact = one("pyspark.window", 'w = Window.partitionBy("k").orderBy("ts")\n')
        assert fact.attrs["has_partition_by"] is True
        assert fact.attrs["has_order_by"] is True

    def test_dedup_without_explicit_columns(self):
        assert one("pyspark.dedup", "df.dropDuplicates()\n").attrs[
            "has_explicit_columns"
        ] is False

    def test_dedup_with_explicit_columns(self):
        assert one("pyspark.dedup", 'df.dropDuplicates(["k"])\n').attrs[
            "has_explicit_columns"
        ] is True


class TestLoopAndConf:
    def test_loop_containing_write_is_flagged(self):
        src = textwrap.dedent(
            """
            for lote in lotes:
                df.filter(col("lote") == lote).write.parquet("s3://b/p")
            """
        )
        fact = one("pyspark.loop", src)
        assert fact.attrs["contains_write"] is True
        assert fact.measures["loop_depth"] == 1

    def test_loop_containing_action_is_flagged(self):
        src = "for x in xs:\n    print(df.count())\n"
        assert one("pyspark.loop", src).attrs["contains_action"] is True

    def test_loop_without_spark_work_is_not_emitted(self):
        assert "pyspark.loop" not in kinds("for x in xs:\n    total += x\n")

    def test_conf_set_records_key_and_value(self):
        fact = one("pyspark.conf_set", 'spark.conf.set("spark.sql.shuffle.partitions", "800")\n')
        assert fact.attrs["key"] == "spark.sql.shuffle.partitions"
        assert fact.attrs["value"] == "800"


class TestCallgraph:
    def test_function_to_function_edge(self):
        src = textwrap.dedent(
            """
            def helper(df):
                return df

            def run(df):
                return helper(df)
            """
        )
        edge = one("pyspark.callgraph_edge", src)
        assert edge.attrs["caller"] == "run"
        assert edge.attrs["callee"] == "helper"


class TestCleanFixtureStaysClean:
    def test_idiomatic_code_emits_no_anti_pattern_kinds(self):
        src = textwrap.dedent(
            """
            def run(spark):
                d = spark.read.parquet("s3://b/p")
                return (
                    d.select("a", "b")
                    .filter("a > 1")
                    .write.mode("append")
                    .parquet("s3://b/out")
                )
            """
        )
        got = kinds(src)
        assert "pyspark.unresolved" not in got
        assert "pyspark.driver_collect" not in got
        assert "pyspark.udf" not in got
        assert "pyspark.partitioning" not in got
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_facts_kinds.py -v`
Expected: FAIL with `ImportError: cannot import name 'EMITTED_KINDS'`

- [ ] **Step 3: Implement the remaining kinds**

Add near the top of `pyspark_ast.py`:

```python
EMITTED_KINDS = frozenset(
    {
        "pyspark.read",
        "pyspark.write",
        "pyspark.action",
        "pyspark.driver_collect",
        "pyspark.udf",
        "pyspark.cache",
        "pyspark.partitioning",
        "pyspark.join",
        "pyspark.explode",
        "pyspark.window",
        "pyspark.chain",
        "pyspark.loop",
        "pyspark.withcolumn_run",
        "pyspark.conf_set",
        "pyspark.dedup",
        "pyspark.callgraph_edge",
        "pyspark.unresolved",
    }
)

_READ_METHODS = frozenset({"parquet", "csv", "json", "orc", "load", "table", "sql", "format"})
_WRITE_TERMINALS = frozenset(
    {"parquet", "csv", "json", "orc", "save", "saveAsTable", "insertInto", "append",
     "overwritePartitions", "overwrite", "create", "replace", "createOrReplace"}
)
_ACTIONS = frozenset(
    {"collect", "count", "show", "take", "first", "head", "toPandas", "foreach",
     "foreachPartition", "toLocalIterator", "isEmpty"}
)
_CACHE_METHODS = frozenset({"cache", "persist"})
_EXPLODE_FUNCS = frozenset({"explode", "posexplode", "explode_outer", "posexplode_outer"})
_DEDUP_METHODS = frozenset({"dropDuplicates", "distinct", "drop_duplicates"})
```

> **⚠ Este passo precisa ser expandido antes da execução.** As dez funções abaixo estão
> especificadas por contrato (entrada, kind emitido, `attrs`/`measures` exatos), não por código.
> O contrato é preciso o bastante para os testes do Step 1 servirem de especificação executável,
> mas a regra do plano é código completo. Quem executar deve escrever cada emissor seguindo a
> forma de `_partitioning_fact`, e os testes do Step 1 definem o comportamento esperado de cada
> campo. Se preferir, quebre este task em dez sub-tasks de um kind cada.

Then extend `extract_source`'s call loop with the per-kind emitters. Each is a small function following the `_partitioning_fact` shape already in the file, so the loop stays readable:

- `_read_fact` — chain contains `read`, or method is `table`/`sql`. `attrs.format` from the terminal method (`sql` when the method is `sql`), `attrs.target` from the first string literal argument.
- `_write_fact` — chain contains `write` or `writeTo`; terminal in `_WRITE_TERMINALS`. `attrs.mode` from a `mode("x")` link in the chain, or from the terminal name when it is `append`/`overwritePartitions`.
- `_action_fact` — method in `_ACTIONS`. `attrs.method`.
- `_cache_fact` — method in `_CACHE_METHODS`. `attrs.has_unpersist_in_scope` is True when any `unpersist` call shares the enclosing function symbol; `attrs.storage_level` from the first argument when it is a literal or `ast.Attribute`.
- `_join_fact` — method `join`. `attrs.how` from the `how=` keyword, defaulting to `"inner"`; `attrs.on_arity` from the second positional argument; `attrs.has_broadcast_hint` True when any argument is a `Call` to `broadcast`.
- `_explode_fact` — `ast.Call` whose `func` is a `Name` in `_EXPLODE_FUNCS`. `attrs.variant` is the function name; `attrs.has_prior_reduction` True when the enclosing chain has a reduction method before this position.
- `_window_fact` — chain rooted at `Name` `Window`. `attrs.has_partition_by`, `attrs.has_order_by`, `attrs.has_frame` from membership of `partitionBy`, `orderBy`, `rowsBetween`/`rangeBetween` in the chain.
- `_dedup_fact` — method in `_DEDUP_METHODS`. `attrs.has_explicit_columns` True when there is at least one argument.
- `_conf_set_fact` — chain ending in `set` whose receiver chain contains `conf`. `attrs.key` and `attrs.value` from the two literal arguments; if either is non-literal, emit `pyspark.unresolved` with `reason: non_literal_conf` instead.
- `_udf_facts` — two forms: a `Call` to `udf`/`pandas_udf`, and a `FunctionDef` whose `decorator_list` contains one. `attrs.udf_type` is `"pandas"` for `pandas_udf`, else `"python"`; `attrs.return_type` from the first literal argument or the `returnType=` keyword when literal.

Loop and callgraph facts are emitted in a separate walk, because they are about statements rather than calls:

```python
def _loop_and_callgraph_facts(
    tree: ast.AST, path: str, ctx: _Context, lines: List[str], provenance: Dict[str, Any]
) -> List[Fact]:
    facts: List[Fact] = []
    local_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            contains_action = False
            contains_write = False
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute):
                    if inner.func.attr in _ACTIONS:
                        contains_action = True
                    methods, _ = _chain_methods(inner)
                    if "write" in methods or "writeTo" in methods:
                        contains_write = True
            if contains_action or contains_write:
                facts.append(
                    Fact(
                        kind="pyspark.loop",
                        subject=_subject(node, path, ctx, lines),
                        measures={"loop_depth": ctx.loop_depth.get(id(node), 0) + 1},
                        attrs={
                            "contains_action": contains_action,
                            "contains_write": contains_write,
                        },
                        provenance=provenance,
                    )
                )

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            callee = node.func.id
            caller = ctx.function.get(id(node), "")
            if caller and callee in local_functions and callee != caller:
                facts.append(
                    Fact(
                        kind="pyspark.callgraph_edge",
                        subject=_subject(node, path, ctx, lines),
                        attrs={"caller": caller, "callee": callee},
                        provenance=provenance,
                    )
                )

    return facts
```

Call it from `extract_source` before the final `sort_facts`, and add a module-level assertion so a typo in a kind name fails fast:

```python
    facts.extend(_loop_and_callgraph_facts(tree, path, ctx, lines, provenance))

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError("kind fora do namespace declarado: {0}".format(sorted(unknown)))

    return sort_facts(facts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_facts_kinds.py -v`
Expected: PASS, 24 tests

- [ ] **Step 5: Run the whole suite**

Run: `python -m pytest -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add sparkforge/facts/pyspark_ast.py tests/test_facts_kinds.py
git commit -m "feat(facts): complete the 17 emitted fact kinds"
```

---

## Task 10: Fixture corpus with golden outputs

Golden tests fail in both directions. Missing a finding is a false negative; inventing one is a false positive — and the second matters more, because an analyzer that shouts trains the operator to ignore it.

**Files:**
- Create: `fixtures/pyspark/<16 dirs>/`, `tests/test_fixtures_golden.py`, `scripts/regen_fixtures.py`
- Test: `tests/test_fixtures_golden.py`

- [ ] **Step 1: Write the failing golden runner**

```python
# tests/test_fixtures_golden.py
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "pyspark"

REQUIRED_FIXTURES = {
    # uma por regra SF-PY-001..012
    "python_udf",
    "collect_unbounded",
    "join_before_reduction",
    "action_in_loop",
    "coalesce_one",
    "explode_unbounded",
    "withcolumn_run",
    "cache_no_unpersist",
    "forced_broadcast",
    "repartition_literal",
    "dedup_no_columns",
    "conf_set_conflict",
    # adversariais
    "dynamic_dispatch",
    "clean_job",
    "version_out_of_scope",
    "near_threshold",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in extract_tree(directory / "input", directory / "input")]
        second = [f.to_dict() for f in extract_tree(directory / "input", directory / "input")]
        assert first == second


class TestAdversarial:
    def test_clean_job_produces_zero_findings(self):
        _, _, findings, _ = run_fixture(FIXTURES / "clean_job")
        assert findings == []

    def test_dynamic_dispatch_reports_unresolved_and_no_findings(self):
        _, facts, findings, _ = run_fixture(FIXTURES / "dynamic_dispatch")
        assert [f for f in facts if f.kind == "pyspark.unresolved"]
        assert findings == []

    def test_near_threshold_does_not_fire(self):
        """withColumn run_length = 9, limiar SF-PY-007 = 10."""
        _, facts, findings, _ = run_fixture(FIXTURES / "near_threshold")
        runs = [f for f in facts if f.kind == "pyspark.withcolumn_run"]
        assert runs and runs[0].measures["run_length"] == 9
        assert "SF-PY-007" not in {f.rule_id for f in findings}

    def test_out_of_scope_rule_is_reported_as_skipped_with_reason(self):
        _, _, findings, skipped = run_fixture(FIXTURES / "version_out_of_scope")
        by_version = [s for s in skipped if s["reason"] == "runtime_scope"]
        assert by_version, "nenhuma regra reportada como skipped por versao"
        assert "SF-ENV-002" in {s["rule_id"] for s in by_version}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fixtures_golden.py -v`
Expected: FAIL — `fixtures/pyspark` does not exist

- [ ] **Step 3: Create the fixture layout**

Each of the 16 directories has this shape. `coalesce_one` is the worked example; the other 15 follow it exactly, with the source and `expects_rules` changed.

`fixtures/pyspark/coalesce_one/meta.yaml`:

```yaml
name: coalesce_one
proves: >
  coalesce(1) força todo o dado por uma task. SF-PY-005 dispara em P0 com âncora
  exata de linha.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
  iceberg: "1.7.1"
expects_kinds: [pyspark.partitioning, pyspark.write, pyspark.chain]
expects_rules: [SF-PY-005]
```

`fixtures/pyspark/coalesce_one/input/lib/loader.py`:

```python
def gravar(df, destino):
    df.coalesce(1).write.mode("overwrite").parquet(destino)
```

Sources for the other fifteen:

| Fixture | `input/lib/job.py` content | `expects_rules` |
|---|---|---|
| `python_udf` | `@udf(returnType=StringType())` on a `def limpa(x): return x.strip()` | `SF-PY-001` |
| `collect_unbounded` | `def carregar(df): return df.collect()` | `SF-PY-002` |
| `join_before_reduction` | `def unir(a, b): return a.join(b, "k").select("x").filter("x > 1")` | `SF-PY-003` |
| `action_in_loop` | `for lote in lotes:` then `df.filter(col("lote") == lote).write.parquet(destino)` | `SF-PY-004` |
| `explode_unbounded` | `def abrir(df): return df.select(explode(col("itens")))` | `SF-PY-006` |
| `withcolumn_run` | 12 chained `.withColumn("c<i>", lit(1))` | `SF-PY-007` |
| `cache_no_unpersist` | `def run(df): d = df.cache(); return d.count()` | `SF-PY-008` |
| `forced_broadcast` | `def unir(a, b): return a.join(broadcast(b), "k")` | `SF-PY-009` |
| `repartition_literal` | `def espalhar(df): return df.repartition(347)` | `SF-PY-010` |
| `dedup_no_columns` | `def limpar(df): return df.dropDuplicates()` | `SF-PY-011` |
| `conf_set_conflict` | `spark.conf.set("spark.sql.shuffle.partitions", "800")` | `SF-PY-012` |
| `dynamic_dispatch` | `def run(df, metodo): return getattr(df, metodo)(1)` | *(empty)* |
| `clean_job` | the idiomatic read → select → filter → write from Task 9's clean test | *(empty)* |
| `near_threshold` | 9 chained `.withColumn(...)` | *(empty)* |
| `version_out_of_scope` | `df.writeTo("db.tbl").append()` plus `meta.yaml` with `runtime.glue: "5.0"`, `runtime.iceberg: "1.7.1"` so `SF-ENV-002` (`>=5.1`) is skipped by version | *(empty)* |

- [ ] **Step 4: Write the golden regenerator**

```python
# scripts/regen_fixtures.py
#!/usr/bin/env python3
"""Regenera os golden outputs das fixtures.

Rode SOMENTE quando a mudanca de comportamento for intencional, e revise o diff:
o golden e a defesa contra falso positivo, e regenerar sem ler o diff a destroi.

Uso:
    python scripts/regen_fixtures.py            # todas
    python scripts/regen_fixtures.py coalesce_one
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sparkforge.facts.pyspark_ast import extract_tree  # noqa: E402
from sparkforge.rules.engine import judge  # noqa: E402
from sparkforge.rules.loader import load_catalog  # noqa: E402

FIXTURES = ROOT / "fixtures" / "pyspark"


def regen(directory: Path) -> None:
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])

    out = directory / "expected"
    out.mkdir(exist_ok=True)
    for name, payload in (
        ("facts.json", [f.to_dict() for f in facts]),
        ("findings.json", [f.to_dict() for f in findings]),
    ):
        text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
        (out / name).write_text(text, encoding="utf-8")

    print(
        "{0}: {1} facts, {2} findings ({3})".format(
            directory.name,
            len(facts),
            len(findings),
            ", ".join(sorted({f.rule_id for f in findings})) or "nenhum",
        )
    )


def main() -> int:
    targets = sys.argv[1:]
    dirs = (
        [FIXTURES / name for name in targets]
        if targets
        else sorted(p for p in FIXTURES.iterdir() if p.is_dir())
    )
    for directory in dirs:
        regen(directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Generate the goldens and read the diff**

Run: `python scripts/regen_fixtures.py`
Expected: 16 lines. Verify each fixture's reported `rule_id` list equals its `expects_rules`, and that `clean_job`, `dynamic_dispatch`, `near_threshold` and `version_out_of_scope` report `nenhum`.

If a fixture reports a rule it should not, that is a **false positive in the analyzer** — fix the extractor or the rule, not the fixture.

- [ ] **Step 6: Run the golden tests**

Run: `python -m pytest tests/test_fixtures_golden.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add fixtures scripts/regen_fixtures.py tests/test_fixtures_golden.py
git commit -m "test: add 16 fixtures with bidirectional golden checks"
```

---

## Task 11: Runtime detection and `SF-ENV-001`

**Files:**
- Create: `sparkforge/facts/runtime_detect.py`
- Test: `tests/test_runtime_detect.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runtime_detect.py
from sparkforge.facts.runtime_detect import GLUE_MATRIX, detect_runtime


class TestMatrix:
    def test_matrix_matches_committed_knowledge(self):
        """Espelha knowledge/glue/runtime-matrix.md. Divergir aqui e bug de dado."""
        assert GLUE_MATRIX["5.1"] == {
            "spark": "3.5.6",
            "python": "3.11",
            "iceberg": "1.10.0",
        }
        assert GLUE_MATRIX["5.0"]["iceberg"] == "1.7.1"
        assert GLUE_MATRIX["4.0"]["iceberg"] == "1.0.0"
        assert GLUE_MATRIX["3.0"]["spark"] == "3.1.1"


class TestDerivation:
    def test_glue_version_derives_spark_python_iceberg(self):
        context, facts = detect_runtime({"terraform": {"glue_version": "5.0"}})
        assert context.spark == "3.5.4"
        assert context.iceberg == "1.7.1"
        assert "terraform" in context.detected_from
        assert facts

    def test_event_log_spark_version_is_used_directly(self):
        context, _ = detect_runtime({"event_log": {"spark_version": "3.5.6"}})
        assert context.spark == "3.5.6"


class TestDivergence:
    def test_conflicting_spark_version_is_recorded_not_resolved(self):
        sources = {
            "terraform": {"glue_version": "5.0"},   # implica Spark 3.5.4
            "event_log": {"spark_version": "3.3.0"},
        }
        context, facts = detect_runtime(sources)
        assert context.divergences
        assert any("spark" in d for d in context.divergences)

    def test_divergence_emits_runtime_signal_fact_with_count(self):
        sources = {
            "terraform": {"glue_version": "5.0"},
            "event_log": {"spark_version": "3.3.0"},
        }
        _, facts = detect_runtime(sources)
        signal = [f for f in facts if f.kind == "env.runtime_signal"]
        assert signal
        assert signal[0].measures["distinct_versions"] >= 2

    def test_agreement_yields_single_distinct_version(self):
        sources = {
            "terraform": {"glue_version": "5.0"},
            "event_log": {"spark_version": "3.5.4"},
        }
        context, facts = detect_runtime(sources)
        assert context.divergences == []
        signal = [f for f in facts if f.kind == "env.runtime_signal"][0]
        assert signal.measures["distinct_versions"] == 1


class TestSfEnv001FiresOnDivergence:
    def test_divergence_produces_sf_env_001(self):
        from sparkforge.rules.engine import judge
        from sparkforge.rules.loader import load_catalog

        sources = {
            "terraform": {"glue_version": "5.0"},
            "event_log": {"spark_version": "3.3.0"},
        }
        context, facts = detect_runtime(sources)
        rules = [r for r in load_catalog() if r["id"] == "SF-ENV-001"]
        findings = judge(facts, rules, context.to_dict())
        assert [f.rule_id for f in findings] == ["SF-ENV-001"]
        assert findings[0].severity == "P0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_runtime_detect.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.facts.runtime_detect'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/facts/runtime_detect.py
"""Deteccao de runtime a partir de multiplas fontes.

Divergencia entre fontes NAO e resolvida escolhendo uma: e registrada, e gera
SF-ENV-001 em P0. Aplicar limiar ou API da versao errada invalida qualquer
recomendacao seguinte.

A matriz espelha knowledge/glue/runtime-matrix.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from sparkforge.findings.models import Fact, RuntimeContext, sort_facts

GLUE_MATRIX: Dict[str, Dict[str, str]] = {
    "5.1": {"spark": "3.5.6", "python": "3.11", "iceberg": "1.10.0"},
    "5.0": {"spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"},
    "4.0": {"spark": "3.3.0", "python": "3.10", "iceberg": "1.0.0"},
    "3.0": {"spark": "3.1.1", "python": "3.7", "iceberg": "0.13.1"},
}

_PRECEDENCE = ("event_log", "terraform", "requirements")


def detect_runtime(sources: Dict[str, Dict[str, Any]]) -> Tuple[RuntimeContext, List[Fact]]:
    """Cruza as fontes. Devolve (contexto, facts)."""
    observed: Dict[str, Dict[str, str]] = {}

    def observe(key: str, value: str, origin: str) -> None:
        if not value:
            return
        observed.setdefault(key, {})[origin] = str(value)

    for origin, payload in (sources or {}).items():
        if not payload:
            continue
        glue = payload.get("glue_version")
        if glue:
            observe("glue", glue, origin)
            derived = GLUE_MATRIX.get(str(glue))
            if derived:
                for key, value in derived.items():
                    observe(key, value, origin + ":matrix")
        for key in ("spark", "python", "iceberg", "athena"):
            observe(key, payload.get(key + "_version") or payload.get(key), origin)

    resolved: Dict[str, str] = {}
    divergences: List[str] = []

    for key, by_origin in sorted(observed.items()):
        distinct = sorted(set(by_origin.values()))
        if len(distinct) > 1:
            detail = ", ".join(
                "{0}={1}".format(o, v) for o, v in sorted(by_origin.items())
            )
            divergences.append("{0}: {1}".format(key, detail))

        chosen = None
        for origin in _PRECEDENCE:
            for candidate_origin, value in by_origin.items():
                if candidate_origin.startswith(origin) and ":matrix" not in candidate_origin:
                    chosen = value
                    break
            if chosen:
                break
        resolved[key] = chosen or distinct[0]

    context = RuntimeContext(
        glue=resolved.get("glue", ""),
        spark=resolved.get("spark", ""),
        python=resolved.get("python", ""),
        iceberg=resolved.get("iceberg", ""),
        athena=resolved.get("athena", ""),
        detected_from=sorted(sources or {}),
        divergences=divergences,
    )

    facts: List[Fact] = []
    for key, by_origin in sorted(observed.items()):
        distinct = sorted(set(by_origin.values()))
        facts.append(
            Fact(
                kind="env.runtime_signal",
                subject={"type": "job_run", "symbol": key},
                measures={
                    "distinct_versions": len(distinct),
                    "source_count": len(by_origin),
                },
                attrs={
                    "component": key,
                    "resolved": resolved.get(key, ""),
                    "observed": distinct,
                    "source": "resolved",
                },
                provenance={"extractor": "runtime_detect@0.1.0"},
            )
        )

    return context, sort_facts(facts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_runtime_detect.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/runtime_detect.py tests/test_runtime_detect.py
git commit -m "feat(facts): detect runtime and record version divergence"
```

---

## Task 12: Case store

`.sparkforge/case.yaml` is the handoff bus between Devin and Claude Code. Derived state is committed; raw artifacts are not. `.gitignore` already encodes that.

**Files:**
- Create: `sparkforge/case/store.py`
- Test: `tests/test_case_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_case_store.py
import pytest
import yaml

from sparkforge.case.store import (
    CaseError,
    add_hypothesis,
    load_case,
    new_case,
    record_skill_use,
    save_case,
    set_gate,
    set_phase,
)

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


class TestNewCase:
    def test_has_required_top_level_keys(self):
        case = new_case("sf-2026-07-29-a", "2026-07-29T14:02:11Z", RUNTIME, repo="/r")
        for key in (
            "schema_version",
            "case_id",
            "created_at",
            "runtime",
            "scope",
            "phase",
            "artifacts",
            "facts_index",
            "findings_index",
            "baseline",
            "hypotheses",
            "gates",
            "skills_used",
            "open_questions",
        ):
            assert key in case

    def test_starts_in_intake_phase(self):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME)
        assert case["phase"] == "intake"

    def test_gates_start_false(self):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME)
        assert case["gates"] == {
            "baseline_captured": False,
            "dominant_bottleneck_identified": False,
            "functional_validation_defined": False,
            "flows_mapped": False,
        }

    def test_baseline_starts_null(self):
        assert new_case("c", "2026-07-29T00:00:00Z", RUNTIME)["baseline"] is None

    def test_timestamp_is_injected_never_generated(self):
        """Timestamp vem do processo, nunca do LLM, e nunca de Date.now interno."""
        case = new_case("c", "2026-07-29T09:15:00Z", RUNTIME)
        assert case["created_at"] == "2026-07-29T09:15:00Z"


class TestRoundTrip:
    def test_save_then_load_is_identical(self, tmp_path):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME, repo=str(tmp_path))
        path = save_case(case, tmp_path)
        assert path == tmp_path / ".sparkforge" / "case.yaml"
        assert load_case(tmp_path) == case

    def test_saved_yaml_is_deterministic(self, tmp_path):
        case = new_case("c", "2026-07-29T00:00:00Z", RUNTIME)
        first = save_case(case, tmp_path).read_text(encoding="utf-8")
        second = save_case(case, tmp_path).read_text(encoding="utf-8")
        assert first == second

    def test_saved_yaml_keys_are_sorted(self, tmp_path):
        save_case(new_case("c", "2026-07-29T00:00:00Z", RUNTIME), tmp_path)
        text = (tmp_path / ".sparkforge" / "case.yaml").read_text(encoding="utf-8")
        keys = [line.split(":")[0] for line in text.splitlines() if line and not line[0].isspace()]
        assert keys == sorted(keys)

    def test_load_missing_case_raises_with_actionable_message(self, tmp_path):
        with pytest.raises(CaseError, match="sparkforge case open"):
            load_case(tmp_path)

    def test_load_rejects_unknown_schema_version(self, tmp_path):
        target = tmp_path / ".sparkforge"
        target.mkdir()
        (target / "case.yaml").write_text(
            yaml.safe_dump({"schema_version": 99, "case_id": "c"}), encoding="utf-8"
        )
        with pytest.raises(CaseError, match="schema_version"):
            load_case(tmp_path)


class TestMutators:
    def _case(self):
        return new_case("c", "2026-07-29T00:00:00Z", RUNTIME)

    def test_set_phase_accepts_known_phase(self):
        assert set_phase(self._case(), "diagnosis")["phase"] == "diagnosis"

    def test_set_phase_rejects_unknown_phase(self):
        with pytest.raises(CaseError, match="fase"):
            set_phase(self._case(), "vibes")

    def test_set_gate_flips_value(self):
        case = set_gate(self._case(), "baseline_captured", True)
        assert case["gates"]["baseline_captured"] is True

    def test_set_gate_rejects_unknown_gate(self):
        with pytest.raises(CaseError, match="gate"):
            set_gate(self._case(), "vibes_ok", True)

    def test_add_hypothesis_assigns_sequential_id(self):
        case = add_hypothesis(self._case(), "loop recomputa DAG", "N jobs identicos", "materializar")
        case = add_hypothesis(case, "skew na chave nula", "max/p50 cai", "separar nulls")
        assert [h["id"] for h in case["hypotheses"]] == ["h1", "h2"]

    def test_new_hypothesis_starts_open(self):
        case = add_hypothesis(self._case(), "s", "p", "e")
        assert case["hypotheses"][0]["status"] == "open"

    def test_record_skill_use_appends_with_outcome_and_reason(self):
        case = record_skill_use(
            self._case(), "diagnose-data-skew", "2026-07-29T10:00:00Z", "skew confirmado"
        )
        entry = case["skills_used"][0]
        assert entry["skill"] == "diagnose-data-skew"
        assert entry["at"] == "2026-07-29T10:00:00Z"
        assert entry["outcome"] == "skew confirmado"

    def test_mutators_do_not_alter_the_input(self):
        original = self._case()
        set_phase(original, "diagnosis")
        assert original["phase"] == "intake"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_case_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.case.store'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/case/store.py
"""Estado da investigacao em .sparkforge/case.yaml.

E o barramento de handoff entre Devin e Claude Code: as duas ferramentas rodam em
maquinas diferentes sem contexto compartilhado, e o que trafega entre elas e
commit. Derivado e commitado; artefato bruto nao (ver .gitignore).

Timestamp SEMPRE vem de fora. A camada nao gera hora: isso mantem a saida
reproduzivel e impede o LLM de inventar tempo.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

SCHEMA_VERSION = 1
CASE_DIR = ".sparkforge"
CASE_FILE = "case.yaml"

PHASES = (
    "intake",
    "inventory",
    "facts",
    "diagnosis",
    "hypothesis",
    "experiment",
    "validation",
    "report",
)

GATES = (
    "baseline_captured",
    "dominant_bottleneck_identified",
    "functional_validation_defined",
    "flows_mapped",
)


class CaseError(ValueError):
    """Case ausente, com schema desconhecido, ou mutacao invalida."""


def case_path(root: Path) -> Path:
    return Path(root) / CASE_DIR / CASE_FILE


def new_case(
    case_id: str,
    created_at: str,
    runtime: Dict[str, Any],
    repo: str = "",
) -> Dict[str, Any]:
    return {
        "artifacts": [],
        "baseline": None,
        "case_id": case_id,
        "created_at": created_at,
        "facts_index": {"path": "", "count": 0, "by_kind": {}},
        "findings_index": {"path": "", "count": 0, "by_severity": {}},
        "gates": {gate: False for gate in GATES},
        "hypotheses": [],
        "open_questions": [],
        "phase": "intake",
        "runtime": dict(runtime),
        "schema_version": SCHEMA_VERSION,
        "scope": {"repo": repo, "entrypoints": [], "job_names": [], "consumers": []},
        "skills_used": [],
    }


def save_case(case: Dict[str, Any], root: Path) -> Path:
    path = case_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(case, sort_keys=True, allow_unicode=True, default_flow_style=False)
    path.write_text(text, encoding="utf-8")
    return path


def load_case(root: Path) -> Dict[str, Any]:
    path = case_path(root)
    if not path.is_file():
        raise CaseError(
            "case ausente em {0}. Abra com: sparkforge case open --repo {1}".format(path, root)
        )
    case = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    version = case.get("schema_version")
    if version != SCHEMA_VERSION:
        raise CaseError(
            "schema_version {0!r} nao suportado (esperado {1})".format(version, SCHEMA_VERSION)
        )
    return case


def set_phase(case: Dict[str, Any], phase: str) -> Dict[str, Any]:
    if phase not in PHASES:
        raise CaseError("fase desconhecida: {0!r} (esperado: {1})".format(phase, ", ".join(PHASES)))
    updated = copy.deepcopy(case)
    updated["phase"] = phase
    return updated


def set_gate(case: Dict[str, Any], gate: str, value: bool) -> Dict[str, Any]:
    if gate not in GATES:
        raise CaseError("gate desconhecido: {0!r} (esperado: {1})".format(gate, ", ".join(GATES)))
    updated = copy.deepcopy(case)
    updated["gates"][gate] = bool(value)
    return updated


def add_hypothesis(
    case: Dict[str, Any], statement: str, predicted_signal: str, experiment: str
) -> Dict[str, Any]:
    updated = copy.deepcopy(case)
    next_id = "h{0}".format(len(updated["hypotheses"]) + 1)
    updated["hypotheses"].append(
        {
            "id": next_id,
            "statement": statement,
            "predicted_signal": predicted_signal,
            "experiment": experiment,
            "status": "open",
        }
    )
    return updated


def record_skill_use(
    case: Dict[str, Any], skill: str, at: str, outcome: str
) -> Dict[str, Any]:
    updated = copy.deepcopy(case)
    updated["skills_used"].append({"skill": skill, "at": at, "outcome": outcome})
    return updated


def set_index(
    case: Dict[str, Any],
    which: str,
    path: str,
    count: int,
    breakdown: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    if which not in ("facts_index", "findings_index"):
        raise CaseError("indice desconhecido: {0!r}".format(which))
    updated = copy.deepcopy(case)
    key = "by_kind" if which == "facts_index" else "by_severity"
    updated[which] = {"path": path, "count": count, key: dict(breakdown or {})}
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_case_store.py -v`
Expected: PASS, 17 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/case/store.py tests/test_case_store.py
git commit -m "feat(case): add case store with injected timestamps"
```

---

## Task 13: Convert `routing.yaml` to declarative predicates, then build the router

The committed `routing.yaml` uses `len(value) > 1`, `any(h.status == 'open')` and `'athena' in value`. All three need `ast.Call` or `ast.In`, which the whitelist forbids. Weakening the evaluator is not an option: the catalog is editable data and therefore an execution surface. Convert the predicates instead.

**Files:**
- Modify: `rules/catalog/routing.yaml`, `rules/catalog/README.md`
- Create: `sparkforge/case/router.py`
- Test: `tests/test_case_router.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_case_router.py
import pytest

from sparkforge.case.router import ROUTING_OPERATORS, next_step
from sparkforge.case.store import new_case, set_gate, set_phase

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def case(phase="diagnosis", **over):
    base = set_phase(new_case("c", "2026-07-29T00:00:00Z", RUNTIME), phase)
    for key, value in over.items():
        base[key] = value
    return base


class TestOperators:
    def test_declared_operator_set_is_closed(self):
        assert ROUTING_OPERATORS == frozenset(
            {"equals", "absent", "present", "count_gt", "count_eq", "contains", "any_where"}
        )


class TestIntake:
    def test_missing_runtime_routes_to_diagnose(self):
        blank = case(phase="intake", runtime={})
        step = next_step(blank, [])
        assert step["recommended_skill"] == "sparkforge-diagnose"
        assert step["reason"].startswith("ROUTE-001")

    def test_divergent_runtime_routes_to_diagnose(self):
        divergent = case(phase="intake", runtime=dict(RUNTIME, divergences=["spark: ..."]))
        assert next_step(divergent, [])["reason"].startswith("ROUTE-001")

    def test_no_facts_routes_to_call_graph(self):
        step = next_step(case(phase="inventory"), [])
        assert step["recommended_skill"] == "analyze-library-call-graph"


class TestFindingDrivenRouting:
    def test_loop_finding_routes_to_batch_loop(self):
        step = next_step(case(), ["SF-PY-004"])
        assert step["recommended_skill"] == "analyze-batch-loop"

    def test_pruning_finding_routes_to_plan_analysis(self):
        step = next_step(case(), ["SF-PQ-002"])
        assert step["recommended_skill"] == "analyze-spark-plan"

    def test_skew_with_input_skew_routes_to_data_skew(self):
        step = next_step(case(), ["SF-UI-001", "SF-UI-002"])
        assert step["recommended_skill"] == "diagnose-data-skew"

    def test_skew_without_input_skew_routes_to_code(self):
        """Duracao desigual com input uniforme e skew de computacao. Repartition nao resolve."""
        step = next_step(case(), ["SF-UI-001"])
        assert step["recommended_skill"] == "optimize-pyspark-code"

    def test_alternatives_are_ranked(self):
        step = next_step(case(), ["SF-PY-004", "SF-PQ-002"])
        assert step["alternatives"]
        assert step["alternatives"][0]["rank"] == 2


class TestGatesAreAdvisory:
    def test_missing_baseline_is_reported_not_blocking(self):
        ready = set_gate(case(), "dominant_bottleneck_identified", True)
        step = next_step(ready, [])
        assert step["recommended_skill"] == "benchmark-pyspark-job"
        assert "baseline_captured" in step["blocked_by"]

    def test_blocked_by_is_empty_when_gates_satisfied(self):
        ready = set_gate(
            set_gate(case(), "dominant_bottleneck_identified", True), "baseline_captured", True
        )
        step = next_step(ready, [])
        assert step["blocked_by"] == []


class TestConsumers:
    def test_athena_consumer_is_detected_by_contains(self):
        with_athena = case(scope={"repo": "", "entrypoints": [], "job_names": [], "consumers": ["athena"]})
        step = next_step(with_athena, [])
        assert "cross-service-constraints" in step.get("note", "")


class TestFallback:
    def test_unmatched_state_falls_back_and_says_so(self):
        odd = case(phase="report")
        odd["gates"] = {k: True for k in odd["gates"]}
        step = next_step(odd, [])
        assert step["recommended_skill"] == "sparkforge-diagnose"
        assert "Nenhuma regra" in step["reason"]


class TestDeterminism:
    def test_same_case_yields_same_step(self):
        first = next_step(case(), ["SF-UI-001", "SF-UI-002"])
        second = next_step(case(), ["SF-UI-002", "SF-UI-001"])
        assert first == second

    def test_reason_always_cites_a_rule_id(self):
        for findings in ([], ["SF-PY-004"], ["SF-UI-001"], ["SF-ICE-002"]):
            step = next_step(case(), findings)
            assert step["reason"][:5] in ("ROUTE", "Nenhu")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_case_router.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.case.router'`

- [ ] **Step 3: Convert the four expression-based predicates in `rules/catalog/routing.yaml`**

`ROUTE-002`:

```yaml
    when:
      all:
        - {case: facts_index.count, count_eq: 0}
```

`ROUTE-003`:

```yaml
    when:
      all:
        - {case: scope.entrypoints, count_gt: 1}
        - {case: gates.flows_mapped, equals: false}
```

`ROUTE-012`:

```yaml
    when:
      all:
        - {case: gates.dominant_bottleneck_identified, equals: true}
        - {case: gates.baseline_captured, equals: false}
```

`ROUTE-013`:

```yaml
    when:
      all:
        - {case: gates.baseline_captured, equals: true}
        - {case: gates.dominant_bottleneck_identified, equals: true}
        - {case: hypotheses, any_where: {status: open}}
```

`ROUTE-014`:

```yaml
    when:
      all:
        - {case: findings_index.count, count_eq: 0}
        - {case: facts_index.count, count_gt: 0}
```

`ROUTE-015`:

```yaml
    when:
      all:
        - {case: gates.functional_validation_defined, equals: false}
```

`ROUTE-016`:

```yaml
    when:
      all:
        - {case: scope.consumers, contains: athena}
```

`ROUTE-001` keeps `absent: true` and gains `present`-style symmetry:

```yaml
    when:
      any:
        - {case: runtime.glue, absent: true}
        - {case: runtime.divergences, count_gt: 0}
```

- [ ] **Step 4: Document the operators in `rules/catalog/README.md`**

Add to the `routing.yaml` section:

```markdown
### Operadores declarativos de roteamento

Predicado de roteamento é **declarativo**, nunca expressão livre. Expressão exigiria
`Call`/`In`, que a whitelist do avaliador proíbe — e o catálogo é dado editável,
portanto superfície de execução.

| Operador | Semântica |
|---|---|
| `equals: <v>` | valor no caminho é igual a `<v>` |
| `absent: true` | caminho ausente, vazio ou `null` |
| `present: true` | caminho existe e é truthy |
| `count_gt: <n>` | comprimento (lista/dict) ou valor numérico maior que `<n>` |
| `count_eq: <n>` | comprimento ou valor numérico igual a `<n>` |
| `contains: <v>` | `<v>` está na lista do caminho |
| `any_where: {k: v}` | algum item da lista tem `k == v` |

`case: <caminho.pontuado>` resolve dentro do case. `finding: <rule_id>` com
`present: true`/`false` testa a presença de um achado.
```

- [ ] **Step 5: Write `router.py`**

```python
# sparkforge/case/router.py
"""Roteamento deterministico sobre routing.yaml.

Funcao pura: nao chama LLM. A arvore de decisao vive em dado, nao em prosa de
prompt, e e isso que sobrevive a troca de sessao Devin <-> Claude Code e a troca
de modelo.

Predicado declarativo, nunca expressao livre: expressao exigiria Call/In, que a
whitelist do avaliador proibe.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import yaml

from sparkforge.rules.loader import ROUTING_FILE, CatalogError, catalog_dir

ROUTING_OPERATORS = frozenset(
    {"equals", "absent", "present", "count_gt", "count_eq", "contains", "any_where"}
)

_MISSING = object()


def _resolve(container: Any, path: str) -> Any:
    current = container
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _length_or_value(value: Any) -> Optional[float]:
    if isinstance(value, (list, tuple, dict, str)):
        return len(value)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _condition_holds(
    condition: Dict[str, Any], case: Dict[str, Any], findings: Sequence[str]
) -> bool:
    if "finding" in condition:
        expected = condition.get("present", True)
        return (condition["finding"] in findings) is bool(expected)

    path = condition.get("case")
    if path is None:
        raise CatalogError("condicao de roteamento sem 'case' nem 'finding': {0}".format(condition))

    value = _resolve(case, path)
    missing = value is _MISSING

    operators = [key for key in condition if key in ROUTING_OPERATORS]
    if not operators:
        raise CatalogError("condicao sem operador conhecido: {0}".format(condition))

    for operator in operators:
        target = condition[operator]

        if operator == "absent":
            holds = (missing or value in (None, "", [], {})) is bool(target)
        elif operator == "present":
            holds = (not missing and bool(value)) is bool(target)
        elif missing:
            holds = False
        elif operator == "equals":
            holds = value == target
        elif operator == "contains":
            holds = isinstance(value, (list, tuple)) and target in value
        elif operator == "any_where":
            holds = isinstance(value, list) and any(
                isinstance(item, dict)
                and all(item.get(k) == v for k, v in target.items())
                for item in value
            )
        else:
            numeric = _length_or_value(value)
            if numeric is None:
                holds = False
            elif operator == "count_gt":
                holds = numeric > target
            else:
                holds = numeric == target

        if not holds:
            return False

    return True


def _rule_matches(
    rule: Dict[str, Any], case: Dict[str, Any], findings: Sequence[str]
) -> bool:
    phases = rule.get("phase_in")
    if phases and case.get("phase") not in phases:
        return False

    when = rule.get("when") or {}
    for group, require_all in (("all", True), ("any", False)):
        conditions = when.get(group)
        if not conditions:
            continue
        results = [_condition_holds(c, case, findings) for c in conditions]
        return all(results) if require_all else any(results)
    return False


def load_routing(directory: Optional[Path] = None) -> Dict[str, Any]:
    base = directory or catalog_dir()
    path = base / ROUTING_FILE
    if not path.is_file():
        raise CatalogError("routing.yaml ausente em {0}".format(base))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _unsatisfied_gates(case: Dict[str, Any], rule: Dict[str, Any]) -> List[str]:
    declared = rule.get("blocked_by") or []
    gates = case.get("gates") or {}
    return [gate for gate in declared if not gates.get(gate)]


def next_step(
    case: Dict[str, Any],
    finding_ids: Sequence[str],
    directory: Optional[Path] = None,
) -> Dict[str, Any]:
    """Proximo passo determinado por regra, nao por julgamento do modelo."""
    document = load_routing(directory)
    findings = sorted(set(finding_ids))

    matched = [
        rule for rule in document.get("rules") or [] if _rule_matches(rule, case, findings)
    ]

    if not matched:
        fallback = document.get("fallback") or {}
        return {
            "phase": case.get("phase", ""),
            "recommended_skill": fallback.get("recommended_skill", "sparkforge-diagnose"),
            "reason": (fallback.get("reason") or "Nenhuma regra de roteamento casou.").strip(),
            "evidence": [],
            "missing_artifacts": [],
            "collect_commands": [],
            "blocked_by": [],
            "alternatives": [],
        }

    primary = matched[0]
    step = {
        "phase": case.get("phase", ""),
        "recommended_skill": primary["recommended_skill"],
        "reason": "{0}: {1}".format(primary["id"], (primary.get("reason") or "").strip()),
        "evidence": list(findings),
        "missing_artifacts": list(primary.get("missing_artifacts") or []),
        "collect_commands": list(primary.get("collect_commands") or []),
        "blocked_by": _unsatisfied_gates(case, primary),
        "alternatives": [
            {
                "skill": rule["recommended_skill"],
                "reason": "{0}: {1}".format(rule["id"], (rule.get("reason") or "").strip()),
                "rank": index,
            }
            for index, rule in enumerate(matched[1:], start=2)
        ],
    }
    if primary.get("note"):
        step["note"] = primary["note"].strip()
    return step
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_case_router.py -v`
Expected: PASS, 14 tests

- [ ] **Step 7: Re-verify the whole catalog still loads**

Run: `python -m pytest tests/test_rules_loader.py -q`
Expected: PASS — routing edits did not break rule loading

- [ ] **Step 8: Commit**

```bash
git add rules/catalog/routing.yaml rules/catalog/README.md sparkforge/case/router.py tests/test_case_router.py
git commit -m "fix(rules): make routing predicates declarative and add router"
```

---

## Task 14: Resume and handoff

The requirement that started this: run out of tokens in one tool, continue in the other, same knowledge and same next step.

**Files:**
- Create: `sparkforge/case/resume.py`
- Test: `tests/test_case_resume.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_case_resume.py
from sparkforge.case.resume import HANDOFF_SECTIONS, render_handoff, resume
from sparkforge.case.store import add_hypothesis, new_case, set_phase

RUNTIME = {"glue": "5.0", "spark": "3.5.4", "python": "3.11", "iceberg": "1.7.1"}


def rich_case():
    case = set_phase(new_case("sf-a", "2026-07-29T14:02:11Z", RUNTIME), "diagnosis")
    case = add_hypothesis(case, "loop recomputa DAG", "N jobs identicos", "materializar antes")
    case["facts_index"] = {"path": ".sparkforge/facts.json", "count": 412, "by_kind": {"pyspark.loop": 2}}
    case["findings_index"] = {
        "path": ".sparkforge/findings.json",
        "count": 3,
        "by_severity": {"P0": 1, "P2": 2},
    }
    case["artifacts"] = [
        {
            "kind": "event_log",
            "path": ".sparkforge/artifacts/eventlog/jr_abc.json",
            "sha256": "a" * 64,
            "source": "s3://bucket/spark-event-logs/jr_abc",
            "collect_command": "sparkforge collect eventlog --job-run jr_abc",
            "present": False,
        }
    ]
    return case


FINDINGS = [
    {"rule_id": "SF-PY-004", "severity": "P0", "title": "Action em loop",
     "subject": {"file": "lib/loader.py", "line": 88}},
    {"rule_id": "SF-PY-008", "severity": "P2", "title": "cache sem unpersist",
     "subject": {"file": "lib/loader.py", "line": 12}},
]


class TestResumePayload:
    def test_reports_phase_and_runtime(self):
        payload = resume(rich_case(), FINDINGS)
        assert payload["phase"] == "diagnosis"
        assert payload["runtime"]["glue"] == "5.0"

    def test_reports_baseline_absent_explicitly(self):
        assert resume(rich_case(), FINDINGS)["baseline"] == "ausente"

    def test_top_findings_are_ordered_by_severity(self):
        payload = resume(rich_case(), FINDINGS)
        assert [f["rule_id"] for f in payload["top_findings"]] == ["SF-PY-004", "SF-PY-008"]

    def test_open_hypotheses_carry_their_experiment(self):
        payload = resume(rich_case(), FINDINGS)
        assert payload["open_hypotheses"][0]["experiment"] == "materializar antes"

    def test_missing_artifacts_carry_the_collect_command(self):
        payload = resume(rich_case(), FINDINGS)
        assert payload["missing_artifacts"][0]["collect_command"] == (
            "sparkforge collect eventlog --job-run jr_abc"
        )

    def test_next_step_is_included(self):
        assert resume(rich_case(), FINDINGS)["next_step"]["recommended_skill"]

    def test_coverage_reports_unresolved_count(self):
        payload = resume(rich_case(), FINDINGS, unresolved_count=7)
        assert payload["coverage"]["unresolved"] == 7

    def test_payload_is_deterministic(self):
        assert resume(rich_case(), FINDINGS) == resume(rich_case(), list(reversed(FINDINGS)))


class TestHandoffMarkdown:
    def test_has_the_ten_declared_sections_in_order(self):
        assert len(HANDOFF_SECTIONS) == 10
        text = render_handoff(resume(rich_case(), FINDINGS))
        positions = [text.index("## " + s) for s in HANDOFF_SECTIONS]
        assert positions == sorted(positions)

    def test_renders_findings_with_file_and_line(self):
        text = render_handoff(resume(rich_case(), FINDINGS))
        assert "lib/loader.py:88" in text
        assert "SF-PY-004" in text

    def test_renders_collect_command_for_missing_artifact(self):
        text = render_handoff(resume(rich_case(), FINDINGS))
        assert "sparkforge collect eventlog --job-run jr_abc" in text

    def test_states_baseline_absent(self):
        assert "ausente" in render_handoff(resume(rich_case(), FINDINGS))

    def test_is_deterministic(self):
        payload = resume(rich_case(), FINDINGS)
        assert render_handoff(payload) == render_handoff(payload)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_case_resume.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.case.resume'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/case/resume.py
"""Reidratacao e briefing de handoff.

Sessao Devin e sessao Claude Code sao maquinas diferentes sem contexto
conversacional compartilhado. Retomar do zero so funciona se o estado for
autossuficiente no repo, e este modulo e o que torna isso legivel.

Secoes fixas e ordem fixa: handoff.md e commitado, portanto precisa ser diffavel.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from sparkforge.case.router import next_step
from sparkforge.findings.models import SEVERITY_ORDER

HANDOFF_SECTIONS = (
    "Onde parou",
    "Runtime detectado",
    "Baseline",
    "Achados principais",
    "Hipoteses abertas",
    "Gates",
    "Artefatos ausentes",
    "Proximo passo",
    "Em voo na interrupcao",
    "Cobertura",
)

_TOP_FINDINGS = 10


def _severity_rank(severity: str) -> int:
    try:
        return SEVERITY_ORDER.index(severity)
    except ValueError:
        return len(SEVERITY_ORDER)


def resume(
    case: Dict[str, Any],
    findings: Sequence[Dict[str, Any]],
    unresolved_count: int = 0,
    in_flight: str = "",
) -> Dict[str, Any]:
    """Payload completo de reidratacao. Deterministico."""
    ordered = sorted(
        findings,
        key=lambda f: (_severity_rank(f.get("severity", "")), f.get("rule_id", "")),
    )

    gates = case.get("gates") or {}
    artifacts = case.get("artifacts") or []

    return {
        "case_id": case.get("case_id", ""),
        "phase": case.get("phase", ""),
        "created_at": case.get("created_at", ""),
        "runtime": dict(case.get("runtime") or {}),
        "baseline": case.get("baseline") or "ausente",
        "top_findings": [
            {
                "rule_id": f.get("rule_id", ""),
                "severity": f.get("severity", ""),
                "title": f.get("title", ""),
                "file": (f.get("subject") or {}).get("file", ""),
                "line": (f.get("subject") or {}).get("line", 0),
            }
            for f in ordered[:_TOP_FINDINGS]
        ],
        "open_hypotheses": [
            h for h in case.get("hypotheses") or [] if h.get("status") == "open"
        ],
        "gates": dict(gates),
        "unsatisfied_gates": sorted(g for g, ok in gates.items() if not ok),
        "missing_artifacts": [a for a in artifacts if not a.get("present", True)],
        "next_step": next_step(case, [f.get("rule_id", "") for f in ordered]),
        "in_flight": in_flight,
        "coverage": {
            "facts": (case.get("facts_index") or {}).get("count", 0),
            "findings": (case.get("findings_index") or {}).get("count", 0),
            "unresolved": unresolved_count,
        },
        "skills_used": list(case.get("skills_used") or []),
        "open_questions": list(case.get("open_questions") or []),
    }


def _bullets(lines: Sequence[str]) -> str:
    return "\n".join("- {0}".format(line) for line in lines) if lines else "- (nenhum)"


def render_handoff(payload: Dict[str, Any]) -> str:
    """Markdown colavel. Cobre o caso do outro lado ainda nao ter MCP configurado."""
    runtime = payload["runtime"]
    parts: List[str] = [
        "# Handoff — {0}".format(payload["case_id"]),
        "",
        "## {0}".format(HANDOFF_SECTIONS[0]),
        "",
        "Fase: **{0}**. Case aberto em {1}.".format(payload["phase"], payload["created_at"]),
        "",
        "## {0}".format(HANDOFF_SECTIONS[1]),
        "",
        _bullets(
            [
                "{0}: {1}".format(key, runtime.get(key, ""))
                for key in ("glue", "spark", "python", "iceberg", "athena")
                if runtime.get(key)
            ]
        ),
    ]

    divergences = runtime.get("divergences") or []
    if divergences:
        parts += ["", "**Divergencias de versao (SF-ENV-001):**", "", _bullets(divergences)]

    parts += [
        "",
        "## {0}".format(HANDOFF_SECTIONS[2]),
        "",
        "Baseline: **{0}**.".format(payload["baseline"]),
        "",
        "## {0}".format(HANDOFF_SECTIONS[3]),
        "",
        _bullets(
            [
                "`{rule_id}` {severity} — {title} ({file}:{line})".format(**f)
                for f in payload["top_findings"]
            ]
        ),
        "",
        "## {0}".format(HANDOFF_SECTIONS[4]),
        "",
        _bullets(
            [
                "`{0}` {1} — experimento: {2}".format(
                    h.get("id", ""), h.get("statement", ""), h.get("experiment", "")
                )
                for h in payload["open_hypotheses"]
            ]
        ),
        "",
        "## {0}".format(HANDOFF_SECTIONS[5]),
        "",
        _bullets(
            [
                "{0}: {1}".format(gate, "ok" if ok else "PENDENTE")
                for gate, ok in sorted(payload["gates"].items())
            ]
        ),
        "",
        "## {0}".format(HANDOFF_SECTIONS[6]),
        "",
        _bullets(
            [
                "{0} — recoleta: `{1}`".format(
                    a.get("kind", ""), a.get("collect_command", "(sem comando registrado)")
                )
                for a in payload["missing_artifacts"]
            ]
        ),
        "",
        "## {0}".format(HANDOFF_SECTIONS[7]),
        "",
        "Skill: **{0}**".format(payload["next_step"]["recommended_skill"]),
        "",
        "Motivo: {0}".format(payload["next_step"]["reason"]),
    ]

    blocked = payload["next_step"].get("blocked_by") or []
    if blocked:
        parts += [
            "",
            "Gates pendentes (advisory, nao bloqueiam): {0}".format(", ".join(blocked)),
        ]

    coverage = payload["coverage"]
    parts += [
        "",
        "## {0}".format(HANDOFF_SECTIONS[8]),
        "",
        payload["in_flight"] or "(nada registrado)",
        "",
        "## {0}".format(HANDOFF_SECTIONS[9]),
        "",
        "{0} facts, {1} findings, **{2} nos nao resolvidos**.".format(
            coverage["facts"], coverage["findings"], coverage["unresolved"]
        ),
        "",
    ]
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_case_resume.py -v`
Expected: PASS, 13 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/case/resume.py tests/test_case_resume.py
git commit -m "feat(case): add resume payload and handoff rendering"
```

---

## Task 15: CLI adapter

Extraction and judgment are separate verbs on purpose. That enforces the layer boundary, and it lets old facts be re-judged with a new catalog without reprocessing source — which is what makes knowledge evolution auditable.

**Files:**
- Create: `sparkforge/adapters/cli.py`
- Test: `tests/test_adapters_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapters_cli.py
import json
from pathlib import Path

import pytest

from sparkforge.adapters.cli import main

JOB = 'def gravar(df, dest):\n    df.coalesce(1).write.parquet(dest)\n'


@pytest.fixture()
def repo(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return tmp_path


def run(args, capsys):
    code = main(args)
    return code, capsys.readouterr().out


class TestAnalyze:
    def test_writes_facts_json(self, repo, capsys):
        out = repo / "facts.json"
        code, _ = run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(out)], capsys)
        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["kind"] == "pyspark.partitioning" for f in facts)

    def test_prints_summary_to_stdout(self, repo, capsys):
        _, output = run(["analyze", "pyspark", "--path", str(repo / "lib")], capsys)
        payload = json.loads(output)
        assert payload["total_count"] >= 1
        assert "by_kind" in payload

    def test_filter_by_kind(self, repo, capsys):
        _, output = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--kind", "pyspark.partitioning"],
            capsys,
        )
        payload = json.loads(output)
        assert set(payload["by_kind"]) == {"pyspark.partitioning"}

    def test_limit_and_cursor_report_truncation(self, repo, capsys):
        _, output = run(
            ["analyze", "pyspark", "--path", str(repo / "lib"), "--limit", "1"], capsys
        )
        payload = json.loads(output)
        assert payload["returned_count"] == 1
        assert payload["filters_applied"]["limit"] == 1


class TestJudge:
    def test_produces_sf_py_005(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        out = repo / "findings.json"
        code, _ = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--out", str(out)], capsys
        )
        assert code == 0
        findings = json.loads(out.read_text(encoding="utf-8"))
        assert [f["rule_id"] for f in findings] == ["SF-PY-005"]

    def test_severity_filter(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--severity", "P4"], capsys
        )
        assert json.loads(output)["returned_count"] == 0

    def test_reports_skipped_rules_with_reason(self, repo, capsys):
        facts_path = repo / "facts.json"
        run(["analyze", "pyspark", "--path", str(repo / "lib"), "--out", str(facts_path)], capsys)
        _, output = run(
            ["judge", "--facts", str(facts_path), "--glue", "5.0", "--show-skipped"], capsys
        )
        payload = json.loads(output)
        assert payload["skipped"]
        assert {"requires_facts", "runtime_scope"} & {s["reason"] for s in payload["skipped"]}


class TestCaseLifecycle:
    def test_open_then_get(self, repo, capsys):
        code, _ = run(
            ["case", "open", "--repo", str(repo), "--case-id", "c1",
             "--now", "2026-07-29T00:00:00Z", "--glue", "5.0"],
            capsys,
        )
        assert code == 0
        _, output = run(["case", "get", "--repo", str(repo)], capsys)
        assert json.loads(output)["case_id"] == "c1"

    def test_next_step_after_open(self, repo, capsys):
        run(["case", "open", "--repo", str(repo), "--case-id", "c1",
             "--now", "2026-07-29T00:00:00Z", "--glue", "5.0"], capsys)
        _, output = run(["next-step", "--repo", str(repo)], capsys)
        assert json.loads(output)["recommended_skill"]

    def test_handoff_writes_markdown(self, repo, capsys):
        run(["case", "open", "--repo", str(repo), "--case-id", "c1",
             "--now", "2026-07-29T00:00:00Z", "--glue", "5.0"], capsys)
        code, _ = run(["handoff", "--repo", str(repo)], capsys)
        assert code == 0
        assert (repo / ".sparkforge" / "handoff.md").is_file()


class TestErrorsAreActionable:
    def test_missing_case_names_the_command_that_fixes_it(self, repo, capsys):
        code = main(["case", "get", "--repo", str(repo)])
        assert code == 2
        assert "sparkforge case open" in capsys.readouterr().err

    def test_missing_facts_file_is_actionable(self, repo, capsys):
        code = main(["judge", "--facts", str(repo / "nope.json"), "--glue", "5.0"])
        assert code == 2
        assert "sparkforge analyze pyspark" in capsys.readouterr().err


class TestRuntimeAndRules:
    def test_runtime_detect_reports_matrix(self, repo, capsys):
        _, output = run(["runtime", "detect", "--glue", "5.0"], capsys)
        payload = json.loads(output)
        assert payload["spark"] == "3.5.4"
        assert payload["iceberg"] == "1.7.1"

    def test_rules_lookup_by_id_returns_full_rule(self, capsys):
        _, output = run(["rules", "lookup", "--id", "SF-PY-005"], capsys)
        rule = json.loads(output)["rules"][0]
        assert rule["id"] == "SF-PY-005"
        assert rule["sources"]
        assert rule["validation"]

    def test_rules_lookup_by_category(self, capsys):
        _, output = run(["rules", "lookup", "--category", "athena"], capsys)
        assert json.loads(output)["total_count"] == 5

    def test_validate_rejects_unbacked_gain(self, tmp_path, capsys):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40% do runtime", "benchmark_ref": "",
        }
        path = tmp_path / "f.json"
        path.write_text(json.dumps([payload]), encoding="utf-8")
        code = main(["validate", "--findings", str(path)])
        assert code == 1
        assert "benchmark_ref" in capsys.readouterr().err
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.adapters.cli'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/adapters/cli.py
"""Adaptador CLI. Casca fina: zero logica de dominio.

Extracao e julgamento sao verbos separados de proposito. Isso forca a fronteira
de camadas e permite rejulgar facts antigos com catalogo novo sem reprocessar
codigo, que e o que torna auditavel a evolucao do conhecimento.

Erro nunca e generico: traz causa, o que falta e o comando que resolve.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sparkforge import __version__
from sparkforge.case import resume as resume_mod
from sparkforge.case import store
from sparkforge.case.router import next_step
from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.findings.models import Fact, sort_facts
from sparkforge.findings.validate import ValidationFailed, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

DEFAULT_LIMIT = 50


def _emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _fail(message: str, code: int = 2) -> int:
    print(message, file=sys.stderr)
    return code


def _paginate(
    items: Sequence[Dict[str, Any]], limit: int, cursor: int
) -> Dict[str, Any]:
    window = items[cursor : cursor + limit]
    next_cursor = cursor + limit if cursor + limit < len(items) else None
    return {
        "total_count": len(items),
        "returned_count": len(window),
        "next_cursor": next_cursor,
        "items": list(window),
    }


def _runtime_from_args(args: argparse.Namespace) -> Dict[str, str]:
    sources: Dict[str, Dict[str, Any]] = {}
    if getattr(args, "glue", None):
        sources["terraform"] = {"glue_version": args.glue}
    if getattr(args, "spark", None):
        sources.setdefault("event_log", {})["spark_version"] = args.spark
    context, _ = detect_runtime(sources)
    return context.to_dict()


def _cmd_analyze_pyspark(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if not root.exists():
        return _fail("ERRO path_missing: {0} inexistente.".format(root))

    facts = extract_tree(root, repo_root=Path(args.repo) if args.repo else root)
    if args.kind:
        facts = [f for f in facts if f.kind in set(args.kind)]
    if args.path_filter:
        facts = [f for f in facts if args.path_filter in (f.subject.get("file") or "")]

    payload = [f.to_dict() for f in sort_facts(facts)]

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    by_kind: Dict[str, int] = {}
    for entry in payload:
        by_kind[entry["kind"]] = by_kind.get(entry["kind"], 0) + 1

    page = _paginate(payload, args.limit, args.cursor)
    page["by_kind"] = dict(sorted(by_kind.items()))
    page["unresolved"] = by_kind.get("pyspark.unresolved", 0)
    page["filters_applied"] = {
        "kind": sorted(args.kind) if args.kind else None,
        "path": args.path_filter,
        "limit": args.limit,
    }
    page["out"] = args.out or None
    _emit(page)
    return 0


def _load_facts(path: Path) -> List[Fact]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Fact(
            kind=entry["kind"],
            subject=entry["subject"],
            measures=entry.get("measures") or {},
            attrs=entry.get("attrs") or {},
            provenance=entry.get("provenance") or {},
        )
        for entry in raw
    ]


def _cmd_judge(args: argparse.Namespace) -> int:
    facts_path = Path(args.facts)
    if not facts_path.is_file():
        return _fail(
            "ERRO facts_missing: {0} inexistente.\n"
            "  Extraia primeiro: sparkforge analyze pyspark --path <lib> --out {0}".format(
                facts_path
            )
        )

    facts = _load_facts(facts_path)
    rules = load_catalog(validate_exprs=True)
    if args.rule:
        rules = [r for r in rules if r["id"] in set(args.rule)]

    findings, skipped = judge(facts, rules, _runtime_from_args(args), return_skipped=True)

    payload = [f.to_dict() for f in findings]
    if args.severity:
        payload = [f for f in payload if f["severity"] in set(args.severity)]
    if args.status:
        payload = [f for f in payload if f["status"] == args.status]

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    by_severity: Dict[str, int] = {}
    for entry in payload:
        by_severity[entry["severity"]] = by_severity.get(entry["severity"], 0) + 1

    page = _paginate(payload, args.limit, args.cursor)
    page["by_severity"] = dict(sorted(by_severity.items()))
    page["filters_applied"] = {
        "severity": sorted(args.severity) if args.severity else None,
        "rule": sorted(args.rule) if args.rule else None,
        "status": args.status,
        "limit": args.limit,
    }
    page["out"] = args.out or None
    if args.show_skipped:
        page["skipped"] = skipped
    _emit(page)
    return 0


def _cmd_case_open(args: argparse.Namespace) -> int:
    root = Path(args.repo)
    case = store.new_case(args.case_id, args.now, _runtime_from_args(args), repo=str(root))
    path = store.save_case(case, root)
    _emit({"case_id": args.case_id, "path": str(path), "phase": case["phase"]})
    return 0


def _cmd_case_get(args: argparse.Namespace) -> int:
    try:
        _emit(store.load_case(Path(args.repo)))
    except store.CaseError as exc:
        return _fail("ERRO case_missing: {0}".format(exc))
    return 0


def _cmd_case_update(args: argparse.Namespace) -> int:
    root = Path(args.repo)
    try:
        case = store.load_case(root)
    except store.CaseError as exc:
        return _fail("ERRO case_missing: {0}".format(exc))

    try:
        if args.phase:
            case = store.set_phase(case, args.phase)
        if args.gate:
            gate, _, raw = args.gate.partition("=")
            case = store.set_gate(case, gate, raw.strip().lower() in ("1", "true", "sim"))
        if args.skill:
            case = store.record_skill_use(case, args.skill, args.now or "", args.outcome or "")
    except store.CaseError as exc:
        return _fail("ERRO case_update: {0}".format(exc))

    store.save_case(case, root)
    _emit({"phase": case["phase"], "gates": case["gates"]})
    return 0


def _findings_for_case(root: Path) -> List[Dict[str, Any]]:
    path = root / ".sparkforge" / "findings.json"
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _cmd_next_step(args: argparse.Namespace) -> int:
    root = Path(args.repo)
    try:
        case = store.load_case(root)
    except store.CaseError as exc:
        return _fail("ERRO case_missing: {0}".format(exc))
    findings = _findings_for_case(root)
    _emit(next_step(case, [f.get("rule_id", "") for f in findings]))
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    root = Path(args.repo)
    try:
        case = store.load_case(root)
    except store.CaseError as exc:
        return _fail("ERRO case_missing: {0}".format(exc))
    _emit(resume_mod.resume(case, _findings_for_case(root)))
    return 0


def _cmd_handoff(args: argparse.Namespace) -> int:
    root = Path(args.repo)
    try:
        case = store.load_case(root)
    except store.CaseError as exc:
        return _fail("ERRO case_missing: {0}".format(exc))

    payload = resume_mod.resume(case, _findings_for_case(root))
    text = resume_mod.render_handoff(payload)
    target = root / ".sparkforge" / "handoff.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    _emit({"path": str(target), "next_step": payload["next_step"]["recommended_skill"]})
    return 0


def _cmd_runtime_detect(args: argparse.Namespace) -> int:
    _emit(_runtime_from_args(args))
    return 0


def _cmd_rules_lookup(args: argparse.Namespace) -> int:
    rules = load_catalog()
    if args.id:
        rules = [r for r in rules if r["id"] in set(args.id)]
    if args.category:
        rules = [r for r in rules if r["category"] == args.category]
    if args.symptom:
        needle = args.symptom.lower()
        rules = [
            r
            for r in rules
            if needle in r["title"].lower() or needle in (r.get("explanation") or "").lower()
        ]

    page = _paginate(rules, args.limit, args.cursor)
    page["rules"] = page.pop("items")
    _emit(page)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.findings)
    if not path.is_file():
        return _fail("ERRO findings_missing: {0} inexistente.".format(path))

    problems: List[str] = []
    for entry in json.loads(path.read_text(encoding="utf-8")):
        try:
            validate_finding(entry)
        except ValidationFailed as exc:
            problems.append("{0}: {1}".format(entry.get("rule_id", "<sem id>"), exc))

    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        return 1
    _emit({"validated": True})
    return 0


def _add_runtime_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--glue", help="versao do Glue, ex.: 5.0")
    parser.add_argument("--spark", help="versao do Spark, ex.: 3.5.4")


def _add_page_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--cursor", type=int, default=0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sparkforge", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze", help="extrai facts").add_subparsers(
        dest="target", required=True
    )
    ast_parser = analyze.add_parser("pyspark", help="AST estatico de PySpark")
    ast_parser.add_argument("--path", required=True)
    ast_parser.add_argument("--repo")
    ast_parser.add_argument("--out")
    ast_parser.add_argument("--kind", action="append")
    ast_parser.add_argument("--path-filter", dest="path_filter")
    _add_page_flags(ast_parser)
    ast_parser.set_defaults(func=_cmd_analyze_pyspark)

    judge_parser = sub.add_parser("judge", help="aplica o catalogo sobre facts")
    judge_parser.add_argument("--facts", required=True)
    judge_parser.add_argument("--out")
    judge_parser.add_argument("--severity", action="append")
    judge_parser.add_argument("--rule", action="append")
    judge_parser.add_argument("--status", choices=["structural", "confirmed"])
    judge_parser.add_argument("--show-skipped", action="store_true", dest="show_skipped")
    _add_runtime_flags(judge_parser)
    _add_page_flags(judge_parser)
    judge_parser.set_defaults(func=_cmd_judge)

    case_sub = sub.add_parser("case", help="ciclo de vida do case").add_subparsers(
        dest="case_command", required=True
    )
    open_parser = case_sub.add_parser("open")
    open_parser.add_argument("--repo", required=True)
    open_parser.add_argument("--case-id", required=True, dest="case_id")
    open_parser.add_argument("--now", required=True, help="timestamp ISO 8601")
    _add_runtime_flags(open_parser)
    open_parser.set_defaults(func=_cmd_case_open)

    get_parser = case_sub.add_parser("get")
    get_parser.add_argument("--repo", required=True)
    get_parser.set_defaults(func=_cmd_case_get)

    update_parser = case_sub.add_parser("update")
    update_parser.add_argument("--repo", required=True)
    update_parser.add_argument("--phase", choices=list(store.PHASES))
    update_parser.add_argument("--gate", help="gate=true|false")
    update_parser.add_argument("--skill")
    update_parser.add_argument("--outcome")
    update_parser.add_argument("--now")
    update_parser.set_defaults(func=_cmd_case_update)

    for name, handler in (
        ("next-step", _cmd_next_step),
        ("resume", _cmd_resume),
        ("handoff", _cmd_handoff),
    ):
        item = sub.add_parser(name)
        item.add_argument("--repo", required=True)
        item.set_defaults(func=handler)

    runtime_sub = sub.add_parser("runtime").add_subparsers(dest="runtime_command", required=True)
    detect_parser = runtime_sub.add_parser("detect")
    _add_runtime_flags(detect_parser)
    detect_parser.set_defaults(func=_cmd_runtime_detect)

    rules_sub = sub.add_parser("rules").add_subparsers(dest="rules_command", required=True)
    lookup_parser = rules_sub.add_parser("lookup")
    lookup_parser.add_argument("--id", action="append")
    lookup_parser.add_argument("--category")
    lookup_parser.add_argument("--symptom")
    _add_page_flags(lookup_parser)
    lookup_parser.set_defaults(func=_cmd_rules_lookup)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--findings", required=True)
    validate_parser.set_defaults(func=_cmd_validate)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_adapters_cli.py -v`
Expected: PASS, 16 tests

- [ ] **Step 5: Verify the entry point works after an editable install**

Run: `python -m pip install -e . --no-deps --quiet && sparkforge --version`
Expected: `0.4.0`

- [ ] **Step 6: Commit**

```bash
git add sparkforge/adapters/cli.py tests/test_adapters_cli.py
git commit -m "feat(cli): add sparkforge CLI adapter"
```

---

## Task 16: MCP adapter

`rules_lookup` and `validate_output` are the core of model independence: the model does not need to *know* the knowledge, it queries it, and its written recommendation is rejected until it conforms.

**Files:**
- Create: `sparkforge/adapters/mcp.py`, `sparkforge/adapters/tools.py`
- Test: `tests/test_adapters_tools.py`

- [ ] **Step 1: Write the failing test**

Test the tool layer, not the SDK wiring — the SDK is an optional extra and must not be needed to run the suite.

```python
# tests/test_adapters_tools.py
import json

import pytest

from sparkforge.adapters.tools import TOOLS, call_tool

JOB = 'def gravar(df, dest):\n    df.coalesce(1).write.parquet(dest)\n'


@pytest.fixture()
def repo(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "loader.py").write_text(JOB, encoding="utf-8")
    return tmp_path


class TestToolSurface:
    def test_the_ten_phase_zero_tools_are_declared(self):
        assert set(TOOLS) == {
            "sparkforge_case_open",
            "sparkforge_case_get",
            "sparkforge_case_update",
            "sparkforge_next_step",
            "sparkforge_resume",
            "sparkforge_runtime_detect",
            "sparkforge_analyze_pyspark",
            "sparkforge_judge",
            "sparkforge_rules_lookup",
            "sparkforge_validate_output",
        }

    def test_every_tool_declares_an_output_schema(self):
        for name, spec in TOOLS.items():
            assert spec["outputSchema"]["type"] == "object", name

    def test_every_tool_declares_annotations(self):
        for name, spec in TOOLS.items():
            for key in ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"):
                assert key in spec["annotations"], "{0} sem {1}".format(name, key)

    def test_no_phase_zero_tool_is_destructive(self):
        assert all(spec["annotations"]["destructiveHint"] is False for spec in TOOLS.values())

    def test_no_phase_zero_tool_is_open_world(self):
        """Nucleo e offline. Coletores AWS da Fase 1 serao openWorld."""
        assert all(spec["annotations"]["openWorldHint"] is False for spec in TOOLS.values())

    def test_only_case_writers_are_not_read_only(self):
        writers = {
            name for name, spec in TOOLS.items() if not spec["annotations"]["readOnlyHint"]
        }
        assert writers == {"sparkforge_case_open", "sparkforge_case_update"}

    def test_every_tool_has_a_description(self):
        for name, spec in TOOLS.items():
            assert len(spec["description"]) > 20, name


class TestCallTool:
    def test_analyze_returns_structured_content(self, repo):
        result = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
        assert result["total_count"] >= 1
        assert result["by_kind"]["pyspark.partitioning"] == 1

    def test_judge_finds_sf_py_005(self, repo):
        facts = call_tool("sparkforge_analyze_pyspark", {"path": str(repo / "lib")})
        result = call_tool("sparkforge_judge", {"facts": facts["items"], "glue": "5.0"})
        assert [f["rule_id"] for f in result["items"]] == ["SF-PY-005"]

    def test_rules_lookup_returns_thresholds_and_sources(self):
        result = call_tool("sparkforge_rules_lookup", {"id": ["SF-PY-007"]})
        rule = result["rules"][0]
        assert rule["threshold"] == {"run_length": 10}
        assert rule["sources"]

    def test_validate_output_rejects_unbacked_gain(self):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
            "expected_effect": "reduz 40%", "benchmark_ref": "",
        }
        result = call_tool("sparkforge_validate_output", {"finding": payload})
        assert result["valid"] is False
        assert "benchmark_ref" in result["errors"][0]

    def test_validate_output_accepts_a_clean_finding(self):
        payload = {
            "rule_id": "SF-PY-005", "schema_version": 1, "title": "t", "severity": "P0",
            "confidence": "high", "status": "structural",
            "subject": {"type": "source_location"}, "evidence": ["f_abc123"],
        }
        assert call_tool("sparkforge_validate_output", {"finding": payload})["valid"] is True

    def test_case_open_then_next_step(self, repo):
        call_tool(
            "sparkforge_case_open",
            {"repo": str(repo), "case_id": "c1", "now": "2026-07-29T00:00:00Z", "glue": "5.0"},
        )
        assert call_tool("sparkforge_next_step", {"repo": str(repo)})["recommended_skill"]

    def test_unknown_tool_raises_with_the_valid_names(self):
        with pytest.raises(KeyError, match="sparkforge_judge"):
            call_tool("sparkforge_nope", {})

    def test_error_result_carries_a_collect_command(self, repo):
        result = call_tool("sparkforge_judge", {"facts_path": str(repo / "nope.json")})
        assert "sparkforge analyze pyspark" in json.dumps(result)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.adapters.tools'`

- [ ] **Step 3: Write `tools.py`**

Declare the ten tools with `inputSchema`, `outputSchema` and annotations, and a `call_tool(name, arguments)` dispatcher that reuses the same core functions the CLI calls. Structure:

```python
# sparkforge/adapters/tools.py
"""Definicao e despacho das tools. Zero logica de dominio.

outputSchema declarado em toda tool: o cliente processa structuredContent sem
reparsear texto, e o contrato fica igual sob qualquer LLM.

Anotacoes: nenhuma tool da Fase 0 e destrutiva, nenhuma e openWorld (o nucleo e
offline). Somente case_open e case_update escrevem.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

from sparkforge.case import resume as resume_mod
from sparkforge.case import store
from sparkforge.case.router import next_step
from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.facts.runtime_detect import detect_runtime
from sparkforge.findings.models import Fact
from sparkforge.findings.validate import ValidationFailed, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

_PAGE_PROPS = {
    "limit": {"type": "integer", "default": 50},
    "cursor": {"type": "integer", "default": 0},
}

_PAGE_OUT = {
    "total_count": {"type": "integer"},
    "returned_count": {"type": "integer"},
    "next_cursor": {"type": ["integer", "null"]},
    "filters_applied": {"type": "object"},
    "items": {"type": "array"},
}


def _annotations(read_only: bool, idempotent: bool) -> Dict[str, bool]:
    return {
        "readOnlyHint": read_only,
        "destructiveHint": False,
        "idempotentHint": idempotent,
        "openWorldHint": False,
    }
```

> **⚠ Este passo precisa ser expandido antes da execução.** Uma entrada de `TOOLS` está escrita
> por extenso; as outras nove estão especificadas pela tabela de descrição e anotações abaixo.
> Os testes do Step 1 verificam `outputSchema`, anotações e descrição de **todas**, então eles
> servem de especificação executável — mas quem executar precisa escrever as nove entradas e os
> dez handlers, espelhando os comandos do CLI da Task 15.

Then one entry per tool, each with the shape:

```python
TOOLS: Dict[str, Dict[str, Any]] = {
    "sparkforge_analyze_pyspark": {
        "description": (
            "Extrai Facts ancorados em file:line:col de codigo PySpark, por AST "
            "estatico. Nunca importa nem executa o codigo analisado. Retorna "
            "contagem por kind e o total de nos nao resolvidos."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string", "description": "diretorio ou arquivo .py"},
                "repo": {"type": "string"},
                "kind": {"type": "array", "items": {"type": "string"}},
                "path_filter": {"type": "string"},
                **_PAGE_PROPS,
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                **_PAGE_OUT,
                "by_kind": {"type": "object"},
                "unresolved": {"type": "integer"},
            },
        },
        "annotations": _annotations(read_only=True, idempotent=True),
    },
    # ... nove restantes
}
```

Descriptions and annotations per tool:

| Tool | `readOnlyHint` | `idempotentHint` | Description focus |
|---|---|---|---|
| `sparkforge_case_open` | `false` | `false` | creates `.sparkforge/case.yaml`; `now` is a required ISO 8601 timestamp supplied by the caller |
| `sparkforge_case_get` | `true` | `true` | reads the case; error names `sparkforge case open` |
| `sparkforge_case_update` | `false` | `false` | sets phase, gate, or records a skill use with outcome |
| `sparkforge_next_step` | `true` | `true` | deterministic routing; `reason` always cites a `ROUTE-*` id; `blocked_by` is advisory |
| `sparkforge_resume` | `true` | `true` | full rehydration payload plus renderable handoff |
| `sparkforge_runtime_detect` | `true` | `true` | version matrix and divergences; divergence is recorded, never resolved |
| `sparkforge_analyze_pyspark` | `true` | `true` | anchored Facts, `unresolved` count |
| `sparkforge_judge` | `true` | `true` | Facts plus catalog to Findings; `skipped` explains version and missing-kind skips |
| `sparkforge_rules_lookup` | `true` | `true` | rule by id, category or symptom, with threshold, `runtime_scope` and sourced provenance — so the model queries knowledge instead of recalling it |
| `sparkforge_validate_output` | `true` | `true` | validates a Finding the model wrote; rejects empty `evidence` and quantified `expected_effect` without `benchmark_ref` |

Dispatcher:

```python
def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name not in TOOLS:
        raise KeyError(
            "tool desconhecida: {0!r}. Validas: {1}".format(name, ", ".join(sorted(TOOLS)))
        )
    return _HANDLERS[name](arguments or {})
```

Handlers mirror the CLI commands, returning dicts rather than printing, and returning an error dict with `collect_commands` instead of raising when an artifact is missing.

- [ ] **Step 4: Write `mcp.py`**

```python
# sparkforge/adapters/mcp.py
"""Servidor MCP. Casca fina sobre sparkforge.adapters.tools.

Dois transportes com o mesmo nucleo: stdio para Claude Code, Devin CLI e CI;
streamable HTTP stateless para Devin Desktop, que configura MCP por serverUrl.

Sem estado de sessao no servidor: o estado vive em .sparkforge/case.yaml, no
repositorio, que e o que permite retomar em outra ferramenta.

O SDK MCP e extra opcional. Importado tarde, para o nucleo rodar sem ele.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Optional, Sequence

from sparkforge.adapters.tools import TOOLS, call_tool


def _require_sdk():
    try:
        import mcp.server  # noqa: F401
        import mcp.types as types

        from mcp.server import Server
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "SDK MCP ausente. Instale com: pip install 'sparkforge-aws[mcp]'\n"
            "Sem MCP, use o CLI: sparkforge --help"
        ) from exc
    return Server, types


def build_server():  # pragma: no cover - exercitado por teste de integracao manual
    Server, types = _require_sdk()
    server = Server("sparkforge")

    @server.list_tools()
    async def list_tools():
        return [
            types.Tool(
                name=name,
                description=spec["description"],
                inputSchema=spec["inputSchema"],
                outputSchema=spec["outputSchema"],
                annotations=types.ToolAnnotations(**spec["annotations"]),
            )
            for name, spec in sorted(TOOLS.items())
        ]

    @server.call_tool()
    async def handle(name: str, arguments: Optional[Dict[str, Any]]):
        payload = call_tool(name, arguments or {})
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        return [types.TextContent(type="text", text=text)], payload

    return server


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(prog="sparkforge-mcp")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8931)
    args = parser.parse_args(argv)

    import asyncio

    server = build_server()

    if args.transport == "stdio":
        from mcp.server.stdio import stdio_server

        async def run_stdio():
            async with stdio_server() as (read, write):
                await server.run(read, write, server.create_initialization_options())

        asyncio.run(run_stdio())
        return 0

    from mcp.server.streamable_http import streamable_http_server

    async def run_http():
        await streamable_http_server(server, host=args.host, port=args.port, stateless=True)

    asyncio.run(run_http())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_adapters_tools.py -v`
Expected: PASS, 15 tests

- [ ] **Step 6: Confirm the core still imports without the MCP SDK**

Run: `python -m pytest tests/test_package_importable.py -v`
Expected: PASS — `sparkforge.adapters.tools` must not import the SDK at module level

- [ ] **Step 7: Commit**

```bash
git add sparkforge/adapters/tools.py sparkforge/adapters/mcp.py tests/test_adapters_tools.py
git commit -m "feat(mcp): add tool surface with outputSchema and annotations"
```

---

## Task 17: Claude Code plugin packaging

The plugin layout expects `skills/` at the repo root, which is already the source of truth. Adding two files converts the repository into an installable plugin with no reorganization.

**Files:**
- Create: `.claude-plugin/plugin.json`, `.mcp.json`, `commands/sf-open.md`, `commands/sf-next.md`, `commands/sf-resume.md`, `commands/sf-handoff.md`
- Test: `tests/test_plugin_structure.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plugin_structure.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = ("sf-open", "sf-next", "sf-resume", "sf-handoff")


class TestManifest:
    def test_manifest_is_in_the_dot_directory(self):
        assert (ROOT / ".claude-plugin" / "plugin.json").is_file()

    def test_manifest_declares_kebab_case_name_and_version(self):
        data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        assert data["name"] == "sparkforge-aws"
        assert data["version"] == "0.4.0"
        assert data["description"]

    def test_component_dirs_are_at_root_not_inside_dot_directory(self):
        for name in ("skills", "agents", "commands"):
            assert (ROOT / name).is_dir()
            assert not (ROOT / ".claude-plugin" / name).exists()


class TestMcpConfig:
    def _config(self):
        return json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))

    def test_declares_the_sparkforge_server(self):
        assert "sparkforge" in self._config()["mcpServers"]

    def test_uses_plugin_root_variable_never_an_absolute_path(self):
        text = (ROOT / ".mcp.json").read_text(encoding="utf-8")
        assert "${CLAUDE_PLUGIN_ROOT}" in text
        assert "C:\\" not in text
        assert "/Users/" not in text
        assert "E:/" not in text

    def test_invokes_the_mcp_module_over_stdio(self):
        server = self._config()["mcpServers"]["sparkforge"]
        assert server["args"][:2] == ["-m", "sparkforge.adapters.mcp"]
        assert "stdio" in server["args"]


class TestCommands:
    def test_all_four_case_commands_exist(self):
        names = {p.stem for p in (ROOT / "commands").glob("*.md")}
        assert set(COMMANDS).issubset(names)

    def test_each_command_has_frontmatter_with_name_and_description(self):
        for name in COMMANDS:
            text = (ROOT / "commands" / (name + ".md")).read_text(encoding="utf-8")
            assert text.startswith("---")
            assert "name: " + name in text
            assert "description:" in text

    def test_commands_reference_the_cli_not_a_hardcoded_path(self):
        for name in COMMANDS:
            text = (ROOT / "commands" / (name + ".md")).read_text(encoding="utf-8")
            assert "sparkforge " in text
            assert "E:/" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_plugin_structure.py -v`
Expected: FAIL — `.claude-plugin/plugin.json` does not exist

- [ ] **Step 3: Write `.claude-plugin/plugin.json`**

```json
{
  "name": "sparkforge-aws",
  "version": "0.4.0",
  "description": "Deterministic performance engineering for AWS Glue PySpark, Parquet, Iceberg and Athena: anchored evidence, version-guarded rules, portable investigations",
  "license": "MIT",
  "keywords": ["aws-glue", "pyspark", "spark", "iceberg", "athena", "performance", "tuning"]
}
```

- [ ] **Step 4: Write `.mcp.json`**

```json
{
  "mcpServers": {
    "sparkforge": {
      "command": "python",
      "args": ["-m", "sparkforge.adapters.mcp", "--transport", "stdio"],
      "env": {
        "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}",
        "SPARKFORGE_CATALOG": "${CLAUDE_PLUGIN_ROOT}/rules/catalog"
      }
    }
  }
}
```

`SPARKFORGE_CATALOG` is set explicitly so the loader finds the catalog when the plugin is installed outside a checkout, where the repo-root fallback does not apply.

- [ ] **Step 5: Write the four commands**

`commands/sf-open.md`:

```markdown
---
name: sf-open
description: Abre uma investigação SparkForge, criando .sparkforge/case.yaml com o runtime detectado
---

Abra uma investigação SparkForge.

1. Detecte o runtime antes de qualquer análise: `sparkforge runtime detect --glue <versao>`.
   Se houver divergência entre fontes, pare e reporte `SF-ENV-001` — aplicar limiar de
   versão errada invalida tudo que vier depois.
2. Abra o case com um timestamp real e um id derivado da data:
   `sparkforge case open --repo . --case-id sf-<AAAA-MM-DD>-a --now <ISO8601> --glue <versao>`
3. Registre em `scope` os entrypoints, os nomes de job e os **consumidores** (Athena entre
   eles, se houver — isso muda as restrições aplicáveis).
4. Chame `/sf-next` para o próximo passo. Não escolha a rota por conta própria.
```

`commands/sf-next.md`:

```markdown
---
name: sf-next
description: Pergunta ao roteador determinístico qual é o próximo passo da investigação
---

Obtenha o próximo passo: `sparkforge next-step --repo .`

Regras:

- A rota é decidida por `rules/catalog/routing.yaml`, não por julgamento seu. Siga o
  `recommended_skill`.
- `reason` cita um `ROUTE-*`. Repasse essa justificativa ao usuário.
- `missing_artifacts` e `collect_commands` dizem o que falta e como coletar. Execute a coleta
  em vez de assumir o dado.
- `blocked_by` é advisory: reporte o gate pendente e siga.
- Registre a skill usada e o resultado: `sparkforge case update --repo . --skill <nome> --outcome <resumo> --now <ISO8601>`
```

`commands/sf-resume.md`:

```markdown
---
name: sf-resume
description: Reidrata uma investigação SparkForge iniciada em outra ferramenta ou sessão
---

Retome uma investigação sem contexto conversacional: `sparkforge resume --repo .`

O payload traz fase, runtime, baseline, achados por severidade, hipóteses abertas com o
experimento pendente, gates, artefatos ausentes com comando de recoleta, próximo passo e
cobertura (incluindo nós não resolvidos).

Antes de concluir qualquer coisa:

- Confira `coverage.unresolved`. Nó não resolvido é ponto cego, não ausência de problema.
- Confira `runtime.divergences`. Divergente significa que nenhum limiar é confiável ainda.
- Artefato ausente: rode o `collect_command` registrado. Facts e findings já estão commitados,
  então a análise não depende do bruto — só reauditoria e extratores novos dependem.
```

`commands/sf-handoff.md`:

```markdown
---
name: sf-handoff
description: Gera .sparkforge/handoff.md para passar a investigação para Devin ou Claude Code
---

Gere o briefing de passagem: `sparkforge handoff --repo .`

Escreve `.sparkforge/handoff.md` com dez seções fixas, na mesma ordem, para ser diffável.

Depois:

1. Commite `.sparkforge/case.yaml`, `facts.json`, `findings.json`, `handoff.md` e
   `artifacts/manifest.json`. Esse commit é o barramento entre as ferramentas.
2. **Não** commite `.sparkforge/artifacts/**` — pode conter dado de negócio e centenas de MB.
   O `.gitignore` já cobre isso; o manifest registra sha256, origem e comando de recoleta.
3. Do outro lado, comece por `/sf-resume`.
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_plugin_structure.py -v`
Expected: PASS, 9 tests

- [ ] **Step 7: Commit**

```bash
git add .claude-plugin .mcp.json commands tests/test_plugin_structure.py
git commit -m "feat(plugin): package repo as Claude Code plugin"
```

---

## Task 18: `AGENT_PROTOCOL.md` and agents as a single source

There is already drift: `.claude/agents/spark-performance-architect.md` versus `.github/agents/spark-performance-engineer.agent.md` — different names, different content. A single source plus sync plus a parity test kills it.

**Files:**
- Create: `AGENT_PROTOCOL.md`, `agents/spark-performance-architect.md`, `agents/iceberg-performance-engineer.md`, `agents/glue-incremental-performance-architect.md`
- Modify: `scripts/sync_skills.py`
- Test: `tests/test_agents_parity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agents_parity.py
import filecmp
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "agents"
NAMES = (
    "spark-performance-architect",
    "iceberg-performance-engineer",
    "glue-incremental-performance-architect",
)


class TestSingleSource:
    def test_agents_dir_holds_all_three(self):
        assert {p.stem for p in AGENTS.glob("*.md")} == set(NAMES)

    def test_each_agent_has_name_description_and_tools(self):
        for name in NAMES:
            text = (AGENTS / (name + ".md")).read_text(encoding="utf-8")
            assert text.startswith("---")
            assert "name: " + name in text
            assert "description:" in text
            assert "tools:" in text

    def test_each_agent_references_the_protocol(self):
        for name in NAMES:
            text = (AGENTS / (name + ".md")).read_text(encoding="utf-8")
            assert "AGENT_PROTOCOL.md" in text

    def test_copilot_name_drift_is_gone(self):
        """spark-performance-engineer era o nome divergente no Copilot."""
        stale = ROOT / ".github" / "agents" / "spark-performance-engineer.agent.md"
        assert not stale.exists()


class TestProtocol:
    def _text(self):
        return (ROOT / "AGENT_PROTOCOL.md").read_text(encoding="utf-8")

    def test_protocol_exists(self):
        assert (ROOT / "AGENT_PROTOCOL.md").is_file()

    def test_declares_the_nine_hard_rules(self):
        text = self._text()
        for marker in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."):
            assert marker in text

    def test_forbids_numbers_without_a_fact(self):
        assert "fact_id" in self._text()

    def test_requires_next_step_before_choosing_a_skill(self):
        assert "next_step" in self._text()

    def test_requires_rules_lookup_instead_of_memory(self):
        assert "rules_lookup" in self._text()

    def test_requires_validate_output_before_presenting(self):
        assert "validate_output" in self._text()

    def test_requires_reporting_unresolved(self):
        assert "unresolved" in self._text()

    def test_requires_explicit_confirmation_for_destructive_maintenance(self):
        text = self._text()
        assert "expire_snapshots" in text
        assert "remove_orphan_files" in text


class TestMirrors:
    def test_sync_check_passes_after_sync(self):
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_skills.py")],
            check=True, capture_output=True, cwd=ROOT,
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sync_skills.py"), "--check"],
            capture_output=True, text=True, cwd=ROOT,
        )
        assert result.returncode == 0, result.stdout

    def test_claude_agents_mirror_matches_source(self):
        for name in NAMES:
            src = AGENTS / (name + ".md")
            dst = ROOT / ".claude" / "agents" / (name + ".md")
            assert dst.is_file()
            assert filecmp.cmp(src, dst, shallow=False), name

    def test_copilot_agents_mirror_exists_with_agent_md_suffix(self):
        for name in NAMES:
            assert (ROOT / ".github" / "agents" / (name + ".agent.md")).is_file()

    def test_devin_agents_mirror_matches_source(self):
        for name in NAMES:
            src = AGENTS / (name + ".md")
            dst = ROOT / ".agents" / "agents" / (name + ".md")
            assert filecmp.cmp(src, dst, shallow=False), name


class TestNoPlatformKnowledge:
    """Conhecimento nao pode viver em diretorio de plataforma, senao o drift volta."""

    FORBIDDEN = ("threshold:", "runtime_scope:", "retrieved:")

    def test_platform_dirs_carry_no_thresholds_or_sources(self):
        offenders = []
        for platform in (".claude", ".agents", ".github"):
            for path in (ROOT / platform).rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                for marker in self.FORBIDDEN:
                    if marker in text:
                        offenders.append("{0}: {1}".format(path.relative_to(ROOT), marker))
        assert not offenders, offenders
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_agents_parity.py -v`
Expected: FAIL — `agents/` and `AGENT_PROTOCOL.md` do not exist

- [ ] **Step 3: Write `AGENT_PROTOCOL.md`**

```markdown
# Protocolo do agente — SparkForge AWS

Injetado em todo agente e toda skill por `scripts/sync_skills.py`. Estas regras são duras:
elas são o que faz o resultado ser igual sob qualquer modelo e qualquer ferramenta.

## Regras

1. **Abra ou carregue o case antes de qualquer análise.** Investigação sem `.sparkforge/case.yaml` não é retomável em outra ferramenta, e retomabilidade é requisito, não conveniência.
2. **Chame `next_step` antes de escolher skill.** A árvore de decisão vive em `rules/catalog/routing.yaml`. Não escolha a rota por julgamento próprio — é isso que divergiria entre modelos.
3. **Nenhum número na saída sem `fact_id` que o sustente.** Toda afirmação quantitativa cita `rule_id` e o `fact_id` da evidência. Sem Fact, é hipótese, e tem que estar rotulada como hipótese.
4. **Use `rules_lookup` em vez de memória** para limiar, guarda de versão e fonte. Você não precisa saber o conhecimento; precisa consultá-lo.
5. **Chame `validate_output` antes de apresentar recomendação.** Ganho quantificado sem `benchmark_ref` é rejeitado pelo schema. Não contorne.
6. **Registre no case** cada skill usada, o resultado, e o motivo de não usar as descartadas.
7. **Reporte `unresolved` sempre.** Nó não resolvido é ponto cego, não ausência de problema. Nunca omita a contagem.
8. **Confirme o runtime antes de citar API ou propriedade.** Divergência entre fontes é `SF-ENV-001` em P0, e trava qualquer conclusão dependente de versão. Leia `knowledge/cross-service-constraints.md` antes de recomendar mudança de versão, formato de tabela ou particionamento.
9. **Manutenção destrutiva exige confirmação explícita** de escopo e retenção. `expire_snapshots` e `remove_orphan_files` destroem time travel e podem apagar arquivo em uso por escrita concorrente. Não há rollback para eles.

## Loop de fase

```
next_step → coletar → extrair facts → julgar → hipótese → experimento
   → medir → validar dados → atualizar case → next_step
```

Uma variável principal por experimento. Sem baseline, não há como provar impacto.

## Escada de degradação

Se as tools MCP não estiverem disponíveis: use o CLI `sparkforge`. Se o Python não estiver
disponível: leia `rules/catalog/*.yaml` diretamente — é YAML legível, com o mesmo limiar, a
mesma guarda de versão e a mesma fonte. Cai a automação, não o conhecimento.
```

- [ ] **Step 4: Write the three agents**

`agents/spark-performance-architect.md`:

```markdown
---
name: spark-performance-architect
description: Use quando precisar coordenar o diagnóstico e a otimização de um job PySpark no AWS Glue — correlacionar código, plano físico, Spark UI, Parquet e Iceberg e identificar o gargalo dominante antes de recomendar mudanças.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - sparkforge-diagnose
  - optimize-pyspark-code
  - analyze-spark-plan
  - analyze-spark-ui
  - diagnose-data-skew
  - tune-glue-job
  - optimize-parquet-layout
  - optimize-iceberg-table
  - benchmark-pyspark-job
  - review-pyspark-pr
---

Você atua como Principal Spark Performance Engineer.

**Siga `AGENT_PROTOCOL.md`.** As nove regras não são orientação; são o contrato.

Fluxo: abra o case, detecte o runtime, extraia facts com `sparkforge_analyze_pyspark`, julgue
com `sparkforge_judge`, e deixe `sparkforge_next_step` decidir a rota. Consulte limiar por
`sparkforge_rules_lookup`, nunca de memória.

Identifique o gargalo **dominante**, não o primeiro achado. Quatro das oito linhas da tabela de
decisão em `knowledge/glue/workers-and-capacity.md` têm capacidade como resposta errada — não
recomende mais workers como primeira resposta.

Nunca invente ganho. Preserve a semântica: valide contagem, schema, chaves e agregados de
controle. Exija baseline, benchmark, risco e rollback. Ao alterar código, rode os testes
disponíveis e apresente diff com plano de validação.
```

`agents/iceberg-performance-engineer.md`:

```markdown
---
name: iceberg-performance-engineer
description: Use quando o gargalo estiver em tabelas Apache Iceberg no Glue Data Catalog e S3 — small files, delete files, snapshots, manifests, metadata planning, partition spec, sort order, writes e manutenção.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - optimize-iceberg-table
  - optimize-parquet-layout
  - benchmark-pyspark-job
---

**Siga `AGENT_PROTOCOL.md`.**

Distinga as cinco camadas antes de agir: data files, delete files, manifests, snapshots e
metadata files. **Planejamento lento** aponta para manifests, snapshots e metadata.
**Leitura lenta** aponta para data files e delete files. Compactar dados quando o problema é
manifest custa horas de DPU sem ganho.

Confirme a versão de Iceberg embarcada antes de usar qualquer API: Glue 4.0 traz 1.0.0, 5.0
traz 1.7.1, 5.1 traz 1.10.0. Não cite a documentação `latest` para um runtime antigo.

Antes de recomendar mudança de format version, leia `knowledge/cross-service-constraints.md`:
Glue 5.1 escreve Iceberg V3, e **Athena não lê V3**.

Prefira corrigir na escrita — `write.distribution-mode`, `write.target-file-size-bytes` — a
compactar indefinidamente.

`expire_snapshots` e `remove_orphan_files` são destrutivos e não têm rollback. Não execute sem
escopo, retenção acordada e confirmação explícita.
```

`agents/glue-incremental-performance-architect.md`:

```markdown
---
name: glue-incremental-performance-architect
description: Use quando investigar de ponta a ponta um job ou biblioteca Glue PySpark com fluxos full e incremental, latest-per-key em Iceberg bilionário, batching, OOM após horas e cargas muito variáveis, coordenando as skills especializadas em vez de tuning localizado.
tools: Read, Grep, Glob, Bash, Edit, Write
skills:
  - glue-incremental-performance-architect
  - sparkforge-diagnose
  - analyze-library-call-graph
  - design-incremental-processing
  - optimize-latest-per-key
  - analyze-batch-loop
  - diagnose-oom
  - optimize-variable-volume-job
  - review-glue-terraform
  - optimize-pyspark-code
  - analyze-spark-plan
  - analyze-spark-ui
  - diagnose-data-skew
  - tune-glue-job
  - optimize-parquet-layout
  - optimize-iceberg-table
  - benchmark-pyspark-job
---

**Siga `AGENT_PROTOCOL.md`.** Leia `PROMPT_INICIAL_MESTRE.md`.

Conduza investigação ponta a ponta. Mapeie biblioteca e os dois fluxos antes de alterar código:
sem separar o DAG do full e do incremental, trabalho global rodando no incremental fica
invisível.

Questione, em ordem: falso incremental; latest-per-key recalculado sobre todo o histórico;
batching que só filtra um DAG caro antes de cada action em vez de reduzir trabalho na origem;
OOM classificado errado; e dívida de metadados Iceberg acumulada por commit em loop.

Classifique OOM entre as sete classes de `knowledge/spark/memory-and-oom.md`. Executor removido
sem OOM de heap no log é overhead de container, não heap — a correção é `memoryOverhead`, e
"aumentei a memória e continuou" é a assinatura de ter classificado errado.

Para OOM que aparece depois de horas, plote heap do driver **ao longo** do run. Crescimento
monotônico é acúmulo; pico isolado no fim é dado.

Revise Terraform só depois de ter evidência. Produza arquitetura-alvo, experimentos, validação
funcional e rollback.
```

- [ ] **Step 5: Extend `scripts/sync_skills.py`**

Add agent mirroring and protocol injection. After the existing `MIRRORS` constant, add:

```python
AGENTS_SRC = ROOT / "agents"
AGENT_MIRRORS = (
    (ROOT / ".claude" / "agents", "{stem}.md"),
    (ROOT / ".agents" / "agents", "{stem}.md"),
    (ROOT / ".github" / "agents", "{stem}.agent.md"),
)
STALE_AGENTS = (ROOT / ".github" / "agents" / "spark-performance-engineer.agent.md",)


def iter_agent_files() -> list[Path]:
    return sorted(p for p in AGENTS_SRC.glob("*.md"))


def check_agents() -> list[str]:
    problems: list[str] = []
    for stale in STALE_AGENTS:
        if stale.exists():
            problems.append(f"OBSOLETO {stale}")
    for src in iter_agent_files():
        for mirror, pattern in AGENT_MIRRORS:
            dst = mirror / pattern.format(stem=src.stem)
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not filecmp.cmp(src, dst, shallow=False):
                problems.append(f"DIVERGENTE {dst}")
    return problems


def sync_agents() -> int:
    changed = 0
    for stale in STALE_AGENTS:
        if stale.exists():
            stale.unlink()
            print(f"DEL  {stale}")
            changed += 1
    for src in iter_agent_files():
        for mirror, pattern in AGENT_MIRRORS:
            dst = mirror / pattern.format(stem=src.stem)
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPY {dst}")
            changed += 1
    return changed
```

Wire them in: in `check()`, append `problems.extend(check_agents())` before the final `if problems:`; in `sync()`, add `changed += sync_agents()` before the summary print. Update the module docstring to say agents are mirrored too.

The Copilot mirror is byte-identical to the source, only the filename differs. Copilot reads the frontmatter the same way, so no transformation is needed — and byte identity is what makes the parity test meaningful.

- [ ] **Step 6: Run the sync and the tests**

Run: `python scripts/sync_skills.py`
Expected: `COPY` lines for nine agent mirrors, one `DEL` for the stale Copilot file

Run: `python -m pytest tests/test_agents_parity.py -v`
Expected: PASS, 15 tests

- [ ] **Step 7: Inject the protocol reference into every skill**

Append this block to each of the 18 files in `skills/*/SKILL.md`, then re-sync:

```markdown

## Protocolo

Siga `AGENT_PROTOCOL.md`. Resumo: abra o case antes de analisar; chame `next_step` antes de
escolher skill; nenhum número sem `fact_id`; `rules_lookup` em vez de memória para limiar e
versão; `validate_output` antes de apresentar; reporte `unresolved`; confirme o runtime;
manutenção destrutiva só com confirmação explícita.
```

Run: `python scripts/sync_skills.py && python -m pytest tests/test_skill_content.py tests/test_agents_parity.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add AGENT_PROTOCOL.md agents skills .claude .agents .github scripts/sync_skills.py tests/test_agents_parity.py
git commit -m "feat(agents): add protocol and single-source agents"
```

---

## Task 19: `parity.yaml` and the capability parity gate

**Files:**
- Create: `parity.yaml`
- Test: `tests/test_capability_parity.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_capability_parity.py
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ("claude_code", "devin_desktop", "devin_cli", "copilot_ci")
MECHANISMS = ("mcp", "cli", "files")


def manifest():
    return yaml.safe_load((ROOT / "parity.yaml").read_text(encoding="utf-8"))


class TestManifestShape:
    def test_exists(self):
        assert (ROOT / "parity.yaml").is_file()

    def test_declares_the_four_platforms(self):
        assert tuple(manifest()["platforms"]) == PLATFORMS

    def test_declares_the_three_mechanisms(self):
        assert tuple(manifest()["mechanisms"]) == MECHANISMS


class TestEveryCapabilityHasAPathEverywhere:
    def test_no_capability_is_missing_a_platform(self):
        gaps = []
        for capability in manifest()["capabilities"]:
            for platform in PLATFORMS:
                if not capability["platforms"].get(platform):
                    gaps.append("{0} sem {1}".format(capability["name"], platform))
        assert not gaps, gaps

    def test_every_declared_mechanism_is_known(self):
        for capability in manifest()["capabilities"]:
            for platform, mechanisms in capability["platforms"].items():
                for mechanism in mechanisms:
                    assert mechanism in MECHANISMS, (capability["name"], platform, mechanism)

    def test_every_capability_reaches_the_files_rung(self):
        """Terceiro degrau: sem MCP e sem Python, o conhecimento ainda chega."""
        for capability in manifest()["capabilities"]:
            if capability.get("automation_only"):
                continue
            for platform in PLATFORMS:
                assert "files" in capability["platforms"][platform], capability["name"]


class TestManifestMatchesReality:
    def test_every_declared_tool_exists_in_the_tool_surface(self):
        from sparkforge.adapters.tools import TOOLS

        for capability in manifest()["capabilities"]:
            for tool in capability.get("tools") or []:
                assert tool in TOOLS, tool

    def test_the_cli_exposes_every_verb_the_manifest_relies_on(self):
        from sparkforge.adapters.cli import build_parser

        parser = build_parser()
        subparsers = next(
            action for action in parser._actions if hasattr(action, "choices") and action.choices
        )
        assert {"analyze", "judge", "case", "next-step", "resume", "handoff",
                "runtime", "rules", "validate"}.issubset(set(subparsers.choices))

    def test_every_declared_knowledge_file_exists(self):
        for capability in manifest()["capabilities"]:
            for path in capability.get("knowledge") or []:
                assert (ROOT / path).is_file(), path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_capability_parity.py -v`
Expected: FAIL — `parity.yaml` does not exist

- [ ] **Step 3: Write `parity.yaml`**

```yaml
# Manifesto de paridade: capacidade x plataforma x mecanismo.
# Falha de CI se alguma capacidade nao tiver caminho em alguma plataforma.
# Ver docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md secao 8.

schema_version: 1

platforms: [claude_code, devin_desktop, devin_cli, copilot_ci]
mechanisms: [mcp, cli, files]

notes: >
  Devin Desktop configura MCP por serverUrl (HTTP); Claude Code, Devin CLI e CI usam stdio.
  Devin CLI nao le Knowledge nem Playbooks da conta Devin, por isso o procedimento e
  autoritativo em arquivo no repo, nunca em Playbook.

capabilities:
  - name: detectar runtime e divergencia de versao
    tools: [sparkforge_runtime_detect]
    knowledge: [knowledge/glue/runtime-matrix.md, knowledge/cross-service-constraints.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: extrair facts ancorados de codigo PySpark
    tools: [sparkforge_analyze_pyspark]
    knowledge: [knowledge/spark/execution-model.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: julgar facts contra o catalogo versionado
    tools: [sparkforge_judge]
    knowledge: [rules/catalog/README.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: consultar regra com limiar, guarda de versao e fonte
    tools: [sparkforge_rules_lookup]
    knowledge: [rules/catalog/README.md, knowledge/INDEX.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: validar recomendacao escrita pelo modelo
    tools: [sparkforge_validate_output]
    knowledge: [AGENT_PROTOCOL.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: manter estado da investigacao
    tools: [sparkforge_case_open, sparkforge_case_get, sparkforge_case_update]
    knowledge: [AGENT_PROTOCOL.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: rotear proximo passo deterministicamente
    tools: [sparkforge_next_step]
    knowledge: [rules/catalog/routing.yaml]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: retomar investigacao iniciada em outra ferramenta
    tools: [sparkforge_resume]
    knowledge: [AGENT_PROTOCOL.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]

  - name: aplicar conhecimento de performance sem ferramenta alguma
    knowledge:
      - knowledge/INDEX.md
      - knowledge/spark/config-reference.md
      - knowledge/spark/shuffle-join-skew.md
      - knowledge/spark/memory-and-oom.md
      - knowledge/spark/plan-reading.md
      - knowledge/glue/workers-and-capacity.md
      - knowledge/glue/observability.md
      - knowledge/glue/job-arguments.md
      - knowledge/athena/performance.md
      - knowledge/storage/parquet-layout.md
      - knowledge/storage/iceberg-performance.md
      - knowledge/cross-service-constraints.md
    platforms:
      claude_code: [files]
      devin_desktop: [files]
      devin_cli: [files]
      copilot_ci: [files]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_capability_parity.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add parity.yaml tests/test_capability_parity.py
git commit -m "test: add capability parity manifest and gate"
```

---

## Task 20: Evaluation suite

The eval measures whether an agent *uses the tools correctly*. Facts and Findings are identical across models by construction and are covered by the golden tests, not here. A failed eval is fixed in the tool description or the protocol, never by swapping the model.

**Files:**
- Create: `evals/fase0.xml`, `evals/README.md`, `scripts/check_evals.py`
- Modify: `pyproject.toml` (add `defusedxml` to `[dev]`)
- Test: `tests/test_evals.py`

- [ ] **Step 1: Add the XML parsing dependency**

In `pyproject.toml`, change the `dev` extra to:

```toml
dev = ["pytest>=8.0", "ruff>=0.6", "defusedxml>=0.7"]
```

Then: `python -m pip install -e ".[dev]" --quiet`

- [ ] **Step 2: Write the failing test**

`defusedxml` is used instead of `xml.etree`: the stdlib parsers are vulnerable to XXE and billion-laughs by default. The eval file is repo-controlled today, but a parser that is safe only because of who wrote the input is not safe.

```python
# tests/test_evals.py
from pathlib import Path

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "fase0.xml"


def pairs():
    tree = ET.parse(EVAL)
    return [
        (p.findtext("question", "").strip(), p.findtext("answer", "").strip())
        for p in tree.getroot().findall("qa_pair")
    ]


class TestShape:
    def test_file_exists(self):
        assert EVAL.is_file()

    def test_has_exactly_ten_pairs(self):
        assert len(pairs()) == 10

    def test_every_question_and_answer_is_non_empty(self):
        for question, answer in pairs():
            assert question and answer

    def test_answers_are_short_enough_for_string_comparison(self):
        for _, answer in pairs():
            assert len(answer) <= 80, answer

    def test_questions_are_unique(self):
        questions = [q for q, _ in pairs()]
        assert len(questions) == len(set(questions))


class TestAnswersAreDerivableFromTheFixtures:
    """Cada resposta e verificavel contra o corpus, nao contra opiniao."""

    def test_every_answer_is_reproduced_by_the_checker(self):
        from scripts.check_evals import verify_all

        failures = verify_all()
        assert not failures, failures
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_evals.py -v`
Expected: FAIL — `evals/fase0.xml` does not exist

- [ ] **Step 4: Write `evals/fase0.xml`**

```xml
<evaluation>
  <qa_pair>
    <question>Na fixture coalesce_one, qual rule_id dispara e em qual linha de lib/loader.py?</question>
    <answer>SF-PY-005:2</answer>
  </qa_pair>
  <qa_pair>
    <question>Na fixture action_in_loop, qual a severidade do finding e qual o valor de measures.loop_depth do fact pyspark.loop?</question>
    <answer>P0:1</answer>
  </qa_pair>
  <qa_pair>
    <question>Na fixture near_threshold, qual o valor de measures.run_length do fact pyspark.withcolumn_run, e quantos findings SF-PY-007 sao produzidos?</question>
    <answer>9:0</answer>
  </qa_pair>
  <qa_pair>
    <question>Na fixture dynamic_dispatch, quantos findings sao produzidos e qual o attrs.reason do fact pyspark.unresolved?</question>
    <answer>0:getattr</answer>
  </qa_pair>
  <qa_pair>
    <question>Na fixture clean_job, quantos findings sao produzidos?</question>
    <answer>0</answer>
  </qa_pair>
  <qa_pair>
    <question>Qual o limiar declarado da regra SF-PY-007 e qual o nome do campo de measures que ela compara?</question>
    <answer>10:run_length</answer>
  </qa_pair>
  <qa_pair>
    <question>Qual regra do catalogo tem runtime_scope exigindo Glue maior ou igual a 5.1, e qual a sua severidade default?</question>
    <answer>SF-ENV-002:P0</answer>
  </qa_pair>
  <qa_pair>
    <question>Segundo a matriz de runtime do projeto, quais versoes de Spark e de Iceberg correspondem ao AWS Glue 5.0?</question>
    <answer>3.5.4:1.7.1</answer>
  </qa_pair>
  <qa_pair>
    <question>Na fixture join_before_reduction, quais os valores de measures.join_index e measures.first_reduction_index do fact pyspark.chain?</question>
    <answer>0:1</answer>
  </qa_pair>
  <qa_pair>
    <question>Quantas regras nao-routing existem no catalogo, e quantas delas pertencem a categoria athena?</question>
    <answer>43:5</answer>
  </qa_pair>
</evaluation>
```

- [ ] **Step 5: Write `scripts/check_evals.py`**

```python
#!/usr/bin/env python3
"""Verifica que cada resposta da eval e reproduzivel a partir do corpus.

A eval mede se o AGENTE usa as tools corretamente. Facts e findings sao identicos
entre modelos por construcao, e isso e coberto pelos golden tests, nao aqui.

Resposta que nao se reproduz aqui e resposta errada no XML, nao no analisador.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sparkforge.facts.pyspark_ast import extract_tree  # noqa: E402
from sparkforge.facts.runtime_detect import GLUE_MATRIX  # noqa: E402
from sparkforge.rules.engine import judge  # noqa: E402
from sparkforge.rules.loader import load_catalog  # noqa: E402

FIXTURES = ROOT / "fixtures" / "pyspark"


def _run(name: str):
    directory = FIXTURES / name
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = extract_tree(directory / "input", repo_root=directory / "input")
    findings = judge(facts, load_catalog(), meta["runtime"])
    return facts, findings


def _first(facts, kind):
    return next(f for f in facts if f.kind == kind)


def expected_answers() -> Dict[int, str]:
    catalog = load_catalog()
    by_id = {r["id"]: r for r in catalog}

    facts, findings = _run("coalesce_one")
    a1 = "{0}:{1}".format(findings[0].rule_id, findings[0].subject["line"])

    facts, findings = _run("action_in_loop")
    a2 = "{0}:{1}".format(
        findings[0].severity, int(_first(facts, "pyspark.loop").measures["loop_depth"])
    )

    facts, findings = _run("near_threshold")
    a3 = "{0}:{1}".format(
        int(_first(facts, "pyspark.withcolumn_run").measures["run_length"]),
        len([f for f in findings if f.rule_id == "SF-PY-007"]),
    )

    facts, findings = _run("dynamic_dispatch")
    a4 = "{0}:{1}".format(len(findings), _first(facts, "pyspark.unresolved").attrs["reason"])

    _, findings = _run("clean_job")
    a5 = str(len(findings))

    a6 = "{0}:run_length".format(by_id["SF-PY-007"]["threshold"]["run_length"])

    scoped = [
        r
        for r in catalog
        if str(r["runtime_scope"].get("glue", "")) == ">=5.1"
    ]
    a7 = "{0}:{1}".format(scoped[0]["id"], scoped[0]["severity_default"])

    a8 = "{0}:{1}".format(GLUE_MATRIX["5.0"]["spark"], GLUE_MATRIX["5.0"]["iceberg"])

    facts, _ = _run("join_before_reduction")
    chain = _first(facts, "pyspark.chain")
    a9 = "{0}:{1}".format(
        int(chain.measures["join_index"]), int(chain.measures["first_reduction_index"])
    )

    a10 = "{0}:{1}".format(
        len(catalog), len([r for r in catalog if r["category"] == "athena"])
    )

    return {1: a1, 2: a2, 3: a3, 4: a4, 5: a5, 6: a6, 7: a7, 8: a8, 9: a9, 10: a10}


def verify_all() -> List[str]:
    # defusedxml, nao xml.etree: os parsers da stdlib sao vulneraveis a XXE e a
    # billion-laughs por default.
    from defusedxml import ElementTree as ET

    tree = ET.parse(ROOT / "evals" / "fase0.xml")
    declared = [p.findtext("answer", "").strip() for p in tree.getroot().findall("qa_pair")]
    computed = expected_answers()

    failures = []
    for index, answer in enumerate(declared, start=1):
        actual = computed.get(index)
        if actual != answer:
            failures.append("Q{0}: XML diz {1!r}, corpus diz {2!r}".format(index, answer, actual))
    return failures


def main() -> int:
    failures = verify_all()
    for line in failures:
        print(line, file=sys.stderr)
    if failures:
        return 1
    print("OK: 10 respostas reproduzidas a partir do corpus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Write `evals/README.md`**

```markdown
# Suíte de avaliação — Fase 0

Mede se o **agente usa as tools corretamente**. Não mede o analisador: facts e findings são
idênticos entre modelos por construção, e isso é garantido pelos golden tests em
`tests/test_fixtures_golden.py`.

## Dois níveis de gate

**Determinístico.** Facts e findings idênticos entre execuções e entre modelos. Não é medido
por eval — é garantido por construção e verificado por golden test. Divergência é bug.

**De agente.** Gate: **10/10** para qualquer modelo testado. Uma resposta errada significa que
a descrição de uma tool ou o `AGENT_PROTOCOL.md` está ambíguo. **A correção é no prompt ou na
descrição, nunca trocando o modelo.**

## Matriz de execução

Opus, Sonnet, Haiku e Devin. Qualidade de narrativa não é gated — só a corretude do uso das
tools.

## Como rodar

Verificação de consistência do próprio XML contra o corpus:

    python scripts/check_evals.py

Execução com um agente: dê a ele as tools MCP e faça as 10 perguntas, uma por sessão limpa.
Compare por string exata.

## Propriedades exigidas de cada pergunta

Independente, read-only, exige múltiplas chamadas de tool, resposta única verificável por
comparação de string, e estável no tempo.
```

- [ ] **Step 7: Run the checker and the tests**

Run: `python scripts/check_evals.py`
Expected: `OK: 10 respostas reproduzidas a partir do corpus.`

If any line reports a mismatch, fix the **XML answer** to match the corpus — the corpus is the ground truth.

Run: `python -m pytest tests/test_evals.py -v`
Expected: PASS, 6 tests

- [ ] **Step 8: Commit**

```bash
git add evals scripts/check_evals.py tests/test_evals.py
git commit -m "test: add 10-pair eval suite with corpus verification"
```

---

## Task 21: CI

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tests/test_ci_workflow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ci_workflow.py
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def steps():
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    collected = []
    for job in data["jobs"].values():
        for step in job.get("steps", []):
            collected.append(step.get("run", "") or step.get("uses", ""))
    return "\n".join(collected)


class TestWorkflow:
    def test_exists(self):
        assert WORKFLOW.is_file()

    def test_tests_both_supported_python_versions(self):
        data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        matrix = data["jobs"]["test"]["strategy"]["matrix"]["python-version"]
        assert "3.10" in matrix and "3.11" in matrix

    def test_runs_the_suite(self):
        assert "python -m pytest" in steps()

    def test_checks_mirror_sync(self):
        assert "sync_skills.py --check" in steps()

    def test_verifies_the_eval_corpus(self):
        assert "check_evals.py" in steps()

    def test_lints_with_ruff(self):
        assert "ruff" in steps()

    def test_refresh_knowledge_is_manual_and_never_auto_commits(self):
        data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        assert "workflow_dispatch" in data["on"]
        assert "git commit" not in steps()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ci_workflow.py -v`
Expected: FAIL — the workflow does not exist

- [ ] **Step 3: Write `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.11"]
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install
        run: python -m pip install -e ".[dev]" --quiet

      - name: Lint
        run: python -m ruff check sparkforge scripts tests

      - name: Test suite
        run: python -m pytest -q

      - name: Mirror sync
        run: python scripts/sync_skills.py --check

      - name: Eval corpus consistency
        run: python scripts/check_evals.py

      - name: Catalog loads with expression validation
        run: |
          python -c "from sparkforge.rules.loader import load_catalog; \
                     rules = load_catalog(validate_exprs=True); \
                     print(len(rules), 'regras validadas')"

      - name: No raw artifact is tracked
        run: |
          if git ls-files | grep -E '^\.sparkforge/artifacts/(?!manifest\.json)' ; then
            echo "artefato bruto rastreado pelo git" >&2
            exit 1
          fi
```

The last step encodes the rule from spec §8.1: derived state is committed, raw artifacts are not.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ci_workflow.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Verify lint passes locally**

Run: `python -m pip install ruff --quiet && python -m ruff check sparkforge scripts tests`
Expected: no findings. Fix anything reported before committing.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml tests/test_ci_workflow.py
git commit -m "ci: add test, lint, parity and eval gates"
```

---

## Task 22: Collector interface skeleton and artifact manifest

Spec §2 places only the *complete* AWS collectors in Phase 1; the interface skeleton is Phase 0, because the manifest is what makes resume work — it records sha256, origin and the re-collect command for artifacts that are deliberately not committed.

**Files:**
- Create: `sparkforge/collect/__init__.py`, `sparkforge/collect/base.py`
- Test: `tests/test_collect_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_collect_base.py
import json

import pytest

from sparkforge.collect.base import (
    ArtifactEntry,
    CollectorUnavailable,
    load_manifest,
    register_artifact,
    verify_artifact,
)


class TestArtifactEntry:
    def test_records_origin_and_recollect_command(self):
        entry = ArtifactEntry(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_abc.json",
            sha256="a" * 64,
            source="s3://bucket/spark-event-logs/jr_abc",
            collect_command="sparkforge collect eventlog --job-run jr_abc",
            collected_at="2026-07-29T10:00:00Z",
        )
        payload = entry.to_dict()
        assert payload["collect_command"].startswith("sparkforge collect")
        assert payload["source"].startswith("s3://")

    def test_rejects_a_malformed_sha256(self):
        with pytest.raises(ValueError, match="sha256"):
            ArtifactEntry(
                kind="event_log", path="p", sha256="short", source="s",
                collect_command="c", collected_at="2026-07-29T10:00:00Z",
            )

    def test_rejects_an_entry_without_a_recollect_command(self):
        """Artefato sem comando de recoleta deixa a retomada cega."""
        with pytest.raises(ValueError, match="collect_command"):
            ArtifactEntry(
                kind="event_log", path="p", sha256="a" * 64, source="s",
                collect_command="", collected_at="2026-07-29T10:00:00Z",
            )


class TestManifest:
    def _entry(self, **over):
        base = dict(
            kind="event_log",
            path=".sparkforge/artifacts/eventlog/jr_abc.json",
            sha256="a" * 64,
            source="s3://bucket/x",
            collect_command="sparkforge collect eventlog --job-run jr_abc",
            collected_at="2026-07-29T10:00:00Z",
        )
        base.update(over)
        return ArtifactEntry(**base)

    def test_register_then_load_round_trip(self, tmp_path):
        path = register_artifact(self._entry(), tmp_path)
        assert path == tmp_path / ".sparkforge" / "artifacts" / "manifest.json"
        assert [e["kind"] for e in load_manifest(tmp_path)] == ["event_log"]

    def test_registering_the_same_path_replaces_the_entry(self, tmp_path):
        register_artifact(self._entry(), tmp_path)
        register_artifact(self._entry(sha256="b" * 64), tmp_path)
        entries = load_manifest(tmp_path)
        assert len(entries) == 1
        assert entries[0]["sha256"] == "b" * 64

    def test_manifest_is_sorted_and_deterministic(self, tmp_path):
        register_artifact(self._entry(kind="terraform", path="a/t.tf"), tmp_path)
        register_artifact(self._entry(), tmp_path)
        target = tmp_path / ".sparkforge" / "artifacts" / "manifest.json"
        first = target.read_text(encoding="utf-8")
        register_artifact(self._entry(), tmp_path)
        assert target.read_text(encoding="utf-8") == first
        assert [e["kind"] for e in load_manifest(tmp_path)] == ["event_log", "terraform"]

    def test_load_missing_manifest_returns_empty_not_an_error(self, tmp_path):
        assert load_manifest(tmp_path) == []


class TestVerify:
    def test_absent_file_is_reported_with_its_recollect_command(self, tmp_path):
        entry = ArtifactEntry(
            kind="event_log", path=".sparkforge/artifacts/gone.json", sha256="a" * 64,
            source="s3://b/x", collect_command="sparkforge collect eventlog --job-run jr",
            collected_at="2026-07-29T10:00:00Z",
        )
        result = verify_artifact(entry.to_dict(), tmp_path)
        assert result["present"] is False
        assert result["collect_command"] == "sparkforge collect eventlog --job-run jr"

    def test_present_file_with_matching_hash_is_ok(self, tmp_path):
        import hashlib

        target = tmp_path / ".sparkforge" / "artifacts" / "log.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"{}")
        digest = hashlib.sha256(b"{}").hexdigest()
        entry = {
            "kind": "event_log", "path": ".sparkforge/artifacts/log.json", "sha256": digest,
            "source": "s3://b/x", "collect_command": "c", "collected_at": "2026-07-29T10:00:00Z",
        }
        result = verify_artifact(entry, tmp_path)
        assert result["present"] is True
        assert result["hash_matches"] is True

    def test_present_file_with_wrong_hash_is_flagged(self, tmp_path):
        target = tmp_path / ".sparkforge" / "artifacts" / "log.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"changed")
        entry = {
            "kind": "event_log", "path": ".sparkforge/artifacts/log.json", "sha256": "a" * 64,
            "source": "s3://b/x", "collect_command": "c", "collected_at": "2026-07-29T10:00:00Z",
        }
        result = verify_artifact(entry, tmp_path)
        assert result["present"] is True
        assert result["hash_matches"] is False


class TestOfflineFirst:
    def test_the_aws_adapter_is_optional_and_fails_with_an_actionable_message(self):
        from sparkforge.collect.base import require_boto3

        try:
            import boto3  # noqa: F401
        except ImportError:
            with pytest.raises(CollectorUnavailable, match=r"sparkforge-aws\[aws\]"):
                require_boto3()
        else:
            assert require_boto3() is not None

    def test_base_module_never_imports_boto3_at_module_level(self):
        import sparkforge.collect.base as module

        source = json.dumps(module.__doc__ or "")
        assert "boto3" not in source.split("require_boto3")[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collect_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sparkforge.collect'`

- [ ] **Step 3: Create `sparkforge/collect/__init__.py`**

```python
"""Subpacote SparkForge."""
```

- [ ] **Step 4: Write `sparkforge/collect/base.py`**

```python
# sparkforge/collect/base.py
"""Interface de coleta e manifest de artefatos.

Offline-first: se o arquivo ja existe e o hash confere, nao ha coleta a fazer. O
adaptador AWS e extra opcional e so e importado sob demanda, para o nucleo rodar
em sandbox Devin e em CI sem credencial nem boto3.

O manifest e commitado; o artefato bruto nao. Por isso cada entrada carrega
sha256, origem e o comando exato de recoleta: sem isso a retomada em outra
ferramenta fica cega. Ver secao 8.1 da spec da Fase 0.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

MANIFEST_RELATIVE = Path(".sparkforge") / "artifacts" / "manifest.json"

ARTIFACT_KINDS = (
    "event_log",
    "terraform",
    "explain",
    "cloudwatch",
    "iceberg_metadata",
    "source",
)


class CollectorUnavailable(RuntimeError):
    """Dependencia opcional de coleta ausente."""


@dataclass(frozen=True)
class ArtifactEntry:
    kind: str
    path: str
    sha256: str
    source: str
    collect_command: str
    collected_at: str

    def __post_init__(self) -> None:
        if len(self.sha256) != 64 or any(c not in "0123456789abcdef" for c in self.sha256):
            raise ValueError("sha256 invalido para {0}: {1!r}".format(self.path, self.sha256))
        if not self.collect_command.strip():
            raise ValueError(
                "collect_command vazio para {0}. Artefato sem comando de recoleta "
                "deixa a retomada cega.".format(self.path)
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
            "source": self.source,
            "collect_command": self.collect_command,
            "collected_at": self.collected_at,
        }


def manifest_path(root: Path) -> Path:
    return Path(root) / MANIFEST_RELATIVE


def load_manifest(root: Path) -> List[Dict[str, Any]]:
    path = manifest_path(root)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("artifacts", [])


def register_artifact(entry: ArtifactEntry, root: Path) -> Path:
    """Adiciona ou substitui a entrada de `entry.path`. Saida deterministica."""
    entries = [e for e in load_manifest(root) if e["path"] != entry.path]
    entries.append(entry.to_dict())
    entries.sort(key=lambda e: (e["kind"], e["path"]))

    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": 1, "artifacts": entries}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def verify_artifact(entry: Dict[str, Any], root: Path) -> Dict[str, Any]:
    """Estado de um artefato: presente, hash confere, e como recoletar."""
    target = Path(root) / entry["path"]
    result = {
        "kind": entry["kind"],
        "path": entry["path"],
        "present": target.is_file(),
        "hash_matches": False,
        "collect_command": entry["collect_command"],
        "source": entry["source"],
    }
    if result["present"]:
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        result["hash_matches"] = digest == entry["sha256"]
    return result


def verify_all(root: Path) -> List[Dict[str, Any]]:
    return [verify_artifact(entry, root) for entry in load_manifest(root)]


def require_boto3():
    """Importa boto3 sob demanda. Erro traz o comando de instalacao."""
    try:
        import boto3
    except ImportError as exc:
        raise CollectorUnavailable(
            "boto3 ausente. Instale com: pip install 'sparkforge-aws[aws]'\n"
            "Ou colete o artefato manualmente e registre no manifest."
        ) from exc
    return boto3
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_collect_base.py -v`
Expected: PASS, 12 tests

- [ ] **Step 6: Wire the manifest into `resume`**

In `sparkforge/case/resume.py`, replace the `missing_artifacts` line so it consults the manifest rather than a `present` flag stored in the case:

```python
        "missing_artifacts": [
            a for a in artifacts if not a.get("present", True)
        ],
```

becomes:

```python
        "missing_artifacts": _missing_artifacts(case, root),
```

and add above `resume`:

```python
def _missing_artifacts(case: Dict[str, Any], root: Optional[Path]) -> List[Dict[str, Any]]:
    """Artefato ausente ou com hash divergente, com o comando que o recoleta."""
    if root is None:
        return [a for a in case.get("artifacts") or [] if not a.get("present", True)]

    from sparkforge.collect.base import verify_all

    return [
        state
        for state in verify_all(root)
        if not state["present"] or not state["hash_matches"]
    ]
```

Add `root: Optional[Path] = None` as the last parameter of `resume`, and pass `Path(args.repo)` from the CLI `resume` and `handoff` commands. Keep the `root=None` path working so the existing `tests/test_case_resume.py` stays green without a filesystem.

- [ ] **Step 7: Run the affected suites**

Run: `python -m pytest tests/test_case_resume.py tests/test_collect_base.py tests/test_adapters_cli.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add sparkforge/collect sparkforge/case/resume.py sparkforge/adapters/cli.py tests/test_collect_base.py
git commit -m "feat(collect): add artifact manifest and collector interface"
```

---

## Task 23: Documentation and acceptance sweep

**Files:**
- Modify: `README.md`, `GUIA_DE_USO.md`, `PROMPT_INICIAL_MESTRE.md`, `AGENTS.md`, `manifest.json`, `SOURCES.md`
- Test: `tests/test_docs_coverage.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_coverage.py
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class TestReadme:
    def test_documents_the_four_distribution_channels(self):
        text = read("README.md")
        for marker in ("plugin", "MCP", "pip", "espelho"):
            assert marker.lower() in text.lower(), marker

    def test_documents_the_cli(self):
        assert "sparkforge analyze pyspark" in read("README.md")

    def test_documents_the_handoff_flow(self):
        text = read("README.md")
        assert "handoff" in text.lower()
        assert ".sparkforge" in text


class TestGuia:
    def test_documents_resume_across_tools(self):
        text = read("GUIA_DE_USO.md")
        assert "sparkforge resume" in text
        assert "Devin" in text

    def test_explains_what_is_committed_and_what_is_not(self):
        text = read("GUIA_DE_USO.md")
        assert "artifacts" in text
        assert "manifest.json" in text


class TestPromptMestre:
    def test_requires_opening_a_case_first(self):
        assert "sparkforge case open" in read("PROMPT_INICIAL_MESTRE.md")

    def test_references_the_protocol(self):
        assert "AGENT_PROTOCOL.md" in read("PROMPT_INICIAL_MESTRE.md")


class TestManifest:
    def test_declares_tools_mcp_and_schemas(self):
        data = json.loads(read("manifest.json"))
        assert data["version"] == "0.4.0"
        assert data["tools"]
        assert data["mcp"]
        assert data["schemas"]

    def test_tool_list_matches_the_implementation(self):
        from sparkforge.adapters.tools import TOOLS

        assert set(json.loads(read("manifest.json"))["tools"]) == set(TOOLS)


class TestAcceptanceCriteria:
    def test_all_fourteen_criteria_are_tracked(self):
        text = read("docs/superpowers/plans/2026-07-29-sparkforge-fase0.md")
        assert "Acceptance sweep" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_coverage.py -v`
Expected: FAIL on the tools/mcp/schemas keys and the CLI markers

- [ ] **Step 3: Update `manifest.json`**

Add these keys alongside the existing ones:

```json
  "tools": [
    "sparkforge_case_open",
    "sparkforge_case_get",
    "sparkforge_case_update",
    "sparkforge_next_step",
    "sparkforge_resume",
    "sparkforge_runtime_detect",
    "sparkforge_analyze_pyspark",
    "sparkforge_judge",
    "sparkforge_rules_lookup",
    "sparkforge_validate_output"
  ],
  "mcp": {
    "config": ".mcp.json",
    "module": "sparkforge.adapters.mcp",
    "transports": ["stdio", "http"]
  },
  "schemas": {
    "fact": "sparkforge/findings/schemas/fact.schema.json",
    "finding": "sparkforge/findings/schemas/finding.schema.json",
    "case": ".sparkforge/case.yaml"
  },
  "cli": "sparkforge",
  "plugin": ".claude-plugin/plugin.json",
  "parity": "parity.yaml",
  "evals": "evals/fase0.xml"
```

- [ ] **Step 4: Add a section to `README.md` after "Base de conhecimento"**

```markdown
## Camada determinística

Extração e julgamento são determinísticos: mesma entrada, mesma saída, qualquer modelo.

```bash
pip install -e .

sparkforge runtime detect --glue 5.0
sparkforge analyze pyspark --path lib/ --out .sparkforge/facts.json
sparkforge judge --facts .sparkforge/facts.json --glue 5.0 --out .sparkforge/findings.json
sparkforge next-step --repo .
```

Extração e julgamento são verbos separados de propósito: dá para rejulgar facts antigos com um
catálogo novo sem reprocessar código, e é isso que torna auditável a evolução do conhecimento.

### Quatro canais de distribuição

| Canal | Público | Como |
|---|---|---|
| Plugin Claude Code | Claude Code | `.claude-plugin/plugin.json` + `.mcp.json`; skills, agents e commands descobertos automaticamente |
| MCP server | Devin Desktop, Devin CLI, Copilot, Cursor | stdio, ou HTTP para Devin Desktop (`serverUrl`) |
| pip | CI, sandbox, shell | `pip install -e ".[aws,mcp]"`, entry point `sparkforge` |
| Espelhos markdown | qualquer agente compatível | `.claude/`, `.agents/`, `.github/` |

### Handoff entre ferramentas

Ficou sem token numa ferramenta? Continue na outra. O barramento é o git.

```bash
sparkforge handoff --repo .
git add .sparkforge/case.yaml .sparkforge/facts.json .sparkforge/findings.json \
        .sparkforge/handoff.md .sparkforge/artifacts/manifest.json
git commit -m "chore: handoff"
```

Do outro lado: `sparkforge resume --repo .`

Derivado é commitado; artefato bruto não — pode ter dado de negócio e centenas de MB. O
`manifest.json` commitado registra sha256, origem e o comando de recoleta, então a retomada
nunca fica cega.
```

- [ ] **Step 5: Add a section to `GUIA_DE_USO.md`**

```markdown
## 8. Retomada entre Devin e Claude Code

O que trafega entre as ferramentas é commit, não contexto de conversa.

**Commitado** (pequeno e derivado): `.sparkforge/case.yaml`, `facts.json`, `findings.json`,
`handoff.md`, `artifacts/manifest.json`.

**Não commitado**: `.sparkforge/artifacts/**` — event log bruto, `.tf` copiado, dumps.

Ao retomar:

1. `sparkforge resume --repo .`
2. Leia `coverage.unresolved`. Nó não resolvido é ponto cego, não ausência de problema.
3. Leia `runtime.divergences`. Divergente significa que nenhum limiar é confiável ainda.
4. Artefato ausente: rode o `collect_command` do manifest. Facts e findings já estão
   commitados, então a análise não depende do bruto.
5. `sparkforge next-step --repo .` decide a rota. Não escolha por conta.

## 9. Sem MCP e sem Python

O catálogo em `rules/catalog/*.yaml` é YAML legível. Um agente sem tool alguma lê o limiar, a
guarda de versão e a fonte diretamente. Cai a automação, não o conhecimento.
```

- [ ] **Step 6: Add to `PROMPT_INICIAL_MESTRE.md`, right after the mission section**

```markdown
## Antes de qualquer análise

1. `sparkforge runtime detect --glue <versao>` — divergência entre fontes é `SF-ENV-001` em P0 e
   invalida qualquer limiar aplicado depois.
2. `sparkforge case open --repo . --case-id sf-<AAAA-MM-DD>-a --now <ISO8601> --glue <versao>`
3. Leia `AGENT_PROTOCOL.md`. As nove regras são o contrato, não orientação.
4. `sparkforge next-step --repo .` decide a rota. A árvore de decisão vive em
   `rules/catalog/routing.yaml`, não no seu julgamento.

Nenhum número na saída sem `fact_id`. Ganho quantificado sem benchmark é rejeitado pelo schema.
```

- [ ] **Step 7: Add to `AGENTS.md`, at the end**

```markdown
## Camada determinística

Evidência vem de extração determinística, não de leitura por amostragem. `Fact` é observação
ancorada em `file:line:col` sem juízo; `Finding` é juízo com `evidence` não vazio e `rule_id`
rastreável até fonte com data.

O esquema de recomendação acima permanece válido: `Finding` é um superset compatível dele.

Regras duras em `AGENT_PROTOCOL.md`. Contratos em
`docs/superpowers/specs/2026-07-29-sparkforge-fase0-design.md`.
```

- [ ] **Step 8: Add to `SOURCES.md`**

```markdown
## Coleta de 2026-07-29

A base em `knowledge/` e o catálogo em `rules/catalog/` registram URL e `retrieved` por
entrada. Heurística de campo é marcada com `origin: field-heuristic` em vez de fingir origem
documental.

Itens explicitamente **não** reconfirmados nessa coleta, marcados nos arquivos: disco de
R.2X/R.4X/R.8X; linhas Hudi e Delta de Glue 3.0 e 4.0; limite de partições em CTAS do Athena;
comportamento exato de `write.distribution-mode` por versão de Iceberg.
```

- [ ] **Step 9: Run test to verify it passes**

Run: `python -m pytest tests/test_docs_coverage.py -v`
Expected: PASS, 11 tests

- [ ] **Step 10: Acceptance sweep**

Run the full suite and check each of the fourteen criteria from spec §15:

Run: `python -m pytest -q && python scripts/sync_skills.py --check && python scripts/check_evals.py`

| # | Criterion | Verified by |
|---|---|---|
| 1 | 17 fact kinds, anchored, schema-valid | `tests/test_facts_kinds.py`, `tests/test_findings_validate.py` |
| 2 | 12 rules produce Findings with non-empty evidence | `tests/test_fixtures_golden.py` |
| 3 | Byte-identical output on re-run | `TestProvenanceAndDeterminism`, `test_extraction_is_deterministic` |
| 4 | 16 fixtures pass in both directions | `tests/test_fixtures_golden.py` |
| 5 | `expr` evaluator rejects everything off-whitelist | `tests/test_rules_expr.py::TestRejections` |
| 6 | Tools with `outputSchema` and annotations | `tests/test_adapters_tools.py` |
| 7 | Plugin installs, MCP resolves via `${CLAUDE_PLUGIN_ROOT}` | `tests/test_plugin_structure.py` |
| 8 | Works without boto3 and without the MCP SDK | `tests/test_package_importable.py` |
| 9 | `resume` renders deterministic 10-section handoff | `tests/test_case_resume.py` |
| 10 | Three parity tests pass | `tests/test_capability_parity.py`, `tests/test_agents_parity.py` |
| 11 | Single-source agents, drift resolved | `TestSingleSource::test_copilot_name_drift_is_gone` |
| 12 | 10 eval pairs, corpus-verified | `tests/test_evals.py`, `scripts/check_evals.py` |
| 13 | CI green with all gates | `tests/test_ci_workflow.py` |
| 14 | Docs updated for four channels and handoff | `tests/test_docs_coverage.py` |
| + | Artifact manifest carries sha256, origin and re-collect command | `tests/test_collect_base.py` |

Criterion 12's cross-model gate (10/10 on at least two model sizes) is the one step that cannot
be automated here: run the eval manually against two models and record the result in
`evals/README.md`.

- [ ] **Step 11: Commit**

```bash
git add README.md GUIA_DE_USO.md PROMPT_INICIAL_MESTRE.md AGENTS.md manifest.json SOURCES.md tests/test_docs_coverage.py
git commit -m "docs: document deterministic layer and handoff flow"
```
