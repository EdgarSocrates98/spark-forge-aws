import hashlib
import json
import subprocess
import sys

import pytest

from sparkforge.collect.base import (
    ARTIFACT_KINDS,
    ArtifactEntry,
    CollectorUnavailable,
    load_manifest,
    manifest_path,
    register_artifact,
    require_boto3,
    verify_all,
    verify_artifact,
)

GOOD_SHA = "a" * 64


def make_entry(**overrides) -> ArtifactEntry:
    kwargs = {
        "kind": "event_log",
        "path": "artifacts/eventlog/jr_abc.json",
        "sha256": GOOD_SHA,
        "source": "s3://bucket/spark-event-logs/jr_abc",
        "collect_command": "sparkforge collect eventlog --job-run jr_abc",
        "collected_at": "2026-07-29T14:02:11Z",
    }
    kwargs.update(overrides)
    return ArtifactEntry(**kwargs)


class TestArtifactEntryValidation:
    def test_valid_entry_does_not_raise(self):
        entry = make_entry()
        assert entry.kind == "event_log"
        assert entry.sha256 == GOOD_SHA

    def test_all_declared_kinds_are_accepted(self):
        for kind in ARTIFACT_KINDS:
            assert make_entry(kind=kind).kind == kind

    def test_rejects_unknown_kind(self):
        with pytest.raises(ValueError, match="kind"):
            make_entry(kind="not_a_real_kind")

    def test_rejects_malformed_sha256_too_short(self):
        with pytest.raises(ValueError, match="sha256"):
            make_entry(sha256="abc123")

    def test_rejects_malformed_sha256_uppercase(self):
        with pytest.raises(ValueError, match="sha256"):
            make_entry(sha256="A" * 64)

    def test_rejects_malformed_sha256_non_hex(self):
        with pytest.raises(ValueError, match="sha256"):
            make_entry(sha256="z" * 64)

    def test_rejects_empty_collect_command(self):
        with pytest.raises(ValueError, match="collect_command"):
            make_entry(collect_command="")

    def test_to_dict_round_trips_all_fields(self):
        entry = make_entry()
        data = entry.to_dict()
        assert data == {
            "kind": "event_log",
            "path": "artifacts/eventlog/jr_abc.json",
            "sha256": GOOD_SHA,
            "source": "s3://bucket/spark-event-logs/jr_abc",
            "collect_command": "sparkforge collect eventlog --job-run jr_abc",
            "collected_at": "2026-07-29T14:02:11Z",
        }


class TestManifestPath:
    def test_manifest_path_is_under_sparkforge_artifacts(self, tmp_path):
        path = manifest_path(tmp_path)
        assert path == tmp_path / ".sparkforge" / "artifacts" / "manifest.json"


class TestLoadManifest:
    def test_returns_empty_list_when_absent(self, tmp_path):
        assert load_manifest(tmp_path) == []

    def test_returns_empty_list_on_malformed_json(self, tmp_path):
        path = manifest_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text("{not valid json", encoding="utf-8")
        assert load_manifest(tmp_path) == []

    def test_returns_empty_list_when_json_is_not_a_list(self, tmp_path):
        path = manifest_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"oops": True}), encoding="utf-8")
        assert load_manifest(tmp_path) == []

    def test_never_raises_on_absent_root(self, tmp_path):
        missing_root = tmp_path / "does" / "not" / "exist"
        assert load_manifest(missing_root) == []


