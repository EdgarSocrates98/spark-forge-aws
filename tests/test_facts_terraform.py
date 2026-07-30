import textwrap

from sparkforge.facts.terraform import (
    EMITTED_KINDS,
    EXTRACTOR_ID,
    extract_terraform,
    extract_terraform_path,
    extract_terraform_tree,
)
from sparkforge.findings.validate import validate_fact

EXPECTED_KINDS = {
    "tf.attribute",
    "tf.resource",
    "tf.unresolved",
    "tf.module_analyzed",
    "tf.observability.spark_ui",
}


def facts_of(kind, facts):
    return [f for f in facts if f.kind == kind]


def one(kind, source, path="main.tf"):
    got = facts_of(kind, extract_terraform(source, path))
    assert got, f"nenhum fact {kind}"
    return got[0]


def attrs_of(kind, key, source, path="main.tf"):
    """Primeiro tf.attribute (ou tf.unresolved) cujo attrs.key == key."""
    for fact in facts_of(kind, extract_terraform(source, path)):
        if fact.attrs.get("key") == key:
            return fact
    raise AssertionError(f"nenhum fact {kind} com key={key!r}")


_BASE_JOB = """
resource "aws_glue_job" "etl" {{
  name              = "etl-job"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 4
  max_retries       = 0
  timeout           = 120

  command {{
    name            = "glueetl"
    script_location = "s3://bucket/scripts/etl.py"
    python_version  = "3"
  }}

  default_arguments = {{
{args}
  }}
}}
"""


def job_with_args(*lines: str) -> str:
    body = "\n".join(f"    {line}" for line in lines)
    return _BASE_JOB.format(args=body)


def test_kind_namespace_is_complete_and_documented():
    assert EMITTED_KINDS == EXPECTED_KINDS
    assert len(EMITTED_KINDS) == 5
    assert EXTRACTOR_ID.startswith("terraform@")


class TestRootAttributes:
    def test_numeric_literal_has_measure(self):
        fact = attrs_of("tf.attribute", "number_of_workers", job_with_args())
        assert fact.attrs["value"] == "4"
        assert fact.attrs["literal"] is True
        assert fact.attrs["block"] == "root"
        assert fact.measures["value"] == 4

    def test_string_literal_has_no_measure(self):
        fact = attrs_of("tf.attribute", "worker_type", job_with_args())
        assert fact.attrs["value"] == "G.1X"
        assert fact.attrs["literal"] is True
        assert fact.measures == {}

    def test_reference_is_recorded_as_non_literal(self):
        fact = attrs_of("tf.attribute", "role_arn", job_with_args())
        assert fact.attrs["value"] == "aws_iam_role.glue_role.arn"
        assert fact.attrs["literal"] is False
        assert fact.attrs["present"] is True
        assert fact.measures == {}

    def test_out_of_scope_root_key_is_silently_skipped(self):
        src = _BASE_JOB.format(args="").replace(
            'name              = "etl-job"',
            'name              = "etl-job"\n  description       = "not modeled"',
        )
        facts = extract_terraform(src, "main.tf")
        assert not any(f.attrs.get("key") == "description" for f in facts)


class TestCommandAndExecutionProperty:
    def test_command_block_attributes(self):
        facts = extract_terraform(job_with_args(), "main.tf")
        command_facts = {
            f.attrs["key"]: f.attrs["value"]
            for f in facts_of("tf.attribute", facts)
            if f.attrs.get("block") == "command"
        }
        assert command_facts == {
            "name": "glueetl",
            "script_location": "s3://bucket/scripts/etl.py",
            "python_version": "3",
        }

    def test_execution_property_max_concurrent_runs_is_numeric(self):
        src = _BASE_JOB.format(args="").replace(
            "}\n",
            "}\n\n  execution_property {\n    max_concurrent_runs = 3\n  }\n",
            1,
        )
        fact = attrs_of("tf.attribute", "max_concurrent_runs", src)
        assert fact.attrs["block"] == "execution_property"
        assert fact.measures["value"] == 3


