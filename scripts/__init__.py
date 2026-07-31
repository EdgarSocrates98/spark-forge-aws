"""Torna `scripts/` um pacote importavel para `from scripts.check_evals import verify_all`.

Os demais scripts continuam invocados como `python scripts/<nome>.py`; este
arquivo so existe para o import em tests/test_evals.py, que reusa
`scripts/check_evals.py` em vez de duplicar a logica de verificacao.
"""
