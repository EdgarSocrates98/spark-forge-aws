def transformar(a, b):
    return a.join(b, "k").select("x").filter("x > 1")
