resource "aws_glue_job" "etl_fta_sem_emrfs" {
  name              = "etl-fta-sem-emrfs"
  role_arn          = aws_iam_role.glue.arn
  glue_version      = "5.1"
  worker_type       = "G.2X"
  number_of_workers = 6

  command {
    name            = "glueetl"
    script_location = "s3://artefatos/scripts/etl_fta.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://logs/sparkui/"
    "--conf"                  = "spark.hadoop.fs.s3.credentialsResolverClass=com.amazonaws.glue.accesscontrol.AWSLakeFormationCredentialResolver --conf spark.hadoop.fs.s3.useDirectoryHeaderAsFolderObject=true --conf spark.hadoop.fs.s3.folderObject.autoAction.disabled=true"
  }
}
