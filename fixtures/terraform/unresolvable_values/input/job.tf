resource "aws_glue_job" "etl_interpolado" {
  name              = "etl-interpolado"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_artefatos}/scripts/etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://${var.bucket_logs}/sparkui/"
    "--extra-py-files"                   = join(",", var.bibliotecas)
    "--conf"                             = <<-EOT
      spark.sql.shuffle.partitions=400
      spark.sql.adaptive.enabled=true
    EOT
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
