resource "aws_glue_job" "etl_sdk" {
  name              = "etl-sdk-job"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "6.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 0
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl_sdk.py"
    python_version  = "3"
  }

  default_arguments = {
    "--extra-jars"          = "s3://sparkforge-demo/jars/conector-interno-1.4.0.jar"
    "--user-jars-first"     = "true"
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--job-bookmark-option" = "job-bookmark-disable"
    "--TempDir"             = "s3://sparkforge-demo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
