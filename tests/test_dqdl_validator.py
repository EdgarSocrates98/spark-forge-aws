from sparkforge.dqdl.validator import validate_dqdl_text


def test_validates_external_dqdl_without_generating_rules():
    facts = validate_dqdl_text(
        'Rules = [Completeness "id" > 0.99, IsUnique "id"]',
        "rules.dqdl",
    )
    assert facts[0].kind == "dq.dqdl"
    assert facts[0].measures["rule_count"] == 2
    assert facts[0].attrs["validation_scope"] == "syntax_only"


def test_invalid_dqdl_is_unresolved_and_does_not_guess_rule_type():
    facts = validate_dqdl_text('Rules = [NotARealRule "id"]', "rules.dqdl")
    assert facts[0].kind == "dq.dqdl.unresolved"
    assert facts[0].attrs["reason"] == "unsupported_rule_type"
