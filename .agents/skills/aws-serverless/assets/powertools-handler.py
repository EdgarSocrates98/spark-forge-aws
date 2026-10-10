"""Production-ready AWS Lambda handler skeleton — Powertools wired.

Reference asset for `skills/aws-serverless/references/lambda.md` and
`event-sources.md`. Demonstrates the wiring the docs describe: Logger +
Tracer + Metrics + Idempotency, with the event-source-agnostic handler
shape used across SQS/EventBridge/DynamoDB Streams examples.

Requires: aws-lambda-powertools (declared in the function's requirements,
not vendored here).
"""

from __future__ import annotations

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.batch import (
    BatchProcessor,
    EventType,
    process_partial_response,
)
from aws_lambda_powertools.utilities.data_classes import SQSEvent, event_source
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    idempotent_function,
)
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="example-service")
tracer = Tracer(service="example-service")
metrics = Metrics(namespace="ExampleService", service="example-service")

# Idempotency store — a DynamoDB table created alongside the function;
# the table name arrives via env var, never hardcoded.
persistence = DynamoDBPersistenceLayer(table_name="idempotency-store")
processor = BatchProcessor(event_type=EventType.SQS)


@tracer.capture_method
def _handle_record(record: dict) -> None:
    """Per-record work — raise to mark the record as failed for partial
    batch response (SQS) or let the error propagate (single events)."""
    event_id = record.get("messageId", "")
    idempotent_call(event_id=event_id, payload=record.get("body", ""))


@idempotent_function(
    data_keyword_argument="event_id",
    persistence_store=persistence,
)
def idempotent_call(event_id: str, payload: str) -> dict:
    """Side-effecting work guarded by the idempotency layer."""
    logger.info("processing", extra={"event_id": event_id})
    metrics.add_metric(name="RecordsProcessed", unit="Count", value=1)
    return {"event_id": event_id, "status": "processed"}


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """SQS partial-batch shape; swap the event class + processor for other
    sources (EventBridge → no batch; DynamoDB Streams → STREAMS type)."""
    return process_partial_response(
        event=event,
        record_handler=_handle_record,
        processor=processor,
        context=context,
    )
