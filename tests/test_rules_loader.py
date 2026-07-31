from pathlib import Path

import pytest

from sparkforge.rules.loader import CatalogError, catalog_dir, load_catalog

ROOT = Path(__file__).resolve().parents[1]


class TestCatalogDiscovery:
    def test_finds_repo_root_catalog(self):
        assert catalog_dir() == ROOT / "rules" / "catalog"

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))
        assert catalog_dir() == tmp_path


class TestLoadCommittedCatalog:
    def test_loads_all_non_routing_rules(self):
        assert len(load_catalog()) == 43

    def test_routing_is_excluded(self):
        assert not [r for r in load_catalog() if r["id"].startswith("ROUTE-")]

    def test_every_rule_id_is_unique(self):
        ids = [r["id"] for r in load_catalog()]
        assert len(ids) == len(set(ids))

    def test_every_rule_has_required_fields(self):
        required = (
            "id",
            "category",
            "title",
            "requires_facts",
            "when",
            "status",
            "runtime_scope",
            "sources",
        )
        for rule in load_catalog():
            for key in required:
                assert key in rule, f"{rule.get('id')} sem {key}"

    def test_every_rule_has_a_severity(self):
        for rule in load_catalog():
            assert "severity_default" in rule or "severity_by" in rule, rule["id"]

    def test_every_source_has_url_or_origin(self):
        for rule in load_catalog():
            for src in rule["sources"]:
                assert "url" in src or "origin" in src, rule["id"]

    def test_every_expr_is_accepted_by_the_safe_evaluator(self):
        """Expressao invalida no catalogo falha na carga, nao em producao."""
        load_catalog(validate_exprs=True)

    def test_catalog_version_is_stamped(self):
        for rule in load_catalog():
            assert isinstance(rule["catalog_version"], int)

    def test_sf_env_003_requires_the_pyspark_sentinel(self):
        """`absent: pyspark.glue_context_init` so e som quando pyspark.module_analyzed
        provar que o extrator PySpark rodou. Sem isso, analise so-Terraform dispararia
        falso positivo por ausencia vazia. Guarda contra regressao dessa correcao."""
        rule = next(r for r in load_catalog() if r["id"] == "SF-ENV-003")
        assert "pyspark.module_analyzed" in rule["requires_facts"]
        conditions = rule["when"]["all"]
        assert any(c.get("fact") == "pyspark.module_analyzed" for c in conditions)
        assert any(c.get("absent") == "pyspark.glue_context_init" for c in conditions)


