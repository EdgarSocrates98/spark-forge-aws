resource "aws_glue_job" "etl_iceberg_declarado" {
  name              = "etl-iceberg-declarado"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.1"
  worker_type       = "G.2X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl.py"
    python_version  = "3"
  }

  # O job declara Iceberg 1.4.2 e o Glue 5.1 embarca 1.10.0. NAO ha
  # `--user-jars-first`, e e essa ausencia que SF-ICE-009 julga: sem ela, qual
  # das duas versoes vence nao esta declarado em lugar nenhum.
  #
  # `--enable-spark-ui` esta aqui para `SF-GLUE-002` nao contaminar.
  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
    "--conf"                  = "spark.jars.packages=org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.2"
  }
}
