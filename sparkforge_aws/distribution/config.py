"""Bounded strict settings; explicit overrides never silently disappear."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


class PortableError(ValueError):
    """Named portable refusal safe to expose at the CLI boundary."""


class _Loader(yaml.SafeLoader):
    pass


def _mapping(loader, node, deep=False):
    result = {}
    for key, value in node.value:
        field = loader.construct_object(key, deep=deep)
        if not isinstance(field, str) or field in result:
            raise PortableError("SF-MANIFEST-INVALID: duplicate or non-string key")
        result[field] = loader.construct_object(value, deep=deep)
    return result


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def read_mapping(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise PortableError("SF-MANIFEST-INVALID: missing or symlink manifest")
    try:
        if path.stat().st_size > 128 * 1024:
            raise PortableError("SF-MANIFEST-INVALID: manifest too large")
        text = path.read_text(encoding="utf-8")
        depth = 0
        for event in yaml.parse(text):
            if isinstance(event, (yaml.events.MappingStartEvent, yaml.events.SequenceStartEvent)):
                depth += 1
                if depth > 20:
                    raise PortableError("SF-MANIFEST-INVALID: nesting limit")
            elif isinstance(event, (yaml.events.MappingEndEvent, yaml.events.SequenceEndEvent)):
                depth -= 1
        # Aliases (including recursive aliases) and merge keys are unsupported.
        if any(
            isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
            for token in yaml.scan(text)
        ):
            raise PortableError("SF-MANIFEST-INVALID: YAML aliases unsupported")
        data = yaml.load(text, Loader=_Loader)  # noqa: S506 - strict subclass of SafeLoader
    except (OSError, UnicodeError, yaml.YAMLError, RecursionError) as exc:
        raise PortableError("SF-MANIFEST-INVALID: unreadable YAML") from exc
    if not isinstance(data, dict):
        raise PortableError("SF-MANIFEST-INVALID: mapping required")
    _check_tree(data)
    return data


def _check_tree(value: Any, depth: int = 0) -> None:
    if depth > 20:
        raise PortableError("SF-MANIFEST-INVALID: nesting limit")
    if isinstance(value, dict):
        for key, item in value.items():
            if any(
                part in key.casefold()
                for part in ("secret", "password", "token", "credential", "api_key", "private_key")
            ):
                raise PortableError("SF-MANIFEST-SECRET: secret-like key forbidden")
            _check_tree(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check_tree(item, depth + 1)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise PortableError("SF-MANIFEST-INVALID: unsupported YAML value")


DEFAULT_CONFIG = {
    "scope": {"default": "repo"},
    "network": {"mode": "offline"},
    "host": {"activation": "plan_only"},
}


def _merge(base, extra):
    if not isinstance(extra, dict):
        raise PortableError("SF-CONFIG-INVALID: configuration mapping required")
    _check_tree(extra)
    result = copy.deepcopy(base)
    for key, value in extra.items():
        if key not in base or type(value) is not type(base[key]):
            raise PortableError("SF-CONFIG-INVALID: unknown setting or invalid type")
        result[key] = _merge(base[key], value) if isinstance(value, dict) else value
    return result


def resolve_config(paths, *, workspace_path=None, project_path=None, overrides=None):
    result = copy.deepcopy(DEFAULT_CONFIG)
    if paths is not None and paths.config_path:
        if not paths.config_path.is_file():
            raise PortableError("SF-CONFIG-MISSING: explicit config does not exist")
        result = _merge(result, read_mapping(paths.config_path))
    for path in (workspace_path, project_path):
        if path and Path(path).is_file():
            result = _merge(result, read_mapping(Path(path)).get("config", {}))
    if overrides:
        result = _merge(result, overrides)
    if (
        result["scope"]["default"] not in ("repo", "workspace", "target")
        or result["network"]["mode"] != "offline"
        or result["host"]["activation"] != "plan_only"
    ):
        raise PortableError("SF-CONFIG-INVALID: unsupported setting value")
    return result
