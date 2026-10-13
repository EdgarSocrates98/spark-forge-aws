"""Golden coverage for checkpoint, Kafka integration and OpenLineage fixtures."""

from pathlib import Path

from test_streaming_integrations import (
    test_goldens_cover_checkpoint_connect_streams_and_openlineage,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "streaming_integrations"

__all__ = ["test_goldens_cover_checkpoint_connect_streams_and_openlineage"]
