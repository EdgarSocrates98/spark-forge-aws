from sparkforge.lakeformation.capabilities import capability, load_matrix


def test_capability_matrix_is_source_backed():
    matrix = load_matrix()
    assert {"glue", "emr_ec2", "emr_serverless"} <= set(matrix["engines"])
    for row in matrix["capabilities"]:
        assert row["status"] in {
            "supported",
            "limited",
            "read_only",
            "version_dependent",
            "not_supported",
            "unknown",
        }
        if row["status"] != "unknown":
            assert row["source"] and row["last_verified"] and row["limitations"]
    assert capability("glue", "5.1", "fgac", "iceberg", "merge")["status"] in {
        "supported",
        "limited",
        "version_dependent",
    }
    assert capability("emr_ec2", "7.8.0", "fta", "iceberg", "read")["status"] == "supported"
