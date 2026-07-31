resource "aws_glue_job" "etl_sem_contexto" {
  name              = "etl-sem-contexto"
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
    "--enable-observability-metrics" = "true"
    "--enable-spark-ui"              = "true"
    "--spark-event-logs-path"        = "s3://logs/sparkui/"
  }
}
