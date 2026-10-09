resource "aws_glue_job" "etl" {
  name         = "etl-sintetico"
  role_arn     = "arn:aws:iam::123456789012:role/glue-sintetico"
  glue_version = "4.0"
  worker_type  = "G.1X"

  command {
    name            = "glueetl"
    script_location = "s3://bucket-sintetico/scripts/etl.py"
  }

  default_arguments = {
    "--conf" = "spark.sql.shuffle.partitions=600"
  }
}
