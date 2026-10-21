"""Runtime peer discovery (lf-0029): find sibling forges on this machine.

Native re-implementation of the discovery semantics of
``theforge/discovery.py`` (lf-0027), scoped to what a *consumer* forge needs:
resolve whether a declared specialist is present, what version it reports
and whether its declared capability surface validates — before any
delegation is planned.

Sources (cheap first):

1. ``path``             — ``shutil.which(cli)``: the console script on PATH.
2. ``package``          — ``importlib.metadata``: installed distribution
   name/version/``Requires-Python`` — metadata reads only, never an import
   and never a command from an untrusted source.
3. ``bundled-manifest`` — ``forge.capabilities.json`` / ``forge.agentic.json``
   inside the installed distribution's file list, or at a checkout root.
4. ``checkout``         — a workspace sibling directory carrying
   ``forge.json`` with a matching ``forge_id`` (declared via ``roots``, or
   sibling scan of the workspace's parent — never a deep walk).
5. ``probe``            — typed-argv ``<cli> --version`` plus, when the peer
   declares one, a capability-descriptors probe (``data-sentinel
   capabilities --descriptors``). Always through ``execute.run_governed``:
   argv only, scrubbed env, bounded output, timeout.

DISCOVERED is not VERIFIED. A scan with ``probe=False`` never executes a CLI
and therefore never reaches VERIFIED — it tops out at DISCOVERED. State
precedence mirrors the-forge: a dishonest/broken *declared surface*
(UNTRUSTED) outranks mere presence; a probe that was observed failing this
scan (UNAVAILABLE/DEGRADED) outranks stale VERIFIED evidence; INCOMPATIBLE
(``Requires-Python`` unsatisfied, major-version drift against a bundled
manifest) blocks execution explicitly — never a silent skip.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

from sparkforge_aws.delegation.contracts import (
    AGENTIC_MANIFEST_NAME,
    CAPABILITY_MANIFEST_NAMES,
    RUNTIME_DETECTED,
    SPECIALIST_CAPABILITY_SCHEMA,
    DeclaredCapability,
    DelegationError,
    DiscoveryEvidence,
    PeerDiscovery,
    PeerDiscoveryReport,
    SpecialistCapability,
    SpecialistIdentity,
    sha256_hex,
    utc_now,
)

__all__ = [
    "PeerSpec",
    "discover_peer",
    "discover_peers",
    "PROBE_TIMEOUT_S",
    "VERSION_PROBE",
]

PROBE_TIMEOUT_S = 10.0
VERSION_PROBE = "--version"
_VERSION_OUT_RE = re.compile(r"\d+\.\d+(?:\.\d+)?")
_MAX_FILE_BYTES = 262_144
_MAX_MANIFEST_BYTES = 1_048_576


@dataclass(frozen=True, kw_only=True)
class PeerSpec:
    """Where a declared specialist may legitimately exist on this machine.

    ``capabilities_probe`` is the typed argv (after ``{cli}``) for the peer's
    own descriptor surface — for data-sentinel ``capabilities
    --descriptors``; ``None`` when the peer has no descriptor verb.
    ``capabilities`` is the consumer-side catalog: the real CLI verbs this
    forge may delegate, declared statically because the descriptor surface
    does not carry argv/risk metadata. Declared, never inferred.
    """

    provider: str
    cli: str
    dist_names: tuple[str, ...] = ()
    capabilities_probe: tuple[str, ...] | None = None
    capabilities: tuple[DeclaredCapability, ...] = ()
    # Capability ids the probe is expected to confirm; drift is a note,
    # never a silent override of the declared catalog.
    expected_descriptor_ids: tuple[str, ...] = ()


@dataclass
class _Candidate:
    provider: str
    evidence: list[DiscoveryEvidence] = field(default_factory=list)
    cli_path: str | None = None
    dist_name: str | None = None
    dist_version: str | None = None
    dist_requires_python: str | None = None
    dist_files: list[str] = field(default_factory=list)
    dist_locate: Callable[[str], Path] | None = None
    checkout: Path | None = None
    capability_manifest: SpecialistCapability | None = None
    manifest_error: str | None = None
    agentic_version: str | None = None
    agentic_cli: str | None = None

    def seen(self, source: str, detail: str, *,
             path: Path | None = None, sha256: str | None = None) -> None:
        self.evidence.append(
            DiscoveryEvidence(
                source=source,  # type: ignore[arg-type]
                detail=detail,
                path=str(path) if path is not None else None,
                sha256=sha256,
            )
        )


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """(parsed object, sha256 of the bytes read) — provenance per file."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None, None
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, sha256_hex(raw)
    return (doc if isinstance(doc, dict) else None), sha256_hex(raw)


