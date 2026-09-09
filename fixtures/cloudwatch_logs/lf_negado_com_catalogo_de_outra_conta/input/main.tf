# O job le o Data Catalog de OUTRA conta -- e o `--conf` da linha 20 e a unica
# coisa neste arquivo que a regra SF-ERR-006 le. O resto existe para que o job
# seja um `aws_glue_job` plausivel, e nao para disparar nada.

resource "aws_glue_job" "curated_dim" {
  name              = "curated-dim"
  role_arn          = "arn:aws:iam::111111111111:role/glue-curated"
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/dim.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://sparkforge-demo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--conf"                             = "spark.hadoop.hive.metastore.glue.catalogid=222222222222"
  }
}
