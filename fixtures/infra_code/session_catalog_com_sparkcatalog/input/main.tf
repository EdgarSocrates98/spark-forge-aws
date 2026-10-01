resource "aws_glue_job" "etl_session_catalog_sparkcatalog" {
  name              = "etl-session-catalog-sparkcatalog"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.1"
  worker_type       = "G.2X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl_misto.py"
    python_version  = "3"
  }

  # `--enable-spark-ui` e `--spark-event-logs-path` estao aqui de proposito: sem
  # eles `SF-GLUE-002` dispara junto e contamina o que esta fixture prova.
  #
  # NAO ha argumento de FGAC. E deliberado: SF-ICE-006 e sobre a CLASSE do
  # catalogo de sessao, e nao sobre Lake Formation. Ligar FGAC aqui faria
  # SF-LF-003 e SF-LF-005 entrarem e a fixture deixaria de isolar a regra.
  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
    "--conf"                  = "spark.sql.catalog.spark_catalog=org.apache.iceberg.spark.SparkCatalog --conf spark.sql.catalog.spark_catalog.type=hive --conf spark.sql.catalog.spark_catalog.warehouse=s3://lake/warehouse/"
  }
}
