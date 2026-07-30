resource "aws_glue_job" "etl_clean_observed" {
  name              = "etl-clean-observed"
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

  # Configurado corretamente: --enable-spark-ui e --spark-event-logs-path
  # presentes. Este job NAO pode aparecer nos findings de SF-GLUE-002.
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

resource "aws_glue_job" "etl_no_observability_a" {
  name              = "etl-no-observability-a"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 4
  max_retries       = 0
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl_a.py"
    python_version  = "3"
  }

  # Sem --enable-spark-ui e sem --spark-event-logs-path -- primeiro job
  # ofensor de SF-GLUE-002 neste arquivo.
  default_arguments = {
    "--job-bookmark-option" = "job-bookmark-disable"
    "--TempDir"             = "s3://sparkforge-demo/temp/"
  }
}

resource "aws_glue_job" "etl_no_observability_b" {
  name              = "etl-no-observability-b"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 4
  max_retries       = 0
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl_b.py"
    python_version  = "3"
  }

  # Sem --enable-spark-ui e sem --spark-event-logs-path -- segundo job
  # ofensor de SF-GLUE-002 neste arquivo. Precisa das duas ausencias
  # detectadas de forma independente do job_a acima, e sem que o job_clean
  # (que tem os dois argumentos) mascare nenhum dos dois.
  default_arguments = {
    "--job-bookmark-option" = "job-bookmark-disable"
    "--TempDir"             = "s3://sparkforge-demo/temp/"
  }
}