class TestResourceAndSentinel:
    def test_resource_fact_counts_attributes(self):
        facts = extract_terraform(job_with_args('"--TempDir" = "s3://bucket/tmp/"'), "main.tf")
        resource = one("tf.resource", job_with_args('"--TempDir" = "s3://bucket/tmp/"'))
        assert resource.attrs == {"resource_type": "aws_glue_job", "resource_name": "etl"}
        n_attrs = len(facts_of("tf.attribute", facts))
        assert resource.measures["attribute_count"] == n_attrs

    def test_module_analyzed_counts_are_consistent(self):
        src = job_with_args('"--TempDir" = "s3://bucket/tmp/"')
        facts = extract_terraform(src, "main.tf")
        sentinel = one("tf.module_analyzed", src)
        assert sentinel.measures["resource_count"] == 1
        assert sentinel.measures["attribute_count"] == len(facts_of("tf.attribute", facts))
        assert sentinel.measures["unresolved_count"] == len(facts_of("tf.unresolved", facts))

    def test_no_resources_still_emits_sentinel(self):
        facts = extract_terraform('resource "aws_iam_role" "x" {\n  name = "x"\n}\n', "main.tf")
        assert facts_of("tf.resource", facts) == []
        sentinel = facts_of("tf.module_analyzed", facts)
        assert len(sentinel) == 1
        assert sentinel[0].measures["resource_count"] == 0

    def test_multiple_glue_job_resources_in_one_file(self):
        src = job_with_args() + "\n" + job_with_args().replace('"etl"', '"etl_two"')
        facts = extract_terraform(src, "main.tf")
        resources = facts_of("tf.resource", facts)
        assert {r.attrs["resource_name"] for r in resources} == {"etl", "etl_two"}


class TestObservabilitySentinel:
    def test_both_present_and_literal_emits_fact(self):
        src = job_with_args(
            '"--enable-spark-ui" = "true"',
            '"--spark-event-logs-path" = "s3://bucket/logs/"',
        )
        assert facts_of("tf.observability.spark_ui", extract_terraform(src, "main.tf"))

    def test_only_enable_flag_does_not_emit_fact(self):
        src = job_with_args('"--enable-spark-ui" = "true"')
        assert not facts_of("tf.observability.spark_ui", extract_terraform(src, "main.tf"))

    def test_only_path_does_not_emit_fact(self):
        src = job_with_args('"--spark-event-logs-path" = "s3://bucket/logs/"')
        assert not facts_of("tf.observability.spark_ui", extract_terraform(src, "main.tf"))

    def test_enable_flag_false_does_not_emit_fact(self):
        src = job_with_args(
            '"--enable-spark-ui" = "false"',
            '"--spark-event-logs-path" = "s3://bucket/logs/"',
        )
        assert not facts_of("tf.observability.spark_ui", extract_terraform(src, "main.tf"))

    def test_no_default_arguments_at_all_does_not_emit_fact(self):
        facts = extract_terraform(job_with_args(), "main.tf")
        assert not facts_of("tf.observability.spark_ui", facts)


