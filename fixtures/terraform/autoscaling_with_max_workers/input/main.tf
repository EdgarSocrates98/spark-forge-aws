resource "aws_iam_role" "glue_role" {
  name               = "sparkforge-demo-glue-role"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

resource "aws_glue_job" "etl_autoscaling" {
  name              = "etl-autoscaling-with-max-workers"
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

  # Auto Scaling ligado E number_of_workers definido: configuracao CORRETA.
  # number_of_workers e o teto que a API espera junto de Auto Scaling
  # (docs.aws.amazon.com/glue/latest/dg/auto-scaling.html). SF-GLUE-001
  # acusava esta combinacao em P1 e foi aposentada por isso em 2026-08-28 --
  # ver rules/catalog/glue-infra.yaml. Este cenario existe para travar a
  # regressao: nenhuma regra pode voltar a acusar isto.
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
