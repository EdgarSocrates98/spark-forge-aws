resource "aws_iam_role" "glue_role" {
  name               = "sparkforge-demo-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

resource "aws_glue_job" "etl_max_capacity" {
  name              = "etl-max-capacity-conflict"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "4.0"
  worker_type       = "G.2X"
  number_of_workers = 10
  max_capacity      = 20
  max_retries       = 0
  timeout           = 2880

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl.py"
    python_version  = "3"
  }

  # max_capacity E worker_type/number_of_workers definidos ao mesmo tempo,
  # em Glue 4.0 (>= 2.0): contraditorio -- SF-GLUE-007. A API do Job
  # (webapi/API_Job.html, campo MaxCapacity) documenta que, a partir do Glue
  # 2.0, max_capacity nao pode ser especificado -- a forma correta e
  # worker_type + number_of_workers, e os dois modelos nao coexistem.
  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--job-bookmark-option"   = "job-bookmark-disable"
    "--enable-metrics"        = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
