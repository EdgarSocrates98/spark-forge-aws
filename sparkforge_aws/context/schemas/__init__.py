"""Package resources for Context Gateway schemas."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any


def load_gateway_schema() -> dict[str, Any]:
    resource = files("sparkforge_aws.context.schemas").joinpath("gateway.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


__all__ = ["load_gateway_schema"]
