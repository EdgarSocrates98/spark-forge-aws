resource "aws_glue_job" "stream_fgac" {
  name              = "stream-fgac"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 4

  command {
    name            = "gluestreaming"
    script_location = "s3://artefatos/scripts/stream_fgac.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
  }
}

resource "aws_glue_job" "etl_com_jar_sem_fgac" {
  name              = "etl-com-jar-sem-fgac"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--extra-jars"            = "s3://artefatos/jars/conector-jdbc.jar"
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
  }
}
