import json
from pathlib import Path

from sparkforge_aws.adapters.cli import main
from sparkforge_aws.adapters.mcp_compact import CompactRouter
from sparkforge_aws.adapters.tools import TOOLS, call_tool


def test_cli_full_mcp_and_compact_read_share_canonical_result(tmp_path, capsys):
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"signal": "safe"}), encoding="utf-8")
    cli_code = main(
        [
            "decision",
            "evaluate",
            "--repo",
            str(Path.cwd()),
            "--contract",
            "kernel.synthetic",
            "--input",
            str(state_path),
            "--now",
            "2026-09-28T00:00:00Z",
        ]
    )
    cli_payload = json.loads(capsys.readouterr().out)
    full = call_tool(
        "sparkforge_decision_evaluate",
        {
            "repo": str(Path.cwd()),
            "contract": "kernel.synthetic",
            "state": {"signal": "safe"},
            "now": "2026-09-28T00:00:00Z",
        },
    )
    compact = CompactRouter(
        TOOLS,
        lambda name, arguments: call_tool(name, arguments),
        authorized_root=Path.cwd(),
    ).call(
        "execute_read",
        {
            "capability": "sparkforge_decision_evaluate",
            "arguments": {
                "repo": str(Path.cwd()),
                "contract": "kernel.synthetic",
                "state": {"signal": "safe"},
                "now": "2026-09-28T00:00:00Z",
            },
        },
    )
    assert cli_code == 0
    assert cli_payload["result"] == full["result"]
    assert compact["status"] == "ok"
    assert compact["result"]["result"] == full["result"]
