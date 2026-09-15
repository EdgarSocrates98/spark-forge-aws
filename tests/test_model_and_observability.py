from sparkforge.agents import (
    TraceEvent,
    TraceView,
    Usage,
)


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
