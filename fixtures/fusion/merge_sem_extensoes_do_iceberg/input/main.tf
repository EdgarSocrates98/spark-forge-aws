resource "aws_glue_job" "etl_merge_sem_extensoes" {
  name              = "etl-merge-sem-extensoes"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.1"
  worker_type       = "G.2X"
  number_of_workers = 10

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl_merge.py"
    python_version  = "3"
  }

  # `--enable-spark-ui` e `--spark-event-logs-path` estao aqui de proposito: sem
  # eles `SF-GLUE-002` dispara junto e contamina o que esta fixture prova.
  #
  # A conf declara `spark.sql.shuffle.partitions` e NAO declara
  # `spark.sql.extensions`. A presenca de UMA chave e o que faz o ternario
  # `iceberg_extensions_declared` valer `false` em vez de `null`: a superficie de
  # conf FOI lida, e a chave nao estava nela.
  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
    "--conf"                  = "spark.sql.shuffle.partitions=200"
  }
}
