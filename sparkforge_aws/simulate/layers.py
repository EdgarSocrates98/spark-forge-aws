"""As camadas de configuracao que um `--set` pode alterar.

Uma camada e um lugar onde o operador DECLARA configuracao, e a regra 19
separa quem pediu de quem venceu: o `--set` altera uma camada so, a que o
operador mudaria de verdade. Todo kind abaixo guarda a propriedade em
`attrs.key` e o valor em `attrs.value` -- medido em 2026-09-12 sobre os goldens.
"""
from __future__ import annotations

CAMADAS: dict[str, frozenset[str]] = {
    "tf": frozenset({"tf.spark_conf", "tf.attribute"}),
    "code": frozenset({"pyspark.conf_set"}),
    "effective": frozenset({"spark.conf_effective"}),
    "emr": frozenset({"emr.configuration", "emrs.configuration", "emrc.configuration"}),
}
