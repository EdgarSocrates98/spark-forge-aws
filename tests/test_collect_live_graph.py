from __future__ import annotations

import json
from pathlib import Path

from sparkforge.collect import live_graph


class _FakeSts:
    def get_caller_identity(self):
        return {"Account": "111111111111"}


class _FakeGlue:
    def get_table(self, **kwargs):
        assert kwargs["DatabaseName"] == "raw"
        assert kwargs["Name"] == "events"
        return {
            "Table": {
                "Name": "events",
                "DatabaseName": "raw",
                "CatalogId": "111111111111",
                "StorageDescriptor": {"Location": "s3://customer-data/raw/events/"},
            }
        }


class _FakeLakeFormation:
    def list_permissions(self, **kwargs):
        assert kwargs["Resource"]["Table"]["Name"] == "events"
        return {
            "PrincipalResourcePermissions": [
                {"Principal": {"DataLakePrincipalIdentifier": "arn:aws:iam::111111111111:role/job"}}
            ]
        }

    def get_data_lake_settings(self, **kwargs):
        return {
            "DataLakeSettings": {
                "AllowFullTableExternalDataAccess": True,
                "AllowExternalDataFiltering": False,
            }
        }


class _FakeS3:
    def list_objects_v2(self, **kwargs):
        assert kwargs["Bucket"] == "customer-data"
        return {"Contents": [{"Key": "raw/events/part-0.parquet", "Size": 12}]}


class _FakeBoto3:
    def __init__(self, s3=None):
        self._s3 = s3 or _FakeS3()

    def client(self, service, **kwargs):
        return {
            "sts": _FakeSts(),
            "glue": _FakeGlue(),
            "lakeformation": _FakeLakeFormation(),
            "s3": self._s3,
        }[service]


class _AwsError(Exception):
    response = {"Error": {"Code": "AccessDenied"}}


class _DeniedS3:
    def list_objects_v2(self, **kwargs):
        raise _AwsError("denied")


class _TruncatedS3:
    def list_objects_v2(self, **kwargs):
        return {"Contents": [{"Key": "raw/events/part-0.parquet", "Size": 12}], "IsTruncated": True}


def _manifest(tmp_path: Path, *, account_id: str = "111111111111") -> Path:
    (tmp_path / "repo").mkdir()
    path = tmp_path / "workspace.yaml"
    path.write_text(
        f"""workspace: customer-data
repositories:
  - name: repo
    path: repo
relationships: {{}}
cloud_resources:
  - id: events
    kind: dataset
    services: [glue, lakeformation, s3]
    account_id: '{account_id}'
    catalog_id: '{account_id}'
    region: us-east-1
    database: raw
    table: events
    bucket: customer-data
    prefix: raw/events/
""",
        encoding="utf-8",
    )
    return path


def test_collect_live_graph_compose_glue_lakeformation_s3(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path)
    monkeypatch.setattr(live_graph, "require_boto3", lambda: _FakeBoto3())

    entry = live_graph.collect_workspace_graph(
        manifest, tmp_path, now="2026-09-27T00:00:00Z", max_objects=10
    )
    artifact = tmp_path / entry.path
    payload = json.loads(artifact.read_text(encoding="utf-8"))

    kinds = {node["kind"] for node in payload["graph"]["nodes"]}
    relations = {edge["relation"] for edge in payload["graph"]["edges"]}
    assert {"glue_table", "lakeformation", "s3_prefix", "s3_object"} <= kinds
    assert {"catalog_contains", "governed_by", "stored_at", "contains", "grants_to"} <= relations
    assert payload["unresolved"] == []


def test_cross_account_requires_explicit_role(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path, account_id="222222222222")
    monkeypatch.setattr(live_graph, "require_boto3", lambda: _FakeBoto3())

    entry = live_graph.collect_workspace_graph(
        manifest, tmp_path, now="2026-09-27T00:00:00Z", max_objects=10
    )
    payload = json.loads((tmp_path / entry.path).read_text(encoding="utf-8"))

    assert any(item["reason"] == "cross_account_role_required" for item in payload["unresolved"])
    assert payload["resources"][0]["services"] == []


def test_live_graph_preserves_unresolved_states(tmp_path, monkeypatch):
    denied_root = tmp_path / "denied"
    denied_root.mkdir()
    denied_manifest = _manifest(denied_root)
    monkeypatch.setattr(live_graph, "require_boto3", lambda: _FakeBoto3(_DeniedS3()))
    denied_entry = live_graph.collect_workspace_graph(
        denied_manifest, denied_root, now="2026-09-27T00:00:00Z", max_objects=10
    )
    denied_payload = json.loads((denied_root / denied_entry.path).read_text(encoding="utf-8"))
    assert any(item["reason"] == "access_denied" for item in denied_payload["unresolved"])
    assert not any(node["kind"] == "s3_prefix" for node in denied_payload["graph"]["nodes"])

    truncated_root = tmp_path / "truncated"
    truncated_root.mkdir()
    truncated_manifest = _manifest(truncated_root)
    monkeypatch.setattr(live_graph, "require_boto3", lambda: _FakeBoto3(_TruncatedS3()))
    truncated_entry = live_graph.collect_workspace_graph(
        truncated_manifest, truncated_root, now="2026-09-27T00:00:00Z", max_objects=1
    )
    truncated_payload = json.loads(
        (truncated_root / truncated_entry.path).read_text(encoding="utf-8")
    )
    assert any(
        item["reason"] == "s3_listing_truncated" for item in truncated_payload["unresolved"]
    )
