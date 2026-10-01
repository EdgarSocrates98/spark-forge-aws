---
sdd: 1
feature: SDD_OPERATOR
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_OPERATOR/design.md
  sha256: "393ca4bc25010058f3bfa044fdbbdbbc20f6e41aa5a34532642b9666a8b26e69"
tasks:
  - id: T1
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC2]
    test: {path: tests/test_sdd.py, name: test_funcval_not_comparison}
  - id: T2
    files: [sparkforge/sdd/checks.py, tests/test_sdd.py]
    covers: [AC3]
    test: {path: tests/test_sdd.py, name: test_funcval_blind_spot}
  - id: T3
    files: [tests/test_sdd_operator.py]
    covers: [AC1]
    test: {path: tests/test_sdd_operator.py, name: test_fluxo_operator_ponta_a_ponta}
  - id: T4
    files: [agents/spark-performance-architect.md, agents/glue-incremental-performance-architect.md, agents/glue-infra-reviewer.md, agents/pyspark-code-reviewer.md, skills/sdd-define/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-build/SKILL.md, tests/test_sdd_operator.py]
    covers: [AC4]
    test: {path: tests/test_sdd_operator.py, name: test_coordenadores_apontam_o_sdd}
---

# SDD_OPERATOR — plano

## T1 — funcval_not_comparison

```python
def test_funcval_not_comparison(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "funcval", "ref": "out/compare.json"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "compare.json").write_bytes(b'{"items": [{"id": "f1", "kind": "outro"}]}')
    assert _codigos(check(tmp_path)) == (["funcval_not_comparison"], [])
    (tmp_path / "out" / "compare.json").write_bytes(
        b'{"items": [{"id": "f1", "kind": "funcval.check_delta", "subject": {}}]}'
    )
    assert _codigos(check(tmp_path)) == ([], [])
```

Implementar no ramo `funcval` de `_gate_verified_by`, reaproveitando o leitor de
`_ids_de_fact` (extrair `_itens_de_fact`). Commit.

## T2 — funcval_blind_spot

```python
def test_funcval_blind_spot(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "funcval", "ref": "compare.json"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    (tmp_path / "compare.json").write_bytes(
        b'{"items": [{"id": "f1", "kind": "funcval.check_delta"},'
        b' {"id": "f2", "kind": "funcval.unresolved", "subject": {"check": "row_count"}}]}'
    )
    relatorio = check(tmp_path)
    assert _codigos(relatorio) == ([], ["funcval_blind_spot"])
    assert "row_count" in relatorio["unresolved"][0]["unlock"]
```

Commit, com os dois codigos acrescentados ao paragrafo 5.0 do spec do nucleo.

## T3 — ponta a ponta

`tests/test_sdd_operator.py` com o fluxo do design. Antes de escrever, ler os
`inputSchema` de `sparkforge_case_open` e `sparkforge_change_sandbox` em
`sparkforge/adapters/tools.py` e como os testes existentes leem o retorno de
`call_tool`. Commit.

## T4 — coordenadores

```python
COORDENADORES = (
    "spark-performance-architect",
    "glue-incremental-performance-architect",
    "glue-infra-reviewer",
    "pyspark-code-reviewer",
)

def test_coordenadores_apontam_o_sdd():
    for nome in COORDENADORES:
        texto = (ROOT / "agents" / f"{nome}.md").read_text(encoding="utf-8")
        frente, corpo = texto.split("\n---\n", 1)
        assert "sdd-" not in frente, nome
        assert "`sdd-define`" in corpo and "`sdd-build`" in corpo, nome
        assert "sparkforge sdd check" in corpo, nome
        assert "sparkforge case open" in corpo, nome
```

Revisto no build (D2): as `sdd-*` sao nao-despachaveis e ficam fora do
`skills:`; o coordenador as cita na prosa. No mesmo commit, as secoes "Perfil
operator" de `sdd-define`, `sdd-plan` e `sdd-build` trocam o adiamento para o
subprojeto C pelo caminho concreto.

Editar a FONTE em `agents/` e `skills/`, rodar `python scripts/sync_skills.py`
(guardando `.claude/agents/README.md`), e `python -m pytest
tests/test_agents_parity.py tests/test_agent_coverage.py tests/test_sync_render.py
tests/test_skill_content.py tests/test_sdd_skills.py -q`. Commit.
