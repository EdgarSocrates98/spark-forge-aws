from __future__ import annotations

import json

from sparkforge_aws.adapters import cli
from sparkforge_aws.adapters.tools import TOOLS, call_tool


def test_cli_and_mcp_start_share_same_contract(capsys) -> None:
    cli.main(
        ["context", "start", "--intent", "Glue", "--profile", "economy", "--max-bytes", "5000"]
    )
    cli_result = json.loads(capsys.readouterr().out)
    mcp_result = call_tool(
        "sparkforge_aws_context_start",
        {"intent": "Glue", "profile": "economy", "max_bytes": 5000},
    )

    assert cli_result["status"] == mcp_result["status"]
    assert cli_result["profile"] == mcp_result["profile"]
    assert [item["name"] for item in cli_result["capabilities"]] == [
        item["name"] for item in mcp_result["capabilities"]
    ]


def test_new_tools_are_read_only_and_transport_visible() -> None:
    assert TOOLS["sparkforge_aws_context_start"]["annotations"]["readOnlyHint"] is True
    assert TOOLS["sparkforge_aws_context_expand"]["annotations"]["readOnlyHint"] is True
