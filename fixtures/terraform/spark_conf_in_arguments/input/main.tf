resource "aws_glue_job" "etl_conf" {
  name              = "etl-conf-job"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 6
  max_retries       = 0
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/etl_conf.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://sparkforge-demo/spark-logs/"
    "--job-bookmark-option"   = "job-bookmark-disable"
    "--TempDir"               = "s3://sparkforge-demo/temp/"
    "--conf"                  = "spark.sql.shuffle.partitions=200 --conf spark.sql.adaptive.enabled=false --conf spark.serializer=org.apache.spark.serializer.KryoSerializer --conf spark.sql.autoBroadcastJoinThreshold"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
