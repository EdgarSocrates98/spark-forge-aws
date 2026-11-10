from sparkforge_aws.context.obsidian import build_obsidian_diagnostic, to_obsidian_note_ref


def test_aws_projection_is_versioned_and_redacts_secrets():
    note = build_obsidian_diagnostic(
        title="Glue skew",
        summary="Partitions are uneven.",
        workspace="analytics",
        vault_id="team-vault",
        findings=[{"rule": "SF-SPARK-001", "access_token": "do-not-write"}],
        evidence=["job-123", "token=do-not-write-text"],
        runtime="glue-5.0",
        versions={"spark": "3.5"},
    )
    assert note["schema"] == "theforge/ObsidianNoteDraft/v1"
    ref = to_obsidian_note_ref(note)
    assert ref["schema"] == "theforge/ObsidianNoteRef/v1"
    assert "content" not in ref
    assert note["version"] == "v1"
    assert note["workspace"] == "analytics"
    assert note["vault_id"] == "team-vault"
    assert "do-not-write" not in note["content"]
    assert "[REDACTED]" in note["content"]
    assert len(note["content_hash"]) == 64


def test_aws_projection_redacts_secrets_in_title_and_summary():
    note = build_obsidian_diagnostic(
        title="Token=do-not-write",
        summary="password=do-not-write-summary",
        workspace="analytics",
        vault_id="team-vault",
    )
    assert "do-not-write" not in note["content"]
    assert "[REDACTED]" in note["content"]
