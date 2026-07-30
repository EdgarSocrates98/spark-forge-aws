resource "aws_iam_role" "glue_role" {
  name               = "sparkforge-demo-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

resource "aws_glue_job" "etl_autoscaling" {
  name              = "etl-autoscaling-conflict"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.2X"
  number_of_workers = 10
  max_retries       = 0
  timeout           = 2880

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl.py"
    python_version  = "3"
  }

  # Auto Scaling ligado E number_of_workers definido: contraditorio -- SF-GLUE-001.
  default_arguments = {
    "--enable-auto-scaling"   = "true"
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--job-bookmark-option"   = "job-bookmark-disable"
    "--enable-metrics"        = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
