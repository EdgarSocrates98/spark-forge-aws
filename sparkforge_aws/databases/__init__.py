"""SparkForge Database Specializations Package."""
from __future__ import annotations

from sparkforge_aws.databases.dynamodb import DynamoDBHealthReport, DynamoDBSpecialist
from sparkforge_aws.databases.neptune import NeptuneQueryReport, NeptuneSpecialist

__all__ = [
    "DynamoDBSpecialist",
    "DynamoDBHealthReport",
    "NeptuneSpecialist",
    "NeptuneQueryReport",
]
