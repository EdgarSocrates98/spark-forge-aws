---
sdd: 1
feature: SDD_SKILLS
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_SKILLS/design.md
  sha256: "6dae10a38bd5ab645f0d60a7ee95dfc35b5f8a97b3c3e8e060e578c5e0cc0816"
tasks:
  - id: T1
    files: [docs/sdd/templates/explore.md, docs/sdd/templates/define.md, docs/sdd/templates/design.md, docs/sdd/templates/plan.md, docs/sdd/templates/build_report.md, docs/sdd/templates/ship.md, docs/sdd/README.md, tests/test_sdd_skills.py]
    covers: [AC2]
    test: {path: tests/test_sdd_skills.py, name: test_templates_formam_feature_valida}
  - id: T2
    files: [skills/sdd-explore/SKILL.md, skills/sdd-define/SKILL.md, skills/sdd-design/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-build/SKILL.md, skills/sdd-ship/SKILL.md, scripts/sync_skills.py, tests/test_sdd_skills.py]
    covers: [AC1, AC5]
    test: {path: tests/test_sdd_skills.py, name: test_seis_skills_existem}
  - id: T3
    files: [skills/sdd-explore/SKILL.md, skills/sdd-define/SKILL.md, skills/sdd-design/SKILL.md, skills/sdd-plan/SKILL.md, skills/sdd-build/SKILL.md, skills/sdd-ship/SKILL.md, tests/test_sdd_skills.py]
    covers: [AC3]
    test: {path: tests/test_sdd_skills.py, name: test_comandos_citados_existem}
  - id: T4
    files: [vendor/CREDITS.md, tests/test_sdd_skills.py]
    covers: [AC4]
    test: {path: tests/test_sdd_skills.py, name: test_credito_das_bases}
  - id: T5
    files: [docs/surface.lock.json, docs/guia/referencia]
    covers: [AC5]
    test: {path: tests/test_skill_content.py, name: test_copias_conferem_com_a_renderizacao}
---

# SDD_SKILLS — plano

## T1 — templates e README

Teste primeiro, em `tests/test_sdd_skills.py`:

```python
def test_templates_formam_feature_valida(tmp_path):
    """Copia os seis templates para uma feature, carimba em ordem e confere."""
    origem = ROOT / "docs" / "sdd" / "templates"
    destino = tmp_path / "docs" / "sdd" / "EXEMPLO"
    destino.mkdir(parents=True)
    for fase in PHASES:
        (destino / f"{fase}.md").write_bytes((origem / f"{fase}.md").read_bytes())
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_exemplo.py").write_bytes(b"def test_exemplo():\n    pass\n")
    for fase in PHASES[1:]:
        stamp(tmp_path, f"docs/sdd/EXEMPLO/{fase}.md")
    relatorio = check(tmp_path)
    assert relatorio["refused"] == [], relatorio
```

Os templates declaram `feature: EXEMPLO`, `profile: dev`, `status: draft` e
valores de exemplo que passam no schema; o `verified_by` aponta
`tests/test_exemplo.py::test_exemplo`, e o `design` so tem `action: create`.
`status: draft` em todas as fases faria `phase_out_of_order`: por isso os
templates usam `status: ready` e o texto de cada um manda trocar para `draft`
ao comecar. `docs/sdd/README.md` explica a arvore, os tres verbos e aponta as
skills. Commit.

## T2 — as seis skills

Teste primeiro:

```python
SKILLS_SDD = ("sdd-explore", "sdd-define", "sdd-design", "sdd-plan", "sdd-build", "sdd-ship")

def test_seis_skills_existem():
    for nome in SKILLS_SDD:
        texto = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        assert texto.startswith("---\nname: " + nome + "\n")
        for secao in ("## Quando NÃO usar", "## Referência rápida", "## Red flags"):
            assert secao in texto, (nome, secao)
        assert "sparkforge sdd check" in texto, nome
```

Escrever as seis skills seguindo a tabela do design. Ler
`scripts/sync_skills.py` (U1) e registrar as seis como nao despachaveis se a
tabela exigir. `python scripts/sync_skills.py` (com `.claude/agents/README.md`
guardado no scratchpad e devolvido depois) e `python -m pytest
tests/test_skill_content.py tests/test_sync_render.py tests/test_agents_parity.py
-q`. Commit.

## T3 — comandos citados existem

```python
def test_comandos_citados_existem():
    parser = build_parser()
    padrao = re.compile(r"`sparkforge ([a-z][a-z-]*(?: [a-z][a-z-]*)?)")
    for nome in SKILLS_SDD:
        texto = (ROOT / "skills" / nome / "SKILL.md").read_text(encoding="utf-8")
        for verbo in set(padrao.findall(texto)):
            partes = verbo.split()
            try:
                parser.parse_args([*partes, "--help"])
            except SystemExit as saida:
                assert saida.code == 0, (nome, verbo)
```

Corrigir o texto das skills ate passar. Commit.

## T4 — credito

```python
def test_credito_das_bases():
    texto = (ROOT / "vendor" / "CREDITS.md").read_text(encoding="utf-8")
    for trecho in ("luanmorenommaciel/agentspec", "obra/superpowers", "MIT", "sdd-"):
        assert trecho in texto
```

Secao nova em `vendor/CREDITS.md`, no bloco **Adaptado**: o que veio de cada
base e o que e nosso. Commit.

## T5 — superficie e referencia

`python scripts/gen_reference_docs.py`, `python scripts/check_surface_lock.py
--update` (crescimento declarado no commit), `python scripts/check_vnext_claims.py`
remediado pela lista de ids. Commit.
