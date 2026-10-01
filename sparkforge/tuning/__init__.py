"""Configuracao Spark derivada da medida, com a procedencia de cada propriedade.

Pacote proprio, e nao `sparkforge/rules/`: o catalogo JULGA configuracao que ja
existe, e este pacote PROPOE valor a partir de shuffle medido. Julgar e propor
sao operacoes diferentes, e misturar as duas faria a regra concordar com a
recomendacao do proprio projeto em vez de julgar a evidencia.

A separacao esta na seccao 23 do documento de origem, que pede `tuning/` ao lado
de `workload/` e `finops/`.
"""
from sparkforge.tuning.spark_conf import build_conf_advice

__all__ = ["build_conf_advice"]
