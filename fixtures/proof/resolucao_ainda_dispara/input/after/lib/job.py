def carregar(df):
    ativos = df.filter("ativo = true")
    return ativos.collect()
