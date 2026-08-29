"""Tests for Database and Streaming Specialists."""

from sparkforge.databases.dynamodb import DynamoDBSpecialist
from sparkforge.databases.neptune import NeptuneSpecialist
from sparkforge.streaming.kafka import KafkaMSKSpecialist
from sparkforge.streaming.kinesis import KinesisSpecialist


def test_dynamodb_hot_partition():
    specialist = DynamoDBSpecialist()
    cfg = {
        "TableName": "transactions",
        "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}],
        "ProvisionedThroughput": {"WriteCapacityUnits": 100},
        "GlobalSecondaryIndexes": [
            {"IndexName": "gsi_user", "ProvisionedThroughput": {"WriteCapacityUnits": 10}}
        ],
    }
    rep = specialist.analyze_table_config(cfg)
    assert rep.has_hot_partition_risk is True
    assert rep.has_gsi_throttling_risk is True
    assert len(rep.recommendations) >= 2


def test_neptune_full_scan():
    specialist = NeptuneSpecialist()
    rep = specialist.analyze_query_text("MATCH (n) RETURN n")
    assert rep.has_full_graph_scan is True
    assert rep.estimated_cost_class == "high"


def test_kafka_msk_consumer_lag():
    specialist = KafkaMSKSpecialist()
    lags = {0: 100, 1: 200, 2: 80000}
    rep = specialist.diagnose_consumer_lag(
        "events.clickstream", "analytics-group", lags, under_replicated_count=1
    )
    assert rep.has_high_lag is True
    assert rep.has_partition_imbalance is True
    assert rep.under_replicated_partitions == 1


def test_kinesis_hot_shard():
    specialist = KinesisSpecialist()
    tput = {"shardId-0000": 0.2, "shardId-0001": 0.95}
    rep = specialist.diagnose_stream("telemetry-stream", 2, tput, consumer_count=4)
    assert rep.has_hot_shards is True
    assert rep.is_enhanced_fanout_recommended is True
