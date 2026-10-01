from pathlib import Path

from sparkforge.decision import BoundedDecisionKernel, ContractLoader, DecisionCache, DecisionStatus


def test_kernel_cache_and_activation_refusal():
    loader = ContractLoader(Path.cwd())
    contract = loader.load("kernel.synthetic")
    kernel = BoundedDecisionKernel(cache=DecisionCache(2))
    first = kernel.evaluate(contract, {"signal": "safe"}, now="2026-09-28T00:00:00Z")
    second = kernel.evaluate(contract, {"signal": "safe"}, now="2026-09-28T00:00:00Z")
    assert first.result.status is DecisionStatus.ACCEPTED
    assert second.result.cache_hit is True
    assert first.receipt["measurement"]["provider_tokens"] is None
    assert first.receipt["measurement"]["tokens_unresolved"] is True


def test_kernel_package_has_no_provider_or_mcp_sdk_imports():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("sparkforge/decision").glob("*.py")
    )
    for forbidden in ("anthropic", "openai", "bedrock", "litellm", "mcp"):
        assert forbidden not in source.lower()
