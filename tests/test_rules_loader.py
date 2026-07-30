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