def _parse_capability_manifest(
    doc: dict[str, Any], expected_id: str
) -> tuple[SpecialistCapability | None, str | None]:
    """Validate a candidate manifest document; (manifest, error)."""
    if doc.get("schema") != SPECIALIST_CAPABILITY_SCHEMA:
        return None, (
            f"schema {doc.get('schema')!r} is not {SPECIALIST_CAPABILITY_SCHEMA!r}"
        )
    from sparkforge_aws.delegation.contracts import from_dict

    try:
        manifest = from_dict(SpecialistCapability, doc)
    except DelegationError as exc:
        return None, str(exc)
    if manifest.specialist.id != expected_id:
        return None, (
            f"manifest specialist.id {manifest.specialist.id!r} != {expected_id!r}"
        )
    return manifest, None


def _parse_agentic_manifest(doc: dict[str, Any], cand: _Candidate) -> str | None:
    """Best-effort read of a ``forge.agentic.json`` (shape is loose: provider,
    version, cli are what we need). Returns an error string or None."""
    provider = doc.get("provider")
    if provider is not None and provider != cand.provider:
        return f"agentic manifest provider {provider!r} != {cand.provider!r}"
    if not isinstance(doc.get("schema"), str):
        return "agentic manifest has no schema id"
    version = doc.get("version")
    if isinstance(version, str) and version:
        cand.agentic_version = version
    cli = doc.get("cli")
    if isinstance(cli, str) and cli:
        cand.agentic_cli = cli
    return None


