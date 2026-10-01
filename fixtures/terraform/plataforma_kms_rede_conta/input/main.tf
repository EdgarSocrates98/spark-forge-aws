# Os tres eixos de plataforma da secao 32 num arquivo so, com os pares negativos
# que separam cada regra do falso positivo dela. Todos os jobs declaram
# observabilidade e bookmark de proposito: sem isso, SF-GLUE-002 e SF-GLUE-005
# disparariam junto e a fixture deixaria de isolar o eixo que ela existe para
# provar.

resource "aws_glue_job" "curated_vpc_kms" {
  name                   = "curated-vpc-kms"
  role_arn               = aws_iam_role.glue_role.arn
  glue_version           = "5.0"
  worker_type            = "G.1X"
  number_of_workers      = 10
  max_retries            = 0
  timeout                = 480
  security_configuration = "curated-sec"
  connections            = ["rds-curated"]

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/curated.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://sparkforge-demo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--datalake-formats"                 = "iceberg"
    "--conf"                             = "spark.hadoop.hive.metastore.glue.catalogid=222222222222"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}

# Par negativo de SF-KMS-001 e de SF-NET-001: security configuration SEM
# conexao. Sem `same_subject` em SF-KMS-001, o motor casaria a security
# configuration deste com o `connections` do primeiro e acusaria dois jobs
# corretos -- a mesma armadilha que `fgac_com_jar_extra` mede para SF-LF-001.
resource "aws_glue_job" "sem_vpc" {
  name                   = "sem-vpc"
  role_arn               = aws_iam_role.glue_role.arn
  glue_version           = "5.0"
  worker_type            = "G.1X"
  number_of_workers      = 2
  max_retries            = 0
  timeout                = 480
  security_configuration = "curated-sec"

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/sem_vpc.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://sparkforge-demo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}

# Par negativo de SF-KMS-002 e de SF-XACC-001: usa Iceberg e nao tem security
# configuration; le catalogo, e o catalogo e o da propria conta. Iceberg sozinho
# nao e achado, e catalogo local tampouco.
resource "aws_glue_job" "iceberg_local" {
  name              = "iceberg-local"
  role_arn          = aws_iam_role.glue_role.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  max_retries       = 0
  timeout           = 480

  command {
    name            = "glueetl"
    script_location = "s3://sparkforge-demo/scripts/local.py"
    python_version  = "3"
  }

  default_arguments = {
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://sparkforge-demo/spark-logs/"
    "--enable-continuous-cloudwatch-log" = "true"
    "--job-bookmark-option"              = "job-bookmark-disable"
    "--datalake-formats"                 = "iceberg"
  }

  execution_property {
    max_concurrent_runs = 1
  }
}
