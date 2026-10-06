from __future__ import annotations

import json
from functools import partial
from pathlib import Path

from sparkforge_aws.adapters.mcp import tools_do_transporte
from sparkforge_aws.adapters.mcp_compact import CompactRouter
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.economy.cache import ArtifactCache

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "mcp_parity" / "compact_calls.json"


def _router(tmp_path):
    return CompactRouter(
        tools_do_transporte("stdio", "full"),
        partial(call_tool, channel="mcp", transport="stdio"),
        cache=ArtifactCache(tmp_path / "cache"),
    )


def test_compact_fixture_has_explicit_outcome_for_every_case(tmp_path):
    router = _router(tmp_path)
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert cases
    for case in cases:
        result = router.call(case["operation"], case["arguments"])
        assert case["expected_status"] == result.get("status", "error")
        assert case["parity_class"] in {"semantic_equal", "structured_refusal"}


def test_execute_payload_matches_full_dispatch_semantics(tmp_path):
    router = _router(tmp_path)
    arguments = {"glue": "5.0"}

    compact = router.call(
        "execute_read",
        {"capability": "sparkforge_runtime_detect", "arguments": arguments},
    )
    direct = call_tool(
        "sparkforge_runtime_detect",
        arguments,
        channel="mcp",
        transport="stdio",
    )

    assert compact["status"] == "ok"
    assert compact["result"] == direct


def test_execute_refusal_preserves_structured_error_semantics(tmp_path):
    router = _router(tmp_path)

    compact = router.call(
        "execute_read",
        {"capability": "sparkforge_not_real", "arguments": {}},
    )

    assert compact["error_code"] == "COMPACT_REFUSED"
    assert compact["exit_code"] == 2
