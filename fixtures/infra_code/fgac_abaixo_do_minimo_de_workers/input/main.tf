# `number_of_workers = 2` com FGAC ligado. A AWS declara minimo de QUATRO sob
# controle de acesso fino -- um user driver, um system driver, um system executor
# e um user executor de reserva. O segundo job e o par negativo: mesmos
# argumentos, quatro workers.

resource "aws_glue_job" "etl_dois_workers" {
  name              = "etl-dois-workers"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
  }
}

resource "aws_glue_job" "etl_quatro_workers" {
  name              = "etl-quatro-workers"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 4

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl_ok.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
  }
}
