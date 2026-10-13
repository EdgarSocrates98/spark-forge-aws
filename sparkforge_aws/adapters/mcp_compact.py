"""Compact, provider-independent MCP projection over the full tool catalog."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from sparkforge_aws.adapters.mcp_envelope import validar_entrada
from sparkforge_aws.adapters.tools import TOOLS
from sparkforge_aws.context.gateway_capabilities import discover_capabilities, load_profiles
from sparkforge_aws.context.gateway_models import GatewayProfile
from sparkforge_aws.context.gateway_refs import ContextRefError, ContextRefStore
from sparkforge_aws.economy.cache import ArtifactCache

COMPACT_TOOL_NAMES = (
    "context_start",
    "context_expand",
    "execute_read",
    "execute_mutation",
    "search",
    "get",
    "next",
)
COMPACT_SCHEMA_VERSION = 1
_CURSOR_RE = re.compile(r"^cursor://v1/(?P<digest>[0-9a-f]{64})$")


class CompactRoutingError(ValueError):
    """Named refusal at the compact capability boundary."""


def _object_schema(
    properties: Mapping[str, Any],
    required: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }


_SEARCH_ITEM_SCHEMA = {
    "type": "object",
    "required": ["id", "kind", "name", "description", "score"],
    "properties": {
        "id": {"type": "string"},
        "kind": {"type": "string", "enum": ["tool"]},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "score": {"type": "integer"},
    },
}

_UNRESOLVED_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["code", "message"],
        "properties": {
            "code": {"type": "string"},
            "message": {"type": "string"},
            "unlock": {"type": "string"},
        },
    },
}

_SEARCH_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "status", "items", "next_cursor", "unresolved"],
    "properties": {
        "schema_version": {"type": "integer"},
        "status": {"type": "string", "enum": ["ok", "unresolved"]},
        "items": {"type": "array", "items": _SEARCH_ITEM_SCHEMA},
        "next_cursor": {"type": ["string", "null"]},
        "unresolved": _UNRESOLVED_SCHEMA,
    },
}

_GET_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "status", "item", "unresolved"],
    "properties": {
        "schema_version": {"type": "integer"},
        "status": {"type": "string", "enum": ["ok", "unresolved"]},
        "item": {"type": ["object", "null"]},
        "unresolved": _UNRESOLVED_SCHEMA,
    },
}

_EXECUTE_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "status", "capability", "result"],
    "properties": {
        "schema_version": {"type": "integer"},
        "status": {"type": "string", "enum": ["ok"]},
        "capability": {"type": "string"},
        "result": {"type": "object"},
    },
}


def _compact_spec(
    name: str,
    description: str,
    input_schema: Mapping[str, Any],
    output_schema: Mapping[str, Any],
    annotations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    spec = {
        "description": description,
        "inputSchema": deepcopy(dict(input_schema)),
        "outputSchema": deepcopy(dict(output_schema)),
    }
    if annotations is not None:
        spec["annotations"] = deepcopy(dict(annotations))
    return spec


def compact_catalog() -> dict[str, dict[str, Any]]:
    """Return the seven published compact operation definitions in stable order."""
    context_start = TOOLS["sparkforge_aws_context_start"]
    context_expand = TOOLS["sparkforge_aws_context_expand"]
    read_only = deepcopy(context_start.get("annotations", {}))
    execute_read_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
        "destructiveHint": False,
    }
    execute_mutation_annotations = {
        "readOnlyHint": False,
        "openWorldHint": True,
        "destructiveHint": True,
    }
    get_input_schema = _object_schema(
        {
            "id": {"type": "string", "minLength": 1},
            "ref": {"type": "string", "minLength": 1},
            "repo": {"type": "string"},
        },
        (),
    )
    get_input_schema["anyOf"] = [{"required": ["id"]}, {"required": ["ref"]}]
    catalog = {
        "context_start": _compact_spec(
            "context_start",
            "Discover capabilities and materialize selective context under the "
            "declared byte budget.",
            context_start["inputSchema"],
            context_start["outputSchema"],
            read_only,
        ),
        "context_expand": _compact_spec(
            "context_expand",
            "Expand one authorized ctx://v1 reference under the declared byte budget.",
            context_expand["inputSchema"],
            context_expand["outputSchema"],
            deepcopy(context_expand.get("annotations", read_only)),
        ),
        "execute_read": _compact_spec(
            "execute_read",
            "Execute one read-only discovered capability through the existing "
            "deterministic tool dispatcher.",
            _object_schema(
                {
                    "capability": {"type": "string", "minLength": 1},
                    "arguments": {"type": "object"},
                },
                ("capability", "arguments"),
            ),
            _EXECUTE_OUTPUT_SCHEMA,
            execute_read_annotations,
        ),
        "execute_mutation": _compact_spec(
            "execute_mutation",
            "Execute one state-changing discovered capability through the existing "
            "deterministic tool dispatcher.",
            _object_schema(
                {
                    "capability": {"type": "string", "minLength": 1},
                    "arguments": {"type": "object"},
                },
                ("capability", "arguments"),
            ),
            _EXECUTE_OUTPUT_SCHEMA,
            execute_mutation_annotations,
        ),
        "search": _compact_spec(
            "search",
            "Search executable tool capabilities by deterministic name and description terms.",
            _object_schema(
                {
                    "query": {"type": "string", "minLength": 1},
                    "profile": {
                        "type": "string",
                        "enum": ["economy", "balanced", "deep"],
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                    "cursor": {"type": "string"},
                },
                ("query",),
            ),
            _SEARCH_OUTPUT_SCHEMA,
            read_only,
        ),
        "get": _compact_spec(
            "get",
            "Retrieve one exact capability definition or one authorized context "
            "reference on demand.",
            get_input_schema,
            _GET_OUTPUT_SCHEMA,
            read_only,
        ),
        "next": _compact_spec(
            "next",
            "Retrieve the next page represented by an opaque content-addressed cursor.",
            _object_schema({"cursor": {"type": "string", "minLength": 1}}, ("cursor",)),
            _SEARCH_OUTPUT_SCHEMA,
            read_only,
        ),
    }
    return {name: catalog[name] for name in COMPACT_TOOL_NAMES}


def _refusal(message: str, code: str = "COMPACT_REFUSED") -> dict[str, Any]:
    return {"error": message, "exit_code": 2, "error_code": code}


class CompactRouter:
    """Routes compact operations without duplicating full tool handlers."""

    def __init__(
        self,
        catalog: Mapping[str, Mapping[str, Any]],
        execute_full: Callable[[str, dict[str, Any]], Any],
        *,
        cache: ArtifactCache | None = None,
        authorized_root: Path | None = None,
    ) -> None:
        self.catalog = catalog
        self.execute_full = execute_full
        self.cache = cache or ArtifactCache()
        self.profiles = load_profiles()
        self.authorized_root = authorized_root
        self.refs = ContextRefStore(cache=self.cache, authorized_root=authorized_root)

    def call(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        handlers: dict[str, Callable[[Mapping[str, Any]], dict[str, Any]]] = {
            "context_start": self._context_start,
            "context_expand": self._context_expand,
            "execute_read": self._execute_read,
            "execute_mutation": self._execute_mutation,
            "search": self._search,
            "get": self._get,
            "next": self._next,
        }
        handler = handlers.get(name)
        if handler is None:
            return _refusal(f"compact operation is not available: {name}", "UNKNOWN_OPERATION")
        try:
            return handler(dict(arguments))
        except CompactRoutingError as exc:
            return _refusal(str(exc), "COMPACT_REFUSED")
        except ContextRefError as exc:
            return _refusal(str(exc), "CONTEXT_REF_INVALID")

    def _context_start(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._existing_tool("sparkforge_aws_context_start", arguments)

    def _context_expand(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._existing_tool("sparkforge_aws_context_expand", arguments)

    def _existing_tool(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        result = self.execute_full(name, dict(arguments))
        if not isinstance(result, dict):
            raise CompactRoutingError(f"existing tool returned a non-object result: {name}")
        return result

    def _execute_read(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._execute(arguments, read_only=True)

    def _execute_mutation(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._execute(arguments, read_only=False)

    def _execute(
        self,
        arguments: Mapping[str, Any],
        *,
        read_only: bool,
    ) -> dict[str, Any]:
        capability = str(arguments["capability"])
        target = self.catalog.get(capability)
        if target is None:
            raise CompactRoutingError("capability is not available in the selected transport")
        annotations = target.get("annotations")
        target_is_read_only = (
            isinstance(annotations, Mapping) and annotations.get("readOnlyHint") is True
        )
        if target_is_read_only != read_only:
            mode = "read-only" if read_only else "mutation"
            raise CompactRoutingError(
                f"capability annotation does not permit {mode} execution: {capability}"
            )
        target_arguments = dict(arguments["arguments"])
        validation_error = validar_entrada(
            target_arguments,
            target["inputSchema"],
        )
        if validation_error is not None:
            raise CompactRoutingError(validation_error)
        result = self.execute_full(capability, target_arguments)
        if not isinstance(result, dict):
            raise CompactRoutingError(f"capability returned a non-object result: {capability}")
        if "error" in result and "exit_code" in result:
            return result
        return {
            "schema_version": COMPACT_SCHEMA_VERSION,
            "status": "ok",
            "capability": capability,
            "result": result,
        }

    def _search(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if arguments.get("cursor"):
            return self._page(str(arguments["cursor"]))
        query = str(arguments["query"])
        profile = GatewayProfile(str(arguments.get("profile", GatewayProfile.BALANCED.value)))
        limit = int(arguments.get("limit", self.profiles[profile].max_capabilities))
        candidates, _ = discover_capabilities(
            query,
            self.catalog,
            profile,
            self.profiles,
        )
        items = [
            {
                "id": item.name,
                "kind": item.kind,
                "name": item.name,
                "description": item.description,
                "score": item.score,
            }
            for item in candidates
        ]
        return self._page_payload(items, limit)

    def _get(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        reference = arguments.get("ref")
        if reference:
            value = self.refs.resolve(str(reference))
            return {
                "schema_version": COMPACT_SCHEMA_VERSION,
                "status": "ok",
                "item": value,
                "unresolved": [],
            }
        identifier = str(arguments.get("id", ""))
        spec = self.catalog.get(identifier)
        if spec is None:
            return {
                "schema_version": COMPACT_SCHEMA_VERSION,
                "status": "unresolved",
                "item": None,
                "unresolved": [
                    {
                        "code": "capability_not_found",
                        "message": f"capability not found: {identifier}",
                        "unlock": "search with a broader query",
                    }
                ],
            }
        return {
            "schema_version": COMPACT_SCHEMA_VERSION,
            "status": "ok",
            "item": {
                "id": identifier,
                "kind": "tool",
                "name": identifier,
                "description": str(spec.get("description", "")),
                "inputSchema": deepcopy(spec.get("inputSchema", {})),
                "outputSchema": deepcopy(spec.get("outputSchema", {})),
            },
            "unresolved": [],
        }

    def _next(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        return self._page(str(arguments["cursor"]))

    def _page(self, cursor: str) -> dict[str, Any]:
        match = _CURSOR_RE.fullmatch(cursor)
        if match is None:
            raise CompactRoutingError("invalid compact cursor")
        digest = match.group("digest")
        state = self.cache.get("compact_cursor", {"digest": digest})
        if not isinstance(state, Mapping):
            raise CompactRoutingError("compact cursor expired or not found")
        if _digest(state) != digest:
            raise CompactRoutingError("compact cursor integrity check failed")
        return self._page_payload(list(state.get("items", [])), int(state.get("limit", 1)))

    def _page_payload(self, items: list[dict[str, Any]], limit: int) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 50))
        page = items[:bounded_limit]
        remaining = items[bounded_limit:]
        cursor = None
        if remaining:
            state = {"items": remaining, "limit": bounded_limit}
            digest = _digest(state)
            self.cache.set("compact_cursor", {"digest": digest}, state)
            cursor = f"cursor://v1/{digest}"
        unresolved = []
        if not page:
            unresolved.append(
                {
                    "code": "search_no_match",
                    "message": "no executable capability matched the query",
                    "unlock": "provide a broader query",
                }
            )
        return {
            "schema_version": COMPACT_SCHEMA_VERSION,
            "status": "unresolved" if not page else "ok",
            "items": page,
            "next_cursor": cursor,
            "unresolved": unresolved,
        }


def _digest(value: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
