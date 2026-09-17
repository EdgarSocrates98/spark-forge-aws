---
sdd: 1
feature: SDD_MIGRATION
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/SDD_MIGRATION/design.md
  sha256: "6ab8c1017a85141c0702ca3d600a61ff384b708a0a2359c71f01803f81ce0dee"
tasks:
  - id: T1
    files: [.claude/settings.json, tests/test_sdd_migration.py]
    covers: [AC1]
    test: {path: tests/test_sdd_migration.py, name: test_agentspec_desligado_no_projeto}
  - id: T2
    files: [.claude/sdd, docs/sdd/archive/agentspec, .gitignore, tests/test_sdd_migration.py]
    covers: [AC2]
    test: {path: tests/test_sdd_migration.py, name: test_historico_agentspec_arquivado}
  - id: T3
    files: [docs/superpowers/README.md, tests/test_sdd_migration.py]
    covers: [AC3]
    test: {path: tests/test_sdd_migration.py, name: test_superpowers_congelado}
  - id: T4
    files: [CLAUDE.md, AGENTS.md, CONTRIBUTING.md, tests/test_sdd_migration.py]
    covers: [AC4]
    test: {path: tests/test_sdd_migration.py, name: test_documentos_de_entrada_apontam_o_sdd}
  - id: T5
    files: [README.md, .gitignore, tests/test_sdd_migration.py]
    covers: [AC5]
    test: {path: tests/test_sdd_migration.py, name: test_readme_e_journal}
---

# SDD_MIGRATION — plano

## T1

```python
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_agentspec_desligado_no_projeto():
    config = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert config["enabledPlugins"]["agentspec@agentspec"] is False
```

Acrescentar a chave em `enabledPlugins`. Commit.

## T2

```python
def _rastreados(prefixo: str) -> list[str]:
    saida = subprocess.run(
        ["git", "ls-files", prefixo], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [linha for linha in saida.stdout.splitlines() if linha]

def test_historico_agentspec_arquivado():
    assert _rastreados(".claude/sdd") == []
    arquivados = _rastreados("docs/sdd/archive/agentspec")
    assert any(p.endswith("DESIGN_DEBATE_ROI_GATE.md") for p in arquivados)
    assert ".claude/sdd/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
```

`git rm .claude/sdd/.detected-stack.md`; `git mv .claude/sdd/archive
docs/sdd/archive/agentspec/archive` e o mesmo para `features` e `reports`;
linha `.claude/sdd/` no `.gitignore`. Se o teste rodar sem git (wheel), ele e
de arvore: `tests/test_sdd_migration.py` nao e `test_fixtures_*`, entao o gate
de wheel nao o roda. Commit.

## T3

```python
def test_superpowers_congelado():
    texto = (ROOT / "docs" / "superpowers" / "README.md").read_text(encoding="utf-8")
    assert "congelad" in texto
    assert "docs/sdd/" in texto
    assert (ROOT / "docs" / "superpowers" / "STATUS.md").is_file()
```

Commit.

## T4

```python
def test_documentos_de_entrada_apontam_o_sdd():
    for nome in ("CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md"):
        texto = (ROOT / nome).read_text(encoding="utf-8")
        assert "sdd-define" in texto, nome
        assert "sparkforge sdd check" in texto, nome
        assert "fluxo SDD em `.claude/sdd/`" not in texto, nome
```

Secao curta no `CLAUDE.md` (rodar `tests/test_bootstrap_budget.py`), paragrafo
no `AGENTS.md`, e o item de `CONTRIBUTING.md:80` reescrito. Commit.

## T5

```python
def test_readme_e_journal():
    texto = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "sdd-define" in texto and "sparkforge sdd check" in texto
    assert ".sparkforge/journal.jsonl" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
```

Secao curta no `README.md` apontando `docs/sdd/README.md`; linha no `.gitignore`
com comentario: neste repositorio o journal e dos carimbos de desenvolvimento, nao
de um case. Commit.