class TestRejections:
    def _write(self, tmp_path, monkeypatch, name, body):
        (tmp_path / name).write_text(body, encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path))

    def test_duplicate_id_raises(self, tmp_path, monkeypatch):
        one = (
            "{id: SF-X-001, category: c, title: t, requires_facts: [k], "
            "when: {all: []}, status: structural, severity_default: P2, "
            'runtime_scope: {glue: "*"}, sources: [{origin: field-heuristic}]}'
        )
        body = "catalog_version: 1\narea: SF-X\nrules:\n  - " + one + "\n  - " + one + "\n"
        self._write(tmp_path, monkeypatch, "dup.yaml", body)
        with pytest.raises(CatalogError, match="duplicado"):
            load_catalog()

    def test_missing_required_field_raises(self, tmp_path, monkeypatch):
        body = "catalog_version: 1\narea: SF-X\nrules:\n  - {id: SF-X-002, title: t}\n"
        self._write(tmp_path, monkeypatch, "bad.yaml", body)
        with pytest.raises(CatalogError, match="SF-X-002"):
            load_catalog()

    def test_unsafe_expr_raises_at_load_time(self, tmp_path, monkeypatch):
        body = (
            "catalog_version: 1\n"
            "area: SF-X\n"
            "rules:\n"
            "  - id: SF-X-003\n"
            "    category: c\n"
            "    title: t\n"
            "    requires_facts: [k]\n"
            "    when:\n"
            "      all:\n"
            "        - {fact: k, expr: \"__import__('os').system('x')\"}\n"
            "    status: structural\n"
            "    severity_default: P2\n"
            '    runtime_scope: {glue: "*"}\n'
            "    sources: [{origin: field-heuristic}]\n"
        )
        self._write(tmp_path, monkeypatch, "unsafe.yaml", body)
        with pytest.raises(CatalogError, match="SF-X-003"):
            load_catalog(validate_exprs=True)

    def _rule_with_when(self, when_block):
        return (
            "catalog_version: 1\n"
            "area: SF-X\n"
            "rules:\n"
            "  - id: SF-X-004\n"
            "    category: c\n"
            "    title: t\n"
            "    requires_facts: [k]\n"
            "    when:\n" + when_block + "    status: structural\n"
            "    severity_default: P2\n"
            '    runtime_scope: {glue: "*"}\n'
            "    sources: [{origin: field-heuristic}]\n"
        )

    def test_condition_without_fact_or_absent_raises(self, tmp_path, monkeypatch):
        """Typo na chave (`facts:` em vez de `fact:`) faria a regra nunca disparar,
        em silencio: o motor nao acha candidato, nao ha erro, relatorio sai limpo.
        Falso negativo mudo e o pior modo de falha, entao morre na carga."""
        body = self._rule_with_when("      all:\n        - {facts: k}\n")
        self._write(tmp_path, monkeypatch, "typo.yaml", body)
        with pytest.raises(CatalogError, match="sem `fact` nem `absent`"):
            load_catalog()

    def test_error_names_the_keys_actually_present(self, tmp_path, monkeypatch):
        body = self._rule_with_when("      all:\n        - {facts: k, where: {attrs.a: 1}}\n")
        self._write(tmp_path, monkeypatch, "typo2.yaml", body)
        with pytest.raises(CatalogError, match="facts, where"):
            load_catalog()

    def test_when_without_all_or_any_raises(self, tmp_path, monkeypatch):
        body = self._rule_with_when("      todos:\n        - {fact: k}\n")
        self._write(tmp_path, monkeypatch, "nogroup.yaml", body)
        with pytest.raises(CatalogError, match="sem grupo"):
            load_catalog()

    def test_condition_that_is_not_a_mapping_raises(self, tmp_path, monkeypatch):
        body = self._rule_with_when("      all:\n        - k\n")
        self._write(tmp_path, monkeypatch, "scalar.yaml", body)
        with pytest.raises(CatalogError, match="precisa ser um mapa"):
            load_catalog()

    def test_absent_only_condition_is_valid(self, tmp_path, monkeypatch):
        """`absent` sem `fact` e forma legitima: regra que dispara pela ausencia."""
        body = self._rule_with_when("      all:\n        - {absent: other.kind}\n")
        self._write(tmp_path, monkeypatch, "absent.yaml", body)
        assert [r["id"] for r in load_catalog()] == ["SF-X-004"]

    def test_real_catalog_still_passes_condition_validation(self):
        """As 43 regras commitadas nao podem ter condicao malformada."""
        assert len(load_catalog(validate_exprs=True)) == 43


class TestCatalogPathIsContained:
    """SPARKFORGE_CATALOG vem do ambiente — em plugin instalado e escrito por
    configuracao externa (.mcp.json). Sem contencao, um valor com `..` ou um
    symlink apontando para fora vira leitura arbitraria de sistema de arquivos."""

    def test_env_var_pointing_at_a_file_is_rejected(self, tmp_path, monkeypatch):
        target = tmp_path / "nao-e-diretorio.txt"
        target.write_text("x", encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(target))
        with pytest.raises(CatalogError, match="nao e um diretorio"):
            catalog_dir()

    def test_env_var_pointing_at_a_missing_dir_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(tmp_path / "inexistente"))
        with pytest.raises(CatalogError, match="nao e um diretorio"):
            catalog_dir()

    def test_env_var_is_resolved_to_an_absolute_path(self, tmp_path, monkeypatch):
        nested = tmp_path / "a" / ".." / "a"
        (tmp_path / "a").mkdir()
        monkeypatch.setenv("SPARKFORGE_CATALOG", str(nested))
        resolved = catalog_dir()
        assert resolved.is_absolute()
        assert ".." not in resolved.parts

    def test_traversal_out_of_the_catalog_is_refused(self, tmp_path):
        from sparkforge.rules.loader import safe_catalog_file

        base = tmp_path / "catalog"
        base.mkdir()
        with pytest.raises(CatalogError, match="fora do diretorio"):
            safe_catalog_file(base, "../../etc/passwd")

    def test_a_plain_name_inside_the_catalog_is_allowed(self, tmp_path):
        from sparkforge.rules.loader import safe_catalog_file

        base = tmp_path / "catalog"
        base.mkdir()
        assert safe_catalog_file(base, "pyspark.yaml").parent == base.resolve()

    def test_the_real_catalog_still_loads_through_the_check(self):
        assert len(load_catalog(validate_exprs=True)) == 43