def _normalize_dist(name: str) -> str:
    """PEP 503 normalization so ``sentinel_forge`` == ``sentinel-forge``."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requires_python_ok(spec: str | None) -> bool | None:
    """Minimal specifier check for ``>=a.b[.c]``/``<a.b[.c]`` clauses.

    ``None`` return = the specifier is absent or in a form this stdlib check
    does not parse — recorded, never silently failed.
    """
    if not spec or not spec.strip():
        return None
    current = sys.version_info[:3]
    for clause in spec.split(","):
        clause = clause.strip()
        match = re.fullmatch(r"(>=|<)\s*(\d+)\.(\d+)(?:\.(\d+))?", clause)
        if match is None:
            return None  # unparseable form → unknown, not a failure
        op = match.group(1)
        patch = match.group(4)
        wanted = (int(match.group(2)), int(match.group(3)), int(patch) if patch else 0)
        if op == ">=" and not current >= wanted:
            return False
        if op == "<" and not current < wanted:
            return False
    return True


def _load_dist(name: str) -> tuple[Any | None, dict[str, Any] | None]:
    """(Distribution, normalized meta) — injectable for tests."""
    try:
        dist = importlib_metadata.distribution(name)
    except importlib_metadata.PackageNotFoundError:
        return None, None
    except Exception:  # a broken metadata backend is evidence-absent, not a crash
        return None, None
    meta: dict[str, Any] = {}
    try:
        meta["name"] = dist.metadata["Name"] or name
    except Exception:
        meta["name"] = name
    meta["version"] = getattr(dist, "version", None)
    try:
        meta["requires_python"] = dist.metadata["Requires-Python"]
    except KeyError:
        meta["requires_python"] = None
    try:
        meta["files"] = [str(f) for f in (dist.files or ())]
    except (OSError, ValueError):
        meta["files"] = []
    return dist, meta


def _load_checkout_manifests(cand: _Candidate, root: Path) -> None:
    """Read capability/agentic manifests at a checkout root."""
    for name in CAPABILITY_MANIFEST_NAMES:
        path = root / name
        if not path.is_file():
            continue
        doc, digest = _read_json(path)
        cand.seen("bundled-manifest", f"capability manifest at {path.name}",
                  path=path, sha256=digest)
        if doc is None:
            cand.manifest_error = f"{path}: unreadable or not a JSON object"
            continue
        manifest, error = _parse_capability_manifest(doc, cand.provider)
        if manifest is not None:
            cand.capability_manifest = manifest
        else:
            cand.manifest_error = f"{path}: {error}"
        break
    agentic_path = root / AGENTIC_MANIFEST_NAME
    if agentic_path.is_file():
        doc, digest = _read_json(agentic_path)
        cand.seen("bundled-manifest", f"{AGENTIC_MANIFEST_NAME} at {agentic_path.name}",
                  path=agentic_path, sha256=digest)
        if doc is not None:
            if err := _parse_agentic_manifest(doc, cand):
                cand.manifest_error = f"{agentic_path}: {err}"
        else:
            cand.manifest_error = f"{agentic_path}: unreadable or not a JSON object"


def _load_dist_manifests(cand: _Candidate, dist: Any, meta: dict[str, Any]) -> None:
    """Locate manifests declared inside an installed dist's file list."""
    for rel in meta["files"]:
        base = Path(rel).name
        if base not in CAPABILITY_MANIFEST_NAMES and base != AGENTIC_MANIFEST_NAME:
            continue
        try:
            raw = Path(dist.locate_file(rel)).read_bytes()[:_MAX_MANIFEST_BYTES]
        except (OSError, ValueError):
            cand.manifest_error = f"{meta['name']}: {rel} unreadable"
            continue
        cand.seen(
            "bundled-manifest",
            f"{base} bundled in dist {meta['name']}=={meta.get('version')}",
            sha256=sha256_hex(raw),
        )
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            cand.manifest_error = f"{meta['name']}:{rel}: not JSON"
            continue
        if not isinstance(doc, dict):
            cand.manifest_error = f"{meta['name']}:{rel}: not a JSON object"
            continue
        if base in CAPABILITY_MANIFEST_NAMES:
            manifest, error = _parse_capability_manifest(doc, cand.provider)
            if manifest is not None:
                cand.capability_manifest = manifest
            else:
                cand.manifest_error = f"{meta['name']}:{rel}: {error}"
        else:
            if err := _parse_agentic_manifest(doc, cand):
                cand.manifest_error = f"{meta['name']}:{rel}: {err}"


def _descriptors_to_manifest(
    provider: str,
    version: str,
    descriptors: list[dict[str, Any]],
) -> tuple[SpecialistCapability | None, str | None]:
    """Synthesize a ``SpecialistCapability`` from a ``capabilities
    --descriptors`` payload (data-sentinel's interop §5 surface).

    Each ``CapabilityDescriptor`` carries id/provider/version/input_types/
    output_types/permissions/limitations — no argv, no risk. The consumer's
    declared catalog (``PeerSpec.capabilities``) supplies those; the probe
    is *verification evidence* that the live surface really exposes the ids.
    """
    caps: list[DeclaredCapability] = []
    for i, item in enumerate(descriptors):
        if not isinstance(item, dict):
            return None, f"descriptor[{i}] is not an object"
        cid = item.get("capability_id")
        if not isinstance(cid, str) or "." in cid and not cid:
            return None, f"descriptor[{i}] has no capability_id"
        provider_id = item.get("provider")
        if provider_id is not None and provider_id != provider:
            return None, (
                f"descriptor[{i}] provider {provider_id!r} != {provider!r}"
            )
        try:
            caps.append(
                DeclaredCapability(
                    id=str(cid),
                    description=str(item.get("description") or ""),
                    version=str(item.get("version") or ""),
                    permissions=[str(p) for p in item.get("permissions") or []],
                    limitations=[str(p) for p in item.get("limitations") or []],
                    verification_mode="probe",
                )
            )
        except DelegationError as exc:
            return None, f"descriptor[{i}] invalid: {exc}"
    try:
        return (
            SpecialistCapability(
                specialist=SpecialistIdentity(id=provider, version=version),
                capabilities=caps,
            ),
            None,
        )
    except DelegationError as exc:
        return None, str(exc)


