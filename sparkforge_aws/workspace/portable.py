"""Explicit virtual workspaces, bounded metadata discovery and portable roots.

Only the portable discriminator authorizes declared external repositories;
legacy manifests retain their containment policy. Discovery never reads Git
metadata, module content or source files, and never follows directory symlinks.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

import yaml

from sparkforge_aws.distribution.config import PortableError, read_mapping, resolve_config
from sparkforge_aws.durable import write_atomic
from sparkforge_aws.paths import DEFAULT_DENY_NAMES
from sparkforge_aws.workspace.manifest import Repository, WorkspaceManifest, _relationships


def manifest_path(root: Path | str, filename="workspace.yaml") -> Path:
    root = Path(root).expanduser().resolve()
    directory = root / ".sparkforge_aws"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise PortableError("SF-MANIFEST-INVALID: unsafe manifest directory")
    target = directory / filename
    if target.is_symlink():
        raise PortableError("SF-MANIFEST-INVALID: symlink manifest")
    return target


def _write(path, data):
    write_atomic(path, yaml.safe_dump(data, sort_keys=True))


def init_workspace(root: Path | str, *, name=None):
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise PortableError("SF-PATH-INVALID: root must exist")
    path = manifest_path(root)
    if path.exists():
        return workspace_status(root)
    label = name if name is not None else root.name
    if not isinstance(label, str) or not label.strip():
        raise PortableError("SF-MANIFEST-INVALID: workspace name required")
    _write(
        path,
        {
            "portable_version": 1,
            "workspace": label,
            "root": ".",
            "repositories": [],
            "relationships": {},
        },
    )
    return workspace_status(root)


def load_workspace(path: Path | str) -> WorkspaceManifest:
    path = Path(path)
    # Do not resolve before validating the control directory's symlink policy.
    root = path.parent.parent.resolve()
    if manifest_path(root) != path.absolute():
        raise PortableError("SF-MANIFEST-INVALID: noncanonical workspace path")
    raw = read_mapping(path)
    resolve_config(None, workspace_path=path)
    if set(raw) - {
        "portable_version",
        "workspace",
        "root",
        "repositories",
        "relationships",
        "config",
    }:
        raise PortableError("SF-MANIFEST-INVALID: unknown workspace field")
    if (
        type(raw.get("portable_version")) is not int
        or raw["portable_version"] != 1
        or raw.get("root") != "."
    ):
        raise PortableError("SF-MANIFEST-INVALID: unsupported portable workspace")
    if not isinstance(raw.get("workspace"), str) or not raw["workspace"].strip():
        raise PortableError("SF-MANIFEST-INVALID: workspace name required")
    entries = raw.get("repositories")
    if not isinstance(entries, list):
        raise PortableError("SF-MANIFEST-INVALID: repositories list required")
    repositories = []
    seen_names = set()
    seen_paths = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"name", "path", "external"}:
            raise PortableError("SF-MANIFEST-INVALID: repository fields required")
        name = entry["name"]
        relative = entry["path"]
        external = entry["external"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or name in seen_names
            or not isinstance(relative, str)
            or not relative
            or type(external) is not bool
        ):
            raise PortableError("SF-MANIFEST-INVALID: invalid repository declaration")
        candidate = root / relative
        # Intermediate symlinks are refused as well as the terminal component.
        if any(item.is_symlink() for item in (candidate, *candidate.parents)):
            raise PortableError("SF-MANIFEST-INVALID: symlink repository root")
        resolved = candidate.resolve()
        is_external = not resolved.is_relative_to(root)
        if is_external != external or resolved in seen_paths:
            raise PortableError(
                "SF-MANIFEST-INVALID: external authorization mismatch or duplicate root"
            )
        repositories.append(Repository(name, resolved, "", resolved.is_dir()))
        seen_names.add(name)
        seen_paths.add(resolved)
    try:
        relationships = _relationships(raw.get("relationships", {}), seen_names)
    except ValueError as exc:
        raise PortableError("SF-MANIFEST-INVALID: invalid relationships") from exc
    return WorkspaceManifest(raw["workspace"], root, tuple(repositories), relationships)


def add_repository(root: Path | str, repository: Path | str, *, name=None):
    root = Path(root).expanduser().resolve()
    path = manifest_path(root)
    workspace = load_workspace(path)
    candidate = Path(repository).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if any(item.is_symlink() for item in (candidate, *candidate.parents)):
        raise PortableError("SF-MANIFEST-INVALID: symlink repository root")
    candidate = candidate.resolve()
    if not candidate.is_dir():
        raise PortableError("SF-REPOSITORY-MISSING: add requires existing directory")
    label = name if name is not None else candidate.name
    if not isinstance(label, str) or not label.strip():
        raise PortableError("SF-MANIFEST-INVALID: repository name required")
    for item in workspace.repositories:
        if item.path == candidate:
            if item.name != label:
                raise PortableError(
                    "SF-REPOSITORY-COLLISION: root already declared under different name"
                )
            return workspace_status(root)
        if item.name == label:
            raise PortableError("SF-REPOSITORY-COLLISION: duplicate repository name")
    data = read_mapping(path)
    try:
        relative = os.path.relpath(candidate, root)
    except ValueError:
        # Windows separate volumes have no relative spelling. This is an
        # explicit external declaration, never implicit discovery authority.
        relative = str(candidate)
    data["repositories"].append(
        {
            "name": label,
            "path": Path(relative).as_posix(),
            "external": not candidate.is_relative_to(root),
        }
    )
    _write(path, data)
    return workspace_status(root)


def workspace_status(root: Path | str):
    workspace = load_workspace(manifest_path(root))
    unresolved = [
        {"code": "repository_missing", "repository": item.name}
        for item in workspace.repositories
        if not item.exists
    ]
    names = {item.name for item in workspace.repositories}
    unresolved += [
        {"code": "relationship_target_unresolved", "target": item.target}
        for item in workspace.relationships
        if item.target not in names
    ]
    return {
        "workspace": workspace.name,
        "root": str(workspace.root),
        "repositories": [
            {"name": item.name, "path": str(item.path), "exists": item.exists}
            for item in workspace.repositories
        ],
        "relationships": [asdict(item) for item in workspace.relationships],
        "unresolved": unresolved,
        "read_only": True,
    }


def discover(root: Path | str, *, max_depth=4, max_directories=2000):
    root = Path(root).expanduser().resolve()
    if not root.is_dir() or not 0 <= max_depth <= 12 or not 1 <= max_directories <= 10000:
        raise PortableError("SF-DISCOVERY-BOUNDS: existing root and valid bounds required")
    pending = [(root, 0)]
    repos = []
    modules = []
    unresolved = []
    visited = 0
    while pending and visited < max_directories:
        current, depth = pending.pop(0)
        visited += 1
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError:
            unresolved.append(
                {"code": "directory_unreadable", "path": current.relative_to(root).as_posix()}
            )
            continue
        names = {item.name: item for item in entries if not item.is_symlink()}
        relative = current.relative_to(root).as_posix()
        git = names.get(".git")
        project_dir = names.get(".sparkforge_aws")
        project = current / ".sparkforge_aws/project.yaml"
        if (
            git
            and (git.is_dir(follow_symlinks=False) or git.is_file(follow_symlinks=False))
            or project_dir
            and project.is_file()
            and not project.is_symlink()
        ):
            repos.append({"path": relative, "kind": "git" if git else "project"})
        if depth:
            for marker in ("pyproject.toml", "pom.xml", "package.json", "go.mod"):
                if marker in names and names[marker].is_file(follow_symlinks=False):
                    modules.append({"path": relative, "marker": marker})
                    break
        children = [
            Path(item.path)
            for item in entries
            if item.name not in DEFAULT_DENY_NAMES
            and not item.is_symlink()
            and item.is_dir(follow_symlinks=False)
        ]
        if depth < max_depth:
            pending.extend((item, depth + 1) for item in children)
        elif children:
            unresolved.append({"code": "discovery_depth_limit", "path": relative})
    if pending:
        unresolved.append({"code": "discovery_directory_limit", "remaining": len(pending)})
    return {
        "root": str(root),
        "repositories": repos,
        "modules": modules,
        "visited_directories": visited,
        "unresolved": unresolved,
        "read_only": True,
    }
