from __future__ import annotations

import json
from functools import partial
from pathlib import Path

from sparkforge.adapters.mcp import tools_do_transporte
from sparkforge.adapters.mcp_compact import (
    COMPACT_TOOL_NAMES,
    CompactRouter,
    compact_catalog,
)
from sparkforge.adapters.mcp_envelope import envelope_da_chamada
from sparkforge.adapters.tools import TOOLS, call_tool
from sparkforge.economy.cache import ArtifactCache

ROOT = Path(__file__).resolve().parents[1]


def _router(tmp_path):
    return CompactRouter(
        tools_do_transporte("stdio", "full"),
        partial(call_tool, channel="mcp", transport="stdio"),
        cache=ArtifactCache(tmp_path / "cache"),
    )


def test_compact_catalog_has_exactly_seven_stable_operations():
    catalog = compact_catalog()

    assert tuple(catalog) == COMPACT_TOOL_NAMES
    assert len(catalog) == 7
    assert set(catalog) == {
        "context_start",
        "context_expand",
        "execute_read",
        "execute_mutation",
        "search",
        "get",
        "next",
    }
    assert all(spec["inputSchema"] for spec in catalog.values())
    assert all(spec["outputSchema"] for spec in catalog.values())


def test_compact_catalog_splits_read_and_mutation_execution():
    read_annotations = compact_catalog()["execute_read"]["annotations"]
    mutation_annotations = compact_catalog()["execute_mutation"]["annotations"]

    assert read_annotations == {
        "readOnlyHint": True,
        "openWorldHint": True,
        "destructiveHint": False,
    }
    assert mutation_annotations == {
        "readOnlyHint": False,
        "openWorldHint": True,
        "destructiveHint": True,
    }


def test_compact_router_enforces_execution_mode_from_target_annotation(tmp_path):
    calls = []

    def execute_full(name, arguments):
        calls.append((name, arguments))
        return {}

    router = CompactRouter(
        TOOLS,
        execute_full,
        cache=ArtifactCache(tmp_path / "cache"),
    )
    arguments = {
        "capability": "sparkforge_case_open",
        "arguments": {"repo": ".", "case_id": "case-1", "now": "2026-09-27T00:00:00Z"},
    }

    refused = router.call("execute_read", arguments)
    accepted = router.call("execute_mutation", arguments)

    assert refused["error_code"] == "COMPACT_REFUSED"
    assert "read-only" in refused["error"]
    assert accepted["status"] == "ok"
    assert calls == [("sparkforge_case_open", arguments["arguments"])]


def test_compact_catalog_matches_its_golden_fixture():
    golden = json.loads(
        (ROOT / "fixtures" / "mcp_parity" / "compact_tools_list.json").read_text(
            encoding="utf-8"
        )
    )

    assert golden["tool_count"] == len(compact_catalog())
    assert golden["tool_names"] == list(compact_catalog())


def test_full_catalog_remains_declared_and_http_compact_has_no_source_tool():
    assert len(tools_do_transporte("stdio", "full")) == 114
    assert len(tools_do_transporte("http", "full")) == 113
    assert len(tools_do_transporte("stdio", "compact")) == 7
    assert len(tools_do_transporte("http", "compact")) == 7
    assert "sparkforge_code_read" not in tools_do_transporte("http", "compact")


def test_search_get_execute_and_next_are_deterministic(tmp_path):
    router = _router(tmp_path)

    search = router.call("search", {"query": "sparkforge", "limit": 1})
    assert search["status"] == "ok"
    assert search["items"][0]["kind"] == "tool"
    assert search["next_cursor"]

    next_page = router.call("next", {"cursor": search["next_cursor"]})
    assert next_page["status"] == "ok"
    assert next_page["items"]
    assert next_page["items"][0]["id"] != search["items"][0]["id"]

    capability = router.call("get", {"id": "sparkforge_runtime_detect"})
    assert capability["status"] == "ok"
    assert capability["item"]["id"] == "sparkforge_runtime_detect"
    assert capability["item"]["inputSchema"] == TOOLS["sparkforge_runtime_detect"]["inputSchema"]

    executed = router.call(
        "execute_read",
        {"capability": "sparkforge_runtime_detect", "arguments": {"glue": "5.0"}},
    )
    assert executed["status"] == "ok"
    assert executed["capability"] == "sparkforge_runtime_detect"
    assert executed["result"]["spark"]


def test_get_resolves_authorized_context_ref(tmp_path):
    router = _router(tmp_path)
    ref = router.refs.put("artifact", {"source_path": "case.json", "value": "observed"})

    result = router.call("get", {"ref": ref.uri})

    assert result["status"] == "ok"
    assert result["item"]["payload"]["value"] == "observed"


def test_compact_router_rejects_ref_source_outside_authorized_root(tmp_path):
    router = CompactRouter(
        TOOLS,
        lambda name, arguments: {},
        cache=ArtifactCache(tmp_path / "cache"),
        authorized_root=tmp_path,
    )
    ref = router.refs.put("artifact", {"source_path": "../secret.txt"})

    result = router.call("get", {"ref": ref.uri})

    assert result["error_code"] == "CONTEXT_REF_INVALID"


def test_compact_router_refuses_unknown_capability_and_cursor():
    router = CompactRouter(TOOLS, lambda name, arguments: {})

    unknown = router.call(
        "execute_read", {"capability": "sparkforge_not_real", "arguments": {}}
    )
    cursor = router.call("next", {"cursor": "cursor://v1/not-a-digest"})

    assert unknown["error_code"] == "COMPACT_REFUSED"
    assert cursor["error_code"] == "COMPACT_REFUSED"


def test_execute_validates_selected_capability_schema_before_dispatch(tmp_path):
    calls = []

    def execute_full(name, arguments):
        calls.append((name, arguments))
        return {}

    router = CompactRouter(
        TOOLS,
        execute_full,
        cache=ArtifactCache(tmp_path / "cache"),
    )

    result = router.call(
        "execute_read",
        {
            "capability": "sparkforge_release_describe",
            "arguments": {"release": "5.0"},
        },
    )

    assert result["error_code"] == "COMPACT_REFUSED"
    assert "platform" in result["error"]
    assert calls == []


def test_compact_envelope_validates_before_router_execution(tmp_path):
    router = _router(tmp_path)
    catalog = compact_catalog()

    envelope = envelope_da_chamada("get", {}, catalog, "stdio", router.call)

    assert envelope.is_error is True
    assert "not valid under any of the given schemas" in envelope.text


def test_compact_envelope_has_mode_specific_unknown_tool_message(tmp_path):
    router = _router(tmp_path)
    envelope = envelope_da_chamada(
        "sparkforge_runtime_detect",
        {},
        compact_catalog(),
        "stdio",
        router.call,
        "ferramenta indisponivel no modo 'compact'",
    )

    assert envelope.is_error is True
    assert "modo 'compact'" in envelope.text
