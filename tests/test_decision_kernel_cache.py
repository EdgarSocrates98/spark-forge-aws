from sparkforge.decision.cache import DecisionCache
from sparkforge.decision.models import DecisionResult, DecisionStatus


def _result(value):
    return DecisionResult(
        "c", "1", "sha", value, DecisionStatus.ACCEPTED, (value,), "test", 1.0, None
    )


def test_cache_hit_invalidation_and_bounded_eviction():
    cache = DecisionCache(2)
    cache.put("a", _result("a"))
    cache.put("b", _result("b"))
    assert cache.get("a").cache_hit is False
    cache.put("c", _result("c"))
    assert cache.get("b") is None
    assert cache.get("a") is not None
    cache.invalidate("a")
    assert cache.get("a") is None
    assert cache.stats()["evictions"] == 1
