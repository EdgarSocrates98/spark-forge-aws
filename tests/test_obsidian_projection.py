from sparkforge_aws.context.obsidian import build_obsidian_diagnostic


def test_aws_projection_is_versioned_and_redacts_secrets():
    note = build_obsidian_diagnostic(
        title="Glue skew",
        summary="Partitions are uneven.",
        workspace="analytics",
        vault_id="team-vault",
        findings=[{"rule": "SF-SPARK-001", "access_token": "do-not-write"}],
        evidence=["job-123"],
        runtime="glue-5.0",
        versions={"spark": "3.5"},
    )
    assert note["schema"] == "theforge/ObsidianNoteRef/v1"
    assert note["version"] == "v1"
    assert note["workspace"] == "analytics"
    assert note["vault_id"] == "team-vault"
    assert "do-not-write" not in note["content"]
    assert "[REDACTED]" in note["content"]
    assert len(note["content_hash"]) == 64
