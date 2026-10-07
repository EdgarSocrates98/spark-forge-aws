resource "aws_glue_job" "faturamento" {
  name              = "faturamento-diario"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "6.0"
  worker_type       = "G.1X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/faturamento/main.py"
    python_version  = "3"
  }

  default_arguments = {
    "--extra-py-files"                   = "s3://artefatos/scripts/faturamento/conf.zip"
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://logs/sparkui/faturamento/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
