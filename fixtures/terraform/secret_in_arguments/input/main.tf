resource "aws_glue_job" "etl_secret" {
  name              = "etl-secret-leak"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl.py"
    python_version  = "3"
  }

  # Credencial em default argument: exposta na job definition, na API e em
  # logs -- SF-GLUE-006. Valor de exemplo documentado pela AWS
  # (https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html),
  # nao uma credencial real.
  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--aws-access-key-id"     = "AKIAIOSFODNN7EXAMPLE"
  }
}
