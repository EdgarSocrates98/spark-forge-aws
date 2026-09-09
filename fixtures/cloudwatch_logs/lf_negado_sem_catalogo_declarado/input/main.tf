# O MESMO job do par positivo, com UMA linha a menos: sem o `--conf` de
# `catalogid`, nada aqui diz que ele le o catalogo de outra conta -- e
# SF-ERR-006 fica sem o `tf.spark_conf` que ela exige.

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
  }
}