def _final_state(
    *,
    declared_untrusted: bool,
    incompatible: bool,
    verified: bool,
    unavailable: bool,
    degraded: bool,
    has_evidence: bool,
) -> str:
    """Precedence mirrors ``theforge.discovery._final_state``: dishonest or
    broken declarations outrank mere presence; a dead observed surface
    outranks stale verified evidence."""
    if declared_untrusted:
        return "UNTRUSTED"
    if incompatible:
        return "INCOMPATIBLE"
    if unavailable:
        return "UNAVAILABLE"
    if degraded:
        return "DEGRADED"
    if verified:
        return "VERIFIED"
    if has_evidence:
        return "DISCOVERED"
    return "NOT_INSTALLED"


def discover_peer(
    spec: PeerSpec,
    *,
    probe: bool = True,
    roots: Sequence[Path] = (),
    workspace_root: Path | None = None,
    dist_loader: Callable[[str], tuple[Any | None, dict[str, Any] | None]] | None = None,
    which: Callable[[str], str | None] | None = None,
    runner: Callable[..., Any] | None = None,
) -> PeerDiscovery:
    """Resolve one specialist peer: evidence → checks → a named state.

    Injection seams (never touched in production): ``dist_loader``,
    ``which`` and ``runner`` let tests fake package metadata, PATH
    resolution and the subprocess boundary — the code path under test is
    identical either way.
    """
    which = which or shutil.which
    load_dist = dist_loader or _load_dist
    cand = _Candidate(provider=spec.provider)

    # 1. path ----------------------------------------------------------------
    cli_path = which(spec.cli)
    if cli_path:
        cand.cli_path = cli_path
        cand.seen("path", f"console script {spec.cli!r} resolved", path=Path(cli_path))

    # 2. installed distribution metadata --------------------------------------
    dist = None
    for name in spec.dist_names:
        dist, meta = load_dist(name)
        if meta is not None:
            break
    if meta is not None:
        cand.dist_name = meta["name"]
        cand.dist_version = meta.get("version")
        cand.dist_requires_python = meta.get("requires_python")
        cand.dist_files = meta["files"]
        cand.seen(
            "package",
            f"installed distribution {meta['name']}=={meta.get('version')}",
        )
        _load_dist_manifests(cand, dist, meta)

    # 3. checkout roots: declared roots + a sibling scan of the workspace's
    #    parent directory (one level — never a deep walk). A ``forge.json``
    #    with a matching ``forge_id`` marks the root.
    seen_roots: set[Path] = set()
    candidate_roots: list[Path] = [Path(r) for r in roots]
    if workspace_root is not None:
        parent = Path(workspace_root).resolve().parent
        try:
            for sibling in sorted(parent.iterdir()):
                if sibling.is_dir():
                    candidate_roots.append(sibling)
        except OSError:
            pass
    for root in candidate_roots:
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved in seen_roots or not resolved.is_dir():
            continue
        seen_roots.add(resolved)
        doc, digest = _read_json(resolved / "forge.json")
        if doc is None:
            continue
        if doc.get("forge_id") != spec.provider:
            continue
        cand.checkout = resolved
        cand.seen("checkout", f"forge.json at {resolved}", path=resolved, sha256=digest)
        if not cand.cli_path and isinstance(doc.get("cli"), str):
            cand.agentic_cli = doc["cli"]
        _load_checkout_manifests(cand, resolved)

    return _resolve(spec, cand, probe=probe, runner=runner)


