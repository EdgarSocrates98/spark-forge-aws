resource "aws_glue_job" "etl_pedidos" {
  name              = "etl-pedidos"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
  }
}