class TestRegisterArtifact:
    def test_round_trips_through_disk(self, tmp_path):
        entry = make_entry()
        register_artifact(entry, tmp_path)
        loaded = load_manifest(tmp_path)
        assert loaded == [entry.to_dict()]

    def test_replaces_existing_entry_with_same_path(self, tmp_path):
        original = make_entry(sha256=GOOD_SHA)
        register_artifact(original, tmp_path)

        updated = make_entry(sha256="b" * 64, collected_at="2026-07-30T00:00:00Z")
        register_artifact(updated, tmp_path)

        loaded = load_manifest(tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["sha256"] == "b" * 64

    def test_adds_a_second_entry_with_a_different_path(self, tmp_path):
        register_artifact(make_entry(path="a.json"), tmp_path)
        register_artifact(make_entry(path="b.json"), tmp_path)
        loaded = load_manifest(tmp_path)
        assert {e["path"] for e in loaded} == {"a.json", "b.json"}

    def test_output_is_deterministic_regardless_of_insertion_order(self, tmp_path):
        register_artifact(make_entry(path="z.json"), tmp_path)
        register_artifact(make_entry(path="a.json"), tmp_path)
        text_forward = manifest_path(tmp_path).read_text(encoding="utf-8")

        other_root = tmp_path / "other"
        register_artifact(make_entry(path="a.json"), other_root)
        register_artifact(make_entry(path="z.json"), other_root)
        text_backward = manifest_path(other_root).read_text(encoding="utf-8")

        assert text_forward == text_backward

    def test_writing_twice_with_same_content_produces_byte_identical_output(self, tmp_path):
        register_artifact(make_entry(), tmp_path)
        first = manifest_path(tmp_path).read_text(encoding="utf-8")
        register_artifact(make_entry(), tmp_path)
        second = manifest_path(tmp_path).read_text(encoding="utf-8")
        assert first == second


class TestVerifyArtifact:
    def test_absent_artifact_is_not_present_and_hash_does_not_match(self, tmp_path):
        entry = make_entry(path="missing.json").to_dict()
        result = verify_artifact(entry, tmp_path)
        assert result == {
            "kind": "event_log",
            "path": "missing.json",
            "present": False,
            "hash_matches": False,
            "collect_command": "sparkforge collect eventlog --job-run jr_abc",
            "source": "s3://bucket/spark-event-logs/jr_abc",
        }

    def test_present_and_matching_hash(self, tmp_path):
        content = b"hello world"
        digest = hashlib.sha256(content).hexdigest()
        target = tmp_path / "present.json"
        target.write_bytes(content)

        entry = make_entry(path="present.json", sha256=digest).to_dict()
        result = verify_artifact(entry, tmp_path)
        assert result["present"] is True
        assert result["hash_matches"] is True

    def test_present_but_mismatched_hash(self, tmp_path):
        target = tmp_path / "changed.json"
        target.write_bytes(b"content at collection time")

        entry = make_entry(path="changed.json", sha256=GOOD_SHA).to_dict()
        result = verify_artifact(entry, tmp_path)
        assert result["present"] is True
        assert result["hash_matches"] is False


class TestVerifyAll:
    def test_empty_manifest_yields_empty_result(self, tmp_path):
        assert verify_all(tmp_path) == []

    def test_verifies_every_registered_entry(self, tmp_path):
        register_artifact(make_entry(path="a.json"), tmp_path)
        register_artifact(make_entry(path="b.json"), tmp_path)
        results = verify_all(tmp_path)
        assert {r["path"] for r in results} == {"a.json", "b.json"}
        assert all(r["present"] is False for r in results)


class TestRequireBoto3WithoutBoto3Installed:
    def test_module_imports_cleanly_when_boto3_is_poisoned(self):
        # sys.modules["boto3"] = None simula boto3 ausente: qualquer
        # `import boto3` de nivel de modulo levantaria ModuleNotFoundError na
        # importacao do proprio pacote. Isto roda num subprocesso novo, nao
        # via importlib.reload no processo do teste -- reload reexecutaria
        # `class CollectorUnavailable(...)` e criaria uma segunda classe com
        # identidade distinta da importada no topo deste arquivo, quebrando
        # o isinstance em pytest.raises do teste seguinte.
        script = (
            "import sys; sys.modules['boto3'] = None; "
            "import sparkforge.collect.base as m; "
            "assert hasattr(m, 'require_boto3')"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
        )
        assert result.returncode == 0, result.stderr

    def test_require_boto3_raises_collector_unavailable_when_boto3_is_poisoned(
        self, monkeypatch
    ):
        monkeypatch.setitem(sys.modules, "boto3", None)
        with pytest.raises(CollectorUnavailable, match=r"sparkforge-aws\[aws\]"):
            require_boto3()