def _probe_version(
    cand: _Candidate,
    cli: str,
    timeout: float,
    runner: Callable[..., Any] | None,
) -> tuple[bool, str | None]:
    """Run ``<cli> --version`` — argv only, scrubbed env, bounded, no shell."""
    from sparkforge_aws.delegation.execute import run_governed

    run = runner or run_governed
    result = run([cli, VERSION_PROBE], timeout_s=timeout)
    if not hasattr(result, "returncode") or result.returncode != 0:
        return False, None
    out = f"{result.stdout}\n{result.stderr}"
    match = _VERSION_OUT_RE.search(out)
    return True, match.group(0) if match else "ok"


def _probe_descriptors(
    cand: _Candidate,
    cli: str,
    argv_tail: tuple[str, ...],
    timeout: float,
    runner: Callable[..., Any] | None,
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Run the peer's capability-descriptors probe; (descriptors, error)."""
    from sparkforge_aws.delegation.execute import run_governed

    run = runner or run_governed
    result = run([cli, *argv_tail], timeout_s=timeout)
    if not hasattr(result, "returncode"):
        return None, f"descriptor probe refused: {result.detail}"
    if result.returncode != 0:
        return None, "descriptor probe non-zero exit"
    try:
        doc = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None, "descriptor probe output is not JSON"
    if not isinstance(doc, list):
        return None, "descriptor probe output is not a list"
    return doc, None


def _resolve(
    spec: PeerSpec,
    cand: _Candidate,
    *,
    probe: bool,
    runner: Callable[..., Any] | None,
) -> PeerDiscovery:
    """Verify a candidate through governed paths, then resolve its state."""
    checks: dict[str, str] = {"handshake": "SKIP", "manifest": "SKIP", "health": "SKIP"}
    notes: list[str] = []
    limitations: list[str] = []
    version = "unknown"
    declared_untrusted = False
    incompatible = False
    unavailable = False
    degraded = False
    verified = False

    if cand.dist_version:
        version = str(cand.dist_version)

    # -- package path: Requires-Python gate -----------------------------------
    if cand.dist_name is not None:
        satisfied = _requires_python_ok(cand.dist_requires_python)
        if satisfied is False:
            incompatible = True
            limitations.append(
                f"requires-python {cand.dist_requires_python!r} not satisfied by "
                f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
            )
        elif satisfied is None and cand.dist_requires_python:
            notes.append(
                f"requires-python {cand.dist_requires_python!r} unparsed (not enforced)"
            )
        # installed dist is a metadata-level handshake (no execution)
        if checks["handshake"] == "SKIP":
            checks["handshake"] = "PASS"
            notes.append(
                f"handshake: installed dist {cand.dist_name}=={cand.dist_version}"
            )

    # -- declared manifests ----------------------------------------------------
    if cand.capability_manifest is not None:
        checks["manifest"] = "PASS"
        declared = cand.capability_manifest.specialist
        if declared.version not in ("unknown", RUNTIME_DETECTED):
            if version == "unknown":
                version = declared.version
            elif declared.version.split(".", 1)[0] != version.split(".", 1)[0]:
                incompatible = True
                notes.append(
                    f"capability manifest version {declared.version} incompatible "
                    f"with installed {version}"
                )
    elif cand.manifest_error is None and cand.agentic_version:
        if checks["manifest"] == "SKIP":
            checks["manifest"] = "PASS"
        if version == "unknown":
            version = cand.agentic_version
    if cand.manifest_error is not None:
        declared_untrusted = True
        checks["manifest"] = "FAIL"
        notes.append(f"manifest rejected: {cand.manifest_error}")

    # -- live probes -----------------------------------------------------------
    cli = cand.cli_path
    ran_version_probe = False
    if probe and cli:
        ok, observed = _probe_version(cand, cli, PROBE_TIMEOUT_S, runner)
        if ok:
            checks["handshake"] = "PASS"
            ran_version_probe = True
            notes.append(f"version probe ok: {cli} {VERSION_PROBE}")
            if observed and observed != "ok" and version == "unknown":
                version = observed
        else:
            checks["handshake"] = "FAIL"
            degraded = True
            notes.append(f"version probe failed: {cli} {VERSION_PROBE}")
    elif probe and not cli:
        if cand.evidence:
            notes.append(f"cli {spec.cli!r} not resolvable for a version probe")

    if spec.capabilities_probe and probe and cli and checks["handshake"] == "PASS":
        descriptors, error = _probe_descriptors(
            cand, cli, spec.capabilities_probe, PROBE_TIMEOUT_S, runner
        )
        if descriptors is not None:
            checks["health"] = "PASS"
            notes.append(
                f"descriptor probe ok: {len(descriptors)} descriptor(s)"
            )
            manifest, merr = _descriptors_to_manifest(
                spec.provider, version, descriptors
            )
            if manifest is not None:
                if cand.capability_manifest is None:
                    cand.capability_manifest = manifest
                # drift note: declared catalog ids vs live surface ids
                live_ids = {c.id for c in manifest.capabilities}
                declared_ids = {c.id for c in spec.capabilities}
                missing = declared_ids - live_ids
                if missing:
                    limitations.append(
                        "declared capability ids absent from the live "
                        f"descriptor surface: {sorted(missing)}"
                    )
            elif merr:
                notes.append(f"descriptor manifest not adopted: {merr}")
        else:
            # The peer is alive (version probe passed) but its capability
            # surface did not answer — degraded, not a verdict of absence.
            checks["health"] = "FAIL"
            degraded = True
            notes.append(f"descriptor probe failed: {error}")
    elif checks["health"] == "SKIP" and ran_version_probe:
        # The same governed probe is the liveness evidence for a peer
        # without a descriptor surface (forge-doctor-data).
        checks["health"] = "PASS"
        notes.append("health: liveness via the version probe")

    if (
        probe
        and not degraded
        and not unavailable
        and checks["handshake"] == "PASS"
        and checks["manifest"] in ("PASS", "SKIP")
        and checks["health"] in ("PASS", "SKIP")
        and ran_version_probe
    ):
        # A live governed probe ran and every check passed; health SKIP
        # means no descriptor surface was declared — recorded, not hidden.
        verified = True
    if checks["handshake"] == "PASS" and not ran_version_probe and probe:
        limitations.append(
            "identity evidence is cached/metadata only — rerun with probe to verify"
        )
    if checks["manifest"] == "SKIP" and cand.evidence:
        limitations.append("no capability/agentic manifest found to parse")

    state = _final_state(
        declared_untrusted=declared_untrusted,
        incompatible=incompatible,
        verified=verified,
        unavailable=unavailable,
        degraded=degraded,
        has_evidence=bool(cand.evidence),
    )
    return PeerDiscovery(
        provider=spec.provider,
        state=state,  # type: ignore[arg-type]
        version=version,
        cli_resolved=cand.cli_path or spec.cli,
        sources=cand.evidence,
        capability_manifest=cand.capability_manifest,
        checks=checks,
        notes=notes,
        limitations=limitations,
    )


def discover_peers(
    specs: Sequence[PeerSpec],
    *,
    probe: bool = True,
    roots: Sequence[Path] = (),
    workspace_root: Path | None = None,
    dist_loader: Callable[[str], tuple[Any | None, dict[str, Any] | None]] | None = None,
    which: Callable[[str], str | None] | None = None,
    runner: Callable[..., Any] | None = None,
) -> PeerDiscoveryReport:
    """One discovery pass over every declared specialist."""
    entries = [
        discover_peer(
            spec,
            probe=probe,
            roots=roots,
            workspace_root=workspace_root,
            dist_loader=dist_loader,
            which=which,
            runner=runner,
        )
        for spec in specs
    ]
    return PeerDiscoveryReport(
        generated_at=utc_now(),
        probed=probe,
        entries=entries,
    )
