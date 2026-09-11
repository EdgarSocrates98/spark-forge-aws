resource "aws_glue_job" "etl_grafo" {
  name     = "etl-grafo"
  role_arn = aws_iam_role.glue.arn

  default_arguments = {
    "--extra-jars" = "s3://artefatos/jars/graphframes-0.8.3-spark3.5-s_2.12.jar"
  }
}
