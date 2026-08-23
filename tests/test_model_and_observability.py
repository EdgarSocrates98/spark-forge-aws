from sparkforge.agents import (
    ModelDemand,
    ModelInfo,
    ModelSelector,
    TraceEvent,
    TraceView,
    Usage,
)


def test_selector_uses_available_account_inventory_and_budget():
    models = [
        ModelInfo("cheap", input_price=0.1, output_price=0.5, quality=2, tools=True),
        ModelInfo(
            "strong",
            input_price=3.0,
            output_price=15.0,
            quality=5,
            reasoning=True,
            tools=True,
        ),
    ]
    choice = ModelSelector().choose(
        models,
        ModelDemand("bulk extraction", max_output_price=1.0, needs_tools=True),
    )
    assert choice.model is not None
    assert choice.model.model_id == "cheap"

def test_selector_uses_reasoning_for_high_risk_work():
    models = [ModelInfo("basic", quality=3), ModelInfo("reasoner", quality=3, reasoning=True)]
    choice = ModelSelector().choose(models, ModelDemand("verify", risk="high"))
    assert choice.model is not None
    assert choice.model.model_id == "reasoner"

def test_trace_view_is_hidden_by_default_and_warns_when_usage_is_partial():
    hidden = TraceView()
    hidden.record(TraceEvent("1", "a", "handoff", "verify", "secret", Usage(total_tokens=10)))
    assert hidden.render()["enabled"] is False
    visible = TraceView(enabled=True)
    visible.record(
        TraceEvent(
            "1",
            "a",
            "handoff",
            "verify",
            "summary",
            Usage(input_tokens=5, output_tokens=3, total_tokens=8),
        )
    )
    visible.record(TraceEvent("2", "b", "handoff", "verify", "unknown", Usage(estimated=True)))
    result = visible.render()
    assert result["total_tokens"] is None
    assert "unavailable" in result["token_notice"]
