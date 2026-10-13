"""Torna `scripts/` um pacote importável para `from scripts.check_evals import verify_all`.
Os demais scripts continuam invocados como `python scripts/<nome>.py`; este
arquivo só existe para o import em tests/test_evals.py, que reutiliza
`scripts/check_evals.py` em vez de duplicar a lógica de verificação.
"""
