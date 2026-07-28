import sys

from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions

from pyspark import StorageLevel
from pyspark.context import SparkContext
from pyspark.sql.functions import col, dayofmonth, month, to_date, year
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)
from pyspark.sql.utils import AnalysisException


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DATABASE_NAME = "meu_database"

ICEBERG_TABLE_NAME = "vendas_iceberg"
PARQUET_TABLE_NAME = "vendas_parquet"

PARQUET_OUTPUT_PATH = (
    "s3://meu-bucket/datalake/vendas_parquet/"
)

ICEBERG_IDENTIFIER = (
    f"glue_catalog.{DATABASE_NAME}.{ICEBERG_TABLE_NAME}"
)

PARTITION_COLUMNS = ["ano", "mes", "dia"]


# ============================================================
# INICIALIZAÇÃO DO GLUE
# ============================================================

args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME"],
)

sc = SparkContext.getOrCreate()
glue_context = GlueContext(sc)
spark = glue_context.spark_session

job = Job(glue_context)
job.init(args["JOB_NAME"], args)


# ============================================================
# FUNÇÕES
# ============================================================

def iceberg_table_exists(table_identifier: str) -> bool:
    """
    Verifica se a tabela Iceberg já existe no Glue Data Catalog.
    """
    try:
        spark.table(table_identifier)
        return True
    except AnalysisException:
        return False


def write_iceberg(df) -> None:
    """
    Cria a tabela Iceberg na primeira execução.
    Nas execuções seguintes, adiciona os dados.
    """

    if iceberg_table_exists(ICEBERG_IDENTIFIER):
        print(
            f"Tabela Iceberg existente. Executando append: "
            f"{ICEBERG_IDENTIFIER}"
        )

        (
            df.writeTo(ICEBERG_IDENTIFIER)
            .append()
        )

    else:
        print(
            f"Criando tabela Iceberg: "
            f"{ICEBERG_IDENTIFIER}"
        )

        (
            df.writeTo(ICEBERG_IDENTIFIER)
            .tableProperty("format-version", "2")
            .tableProperty(
                "write.parquet.compression-codec",
                "snappy",
            )
            .partitionedBy(*PARTITION_COLUMNS)
            .create()
        )


def write_partitioned_parquet(df) -> None:
    """
    Grava Parquet tradicional particionado no S3 e cria/atualiza
    a tabela e as partições no AWS Glue Data Catalog.
    """

    print(
        f"Gravando tabela Parquet tradicional: "
        f"{DATABASE_NAME}.{PARQUET_TABLE_NAME}"
    )

    dynamic_frame = DynamicFrame.fromDF(
        df,
        glue_context,
        "dynamic_frame_parquet",
    )

    sink = glue_context.getSink(
        connection_type="s3",
        path=PARQUET_OUTPUT_PATH,
        enableUpdateCatalog=True,
        updateBehavior="UPDATE_IN_DATABASE",
        partitionKeys=PARTITION_COLUMNS,
        compression="snappy",
        transformation_ctx="sink_parquet",
    )

    sink.setCatalogInfo(
        catalogDatabase=DATABASE_NAME,
        catalogTableName=PARQUET_TABLE_NAME,
    )

    sink.setFormat(
        "parquet",
        useGlueParquetWriter=True,
    )

    sink.writeFrame(dynamic_frame)


# ============================================================
# LEITURA / CRIAÇÃO DOS DADOS
# ============================================================

# Dados apenas para demonstração.
# Em um job real, substitua por spark.read.parquet(),
# glue_context.create_dynamic_frame.from_catalog(), JDBC etc.

schema = StructType(
    [
        StructField("id", IntegerType(), False),
        StructField("cliente", StringType(), False),
        StructField("valor", DoubleType(), False),
        StructField("data_evento", StringType(), False),
    ]
)

dados_exemplo = [
    (1, "Cliente A", 150.50, "2026-07-28"),
    (2, "Cliente B", 320.90, "2026-07-28"),
    (3, "Cliente C", 75.25, "2026-07-27"),
]

df_origem = spark.createDataFrame(
    dados_exemplo,
    schema=schema,
)


# Exemplo lendo Parquet do S3:
#
# df_origem = spark.read.parquet(
#     "s3://meu-bucket/datalake/origem/"
# )


# ============================================================
# TRANSFORMAÇÕES
# ============================================================

df_saida = (
    df_origem
    .withColumn(
        "data_evento",
        to_date(col("data_evento")),
    )
    .withColumn(
        "ano",
        year(col("data_evento")),
    )
    .withColumn(
        "mes",
        month(col("data_evento")),
    )
    .withColumn(
        "dia",
        dayofmonth(col("data_evento")),
    )
)


# O mesmo DataFrame será usado em duas ações de escrita.
df_saida = df_saida.persist(
    StorageLevel.MEMORY_AND_DISK
)


# ============================================================
# GRAVAÇÕES
# ============================================================

try:
    # Primeira saída: Iceberg
    write_iceberg(df_saida)

    # Segunda saída: Parquet tradicional particionado
    write_partitioned_parquet(df_saida)

    print("As duas gravações foram concluídas.")

finally:
    df_saida.unpersist()


job.commit()
