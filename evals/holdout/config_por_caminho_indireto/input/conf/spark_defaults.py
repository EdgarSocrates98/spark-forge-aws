"""Tabela de configuracao do job. Nenhuma chave e aplicada AQUI.

O modulo so declara o mapa; quem chama `spark.conf.set` e `aplicar_conf` em
`sessao.py`, num laco sobre este dicionario. E o caminho indireto: a chave nao
aparece em nenhuma linha de `spark.conf.set(...)` do repositorio.
"""

CONF_PADRAO = {
    # Herdada do EMR. O S3A do Glue 5+ nao le esta chave e nao reclama.
    "fs.s3.consistent": "true",
    # Renomeada no Spark 4.0. O nome antigo tambem nao e lido e tambem nao
    # reclama -- o job segue com a configuracao que quem le acha que esta ativa.
    "spark.sql.legacy.parquet.int96RebaseModeInWrite": "CORRECTED",
    "spark.sql.shuffle.partitions": "800",
}
