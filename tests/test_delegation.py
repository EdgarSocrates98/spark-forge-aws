"""lf-0029: peer delegation — discovery, governance, exec, handoff, routing.

Every test fakes the specialist surface: PATH scripts written into tmp_path,
injected ``which``/``dist_loader``/``runner`` seams, or a fake ``popen_run``.
The real ``data-sentinel`` and ``forge-doctor-data`` binaries are never
executed — an absent/incompatible specialist is a named refusal, never a
simulated run.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from sparkforge_aws.delegation import governance
from sparkforge_aws.delegation.contracts import (
    DelegationRefusal,
    ExecResult,
)
from sparkforge_aws.delegation.discovery import discover_peer
from sparkforge_aws.delegation.env import is_credential_name, safe_env
from sparkforge_aws.delegation.execute import run_governed
from sparkforge_aws.delegation.handoff import (
    HandoffParseError,
    parse_doctor_scan,
    parse_sentinel_report,
)
from sparkforge_aws.delegation.peers import DOCTOR_DATA, SENTINEL, consumer_delegation
from sparkforge_aws.delegation.run import delegate, plan

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

@dataclass
class _FakeProc:
    returncode: int = 0
    stdout: bytes = b""
    stderr: bytes = b""


def _proc(rc: int = 0, out: str = "", err: str = "") -> _FakeProc:
    return _FakeProc(returncode=rc, stdout=out.encode(), stderr=err.encode())


def _no_dist(name: str):
    return None, None


def _no_which(name: str):
    return None


class _FakeDist:
    """An importlib.metadata Distribution stand-in."""

    def __init__(self, meta: dict[str, Any], files_root: Path | None = None):
        self._meta = meta
        self._root = files_root
        self.metadata = meta
        self.version = meta.get("version")
        self.files = meta.get("files", [])

    def locate_file(self, rel: str) -> Path:
        assert self._root is not None
        return self._root / rel


def _dist_loader(meta_by_name: dict[str, dict[str, Any]], root: Path | None = None):
    """Fake ``dist_loader`` — ``meta_by_name`` keys are the *normalized*
    shape ``_load_dist`` produces (``name``/``version``/``requires_python``/
    ``files``), and ``Name`` is accepted as a convenience alias."""
    def load(name: str):
        meta = meta_by_name.get(name)
        if meta is None:
            return None, None
        normalized = {
            "name": meta.get("name") or meta.get("Name") or name,
            "version": meta.get("version"),
            "requires_python": meta.get("requires_python")
                or meta.get("Requires-Python"),
            "files": list(meta.get("files") or []),
        }
        return _FakeDist(meta, root), normalized
    return load


def _probe_runner(table: dict[tuple[str, ...], _FakeProc | BaseException]):
    """A discovery-probe runner: argv tail (after the cli path) → fake proc."""

    def run(argv: list[str], **kwargs: Any):
        key = tuple(argv[1:])
        value = table.get(key)
        if isinstance(value, BaseException):
            raise value
        if value is None:
            return ExecResult(argv=list(argv), returncode=127,
                              stderr="probe not faked")
        return value
    return run


def _write_exe(path: Path, body: str) -> Path:
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if os.name == "nt":
        shim = path.with_name(path.name + ".cmd")
        shim.write_text(
            f'@echo off\r\n"{sys.executable}" "{path}" %*\r\n', encoding="utf-8"
        )
        return shim
    return path


_SENTINEL_CLI = r'''
import json, sys
argv = sys.argv[1:]
if "--version" in argv:
    print("data-sentinel 1.2.3"); sys.exit(0)
if argv[:2] == ["capabilities", "--descriptors"]:
    print(json.dumps([
        {"capability_id": "sentinel.log-analysis", "provider": "data-sentinel-forge",
         "version": "1.2.3", "description": "log diagnostics",
         "input_types": ["log"], "output_types": ["report"]},
        {"capability_id": "sentinel.glue-diagnose", "provider": "data-sentinel-forge",
         "version": "1.2.3", "description": "glue diagnose",
         "input_types": ["cloud"], "output_types": ["report"]},
    ])); sys.exit(0)
if argv and argv[0] in ("analyze", "glue", "sql", "spark", "lakehouse", "emr"):
    print(json.dumps({
        "findings": [{
            "finding_id": "OOM-DRV-1", "severity": "high", "status": "PROBABLE",
            "explanation": "driver memory near limit", "evidence_ids": ["EV-1", "EV-2"],
        }, {
            "finding_id": "SKEW-1", "severity": "medium", "status": "POSSIBLE",
            "explanation": "partition skew suspected", "evidence_ids": [],
        }],
        "limitations": ["sampled logs only"],
    })); sys.exit(0)
sys.exit(2)
'''

_DOCTOR_CLI = r'''
import json, sys
argv = sys.argv[1:]
if "--version" in argv:
    print("forge-doctor-data 0.9.1"); sys.exit(0)
if argv and argv[0] == "scan":
    print(json.dumps({
        "tool": "forge-doctor-data", "version": "0.9.1", "schema_version": "3.0",
        "project": {"path": argv[1] if len(argv) > 1 else "."},
        "summary": {"files": 3, "errors": 1, "warnings": 1},
        "findings": [
            {"id": "DD-SEC-001", "sev": "error", "loc": "jobs/etl.py:12",
             "fp": "ab12cd"},
            {"id": "DD-CFG-010", "sev": "warning", "loc": "conf/spark.yml:4",
             "fp": "ef34ab"},
        ],
    })); sys.exit(1)  # rc 1: findings at/above the exit gate — a result
sys.exit(2)
'''


@pytest.fixture()
def sentinel_cli(tmp_path: Path) -> str:
    return str(_write_exe(tmp_path / "data-sentinel", _SENTINEL_CLI))


@pytest.fixture()
def doctor_cli(tmp_path: Path) -> str:
    return str(_write_exe(tmp_path / "forge-doctor-data", _DOCTOR_CLI))


def _sentinel_injections(cli: str) -> dict[str, Any]:
    # no ``runner``: the fake script answers --version and capabilities
    # --descriptors through the real governed subprocess boundary.
    return {
        "which": lambda name: cli if name == "data-sentinel" else None,
        "dist_loader": _no_dist,
    }


def _doctor_injections(cli: str, *, with_dist: bool = True) -> dict[str, Any]:
    return {
        "which": lambda name: cli if name == "forge-doctor-data" else None,
        "dist_loader": _dist_loader(
            {"forge-doctor-data": {"Name": "forge-doctor-data",
                                   "version": "0.9.1", "files": []}}
        ) if with_dist else _no_dist,
    }


# ---------------------------------------------------------------------------
# Discovery states
# ---------------------------------------------------------------------------

class TestDiscoveryStates:
    def test_not_installed(self, tmp_path: Path):
        entry = discover_peer(
            SENTINEL, probe=True, workspace_root=tmp_path,
            which=_no_which, dist_loader=_no_dist,
        )
        assert entry.state == "NOT_INSTALLED"
        assert entry.checks["handshake"] == "SKIP"

    def test_discovered_without_probe(self, tmp_path: Path):
        loader = _dist_loader(
            {"forge-doctor-data": {"Name": "forge-doctor-data",
                                   "version": "0.9.1", "files": []}}
        )
        entry = discover_peer(
            DOCTOR_DATA, probe=False, workspace_root=tmp_path,
            which=_no_which, dist_loader=loader,
        )
        assert entry.state == "DISCOVERED"
        assert entry.version == "0.9.1"

    def test_verified_via_version_and_descriptors(self, sentinel_cli: str,
                                                  tmp_path: Path):
        entry = discover_peer(
            SENTINEL, probe=True, workspace_root=tmp_path,
            which=lambda n: sentinel_cli if n == "data-sentinel" else None,
            dist_loader=_no_dist,
        )
        # the fake script answers both governed probes for real
        assert entry.state == "VERIFIED", entry.notes
        assert entry.checks["health"] == "PASS"
        assert entry.version == "1.2.3"

    def test_verified_doctor_without_descriptor_surface(self, doctor_cli: str,
                                                        tmp_path: Path):
        entry = discover_peer(
            DOCTOR_DATA, probe=True, workspace_root=tmp_path,
            **_doctor_injections(doctor_cli),
        )
        assert entry.state == "VERIFIED", entry.notes
        assert entry.checks["health"] == "PASS"

    def test_incompatible_requires_python(self, tmp_path: Path):
        loader = _dist_loader(
            {"forge-doctor-data": {
                "Name": "forge-doctor-data", "version": "0.9.1",
                "Requires-Python": ">=99.0", "files": []}}
        )
        entry = discover_peer(
            DOCTOR_DATA, probe=True, workspace_root=tmp_path,
            which=_no_which, dist_loader=loader,
        )
        assert entry.state == "INCOMPATIBLE"
        assert any("requires-python" in lim for lim in entry.limitations)

    def test_incompatible_manifest_major_drift(self, tmp_path: Path):
        # bundled capability manifest declares a different major version
        manifest = {
            "schema": "theforge/SpecialistCapability/v1",
            "specialist": {"id": "forge-doctor-data", "version": "9.0.0"},
            "capabilities": [],
        }
        loader = _dist_loader(
            {"forge-doctor-data": {
                "Name": "forge-doctor-data", "version": "0.9.1",
                "files": ["forge.capabilities.json"]}},
            root=tmp_path,
        )
        (tmp_path / "forge.capabilities.json").write_text(json.dumps(manifest))
        entry = discover_peer(
            DOCTOR_DATA, probe=True, workspace_root=tmp_path,
            which=_no_which, dist_loader=loader,
        )
        assert entry.state == "INCOMPATIBLE", entry.notes

    def test_untrusted_corrupt_manifest(self, tmp_path: Path):
        manifest = {"schema": "wrong/Schema", "specialist": {"id": "x"}}
        loader = _dist_loader(
            {"forge-doctor-data": {
                "Name": "forge-doctor-data", "version": "0.9.1",
                "files": ["forge.capabilities.json"]}},
            root=tmp_path,
        )
        (tmp_path / "forge.capabilities.json").write_text(json.dumps(manifest))
        entry = discover_peer(
            DOCTOR_DATA, probe=True, workspace_root=tmp_path,
            which=_no_which, dist_loader=loader,
        )
        assert entry.state == "UNTRUSTED"
        assert entry.checks["manifest"] == "FAIL"

    def test_degraded_failed_probe(self, tmp_path: Path):
        entry = discover_peer(
            SENTINEL, probe=True, workspace_root=tmp_path,
            which=lambda n: "/nonexistent/data-sentinel" if n == "data-sentinel" else None,
            dist_loader=_no_dist,
            runner=_probe_runner({}),
        )
        # cli on PATH (fake path string) but probe fails → DEGRADED
        assert entry.state == "DEGRADED"
        assert entry.checks["handshake"] == "FAIL"


# ---------------------------------------------------------------------------
# Environment scrubbing
# ---------------------------------------------------------------------------

class TestEnvScrubbing:
    def test_credential_names(self):
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
                     "AWS_SESSION_TOKEN", "AWS_PROFILE", "GITHUB_TOKEN",
                     "MY_API_KEY", "DB_PASSWORD", "HTTPS_PROXY"):
            assert is_credential_name(name), name
        for name in ("PATH", "HOME", "LANG", "TERM"):
            assert not is_credential_name(name), name

    def test_safe_env_strips_aws_credentials(self):
        env = safe_env({
            "PATH": "/usr/bin",
            "AWS_ACCESS_KEY_ID": "AKIA" + "X" * 16,
            "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI",
            "AWS_PROFILE": "prod",
            "AWS_DEFAULT_REGION": "us-east-1",
            "HTTP_PROXY": "http://user:pw@proxy:8080",
            "HOME": "/home/x",
            "SPARKFORGE_CONFIG": "x",  # not allowlisted either
        })
        assert env["PATH"] == "/usr/bin"
        assert env["HOME"] == "/home/x"
        for leaked in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
                       "AWS_PROFILE", "AWS_DEFAULT_REGION", "HTTP_PROXY",
                       "SPARKFORGE_CONFIG"):
            assert leaked not in env, leaked

    def test_env_extra_cannot_smuggle_credentials(self):
        result = run_governed(
            ["data-sentinel", "--version"],
            env_extra={"AWS_SECRET_ACCESS_KEY": "x"},
        )
        assert isinstance(result, DelegationRefusal)
        assert result.code == "policy-refusal"

    def test_subprocess_never_sees_credentials(self, tmp_path: Path):
        captured: dict[str, Any] = {}

        def spy(argv, **kw):
            captured["env"] = kw.get("env", {})
            captured["kw"] = kw
            return _proc(out="ok")

        os.environ["AWS_SECRET_ACCESS_KEY"] = "AKIA" + "Y" * 16
        try:
            run_governed(["data-sentinel", "--version"], _popen_run=spy)
        finally:
            del os.environ["AWS_SECRET_ACCESS_KEY"]
        assert "AWS_SECRET_ACCESS_KEY" not in captured["env"]
        assert captured["kw"].get("shell") in (None, False)


# ---------------------------------------------------------------------------
# Governed execution
# ---------------------------------------------------------------------------

class TestRunGoverned:
    def test_never_shell_argv_only(self):
        seen: dict[str, Any] = {}

        def spy(argv, **kw):
            seen["argv"] = argv
            seen["kw"] = kw
            return _proc(out="ok")

        result = run_governed(["x", "--y"], _popen_run=spy)
        assert isinstance(result, ExecResult)
        assert isinstance(seen["argv"], list)
        assert seen["kw"].get("shell") in (None, False)

    def test_timeout_is_named(self):
        def hang(argv, **kw):
            raise subprocess.TimeoutExpired(cmd=argv[0], timeout=1)

        result = run_governed(["slow-cli"], timeout_s=1, _popen_run=hang)
        assert isinstance(result, DelegationRefusal)
        assert result.code == "timeout"

    def test_spawn_failure_provider_absent(self):
        def missing(argv, **kw):
            raise FileNotFoundError(argv[0])

        result = run_governed(["ghost-cli"], _popen_run=missing)
        assert isinstance(result, DelegationRefusal)
        assert result.code == "provider-absent"

    def test_output_caps(self):
        big = b"x" * (4 * 1024 * 1024 + 10)

        def noisy(argv, **kw):
            return _proc(rc=0, out=big.decode())

        result = run_governed(["loud"], _popen_run=noisy)
        assert isinstance(result, ExecResult)
        assert result.stdout_truncated
        assert result.stdout_bytes > len(result.stdout.encode())


# ---------------------------------------------------------------------------
# Handoff parsers — severity/confidence as declared, never promoted
# ---------------------------------------------------------------------------

class TestHandoffParsers:
    def test_sentinel_confidence_rename_no_promotion(self):
        parsed = parse_sentinel_report(json.dumps({
            "findings": [
                {"finding_id": "F1", "severity": "HIGH", "status": "CONFIRMED",
                 "explanation": "a"},
                {"finding_id": "F2", "severity": "MEDIUM", "status": "PROBABLE",
                 "explanation": "b"},
                {"finding_id": "F3", "severity": "LOW", "status": "POSSIBLE",
                 "explanation": "c"},
                {"finding_id": "F4", "severity": "INFO", "status": "UNKNOWN",
                 "explanation": "d"},
            ],
        }))
        conf = {f["id"]: f["confidence"] for f in parsed["findings"]}
        assert conf == {"F1": "CONFIRMED", "F2": "LIKELY",
                        "F3": "POSSIBLE", "F4": "UNKNOWN"}
        sev = {f["id"]: f["severity"] for f in parsed["findings"]}
        assert sev == {"F1": "high", "F2": "medium", "F3": "low", "F4": "info"}

    def test_possible_never_becomes_confirmed(self):
        parsed = parse_sentinel_report(json.dumps({
            "findings": [{"finding_id": "F", "severity": "info",
                          "status": "POSSIBLE", "explanation": "x"}],
        }))
        assert parsed["findings"][0]["confidence"] == "POSSIBLE"

    def test_sentinel_non_report_json_is_summary_evidence(self):
        parsed = parse_sentinel_report(json.dumps({"job": {"Name": "j1"}}))
        assert parsed["findings"] == []
        assert parsed["summary_refs"][0]["kind"] == "summary"

    def test_sentinel_invalid_output(self):
        with pytest.raises(HandoffParseError):
            parse_sentinel_report("not json at all")

    def test_doctor_scan_maps_agent_format(self):
        parsed = parse_doctor_scan(json.dumps({
            "tool": "forge-doctor-data", "version": "0.9.1",
            "schema_version": "3.0",
            "summary": {"files": 2, "errors": 1},
            "findings": [
                {"id": "DD-1", "sev": "error", "loc": "a.py:1", "fp": "h1"},
                {"id": "DD-2", "sev": "warning", "loc": "b.py:2", "fp": "h2"},
                {"id": "DD-3", "sev": "info", "loc": None, "fp": "h3"},
            ],
        }))
        assert [f["severity"] for f in parsed["findings"]] == [
            "high", "medium", "info"]
        assert all(f["confidence"] == "UNKNOWN" for f in parsed["findings"])
        assert parsed["findings"][0]["evidence_refs"] == ["a.py:1", "fp:h1"]

    def test_doctor_wrong_schema_version_refused(self):
        with pytest.raises(HandoffParseError):
            parse_doctor_scan(json.dumps({"schema_version": "9.9",
                                          "findings": []}))

    def test_dropped_invalid_refs_recorded(self):
        parsed = parse_doctor_scan(json.dumps({
            "schema_version": "3.0",
            "findings": [{"id": "DD-1", "sev": "info",
                          "loc": "dir with spaces/f.py:1", "fp": "ok"}],
        }))
        assert parsed["findings"][0]["evidence_refs"] == ["fp:ok"]
        assert any("dropped" in lim for lim in parsed["limitations"])


# ---------------------------------------------------------------------------
# Chain control — cycle prevention
# ---------------------------------------------------------------------------

class TestChainControl:
    def test_revisit_refused(self):
        d = governance.start_chain(
            consumer_delegation(), correlation_id="dl-testchain")
        d = governance.admit_hop(d, "data-sentinel-forge")
        assert not isinstance(d, DelegationRefusal)
        again = governance.admit_hop(d, "data-sentinel-forge")
        assert isinstance(again, DelegationRefusal)
        assert again.code == "cycle-detected"

    def test_reentering_consumer_refused(self):
        # Sentinel → Spark → Sentinel shape: the consumer is already visited
        # by construction; a hop back to it is a cycle, never execution.
        d = governance.start_chain(
            consumer_delegation(), correlation_id="dl-testchain2")
        back = governance.admit_hop(d, "spark-forge-aws")
        assert isinstance(back, DelegationRefusal)
        assert back.code == "cycle-detected"

    def test_hop_budget(self):
        d = governance.start_chain(
            consumer_delegation(), correlation_id="dl-b", max_hops=1)
        d = governance.admit_hop(d, "data-sentinel-forge")
        exhausted = governance.admit_hop(d, "forge-doctor-data")
        assert isinstance(exhausted, DelegationRefusal)
        assert exhausted.code == "budget-exhausted"


# ---------------------------------------------------------------------------
# argv resolution
# ---------------------------------------------------------------------------

class TestArgvResolution:
    def test_optional_placeholders_drop_flag(self):
        argv = governance.resolve_capability_argv(
            ["{cli}", "glue", "diagnose", "--job", "{job}",
             "--run-id", "{run_id}", "--json"],
            cli_argv=["data-sentinel"],
            values={"job": "j1", "run_id": None},
        )
        assert argv == ["data-sentinel", "glue", "diagnose", "--job", "j1",
                        "--json"]

    def test_traversal_in_target_refused(self):
        refusal = governance.resolve_capability_argv(
            ["{cli}", "analyze", "--file", "{target}"],
            cli_argv=["data-sentinel"],
            values={"target": "../../etc/passwd"},
        )
        assert isinstance(refusal, DelegationRefusal)
        assert refusal.code == "invalid-input"

    def test_unknown_placeholder_refused(self):
        refusal = governance.resolve_capability_argv(
            ["{cli}", "x", "{evil}"], cli_argv=["data-sentinel"], values={})
        assert isinstance(refusal, DelegationRefusal)
        assert refusal.code == "invalid-input"


# ---------------------------------------------------------------------------
# Caso E — absent specialist → explicit refusal + native fallback
# ---------------------------------------------------------------------------

class TestAbsentSpecialist:
    def test_delegate_absent_never_executes(self, tmp_path: Path):
        payload = delegate(
            "data-sentinel-forge", "sentinel.log-analysis",
            values={"target": "driver.log"},
            workspace=tmp_path,
            which=_no_which, dist_loader=_no_dist,
            popen_run=lambda *a, **k: pytest.fail("must not spawn"),
        )
        assert payload["status"] == "refused"
        assert payload["refusal"]["code"] == "provider-absent"
        assert payload["fallback"] == "native-analysis"
        assert payload["handoff"] is None
        # nothing persisted — no simulated execution ever lands on disk
        assert not (tmp_path / ".sparkforge_aws").exists()

    def test_plan_absent_reports_unavailable(self, tmp_path: Path):
        payload = plan(
            "diagnose glue job failures and oom",
            workspace=tmp_path, probe=True,
            which=_no_which, dist_loader=_no_dist,
        )
        assert payload["status"] in ("unavailable", "refused")
        codes = {r["code"] for r in payload["refusals"]}
        assert "provider-absent" in codes


# ---------------------------------------------------------------------------
# Caso F — incompatible specialist → explicit block
# ---------------------------------------------------------------------------

class TestIncompatibleSpecialist:
    def test_delegate_incompatible_blocked(self, tmp_path: Path):
        loader = _dist_loader(
            {"forge-doctor-data": {
                "Name": "forge-doctor-data", "version": "0.9.1",
                "Requires-Python": ">=99.0", "files": []}}
        )
        payload = delegate(
            "forge-doctor-data", "doctor.scan-project",
            values={"target": "."},
            workspace=tmp_path,
            which=lambda n: "/x/forge-doctor-data", dist_loader=loader,
            runner=_probe_runner({}),
            popen_run=lambda *a, **k: pytest.fail("must not spawn"),
        )
        assert payload["status"] == "refused"
        assert payload["refusal"]["code"] == "version-incompatible"


# ---------------------------------------------------------------------------
# Policy gates — EXTERNAL_READ/COST_BEARING need explicit authorization
# ---------------------------------------------------------------------------

class TestPolicyGate:
    def test_external_read_denied_without_authorize(self, sentinel_cli: str,
                                                    tmp_path: Path):
        payload = delegate(
            "data-sentinel-forge", "sentinel.glue-inspect",
            values={"job": "j1", "profile": "p", "region": "us-east-1"},
            workspace=tmp_path,
            popen_run=lambda *a, **k: pytest.fail("gate must stop before exec"),
            **_sentinel_injections(sentinel_cli),
        )
        assert payload["status"] == "refused"
        assert payload["refusal"]["code"] == "policy-refusal"
        assert "EXTERNAL_READ" in payload["refusal"]["detail"]

    def test_glue_diagnose_needs_read_and_cost_grants(self, sentinel_cli: str,
                                                      tmp_path: Path):
        # EXTERNAL_READ alone is not enough: undeclared external cost is
        # COST_BEARING — the gate is conjunctive per level.
        payload = delegate(
            "data-sentinel-forge", "sentinel.glue-diagnose",
            values={"job": "j1"},
            authorized_risks={"EXTERNAL_READ"},
            workspace=tmp_path,
            popen_run=lambda *a, **k: pytest.fail("must not spawn"),
            **_sentinel_injections(sentinel_cli),
        )
        assert payload["refusal"]["code"] == "policy-refusal"
        assert "COST_BEARING" in payload["refusal"]["detail"]

    def test_external_read_authorized_executes(self, sentinel_cli: str,
                                               tmp_path: Path):
        payload = delegate(
            "data-sentinel-forge", "sentinel.glue-diagnose",
            values={"job": "j1"},
            authorized_risks={"EXTERNAL_READ", "COST_BEARING"},
            workspace=tmp_path,
            **_sentinel_injections(sentinel_cli),
        )
        assert payload["status"] == "completed", payload
        assert payload["argv"][0] == sentinel_cli
        assert "--profile" not in payload["argv"]  # unset flags dropped
        assert "--region" not in payload["argv"]
        assert payload["handoff_path"] is not None
        assert Path(payload["handoff_path"]).is_file()


# ---------------------------------------------------------------------------
# End-to-end delegate → handoff
# ---------------------------------------------------------------------------

class TestDelegateEndToEnd:
    def test_sentinel_log_analysis_completed(self, sentinel_cli: str,
                                             tmp_path: Path):
        payload = delegate(
            "data-sentinel-forge", "sentinel.log-analysis",
            values={"target": "driver.log", "platform": None},
            workspace=tmp_path,
            **_sentinel_injections(sentinel_cli),
        )
        assert payload["status"] == "completed", payload
        findings = {f["id"]: f for f in payload["findings"]}
        assert findings["OOM-DRV-1"]["confidence"] == "LIKELY"   # PROBABLE→LIKELY
        assert findings["SKEW-1"]["confidence"] == "POSSIBLE"    # never promoted
        assert findings["SKEW-1"]["severity"] == "medium"
        handoff = payload["handoff"]
        assert handoff["schema"] == "theforge/EvidenceHandoff/v1"
        assert handoff["source_provider"] == "data-sentinel-forge"
        assert handoff["consumer_provider"] == "spark-forge-aws"
        assert handoff["redacted"] is True
        assert handoff["integrity"]

    def test_doctor_scan_completed(self, doctor_cli: str, tmp_path: Path):
        payload = delegate(
            "forge-doctor-data", "doctor.scan-project",
            values={"target": ".", "check": None},
            workspace=tmp_path,
            **_doctor_injections(doctor_cli),
        )
        assert payload["status"] == "completed", payload
        by_id = {f["id"]: f for f in payload["findings"]}
        assert by_id["DD-SEC-001"]["severity"] == "high"   # error → high
        assert by_id["DD-SEC-001"]["confidence"] == "UNKNOWN"
        assert "--check" not in payload["argv"]            # unset flag dropped

    def test_handoff_persisted_and_verifiable(self, sentinel_cli: str,
                                              tmp_path: Path):
        payload = delegate(
            "data-sentinel-forge", "sentinel.log-analysis",
            values={"target": "driver.log"},
            workspace=tmp_path,
            **_sentinel_injections(sentinel_cli),
        )
        path = Path(payload["handoff_path"])
        doc = json.loads(path.read_text(encoding="utf-8"))
        from sparkforge_aws.delegation.contracts import from_dict
        from sparkforge_aws.delegation.governance import verify_integrity

        handoff = from_dict(
            __import__("sparkforge_aws.delegation.contracts",
                       fromlist=["EvidenceHandoff"]).EvidenceHandoff, doc)
        assert verify_integrity(handoff)

    def test_invalid_output_is_named_refusal(self, tmp_path: Path):
        cli = _write_exe(tmp_path / "data-sentinel", r'''
import sys
argv = sys.argv[1:]
if "--version" in argv:
    print("1.0.0"); sys.exit(0)
if argv[:2] == ["capabilities", "--descriptors"]:
    print("[]"); sys.exit(0)
print("this is not a diagnostic report"); sys.exit(0)
''')
        payload = delegate(
            "data-sentinel-forge", "sentinel.log-analysis",
            values={"target": "x.log"},
            workspace=tmp_path,
            which=lambda n: str(cli) if n == "data-sentinel" else None,
            dist_loader=_no_dist,
        )
        assert payload["status"] == "refused"
        assert payload["refusal"]["code"] == "invalid-output"
        assert payload["handoff"]["status"] == "refused"

    def test_timeout_is_named_failure(self, tmp_path: Path):
        cli = _write_exe(tmp_path / "data-sentinel", r'''
import sys, json
argv = sys.argv[1:]
if "--version" in argv:
    print("1.0.0"); sys.exit(0)
if argv[:2] == ["capabilities", "--descriptors"]:
    print("[]"); sys.exit(0)
sys.exit(0)
''')

        def hang(argv, **kw):
            raise subprocess.TimeoutExpired(cmd=argv[0], timeout=1)

        payload = delegate(
            "data-sentinel-forge", "sentinel.log-analysis",
            values={"target": "x.log"},
            workspace=tmp_path,
            which=lambda n: str(cli) if n == "data-sentinel" else None,
            dist_loader=_no_dist,
            popen_run=hang,
        )
        assert payload["status"] == "failed"
        assert payload["handoff"]["error"]["code"] == "timeout"
        assert payload["handoff"]["error"]["retryable"] is True

    def test_capability_not_declared(self, tmp_path: Path):
        payload = delegate(
            "data-sentinel-forge", "sentinel.no-such-cap",
            workspace=tmp_path,
            which=_no_which, dist_loader=_no_dist,
        )
        assert payload["refusal"]["code"] == "capability-absent"

    def test_provider_not_declared(self, tmp_path: Path):
        payload = delegate(
            "some-other-forge", "x.y",
            workspace=tmp_path,
        )
        assert payload["refusal"]["code"] == "provider-absent"

    def test_cycle_via_chain_refused(self, sentinel_cli: str, tmp_path: Path):
        chained = governance.start_chain(
            consumer_delegation(), correlation_id="dl-cycle")
        chained = governance.admit_hop(chained, "data-sentinel-forge")
        payload = delegate(
            "data-sentinel-forge", "sentinel.log-analysis",
            values={"target": "x.log"},
            workspace=tmp_path,
            delegation=chained,
            popen_run=lambda *a, **k: pytest.fail("cycle must refuse"),
            **_sentinel_injections(sentinel_cli),
        )
        assert payload["refusal"]["code"] == "cycle-detected"


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class TestRouter:
    def test_static_intent_routes_to_doctor(self, doctor_cli: str,
                                            tmp_path: Path):
        payload = plan(
            "static analysis pyspark review antipatterns",
            workspace=tmp_path,
            which=lambda n: doctor_cli if n == "forge-doctor-data" else None,
            dist_loader=_dist_loader(
                {"forge-doctor-data": {"Name": "forge-doctor-data",
                                       "version": "0.9.1", "files": []}}),
        )
        assert payload["status"] == "planned", payload
        assert payload["picks"][0]["provider"] == "forge-doctor-data"
        assert payload["picks"][0]["capability"] == "doctor.scan-project"

    def test_no_intent_match_is_unavailable(self, doctor_cli: str,
                                            tmp_path: Path):
        payload = plan(
            "refactor the billing microservice",
            workspace=tmp_path,
            **_doctor_injections(doctor_cli),
        )
        assert payload["status"] == "unavailable"
        assert payload["picks"] == []
        assert payload["unknowns"]
