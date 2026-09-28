from __future__ import annotations

from sparkforge.decision import ArtifactCache, CacheKind, ContractLoader, DecisionCache
from sparkforge.decision.cache import decision_cache_key
from sparkforge.decision.runtime import BoundedDecisionKernel


def test_decision_key_contains_policy_and_calibration_versions():
    first = decision_cache_key("contract", "state", "policy-v1", "cal-v1")
    second = decision_cache_key("contract", "state", "policy-v2", "cal-v1")
    third = decision_cache_key("contract", "state", "policy-v1", "cal-v2")
    assert first.kind is CacheKind.DECISION
    assert first.canonical() != second.canonical()
    assert first.canonical() != third.canonical()


def test_kernel_applies_contract_cache_max_entries_and_reports_identity():
    contract = ContractLoader().load("kernel.synthetic")
    cache = DecisionCache(max_entries=128)
    kernel = BoundedDecisionKernel(cache=cache)
    evaluation = kernel.evaluate(contract, {"signal": "safe"}, now="2026-09-28T00:00:00Z")
    assert len(cache) == 1
    assert evaluation.receipt["cache"]["key"].startswith("decision|2|")
    assert "kernel-v1" in evaluation.receipt["cache"]["key"]
    assert "none" in evaluation.receipt["cache"]["key"]


def test_economy_artifact_cache_facade_is_bounded_and_persistent(tmp_path):
    cache = ArtifactCache(tmp_path / "cache", default_ttl_seconds=60)
    cache.set("first", {"id": 1}, {"value": "one"})
    cache.set("second", {"id": 2}, {"value": "two"})
    assert cache.get("first", {"id": 1}) == {"value": "one"}
    assert cache.stats()["cache_kind"] == "artifact"

    restarted = ArtifactCache(tmp_path / "cache", default_ttl_seconds=60)
    assert restarted.get("second", {"id": 2}) == {"value": "two"}
