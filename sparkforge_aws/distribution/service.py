"""Portable lifecycle facade: inspection is offline and never initializes state."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
from dataclasses import asdict
from pathlib import Path

from sparkforge_aws.distribution.config import PortableError, read_mapping, resolve_config
from sparkforge_aws.distribution.paths import project_identity, resolve_paths, resolve_project_root
from sparkforge_aws.workspace.portable import _write, load_workspace, manifest_path


def load_project(root):
    path = manifest_path(root, "project.yaml")
    raw = read_mapping(path)
    if (
        set(raw) - {"portable_version", "project_id", "root", "config"}
        or type(raw.get("portable_version")) is not int
        or raw["portable_version"] != 1
        or raw.get("root") != "."
    ):
        raise PortableError("SF-MANIFEST-INVALID: unsupported project manifest")
    from sparkforge_aws.distribution.paths import project_identity

    project_identity(Path(root))
    resolve_config(resolve_paths(root, env={}), project_path=path)
    return raw


def init_project(root):
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise PortableError("SF-PATH-INVALID: project root must exist")
    path = manifest_path(root, "project.yaml")
    if path.exists():
        return load_project(root)
    data = {"portable_version": 1, "project_id": project_identity(root), "root": "."}
    _write(path, data)
    return data


def _roots(root):
    root = Path(root).expanduser().resolve()
    project = None
    git = None
    workspace = None
    module = None
    # Bounded upward discovery; never follow gitdir or load sibling sources.
    for parent in (root, *list(root.parents)[:12]):
        if module is None and any(
            (parent / marker).is_file() and not (parent / marker).is_symlink()
            for marker in ("pyproject.toml", "pom.xml", "package.json", "go.mod")
        ):
            module = parent
        control = parent / ".sparkforge_aws"
        if control.is_symlink():
            raise PortableError("SF-MANIFEST-INVALID: symlink manifest directory")
        if project is None and git is None and (control / "project.yaml").exists():
            load_project(parent)
            project = parent
        if workspace is None and (control / "workspace.yaml").exists():
            load_workspace(control / "workspace.yaml")
            workspace = parent
        marker = parent / ".git"
        if git is None and marker.exists() and not marker.is_symlink():
            git = parent
    return {
        "project_root": resolve_project_root(root),
        "workspace_root": workspace,
        "git_root": git,
        "module_root": module,
    }


def _assets(package):
    checkout = package.parent
    choices = {
        "rules": package / "rules/catalog",
        "knowledge": package / "knowledge",
        "skills": package / "integrate/bundle/skills",
        "agents": package / "integrate/bundle/agents",
    }
    inventory = []
    unresolved = []
    for name, location in choices.items():
        if (
            not location.is_dir()
            and (checkout / "pyproject.toml").is_file()
            and (checkout / "sparkforge_aws").is_dir()
        ):
            location = checkout / ("rules/catalog" if name == "rules" else name)
        if not location.is_dir():
            unresolved.append({"code": "asset_unavailable", "asset": name})
            continue
        digest = hashlib.sha256()
        count = 0
        # Inventory packaged assets only, never consumer sources.
        for directory, subdirs, filenames in os.walk(location, followlinks=False):
            subdirs[:] = sorted(
                item for item in subdirs if not (Path(directory) / item).is_symlink()
            )
            for filename in sorted(filenames):
                item = Path(directory) / filename
                if item.is_symlink():
                    continue
                digest.update(item.relative_to(location).as_posix().encode())
                digest.update(item.read_bytes())
                count += 1
        inventory.append(
            {"name": name, "root": str(location), "files": count, "sha256": digest.hexdigest()}
        )
    return inventory, unresolved


def inspect_distribution(root):
    roots = _roots(root)
    paths = resolve_paths(roots["project_root"])
    project_path = manifest_path(roots["project_root"], "project.yaml")
    workspace_path = manifest_path(roots["workspace_root"]) if roots["workspace_root"] else None
    config = resolve_config(paths, workspace_path=workspace_path, project_path=project_path)
    assets, unresolved = _assets(paths.package_root)
    return {
        "paths": paths.to_dict(),
        "roots": {key: str(value) if value else None for key, value in roots.items()},
        "config": config,
        "assets": assets,
        "offline": True,
        "read_only": True,
        "unresolved": unresolved,
    }


def doctor(root):
    result = inspect_distribution(root)
    checks = []
    for name in ("state_root", "cache_root"):
        path = Path(result["paths"][name])
        ancestor = path
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        checks.append(
            {
                "name": name,
                "status": "available"
                if ancestor.is_dir() and os.access(ancestor, os.W_OK)
                else "unavailable",
                "evidence": "ancestor permission probe; no write performed",
            }
        )
    checks += [
        {
            "name": "git",
            "status": "available" if shutil.which("git") else "unavailable",
            "optional": True,
        },
        {
            "name": "mcp",
            "status": "available" if importlib.util.find_spec("mcp") else "unavailable",
            "optional": True,
        },
        {"name": "network", "status": "unresolved", "evidence": "offline; no network probe"},
        {
            "name": "hosts",
            "status": "unresolved",
            "evidence": "optional; use integrate preview before activation",
        },
    ]
    result["checks"] = checks
    result["status"] = (
        "blocked"
        if any(
            item["status"] == "unavailable" and not item.get("optional", False) for item in checks
        )
        else "degraded"
        if result["unresolved"]
        else "ready"
    )
    result["asset_integrity"] = (
        "inventory_only; wheel integrity checked by verify_wheel, no trusted signing claim"
    )
    return result


def status(root):
    result = inspect_distribution(root)
    project = Path(result["roots"]["project_root"]) / ".sparkforge_aws/project.yaml"
    result["initialized"] = project.is_file()
    if project.is_file():
        result["project"] = load_project(project.parent.parent)
    return result


def resolve_context(root, *, scope=None, target=None, impact="all"):
    if scope not in (None, "repo", "workspace", "target") or impact not in (
        "direct",
        "transitive",
        "all",
    ):
        raise PortableError("SF-CONTEXT-INVALID: invalid scope or impact")
    inspected = inspect_distribution(root)
    roots = inspected["roots"]
    scope = scope or inspected["config"]["scope"]["default"]
    workspace = (
        load_workspace(manifest_path(roots["workspace_root"])) if roots["workspace_root"] else None
    )
    unresolved = list(inspected["unresolved"])
    targets = []
    if scope in ("workspace", "target") and workspace is None:
        raise PortableError("SF-CONTEXT-WORKSPACE-MISSING: explicit workspace required")
    names = {item.name for item in workspace.repositories} if workspace else set()
    edges = [asdict(item) for item in workspace.relationships] if workspace else []
    if scope == "repo":
        included = (
            [
                item.name
                for item in workspace.repositories
                if Path(root).resolve().is_relative_to(item.path)
            ]
            if workspace
            else []
        )
        if not included:
            included = [Path(roots["project_root"]).name]
    elif scope == "workspace":
        included = sorted(names)
        if impact != "all":
            if target is None:
                matches = [
                    item.name
                    for item in workspace.repositories
                    if Path(root).resolve().is_relative_to(item.path)
                ]
                if len(matches) != 1:
                    raise PortableError(
                        "SF-CONTEXT-TARGET-REQUIRED: workspace impact needs a target "
                        "or a current repository"
                    )
                target = "repository:" + matches[0]
            narrowed = resolve_context(root, scope="target", target=target, impact=impact)
            included = narrowed["included_repositories"]
            targets = narrowed["targets"]
    else:
        if (
            not isinstance(target, str)
            or not target.startswith("repository:")
            or target[11:] not in names
        ):
            raise PortableError("SF-CONTEXT-TARGET-NOT-FOUND: target must name declared repository")
        seed = target[11:]
        targets = [target]
        selected = {seed}
        if impact == "all":
            selected = set(names)
        else:
            frontier = {seed}
            for _ in range(1 if impact == "direct" else len(names)):
                neighbors = {
                    edge["target"]
                    for edge in edges
                    if edge["source"] in frontier and edge["target"] in names
                }
                frontier = neighbors - selected
                selected.update(neighbors)
                if not frontier:
                    break
        included = sorted(selected)
    if workspace:
        unresolved.append(
            {
                "code": "repository_content_not_fingerprinted",
                "evidence": "locality resolution reads metadata only; graph build scans explicitly",
            }
        )
        unresolved += [
            {"code": "repository_missing", "repository": item.name}
            for item in workspace.repositories
            if not item.exists
        ]
        unresolved += [
            {"code": "relationship_target_unresolved", "target": edge["target"]}
            for edge in edges
            if edge["target"] not in names
        ]
        if not edges:
            unresolved.append(
                {"code": "relationships_unresolved", "evidence": "no declared dependency edges"}
            )
    return {
        "scope": scope,
        "impact": impact,
        "targets": targets,
        "included_repositories": included,
        "roots": roots,
        "graph": {"edges": edges},
        "funnel": {"selection": "declared repository locality; no source inference"},
        "evidence": ["validated portable manifests", "bounded root metadata"],
        "gaps": [],
        "unresolved": unresolved,
        "read_only": True,
    }
