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


class TestListOfSpecsOnOneKey:
    """Uma faixa de UM minor precisa de dois specs na mesma chave.

    `runtime_scope` e um mapa, entao `>=3.3` e `<3.4` nao cabem em duas
    entradas. E nenhum spec sozinho resolve: `"==3.3"` casa `3.3.0` e reprova
    `3.3.1`/`3.3.2` -- os Sparks de EMR 6.10.x e 6.11.x --, e `">=3.3"` sozinho
    estende a regra a 3.4 e 3.5. Primeiro consumidor: SF-GRAPH-002.
    """

    BANDA = {"spark": [">=3.3", "<3.4"]}

    def test_the_band_accepts_every_patch_of_the_minor(self):
        for versao in ("3.3", "3.3.0", "3.3.1", "3.3.2", "3.3.2-amzn-0.1"):
            assert in_scope(self.BANDA, {"spark": versao}) is True, versao

    def test_the_band_rejects_both_neighbours(self):
        for versao in ("3.2.1-amzn-0", "3.2.0", "3.1.1", "3.4.0-amzn-0", "3.5.4"):
            assert in_scope(self.BANDA, {"spark": versao}) is False, versao

    def test_a_single_spec_could_not_express_it(self):
        """A medicao que justifica a lista, e nao uma opiniao sobre ela."""
        assert in_scope({"spark": "==3.3"}, {"spark": "3.3.0"}) is True
        assert in_scope({"spark": "==3.3"}, {"spark": "3.3.2"}) is False
        assert in_scope({"spark": ">=3.3"}, {"spark": "3.5.4"}) is True

    def test_the_list_still_fails_closed_on_an_absent_key(self):
        assert in_scope(self.BANDA, {"spark": ""}) is False
        assert in_scope(self.BANDA, {}) is False

    def test_the_list_composes_with_other_keys(self):
        scope = {"spark": [">=3.3", "<3.4"], "glue": "*"}
        assert in_scope(scope, {"spark": "3.3.0", "glue": "4.0"}) is True
        assert in_scope(scope, {"spark": "3.3.0"}) is False

    def test_an_empty_list_raises_instead_of_passing_vacuously(self):
        """Chave que nao restringe nada parece guarda e nao e. Quem quer 'sem
        restricao' escreve `runtime_scope: {}`."""
        with pytest.raises(ValueError, match="lista vazia"):
            in_scope({"spark": []}, {"spark": "3.3.0"})

    def test_a_malformed_spec_inside_the_list_still_raises(self):
        with pytest.raises(ValueError, match="runtime_scope"):
            in_scope({"spark": [">=3.3", "~>3.4"]}, {"spark": "3.3.0"})
