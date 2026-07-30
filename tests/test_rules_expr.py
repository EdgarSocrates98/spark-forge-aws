import pytest

from sparkforge.rules.expr import ExprError, evaluate

CTX = {
    "measures": {"max_ms": 41000, "p50_ms": 1200, "run_length": 12},
    "attrs": {"bounded": False, "udf_type": "python"},
    "threshold": {"ratio": 3.0, "run_length": 10},
}


class TestArithmeticAndComparison:
    def test_ratio_comparison_true(self):
        assert evaluate("measures.max_ms / measures.p50_ms >= threshold.ratio", CTX) is True

    def test_ratio_comparison_false(self):
        ctx = {"measures": {"max_ms": 1000, "p50_ms": 1000}, "threshold": {"ratio": 3.0}}
        assert evaluate("measures.max_ms / measures.p50_ms >= threshold.ratio", ctx) is False

    def test_boundary_exact_threshold_is_inclusive(self):
        ctx = {"measures": {"a": 3.0}, "threshold": {"ratio": 3.0}}
        assert evaluate("measures.a >= threshold.ratio", ctx) is True

    def test_boundary_just_below_is_false(self):
        ctx = {"measures": {"a": 2.99}, "threshold": {"ratio": 3.0}}
        assert evaluate("measures.a >= threshold.ratio", ctx) is False

    def test_boolean_and(self):
        expr = "measures.run_length >= threshold.run_length and attrs.bounded == False"
        assert evaluate(expr, CTX) is True

    def test_equality_on_string_attr(self):
        assert evaluate("attrs.udf_type == 'python'", CTX) is True


class TestRejections:
    """These are the tests that matter. Catalog YAML is editable data."""

    @pytest.mark.parametrize(
        "expr",
        [
            "__import__('os').system('echo pwned')",
            "len(measures)",
            "measures.__class__",
            "measures.__class__.__mro__",
            "open('/etc/passwd').read()",
            "[x for x in measures]",
            "lambda: 1",
            "measures['max_ms']",
            "os.getcwd()",
            "measures.max_ms if True else 0",
            "{'a': 1}",
            "(1, 2)",
        ],
    )
    def test_disallowed_constructs_raise(self, expr):
        with pytest.raises(ExprError):
            evaluate(expr, CTX)

    def test_unknown_root_rejected(self):
        with pytest.raises(ExprError, match="raiz"):
            evaluate("secrets.token == 'x'", CTX)

    def test_missing_path_rejected(self):
        with pytest.raises(ExprError, match="ausente"):
            evaluate("measures.does_not_exist > 1", CTX)

    def test_syntax_error_rejected(self):
        with pytest.raises(ExprError, match="invalida"):
            evaluate("measures.a >>>", CTX)

    def test_division_by_zero_is_expr_error_not_crash(self):
        ctx = {"measures": {"a": 1, "b": 0}, "threshold": {}}
        with pytest.raises(ExprError, match="divis"):
            evaluate("measures.a / measures.b > 1", ctx)
