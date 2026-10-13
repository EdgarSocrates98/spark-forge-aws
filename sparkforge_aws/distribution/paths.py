"""Portable path resolver used by operational persistence, without writes."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from sparkforge_aws.distribution.config import PortableError, read_mapping


def project_identity(root: Path) -> str:
    manifest = root / ".sparkforge_aws/project.yaml"
    if manifest.parent.is_symlink():
        raise PortableError("SF-MANIFEST-INVALID: symlink manifest directory")
    if manifest.exists():
        data = read_mapping(manifest)
        identity = data.get("project_id")
        if not isinstance(identity, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", identity):
            raise PortableError("SF-MANIFEST-INVALID: invalid project_id")
        return identity
    return hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:24]


def resolve_project_root(root: Path | str) -> Path:
    """Nearest declared project or Git boundary, bounded and metadata-only."""
    base = Path(root).expanduser().resolve()
    for current in (base, *list(base.parents)[:12]):
        control = current / ".sparkforge_aws"
        if control.is_symlink():
            raise PortableError("SF-MANIFEST-INVALID: symlink manifest directory")
        if (control / "project.yaml").exists():
            project_identity(current)
            return current
        git = current / ".git"
        if git.exists() and not git.is_symlink():
            return current
    return base


def _override(name: str, base: Path, env) -> Path | None:
    if name not in env:
        return None
    raw = env[name].strip()
    if not raw:
        raise PortableError(f"SF-PATH-INVALID: empty {name}")
    target = Path(raw).expanduser()
    return (base / target).resolve() if not target.is_absolute() else target.resolve()


@dataclass(frozen=True)
class ForgePaths:
    package_root: Path
    executable: Path
    project_root: Path
    state_root: Path
    cache_root: Path
    config_path: Path | None
    sources: dict[str, str]

    def to_dict(self):
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in asdict(self).items()
        }


def resolve_paths(root: Path | str, *, env=None) -> ForgePaths:
    base = resolve_project_root(root)
    values = os.environ if env is None else env
    home = _override("SPARKFORGE_AWS_HOME", base, values)
    cache = _override("SPARKFORGE_AWS_CACHE", base, values)
    config = _override("SPARKFORGE_AWS_CONFIG", base, values)
    identity = project_identity(base) if home or cache else ""
    state = home / "projects" / identity if home else base / ".sparkforge_aws"
    cache_root = cache / "projects" / identity if cache else state / "cache"
    package = Path(__file__).resolve().parents[1]
    if (
        package == state
        or package in state.parents
        or package == cache_root
        or package in cache_root.parents
    ):
        raise PortableError("SF-PATH-INVALID: mutable paths overlap package")
    return ForgePaths(
        package,
        Path(sys.executable).resolve(),
        base,
        state,
        cache_root,
        config,
        {
            "state_root": "environment" if home else "default",
            "cache_root": "environment" if cache else "default",
            "config_path": "environment" if config else "default",
        },
    )
