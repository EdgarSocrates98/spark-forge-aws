from pyspark.sql.functions import udf
from pyspark.sql.types import StringType


@udf(returnType=StringType())
def normaliza(valor):
    return valor.strip().lower()
