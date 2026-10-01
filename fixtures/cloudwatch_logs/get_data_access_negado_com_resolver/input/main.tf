# O job pede que o acesso ao S3 use a credencial que o Lake Formation vende --
# e o `--conf` abaixo e a unica coisa que a regra le. Nao ha
# `--enable-lakeformation-fine-grained-access` aqui, e a ausencia e o par
# negativo embutido: sem ela nenhum `lakeformation.access_model` e emitido.

resource "aws_glue_job" "curated_fta" {
  name              = "curated-fta"
  role_arn          = "arn:aws:iam::111111111111:role/glue-fta"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/fta.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--conf"                  = "spark.hadoop.fs.s3.credentialsResolverClass=com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver --conf spark.hadoop.fs.s3.impl=com.amazon.ws.emr.hadoop.fs.EmrFileSystem"
  }
}