class TestSecretDetection:
    def test_akia_pattern_is_flagged_and_redacted(self):
        # Access key id de exemplo documentado pela AWS -- nunca uma credencial real.
        src = job_with_args('"--aws-access-key-id" = "AKIAIOSFODNN7EXAMPLE"')
        fact = attrs_of("tf.attribute", "--aws-access-key-id", src)
        assert fact.attrs["secret_pattern_match"] is True
        assert fact.attrs["redacted"] is True
        assert fact.attrs["value"] == "<redigido>"
        assert "AKIA" not in fact.attrs["value"]

    def test_high_entropy_value_under_secret_key_hint_is_flagged(self):
        # Base64-ish, alta entropia, sob uma chave que soa a segredo -- nao e
        # uma credencial de verdade, so a forma que o detector procura.
        high_entropy_value = "Zm9vYmFyYmF6cXV1eGNvcmdlZ3JhdWx0dGhpc2lzZmFrZQ"
        src = job_with_args(f'"--db-password" = "{high_entropy_value}"')
        fact = attrs_of("tf.attribute", "--db-password", src)
        assert fact.attrs["secret_pattern_match"] is True
        assert fact.attrs["value"] == "<redigido>"

    def test_high_entropy_value_under_unrelated_key_is_not_flagged(self):
        long_value = "s3-bucket-name-that-is-quite-long-but-not-a-secret-abc"
        src = job_with_args(f'"--TempDir" = "{long_value}"')
        fact = attrs_of("tf.attribute", "--TempDir", src)
        assert "secret_pattern_match" not in fact.attrs
        assert fact.attrs["value"] == long_value

    def test_url_with_inline_password_is_flagged(self):
        # Host/credencial fake, forma sintatica apenas -- nunca uma conexao real.
        src = job_with_args(
            '"--conn" = "postgres://svc_user:fake-pw-value@db.internal:5432/warehouse"'
        )
        fact = attrs_of("tf.attribute", "--conn", src)
        assert fact.attrs["secret_pattern_match"] is True
        assert fact.attrs["value"] == "<redigido>"

    def test_short_string_is_never_flagged(self):
        src = job_with_args('"--job-bookmark-option" = "job-bookmark-disable"')
        fact = attrs_of("tf.attribute", "--job-bookmark-option", src)
        assert "secret_pattern_match" not in fact.attrs


class TestUnresolvedConstructs:
    def test_interpolation_is_unresolved(self):
        src = job_with_args('"--TempDir" = "s3://${var.bucket}/tmp/"')
        fact = attrs_of("tf.unresolved", "--TempDir", src)
        assert fact.attrs["reason"] == "interpolation"

    def test_function_call_is_unresolved(self):
        src = job_with_args('"--conf" = format("spark.foo=%s", var.x)')
        fact = attrs_of("tf.unresolved", "--conf", src)
        assert fact.attrs["reason"] == "function_call"

    def test_heredoc_is_a_single_unresolved_fact_and_skips_body(self):
        src = job_with_args('"--extra-py-files" = <<EOT', "a.py", "b.py", "EOT")
        facts = extract_terraform(src, "main.tf")
        unresolved = facts_of("tf.unresolved", facts)
        heredoc_facts = [f for f in unresolved if f.attrs.get("reason") == "heredoc"]
        assert len(heredoc_facts) == 1
        assert heredoc_facts[0].attrs["key"] == "--extra-py-files"
        # As linhas do corpo ("a.py", "b.py") nao viram tf.unresolved avulsos.
        assert len(unresolved) == 1

    def test_dynamic_block_is_unresolved_and_body_is_skipped(self):
        src = textwrap.dedent(
            """
            resource "aws_glue_job" "etl" {
              name = "etl"

              dynamic "notification_property" {
                for_each = var.notify ? [1] : []
                content {
                  notify_delay_after = 5
                }
              }
            }
            """
        )
        facts = extract_terraform(src, "main.tf")
        unresolved = facts_of("tf.unresolved", facts)
        assert any(f.attrs.get("reason") == "dynamic_block" for f in unresolved)
        # tf.resource ainda e emitido: o dynamic block e pulado, nao invalida
        # o resto do recurso (ao contrario de for_each no proprio recurso).
        assert facts_of("tf.resource", facts)

    def test_for_each_on_resource_bails_the_whole_resource(self):
        src = textwrap.dedent(
            """
            resource "aws_glue_job" "etl" {
              for_each          = var.jobs
              name              = each.key
              number_of_workers = 4
            }
            """
        )
        facts = extract_terraform(src, "main.tf")
        assert facts_of("tf.resource", facts) == []
        assert facts_of("tf.attribute", facts) == []
        unresolved = facts_of("tf.unresolved", facts)
        assert len(unresolved) == 1
        assert unresolved[0].attrs["reason"] == "for_each"

    def test_unbalanced_braces_is_reported_and_stops_the_file(self):
        src = 'resource "aws_glue_job" "etl" {\n  name = "etl"\n'
        facts = extract_terraform(src, "main.tf")
        unresolved = facts_of("tf.unresolved", facts)
        assert any(f.attrs.get("reason") == "unbalanced_braces" for f in unresolved)
        assert facts_of("tf.module_analyzed", facts)


