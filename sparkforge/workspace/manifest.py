"""Secure loader for explicitly declared multi-repository workspaces."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.paths import resolve_within, scan_repository


class WorkspaceManifestError(ValueError):
    """Invalid or unsafe workspace declaration."""


@dataclass(frozen=True, slots=True)
class Repository:
    name: str
    path: Path
    fingerprint: str
    exists: bool


@dataclass(frozen=True, slots=True)
class Relationship:
    source: str
    relation: str
    target: str


@dataclass(frozen=True, slots=True)
class GraphLink:
    """Explicit bridge between graph fragments from different authorities."""

    source: str
    relation: str
    target: str


@dataclass(frozen=True, slots=True)
class CloudResource:
    """A cloud dataset explicitly allowed for live graph collection."""

    id: str
    kind: str
    services: tuple[str, ...]
    account_id: str = ""
    catalog_id: str = ""
    region: str = ""
    database: str = ""
    table: str = ""
    resource_arn: str = ""
    bucket: str = ""
    prefix: str = ""
    role_arn: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceManifest:
    name: str
    root: Path
    repositories: tuple[Repository, ...]
    relationships: tuple[Relationship, ...]
    schema_version: int = 1
    cloud_resources: tuple[CloudResource, ...] = ()
    federated_links: tuple[GraphLink, ...] = ()

    def repository(self, name: str) -> Repository | None:
        return next((item for item in self.repositories if item.name == name), None)


def load_manifest(path: str | Path) -> WorkspaceManifest:
    """Load and validate a manifest without discovering undeclared repos."""

    manifest_path = Path(path).expanduser().resolve()
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise WorkspaceManifestError(f"manifest unreadable: {manifest_path}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version", 1) != 1:
        raise WorkspaceManifestError("schema_version must be 1")
    name = raw.get("workspace")
    if not isinstance(name, str) or not name.strip():
        raise WorkspaceManifestError("workspace must be a non-empty string")
    root = manifest_path.parent.resolve()
    entries = raw.get("repositories")
    if not isinstance(entries, list) or not entries:
        raise WorkspaceManifestError("repositories must be a non-empty list")
    repositories: list[Repository] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkspaceManifestError("repository entry must be an object")
        repo_name = entry.get("name", entry.get("id"))
        repo_path = entry.get("path")
        if not isinstance(repo_name, str) or not repo_name or repo_name in seen:
            raise WorkspaceManifestError(f"duplicate or invalid repository: {repo_name!r}")
        if not isinstance(repo_path, str) or not repo_path:
            raise WorkspaceManifestError(f"repository path missing: {repo_name}")
        candidate = root / repo_path
        if candidate.is_symlink():
            raise WorkspaceManifestError(f"repository path symlink not allowed: {repo_name}")
        resolved = resolve_within(root, candidate)
        if resolved is None:
            raise WorkspaceManifestError(f"repository escapes workspace root: {repo_name}")
        exists = resolved.is_dir()
        repositories.append(
            Repository(repo_name, resolved, fingerprint(resolved) if exists else "", exists)
        )
        seen.add(repo_name)

    relationships = _relationships(raw.get("relationships", {}), seen)
    cloud_resources = _cloud_resources(raw.get("cloud_resources", []))
    federated_links = _federated_links(raw.get("federated_links", []))
    return WorkspaceManifest(
        name.strip(),
        root,
        tuple(repositories),
        relationships,
        1,
        cloud_resources,
        federated_links,
    )


def _relationships(raw: Any, names: set[str]) -> tuple[Relationship, ...]:
    result: list[Relationship] = []
    if not isinstance(raw, dict):
        raise WorkspaceManifestError("relationships must be an object")
    for source, declarations in raw.items():
        if source not in names:
            raise WorkspaceManifestError(f"relationship source is undeclared: {source}")
        if not isinstance(declarations, dict):
            raise WorkspaceManifestError(f"relationships[{source}] must be an object")
        for relation, targets in declarations.items():
            values = [targets] if isinstance(targets, str) else targets
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                raise WorkspaceManifestError(f"relationship targets must be strings: {source}")
            for target in values:
                if target not in names:
                    result.append(Relationship(source, str(relation), target))
                else:
                    result.append(Relationship(source, str(relation), target))
    return tuple(sorted(result, key=lambda item: (item.source, item.relation, item.target)))


def _cloud_resources(raw: Any) -> tuple[CloudResource, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise WorkspaceManifestError("cloud_resources must be a list")
    result: list[CloudResource] = []
    seen: set[str] = set()
    allowed_services = {"glue", "lakeformation", "s3"}
    string_fields = (
        "account_id",
        "catalog_id",
        "region",
        "database",
        "table",
        "resource_arn",
        "bucket",
        "prefix",
        "role_arn",
    )
    for entry in raw:
        if not isinstance(entry, dict):
            raise WorkspaceManifestError("cloud resource entry must be an object")
        resource_id = entry.get("id", entry.get("name"))
        resource_key = resource_id.strip() if isinstance(resource_id, str) else ""
        if not resource_key or resource_key in seen:
            raise WorkspaceManifestError(f"duplicate or invalid cloud resource: {resource_id!r}")
        if entry.get("kind") != "dataset":
            raise WorkspaceManifestError(f"cloud resource kind must be dataset: {resource_id}")
        services = entry.get("services")
        if (
            not isinstance(services, list)
            or not services
            or not all(
                isinstance(service, str) and service in allowed_services for service in services
            )
            or len(set(services)) != len(services)
        ):
            raise WorkspaceManifestError(f"cloud resource services invalid: {resource_id}")
        values: dict[str, str] = {}
        for field in string_fields:
            value = entry.get(field, "")
            if not isinstance(value, str):
                raise WorkspaceManifestError(
                    f"cloud resource {field} must be a string: {resource_id}"
                )
            values[field] = value.strip()
        if ".." in resource_key or any(".." in value for value in values.values()):
            raise WorkspaceManifestError(
                f"cloud resource contains path traversal marker: {resource_key}"
            )
        result.append(CloudResource(resource_key, "dataset", tuple(services), **values))
        seen.add(resource_key)
    return tuple(sorted(result, key=lambda item: item.id))


def _federated_links(raw: Any) -> tuple[GraphLink, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise WorkspaceManifestError("federated_links must be a list")
    result: list[GraphLink] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise WorkspaceManifestError("federated link entry must be an object")
        values = tuple(entry.get(field, "") for field in ("source", "relation", "target"))
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise WorkspaceManifestError("federated link source, relation and target are required")
        source, relation, target = (value.strip() for value in values)
        link = (source, relation, target)
        if link in seen:
            raise WorkspaceManifestError(f"duplicate federated link: {link!r}")
        if any(".." in value for value in link):
            raise WorkspaceManifestError("federated link contains path traversal marker")
        result.append(GraphLink(*link))
        seen.add(link)
    return tuple(sorted(result, key=lambda item: (item.source, item.relation, item.target)))


def fingerprint(path: Path) -> str:
    """Hash declared source contents and relative names; no code is executed."""

    base = Path(path).expanduser().resolve()
    digest = hashlib.sha256()
    if not base.is_dir():
        return ""
    report = scan_repository(base)
    digest.update(f"policy:{report.policy_version}\n".encode())
    for skipped in report.skipped:
        digest.update(f"skip:{skipped['path']}:{skipped['reason']}\n".encode())
    for item in report.files:
        relative = item.relative_to(base).as_posix()
        digest.update(relative.encode("utf-8"))
        try:
            digest.update(item.read_bytes())
        except OSError as exc:
            raise WorkspaceManifestError(f"repository file unreadable: {relative}") from exc
    return digest.hexdigest()


def _repository_files(root: Path) -> tuple[Path, ...]:
    return scan_repository(root).files


__all__ = [
    "CloudResource",
    "GraphLink",
    "Repository",
    "Relationship",
    "WorkspaceManifest",
    "WorkspaceManifestError",
    "fingerprint",
    "load_manifest",
]
