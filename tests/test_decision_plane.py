from __future__ import annotations

import json
import shutil
from pathlib import Path

from sparkforge_aws.adapters.cli import main
from sparkforge_aws.economy.decision_contracts import ContractRegistry
from sparkforge_aws.economy.decision_models import DecisionInput
from sparkforge_aws.economy.decision_plane import DecisionPlaneService
from sparkforge_aws.economy.decision_receipts import DecisionReceiptStore

ROOT = Path(__file__).resolve().parents[1]


def test_shadow_returns_complete_result_and_receipt(tmp_path: Path) -> None:
    service = DecisionPlaneService(
        ROOT, registry=ContractRegistry(ROOT), receipts=DecisionReceiptStore(tmp_path)
    )
    contract = service.validate("routing.data_domain")
    evaluation = service.shadow(
        DecisionInput("task", "diagnose", deterministic_available=True),
        "tier_0_deterministic",
        contract=contract,
        now="fixed",
    )

    result = evaluation.result.to_dict()
    assert set(result) >= {
        "contract_id",
        "contract_version",
        "contract_sha256",
        "status",
        "selected",
        "confidence",
        "confidence_source",
        "method",
        "unresolved",
        "budget",
        "receipt_id",
        "fingerprint",
        "cache_hit",
        "evidence",
    }
    assert evaluation.receipt.path.is_file()
    assert evaluation.receipt.document["kernel"]["fingerprint"] == result["fingerprint"]
    assert evaluation.receipt.document["control"]["mode"] == "shadow"


def test_runtime_and_cli_projection_match(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    shutil.copytree(ROOT / "config", repo / "config")
    service = DecisionPlaneService(repo)
    contract = service.validate("routing.data_domain")
    request = DecisionInput("task", "diagnose", current_route="tier_3_cheap_local")
    runtime = service.shadow(
        request, request.current_route, contract=contract, now="fixed"
    ).to_dict()
    input_path = repo / "input.json"
    input_path.write_text(json.dumps(request.canonical()), encoding="utf-8")
    output_path = repo / "shadow.json"
    assert (
        main(
            [
                "decision",
                "shadow",
                "--repo",
                str(repo),
                "--input",
                str(input_path),
                "--now",
                "fixed",
                "--out",
                str(output_path),
            ]
        )
        == 0
    )
    cli_projection = json.loads(output_path.read_text(encoding="utf-8"))

    assert cli_projection["result"] == runtime["result"]
    assert cli_projection["comparison"] == runtime["comparison"]
