def run(df, metodo):
    return getattr(df, metodo)(1)
