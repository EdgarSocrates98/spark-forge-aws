from __future__ import annotations

import pytest

from sparkforge.decision import (
    ArtifactCache,
    CacheKind,
    FactCache,
    artifact_cache_key,
    decision_cache_key,
    fact_cache_key,
)


def test_fact_and_artifact_namespaces_cannot_collide() -> None:
    fact = FactCache()
    artifact = ArtifactCache()
    fact_key = fact_cache_key("artifact", "extractor-v1", "rules-v1")
    artifact_key = artifact_cache_key("pack", "artifact", "compiler-v1")
    fact.put(fact_key, {"fact_id": "f1"}, owner="extractor")
    artifact.put(artifact_key, {"descriptor": "a"}, owner="pack-registry")
    assert fact.get(fact_key).to_dict()["cache_kind"] == CacheKind.FACT.value
    assert artifact.get(artifact_key).to_dict()["cache_kind"] == CacheKind.ARTIFACT.value
    with pytest.raises(ValueError, match="namespace mismatch"):
        fact.get(artifact_key)


def test_decision_key_changes_when_semantic_policy_changes() -> None:
    first = decision_cache_key("contract", "state", "policy-v1", "cal-v1")
    second = decision_cache_key("contract", "state", "policy-v2", "cal-v1")
    assert first.kind is CacheKind.DECISION
    assert first.canonical() != second.canonical()


def test_cache_metadata_records_owner_and_freshness() -> None:
    cache = FactCache()
    key = fact_cache_key("artifact", "extractor-v1", "rules-v1")
    record = cache.put(key, {"facts": []}, owner="extractor", freshness="fresh")
    assert record.to_dict()["owner"] == "extractor"
    assert record.to_dict()["freshness"] == "fresh"


def test_cross_namespace_key_is_rejected() -> None:
    cache = FactCache()
    key = decision_cache_key("contract", "state")
    with pytest.raises(ValueError, match="namespace mismatch"):
        cache.get(key)
