resource "aws_glue_job" "vendas_governado" {
  name              = "vendas-governado"
  role_arn          = aws_iam_role.glue_governado.arn
  glue_version      = "6.0"
  worker_type       = "G.2X"
  number_of_workers = 20

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/vendas_governado.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--extra-jars"                               = "s3://artefatos/jars/conector-jdbc-8.0.33.jar"
    "--datalake-formats"                         = "iceberg"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/vendas-governado/"
    "--enable-continuous-cloudwatch-log"         = "true"
    "--enable-metrics"                           = "true"
    "--job-bookmark-option"                      = "job-bookmark-disable"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
