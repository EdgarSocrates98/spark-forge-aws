import pytest

from sparkforge.rules.version_scope import in_scope


class TestInScope:
    def test_wildcard_always_matches(self):
        assert in_scope({"glue": "*"}, {"glue": "5.0"}) is True

    def test_wildcard_requires_the_key_to_be_present(self):
        """`{glue: "*"}` significa "qualquer VERSAO de Glue", nao "qualquer
        runtime". Antes desta fase o ramo do curinga pulava a checagem de
        presenca e nunca filtrava nada -- foi essa ambiguidade que fez 20 regras
        agnosticas serem marcadas como de Glue."""
        assert in_scope({"glue": "*"}, {"glue": "5.0"}) is True
        assert in_scope({"glue": "*"}, {"spark": "3.5.1"}) is False
        assert in_scope({"glue": "*"}, {}) is False

    def test_wildcard_accepts_any_version_of_a_present_key(self):
        for versao in ("3.0", "4.0", "5.0", "5.1"):
            assert in_scope({"glue": "*"}, {"glue": versao}) is True

    def test_wildcard_still_composes_with_other_keys(self):
        scope = {"glue": "*", "iceberg": ">=1.7.0"}
        assert in_scope(scope, {"glue": "5.0", "iceberg": "1.7.1"}) is True
        assert in_scope(scope, {"glue": "5.0", "iceberg": "1.0.0"}) is False
        assert in_scope(scope, {"iceberg": "1.7.1"}) is False

    def test_empty_scope_always_matches(self):
        assert in_scope({}, {"glue": "5.0"}) is True

    def test_gte_matches_equal(self):
        assert in_scope({"spark": ">=3.5"}, {"spark": "3.5.4"}) is True

    def test_gte_matches_greater(self):
        assert in_scope({"spark": ">=3.2"}, {"spark": "3.5.4"}) is True

    def test_gte_rejects_lower(self):
        assert in_scope({"spark": ">=3.2"}, {"spark": "3.1.1"}) is False

    def test_lt_rejects_equal(self):
        assert in_scope({"glue": "<4.0"}, {"glue": "4.0"}) is False

    def test_lt_matches_lower(self):
        assert in_scope({"glue": "<4.0"}, {"glue": "3.0"}) is True

    def test_multiple_keys_all_must_match(self):
        scope = {"glue": ">=5.1", "iceberg": ">=1.10.0"}
        assert in_scope(scope, {"glue": "5.1", "iceberg": "1.10.0"}) is True
        assert in_scope(scope, {"glue": "5.1", "iceberg": "1.7.1"}) is False

    def test_unknown_runtime_key_does_not_match(self):
        """Sem versao detectada a regra nao dispara. Falha fechada por versao."""
        assert in_scope({"iceberg": ">=1.7.0"}, {"glue": "5.0"}) is False

    def test_exact_version_pin(self):
        assert in_scope({"glue": "5.0"}, {"glue": "5.0"}) is True
        assert in_scope({"glue": "5.0"}, {"glue": "5.1"}) is False

    def test_malformed_spec_raises(self):
        with pytest.raises(ValueError, match="runtime_scope"):
            in_scope({"glue": "~>5.0"}, {"glue": "5.0"})
