def processar(lotes, destino):
    for lote in lotes:
        lote.write.parquet(destino)
