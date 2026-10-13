"""Comparacao de um caso golden: o que era esperado contra o que saiu.

`match_rate` e Jaccard sobre os ids, nao percentual de acerto: serve para
ordenar regressoes por gravidade, nunca para declarar um caso aprovado --
quem decide isso e `passed`, que exige igualdade exata.
"""


def _ids(value):
    if isinstance(value, dict):
        value = value.get("findings", value.get("rules", []))
    if not isinstance(value, list):
        return set()
    return {
        str(x if isinstance(x, str) else x.get("id", x.get("rule_id", "")))
        for x in value
    }


def evaluate_golden_case(expected, actual):
    exp, got = _ids(expected), _ids(actual)
    return {
        "passed": exp == got,
        "expected": sorted(exp),
        "actual": sorted(got),
        "missing": sorted(exp - got),
        "unexpected": sorted(got - exp),
        "match_rate": 1.0 if exp == got else len(exp & got) / max(1, len(exp | got)),
    }
