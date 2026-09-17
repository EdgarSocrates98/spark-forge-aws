---
sdd: 1
feature: EXEMPLO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/EXEMPLO/design.md
  sha256: ""
tasks:
  - id: T1
    files: [tests/test_exemplo.py, exemplo/resumo.py]
    covers: [AC1]
    test: {path: tests/test_exemplo.py, name: test_exemplo}
---

# EXEMPLO — plano

> Template da skill `sdd-plan`. Cada tarefa cabe em poucos minutos, nomeia o
> teste que falha antes do codigo e traz o codigo completo no corpo. Sem
> "TBD", sem "igual a T1", sem "tratar os erros".

## T1 — resumo

Teste primeiro, em `tests/test_exemplo.py`:

```python
from exemplo.resumo import resumir


def test_exemplo():
    relatorio = {"run_id": "r1", "status": "ok", "bytes": 10, "detalhe": [1, 2]}
    assert resumir(relatorio) == {"run_id": "r1", "status": "ok", "bytes": 10}
```

Rodar e ver falhar pelo motivo certo (`ModuleNotFoundError: exemplo`):

```bash
python -m pytest tests/test_exemplo.py::test_exemplo -q
```

Codigo minimo, em `exemplo/resumo.py`:

```python
CAMPOS = ("run_id", "status", "bytes")


def resumir(relatorio: dict) -> dict:
    return {campo: relatorio[campo] for campo in CAMPOS}
```

Rodar de novo e ver verde. Commit com os dois arquivos.
