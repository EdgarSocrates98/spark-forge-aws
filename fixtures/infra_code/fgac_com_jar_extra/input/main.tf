resource "aws_glue_job" "etl_fgac_com_jar" {
  name              = "etl-fgac-com-jar"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 20

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl_fgac.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--extra-jars"                               = "s3://artefatos/jars/conector-jdbc.jar"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
  }
}

resource "aws_glue_job" "etl_fgac_sem_jar" {
  name              = "etl-fgac-sem-jar"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 20

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl_limpo.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
  }
}

resource "aws_glue_job" "stream_sem_fgac" {
  name              = "stream-sem-fgac"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.025X"
  number_of_workers = 2

  command {
    name            = "gluestreaming"
    script_location = "s3://artefatos/scripts/stream.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
  }
}
