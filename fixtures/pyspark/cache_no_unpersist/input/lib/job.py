def calcular(df):
    d = df.cache()
    return d.count()