class TestNonGlueResourcesAreIgnored:
    def test_aws_iam_role_does_not_produce_attribute_facts(self):
        src = textwrap.dedent(
            """
            resource "aws_iam_role" "glue_role" {
              name               = "glue-role"
              assume_role_policy = data.aws_iam_policy_document.glue_assume.json
            }
            """
        )
        facts = extract_terraform(src, "main.tf")
        assert facts_of("tf.attribute", facts) == []
        assert facts_of("tf.resource", facts) == []
        assert facts_of("tf.module_analyzed", facts)[0].measures["resource_count"] == 0


class TestPathAndTree:
    def test_extract_terraform_path_read_error(self, tmp_path):
        missing = tmp_path / "missing.tf"
        facts = extract_terraform_path(missing, repo_root=tmp_path)
        assert len(facts) == 1
        assert facts[0].kind == "tf.unresolved"
        assert facts[0].attrs["reason"] == "read_error"

    def test_extract_terraform_path_reads_real_file(self, tmp_path):
        tf_file = tmp_path / "main.tf"
        tf_file.write_text(job_with_args(), encoding="utf-8")
        facts = extract_terraform_path(tf_file, repo_root=tmp_path)
        assert facts_of("tf.resource", facts)
        assert facts[0].subject["file"] == "main.tf"

    def test_extract_terraform_tree_is_resilient_to_one_bad_file(self, tmp_path):
        good = tmp_path / "good.tf"
        good.write_text(job_with_args(), encoding="utf-8")
        bad_dir = tmp_path / "bad.tf"
        bad_dir.mkdir()  # diretorio com extensao .tf: read_text falha com IsADirectoryError

        facts = extract_terraform_tree(tmp_path, repo_root=tmp_path)
        assert facts_of("tf.resource", facts)
        assert any(
            f.kind == "tf.unresolved" and f.attrs.get("reason") == "read_error" for f in facts
        )

    def test_extraction_is_deterministic(self, tmp_path):
        tf_file = tmp_path / "main.tf"
        tf_file.write_text(job_with_args('"--TempDir" = "s3://bucket/tmp/"'), encoding="utf-8")
        first = [f.to_dict() for f in extract_terraform_tree(tmp_path, repo_root=tmp_path)]
        second = [f.to_dict() for f in extract_terraform_tree(tmp_path, repo_root=tmp_path)]
        assert first == second


class TestSchemaValidation:
    def test_every_emitted_kind_validates(self):
        src = textwrap.dedent(
            """
            resource "aws_glue_job" "etl" {
              name              = "etl"
              number_of_workers = 4
              timeout           = "${var.timeout}"

              default_arguments = {
                "--enable-spark-ui"       = "true"
                "--spark-event-logs-path" = "s3://bucket/logs/"
                "--extra-py-files"        = <<EOT
                foo.py
                EOT
              }
            }

            resource "aws_glue_job" "broken" {
              for_each = var.jobs
              name     = each.key
            }
            """
        )
        facts = extract_terraform(src, "main.tf")
        assert {f.kind for f in facts} >= {
            "tf.attribute",
            "tf.resource",
            "tf.unresolved",
            "tf.module_analyzed",
            "tf.observability.spark_ui",
        }
        for fact in facts:
            validate_fact(fact.to_dict())
