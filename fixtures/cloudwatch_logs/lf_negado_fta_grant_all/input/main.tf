# Job sintetico sob Full Table Access: o `--conf` pede a credencial do Lake
# Formation e restaura EMRFS, e nao ha argumento de FGAC.

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
