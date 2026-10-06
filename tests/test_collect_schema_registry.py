from __future__ import annotations

import json
from pathlib import Path

from sparkforge_aws.adapters._core import analyze_schema_registry
from sparkforge_aws.adapters.cli import main
from sparkforge_aws.adapters.tools import call_tool
from sparkforge_aws.collect import schema_registry
from sparkforge_aws.collect.base import load_manifest


class FakeGlueSchemaRegistry:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def get_registry(self, **kwargs):
        self.calls.append(("get_registry", kwargs))
        return {
            "RegistryName": kwargs["RegistryId"]["RegistryName"],
            "RegistryArn": "arn:aws:glue:us-east-1:111111111111:registry/events",
            "Status": "AVAILABLE",
        }

    def list_schemas(self, **kwargs):
        self.calls.append(("list_schemas", kwargs))
        if kwargs.get("NextToken") == "page-2":
            return {"Schemas": [{"SchemaName": "payments", "RegistryName": "events"}]}
        return {
            "Schemas": [{"SchemaName": "orders", "RegistryName": "events"}],
            "NextToken": "page-2",
        }

    def get_schema(self, **kwargs):
        self.calls.append(("get_schema", kwargs))
        name = kwargs["SchemaId"].get("SchemaName", "unknown")
        return {
            "SchemaName": name,
            "RegistryName": "events",
            "SchemaArn": f"arn:aws:glue:us-east-1:111111111111:schema/events/{name}",
            "DataFormat": "AVRO",
            "Compatibility": "BACKWARD",
            "LatestSchemaVersion": 2,
            "SchemaStatus": "AVAILABLE",
            "SecretToken": "must not be copied",
        }

    def get_schema_version(self, **kwargs):
        self.calls.append(("get_schema_version", kwargs))
        name = kwargs["SchemaId"]["SchemaName"]
        response = {
            "SchemaArn": f"arn:aws:glue:us-east-1:111111111111:schema/events/{name}",
            "VersionNumber": 2,
            "SchemaVersionId": f"00000000-0000-0000-0000-{name:0>12}"[-36:],
            "Status": "AVAILABLE",
            "DataFormat": "AVRO",
            "CreatedTime": "2026-10-03T00:00:00Z",
        }
        if name == "orders":
            response["SchemaDefinition"] = json.dumps(
                {"type": "record", "name": name, "fields": [{"name": "id", "type": "long"}]}
            )
        return response


class FakeBoto3:
    def __init__(self, glue: FakeGlueSchemaRegistry) -> None:
        self.glue = glue

    def client(self, name: str, **kwargs):
        assert name == "glue"
        return self.glue


def _args(repo: Path) -> dict[str, str | int]:
    return {
        "repo": str(repo),
        "registry_name": "events",
        "now": "2026-10-03T00:00:00Z",
        "max_schemas": 2,
    }


def test_collector_paginates_and_preserves_schema_versions(monkeypatch, tmp_path):
    fake_glue = FakeGlueSchemaRegistry()
    monkeypatch.setattr(schema_registry, "require_boto3", lambda: FakeBoto3(fake_glue))

    entry = schema_registry.collect_schema_registry(
        tmp_path, registry_name="events", now="2026-10-03T00:00:00Z", max_schemas=2
    )

    lines = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))
    assert entry.kind == "schema_registry"
    assert [line["contract"]["schema"]["name"] for line in lines] == ["orders", "payments"]
    assert lines[0]["contract"]["schema"]["version"] == 2
    assert lines[0]["contract"]["schema"]["definition"]["type"] == "record"
    assert "SecretToken" not in lines[0]["contract"]["schema"]
    assert "schema_definition_missing" in lines[1]["unresolved"]
    facts = analyze_schema_registry(str(tmp_path / entry.path), limit=50)["items"]
    assert any(fact["kind"] == "schema.registry" for fact in facts)
    assert any(fact["kind"] == "schema.definition" for fact in facts)
    assert any(fact["kind"] == "schema.unresolved" for fact in facts)
    assert [name for name, _ in fake_glue.calls].count("list_schemas") == 2
    assert all(
        name in {"get_registry", "list_schemas", "get_schema", "get_schema_version"}
        for name, _ in fake_glue.calls
    )


def test_collector_cache_is_offline_and_manifested(monkeypatch, tmp_path):
    fake_glue = FakeGlueSchemaRegistry()
    monkeypatch.setattr(schema_registry, "require_boto3", lambda: FakeBoto3(fake_glue))
    first = schema_registry.collect_schema_registry(
        tmp_path, registry_name="events", now="2026-10-03T00:00:00Z", max_schemas=2
    )

    def boom():
        raise AssertionError("cache hit não pode tocar AWS")

    monkeypatch.setattr(schema_registry, "require_boto3", boom)
    second = schema_registry.collect_schema_registry(
        tmp_path, registry_name="events", now="2026-10-04T00:00:00Z", max_schemas=2
    )
    assert second == first
    manifest = load_manifest(tmp_path)
    assert manifest[0]["kind"] == "schema_registry"
    assert manifest[0]["collect_command"].startswith("sparkforge-aws collect schema-registry")


def test_cli_and_mcp_schema_registry_collection_match(monkeypatch, tmp_path, capsys):
    first_glue = FakeGlueSchemaRegistry()
    monkeypatch.setattr(schema_registry, "require_boto3", lambda: FakeBoto3(first_glue))
    mcp = call_tool("sparkforge_collect_schema_registry", _args(tmp_path / "mcp"))
    first_output = capsys.readouterr()

    second_glue = FakeGlueSchemaRegistry()
    monkeypatch.setattr(schema_registry, "require_boto3", lambda: FakeBoto3(second_glue))
    cli_code = main(
        [
            "collect",
            "schema-registry",
            "--repo",
            str(tmp_path / "cli"),
            "--registry-name",
            "events",
            "--max-schemas",
            "2",
            "--now",
            "2026-10-03T00:00:00Z",
        ]
    )
    cli = json.loads(capsys.readouterr().out)
    assert cli_code == 0
    assert first_output.err == ""
    for payload in (mcp, cli):
        assert payload["kind"] == "schema_registry"
        assert payload["cache_hit"] is False
        payload.pop("path")
        payload.pop("journal", None)
        payload.pop("journal_reason", None)
        # `_trust` e aditivo de call_tool (FASE 3); formato travado em
        # tests/test_runtime_convergence_trust.py
        payload.pop("_trust", None)
    assert cli == mcp


def test_schema_registry_collection_docs_state_read_only_limits():
    root = Path(__file__).parents[1]
    text = (root / "knowledge/schema-registry-data-contracts.md").read_text(encoding="utf-8")
    cli = (root / "docs/guia/03-cli.md").read_text(encoding="utf-8")
    mcp = (root / "docs/guia/04-mcp.md").read_text(encoding="utf-8")
    for document in (text, cli, mcp):
        assert "schema-registry" in document
        assert "read-only" in document or "somente leitura" in document
        assert "latest" in document.lower() or "mais recente" in document.lower()
