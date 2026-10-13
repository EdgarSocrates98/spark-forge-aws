# O job declara FGAC no argumento E o resolver de credencial do Lake Formation
# no `--conf`. A AWS declara que um job nao roda os dois modelos ao mesmo tempo.
# O EMRFS esta restaurado na mesma linha, de proposito: sem ele SF-LF-004
# disparia junto e a fixture provaria duas coisas.

resource "aws_glue_job" "etl_dois_modelos" {
  name              = "etl-dois-modelos"
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
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://logs/sparkui/"
    "--conf"                                     = "spark.hadoop.fs.s3.credentialsResolverClass=com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver --conf spark.hadoop.fs.s3.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem"
  }
}
