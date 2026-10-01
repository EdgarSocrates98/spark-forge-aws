# O job PEDE a credencial do Lake Formation (resolver + EMRFS restaurado), e a
# CONTA recusa (`allow_full_table_external_data_access` desligado no artefato ao
# lado). As duas metades vem de artefatos diferentes, e nenhuma delas sozinha
# sustenta o achado -- e por isso que SF-LF-007 exige os dois.

resource "aws_glue_job" "etl_fta" {
  name              = "etl-fta"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/fta.py"
    python_version  = "3"
  }

  default_arguments = {
    # Observabilidade declarada de proposito: sem ela `SF-GLUE-002` dispara
    # junto, e a fixture passaria a provar duas coisas ao mesmo tempo.
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--conf" = "spark.hadoop.fs.s3.credentialsResolverClass=com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver --conf spark.hadoop.fs.s3.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem"
  }
}
