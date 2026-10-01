# O job declara controle de acesso fino do Lake Formation. E a UNICA coisa
# neste arquivo que a regra le -- o resto existe para que o job seja um
# `aws_glue_job` plausivel.

resource "aws_glue_job" "curated_fato" {
  name              = "curated-fato"
  role_arn          = "arn:aws:iam::111111111111:role/glue-curated"
  glue_version      = "5.1"
  worker_type       = "G.2X"
  number_of_workers = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/fato.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-lakeformation-fine-grained-access" = "true"
    "--enable-spark-ui"                          = "true"
    "--spark-event-logs-path"                    = "s3://sparkforge-demo/spark-logs/"
  }
}
