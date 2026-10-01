---
sdd: 1
feature: SDD_EVAL
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_EVAL/design.md
  sha256: "d644236ea6c1bc8e05ae839e633903d2bd1e93e9341cee5464bb23455ef9198d"
tasks:
  - id: T1
    files: [fixtures/sdd, .gitattributes, tests/test_sdd_eval_suite.py]
    covers: [AC3]
    test: {path: tests/test_sdd_eval_suite.py, name: test_fixtures_sem_conversao_de_quebra}
  - id: T2
    files: [evals/agentic/sdd/suite.yaml, evals/agentic/sdd/README.md, tests/test_sdd_eval_suite.py]
    covers: [AC1, AC2]
    test: {path: tests/test_sdd_eval_suite.py, name: test_gabarito_recomputado_pelo_gate}
  - id: T3
    files: [scripts/run_agentic_eval.py, tests/test_sdd_eval_suite.py]
    covers: [AC4]
    test: {path: tests/test_sdd_eval_suite.py, name: test_runner_conhece_a_suite_sdd}
  - id: T4
    files: [evals/agentic/sdd/baselines]
    covers: [AC5]
    test: {path: tests/test_sdd_eval_suite.py, name: test_suite_carrega_e_exige_as_tools}
---

# SDD_EVAL — plano

## T1 — fixtures

Cinco repositorios em `fixtures/sdd/<caso>/` com `docs/sdd/<FEATURE>/` e o que
o gate precisa (teste alvo, `.sparkforge/case.yaml` no operador). Os arquivos sao
gerados uma vez por um script de scratchpad que usa `stamp`, e conferidos:

```python
def test_fixtures_sem_conversao_de_quebra():
    texto = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "fixtures/sdd/** -text" in texto.splitlines()
    for caso in ("limpo", "cascata", "cobertura", "tdd", "operador"):
        assert (ROOT / "fixtures" / "sdd" / caso / "docs" / "sdd").is_dir(), caso
```

Rodar `tests/test_fixtures_kind_coverage.py` e o que mais cobrar dominio novo em
`fixtures/`; atender pelo motivo. Commit.

## T2 — suite e gabarito

```python
def test_gabarito_recomputado_pelo_gate():
    suite = load_suite(ROOT / "evals" / "agentic" / "sdd")
    for pergunta in suite.questions:
        caso, derivar = DERIVA[pergunta.id]
        assert pergunta.expected == derivar(ROOT / "fixtures" / "sdd" / caso), pergunta.id
```

`DERIVA` mapeia cada id para o caso e uma funcao sobre `check`/`status`. Commit.

## T3 — runner

Ler `scripts/run_agentic_eval.py` inteiro antes. A suite `sdd` entra como
constante; o teste confere que o runner a conhece sem aceitar caminho livre.
Commit.

## T4 — baseline

```python
def test_suite_carrega_e_exige_as_tools():
    suite = load_suite(ROOT / "evals" / "agentic" / "sdd")
    assert len(suite.questions) == 6
    for pergunta in suite.questions:
        exigidas = {t if isinstance(t, str) else frozenset(t) for t in pergunta.required_tools}
        assert exigidas & {"sdd_check", "sdd_status", frozenset({"sdd_check", "sdd_status"})}
```

Rodar o baseline Haiku com uma execucao; gravar o scorecard sob
`evals/agentic/sdd/baselines/<data>-haiku-4-5/` no formato dos baselines de
`fase0`. Sem `claude` autenticado, U1 fica aberto e o README diz isso.
