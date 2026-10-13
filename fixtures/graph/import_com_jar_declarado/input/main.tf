resource "aws_glue_job" "grafo_com_jar" {
  name              = "grafo-com-jar"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "4.0"
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
    "--extra-jars"            = "s3://artefatos/jars/graphframes-0.8.2-spark3.2-s_2.12.jar"
    "--extra-py-files"        = "s3://artefatos/jars/graphframes-0.8.2-spark3.2-s_2.12.jar"
  }
}
