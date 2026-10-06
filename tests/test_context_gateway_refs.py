from __future__ import annotations

import pytest

from sparkforge_aws.adapters.tools import TOOLS
from sparkforge_aws.context.gateway import ContextGateway
from sparkforge_aws.context.gateway_models import GatewayProfile, GatewayRequest
from sparkforge_aws.context.gateway_refs import ContextRefError, ContextRefStore
from sparkforge_aws.economy.cache import ArtifactCache


def test_context_ref_round_trip_and_integrity(tmp_path) -> None:
    store = ContextRefStore(ArtifactCache(tmp_path / "cache"), authorized_root=tmp_path)
    ref = store.put("knowledge", {"content": "FGAC", "source_path": "docs/fgac.md"})

    resolved = store.resolve(ref.uri)

    assert resolved["payload"]["content"] == "FGAC"
    assert ref.uri.startswith("ctx://v1/knowledge/")


def test_context_ref_rejects_arbitrary_path_and_tampering(tmp_path) -> None:
    store = ContextRefStore(ArtifactCache(tmp_path / "cache"), authorized_root=tmp_path)
    ref = store.put("code", {"source_path": "../secret.py", "content": "private"})

    with pytest.raises(ContextRefError, match="outside authorized scope"):
        store.resolve(ref.uri)

    with pytest.raises(ContextRefError, match="invalid context ref"):
        store.resolve("C:/secret.py")


def test_context_ref_missing_is_named(tmp_path) -> None:
    store = ContextRefStore(ArtifactCache(tmp_path / "cache"))

    with pytest.raises(ContextRefError, match="not found"):
        store.resolve("ctx://v1/fact/" + "0" * 64)


def test_gateway_expand_resolves_ref_across_gateway_instances(tmp_path) -> None:
    cache = ArtifactCache(tmp_path / "cache")
    gateway = ContextGateway(TOOLS, cache=cache, authorized_root=tmp_path)
    started = gateway.start(
        GatewayRequest(
            "Iceberg knowledge",
            GatewayProfile.ECONOMY,
            5000,
            items=({"kind": "knowledge", "content": "Iceberg guidance " * 100},),
        )
    )

    expanded = ContextGateway(TOOLS, cache=cache, authorized_root=tmp_path).expand(
        started["refs"][0]["uri"], max_bytes=5000
    )

    assert expanded["phase"] == "expanded"
    assert expanded["context"][0]["payload"]["content"].startswith("Iceberg guidance")
