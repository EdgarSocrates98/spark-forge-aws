resource "aws_glue_job" "etl_clean" {
  name              = "etl-clean-job"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 0
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl_clean.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://sparkforge-demo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--TempDir"                          = "s3://sparkforge-demo/temp/"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
