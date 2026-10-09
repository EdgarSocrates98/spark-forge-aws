resource "aws_glue_job" "etl_incremental" {
  name              = "etl-incremental"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-bookmark-option"   = "job-bookmark-enable"
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
  }

  execution_property {
    max_concurrent_runs = 3
  }
}
