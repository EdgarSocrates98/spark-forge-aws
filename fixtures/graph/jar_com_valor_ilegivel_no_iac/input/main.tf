resource "aws_glue_job" "grafo_jar_interpolado" {
  name              = "grafo-jar-interpolado"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/job.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"          = "python"
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
    "--extra-jars"            = "s3://${var.bucket_artefatos}/jars/graphframes.jar"
  }
}
