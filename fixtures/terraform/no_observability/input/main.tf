resource "aws_glue_job" "etl_no_observability" {
  name              = "etl-no-observability"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 4
  max_retries       = 0
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl.py"
    python_version  = "3"
  }

  # Sem --enable-spark-ui e sem --spark-event-logs-path: nao ha como
  # diagnosticar este job depois do fato -- SF-GLUE-002.
  default_arguments = {
    "--job-bookmark-option" = "job-bookmark-disable"
    "--TempDir"             = "s3://sparkforge-demo/temp/"
  }
}
