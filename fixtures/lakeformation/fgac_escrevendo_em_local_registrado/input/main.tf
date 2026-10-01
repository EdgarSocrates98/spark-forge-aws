# FGAC ligado, e o artefato ao lado diz que a localizacao da tabela esta
# REGISTRADA no Lake Formation. E a combinacao que a documentacao da AWS nao
# resolve -- ver §6 de `knowledge/glue/lakeformation-fgac.md`.
#
# O catalogo e o session catalog e nao ha `--extra-jars` nem streaming, de
# proposito: com qualquer um dos tres, `SF-LF-001`, `SF-LF-002` ou `SF-LF-003`
# disparia junto e a fixture provaria mais de uma coisa.

resource "aws_glue_job" "etl_fgac_alvo_registrado" {
  name              = "etl-fgac-alvo-registrado"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.1"
  worker_type       = "G.2X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://sparkforge-demo/spark-logs/"
    "--conf"                                     = "spark.sql.catalog.spark_catalog=org.apache.iceberg.spark.SparkSessionCatalog"
  }
}
