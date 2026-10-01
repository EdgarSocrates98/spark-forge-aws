"""SparkForge Database Specializations Package."""
from __future__ import annotations

from sparkforge.databases.dynamodb import DynamoDBHealthReport, DynamoDBSpecialist
from sparkforge.databases.neptune import NeptuneQueryReport, NeptuneSpecialist

__all__ = [
    "DynamoDBSpecialist",
    "DynamoDBHealthReport",
    "NeptuneSpecialist",
    "NeptuneQueryReport",
]
