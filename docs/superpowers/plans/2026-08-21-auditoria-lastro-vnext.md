# Auditoria de lastro do vNext — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provar ou remover cada alegação publicada nos 17 documentos de `docs/vnext/`, registrando o resultado num manifesto versionado e travando a reintrodução de alegação sem lastro com um gate no CI.

**Architecture:** Um script determinístico (`scripts/check_vnext_claims.py`) extrai as alegações dos documentos, compara com `docs/vnext/claims.lock.json` fail-closed nos dois sentidos e reexecuta as provas do tipo `command`. Nenhuma lista é mantida à mão: a realidade sai de comandos declarados no manifesto, no mesmo padrão de `scripts/sync_skills.py --check` e `tests/test_docs_coverage.py`.

**Tech Stack:** Python 3.10/3.11 (stdlib apenas — `argparse`, `json`, `re`, `shlex`, `subprocess`, `pathlib`, `collections.Counter`), pytest, GitHub Actions.

**Spec:** [`../specs/2026-08-21-auditoria-lastro-vnext-design.md`](../specs/2026-08-21-auditoria-lastro-vnext-design.md)

---

## Decisões que este plano fecha (as três perguntas em aberto da §9 do spec)

1. **`line` é informativa.** A comparação entre documento e manifesto é feita por multiconjunto de `(doc, type, text)`, nunca por número de linha. Editar prosa não quebra o gate; mover uma alegação de arquivo, sim — e deve mesmo.
2. **`expect` tem duas formas.** `{"kind": "number", "pattern": "...", "value": N}` extrai o primeiro grupo do padrão da saída e compara como inteiro. `{"kind": "contains", "value": "..."}` exige substring. Nada além disso.
3. **Os oito ADRs entram na mesma varredura dos nove documentos.** Sem exceção: alegação histórica que ninguém consegue provar vira `REMOVIDA` com motivo, como qualquer outra.

## File Structure

| arquivo | responsabilidade |
|---|---|
| `scripts/check_vnext_claims.py` | criar — extrator, validador de manifesto, executor de provas, seed e report. Único arquivo executável do gate. |
| `docs/vnext/claims.lock.json` | criar — manifesto de lastro. Dado, não código. |
| `tests/test_vnext_claims.py` | criar — testes do extrator e do validador contra documentos sintéticos, mais o gate real rodando verde. |
| `docs/vnext/*.md`, `docs/vnext/adrs/*.md` | modificar na Task 9 — remoção do que não tem prova. |
| `docs/superpowers/STATUS.md` | modificar na Task 10 — seção da fase vNext. |
| `.github/workflows/ci.yml` | modificar na Task 11 — passo do gate. |

Um arquivo de script só. Ele tem ~250 linhas ao fim e uma responsabilidade: dizer se `docs/vnext/` afirma algo que o repositório não sustenta. Quebrar em módulo `sparkforge/` seria mover código de gate para dentro do pacote distribuído, que não é onde os outros gates moram.

---

### Task 1: Esqueleto do script e lista de documentos auditados

**Files:**
- Create: `scripts/check_vnext_claims.py`
- Create: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vnext_claims.py
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_vnext_claims as gate  # noqa: E402


class TestDocumentosAuditados:
    def test_cobre_os_nove_documentos_e_os_oito_adrs(self):
        docs = gate.audited_docs()
        nomes = {p.name for p in docs}
        assert "FINAL-REPORT.md" in nomes
        assert "ADR-001-canonical-registry.md" in nomes
        assert len(docs) == 17

    def test_o_caminho_e_relativo_a_raiz(self):
        doc = gate.audited_docs()[0]
        assert gate.rel(doc).startswith("docs/vnext/")
        assert "\\" not in gate.rel(doc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'check_vnext_claims'`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python
"""Gate de lastro das alegações publicadas em `docs/vnext/`.

Fonte da verdade: `docs/vnext/claims.lock.json`. Toda alegação dos documentos
precisa existir no manifesto, e toda entrada do manifesto precisa existir nos
documentos -- fail-closed nos dois sentidos, pela mesma razão registrada em
`tests/test_docs_coverage.py`: lista copiada envelhece sem que nada acuse.

Uso:
    python scripts/check_vnext_claims.py           # audita; sai 1 se divergir
    python scripts/check_vnext_claims.py --full    # inclui provas `tier: slow`
    python scripts/check_vnext_claims.py --seed    # gera manifesto semente
    python scripts/check_vnext_claims.py --report  # tabela de lastro em Markdown
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VNEXT = ROOT / "docs" / "vnext"
MANIFEST = VNEXT / "claims.lock.json"
SOURCES_LOCK = ROOT / "knowledge" / "sources.lock.json"

SCHEMA_VERSION = 1
STATES = frozenset({"PROVADA", "SEM_LASTRO", "REMOVIDA"})
TYPES = frozenset({"number", "capability", "external_fact"})
TIERS = frozenset({"fast", "slow"})
PROOF_KINDS = frozenset({"command", "artifact", "source"})


def rel(path: Path) -> str:
    """Caminho relativo à raiz, sempre com `/`, para o manifesto não mudar
    conforme o sistema operacional de quem rodou o `--seed`."""
    return path.resolve().relative_to(ROOT).as_posix()


def audited_docs(root: Path = VNEXT) -> list[Path]:
    return sorted(root.glob("*.md")) + sorted((root / "adrs").glob("*.md"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Inclui provas tier slow.")
    parser.add_argument("--seed", action="store_true", help="Gera manifesto semente.")
    parser.add_argument("--report", action="store_true", help="Tabela de lastro.")
    args = parser.parse_args()
    if args.seed:
        return seed()
    if args.report:
        return report()
    return audit(include_slow=args.full)


if __name__ == "__main__":
    raise SystemExit(main())
```

As funções `seed`, `report` e `audit` chegam nas Tasks 6 a 8. Até lá o módulo importa, e é só isso que a Task 1 precisa.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 2 testes

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "feat(gate): esqueleto do gate de lastro do vNext"
```

---

### Task 2: Extração numérica com allowlist

**Files:**
- Modify: `scripts/check_vnext_claims.py`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

````python
# acrescentar em tests/test_vnext_claims.py
DOC_SINTETICO = """# Título

Este relatório declara uma economia de 81,8% no custo por mil tarefas
e 5.485 testes na suíte, em 2026-08-21, versão 0.5.0, conforme ADR-003.

Fonte: https://docs.aws.amazon.com/glue/latest/dg/release-notes-5-1.html

```python
BATCH = 1000
```
"""


class TestExtracaoNumerica:
    def _extrai(self, tmp_path):
        doc = tmp_path / "SINTETICO.md"
        doc.write_text(DOC_SINTETICO, encoding="utf-8")
        return [item["text"] for item in gate.extract_numbers(doc)]

    def test_captura_percentual_e_contagem(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert "81,8%" in textos
        assert "5.485" in textos

    def test_ignora_data_versao_e_identificador_de_adr(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert not any("2026-08-21" in t for t in textos)
        assert "0.5.0" not in textos
        assert not any("003" == t for t in textos)

    def test_ignora_bloco_de_codigo_e_linha_de_fonte(self, tmp_path):
        textos = self._extrai(tmp_path)
        assert "1000" not in textos
        assert not any("5-1" in t for t in textos)

    def test_cada_padrao_da_allowlist_declara_a_razao(self):
        for _, razao in gate.IGNORED_TOKENS:
            assert razao and len(razao) > 10
````

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: FAIL com `AttributeError: module 'check_vnext_claims' has no attribute 'extract_numbers'`

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em scripts/check_vnext_claims.py, depois de audited_docs

# Percentual, ou número com pelo menos três caracteres. O lookbehind e o
# lookahead descartam sozinhos qualquer número colado a `-` ou a letra, o que
# mata data ISO (`2026-08-21`) e identificador (`ADR-003`) sem precisar de regra.
NUMBER_RE = re.compile(r"(?<![\w.-])(\d[\d.,]*\s*%|\d[\d.,]{2,})(?![\w-])")

# Cada padrão ignorado carrega a razão. Allowlist sem razão registrada vira
# depósito de exceção conveniente, e ninguém consegue auditar depois por que
# um número deixou de ser alegação.
IGNORED_TOKENS = (
    (re.compile(r"^\d+\.\d+\.\d+$"), "versão semântica é fato de release, não alegação de resultado"),
    (re.compile(r"^(19|20)\d{2}$"), "ano de quatro dígitos é datação; o custo conhecido é mascarar uma contagem que caia em 1900-2099, e a §5 aceita esse risco por ser improvável nestes documentos"),
)


def _strip_code_blocks(text: str) -> str:
    """Zera o conteúdo de bloco cercado. Número dentro de exemplo de código é
    ilustração; auditá-lo produziria ruído sem nenhuma alegação por trás."""
    out: list[str] = []
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return "\n".join(out)


def extract_numbers(path: Path) -> list[dict]:
    text = _strip_code_blocks(path.read_text(encoding="utf-8"))
    found: list[dict] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if "http" in line:
            # Citação de fonte: o número pertence ao endereço, não ao produto.
            continue
        for match in NUMBER_RE.finditer(line):
            token = match.group(1).strip()
            if any(rx.match(token) for rx, _ in IGNORED_TOKENS):
                continue
            found.append(
                {
                    "doc": rel(path),
                    "line": lineno,
                    "text": token,
                    "context": line.strip()[:120],
                    "type": "number",
                }
            )
    return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 6 testes

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "feat(gate): extracao numerica com allowlist justificada"
```

---

### Task 3: Enumeração das alegações de capacidade

**Files:**
- Modify: `scripts/check_vnext_claims.py`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_vnext_claims.py
MATRIZ_SINTETICA = """# Matriz

| Capacidade | Estado |
|---|---|
| Compilador multi-plataforma | entregue |
| Motor de economia em 7 tiers | entregue |

Prosa solta afirmando coisas que não são linha de tabela.
"""


class TestExtracaoDeCapacidade:
    def test_le_a_primeira_celula_de_cada_linha_de_tabela(self, tmp_path):
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert "Compilador multi-plataforma" in textos
        assert "Motor de economia em 7 tiers" in textos

    def test_ignora_cabecalho_separador_e_prosa(self, tmp_path):
        (tmp_path / "CAPABILITY-MATRIX.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        textos = [c["text"] for c in gate.extract_capabilities(tmp_path)]
        assert "Capacidade" not in textos
        assert not any(set(t) <= {"-", " "} for t in textos)
        assert not any(t.startswith("Prosa") for t in textos)

    def test_o_tipo_e_capability(self, tmp_path):
        (tmp_path / "AGENT-CATALOG.md").write_text(MATRIZ_SINTETICA, encoding="utf-8")
        for claim in gate.extract_capabilities(tmp_path):
            assert claim["type"] == "capability"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -k capacidade -v`
Expected: FAIL com `AttributeError: module 'check_vnext_claims' has no attribute 'extract_capabilities'`

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em scripts/check_vnext_claims.py, depois de extract_numbers

# Alegação de capacidade sai de ESTRUTURA, nunca de prosa. Varrer prosa livre
# atrás de "o sistema faz X" produz falso positivo demais para ser gate.
CAPABILITY_TABLES = ("CAPABILITY-MATRIX.md", "AGENT-CATALOG.md")
CAPABILITY_HEADERS = frozenset({"capacidade", "capability", "agente", "agent", "componente"})


def _is_table_separator(stripped: str) -> bool:
    return set(stripped) <= set("|-: ")


def extract_capabilities(root: Path = VNEXT) -> list[dict]:
    found: list[dict] = []
    for name in CAPABILITY_TABLES:
        path = root / name
        if not path.exists():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
            stripped = line.strip()
            if not stripped.startswith("|") or _is_table_separator(stripped):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or not cells[0]:
                continue
            if cells[0].strip("*` ").lower() in CAPABILITY_HEADERS:
                continue
            found.append(
                {
                    "doc": rel(path),
                    "line": lineno,
                    "text": cells[0],
                    "context": stripped[:120],
                    "type": "capability",
                }
            )
    return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 9 testes

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "feat(gate): enumera capacidade a partir de estrutura de tabela"
```

---

### Task 4: Validação do manifesto

**Files:**
- Modify: `scripts/check_vnext_claims.py`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_vnext_claims.py
def manifesto(claims):
    return {"schema_version": 1, "extracted_from": "0" * 40, "claims": claims}


def entrada(**kwargs):
    base = {
        "id": "VNX-001",
        "doc": "docs/vnext/FINAL-REPORT.md",
        "line": 31,
        "text": "81,8%",
        "context": "economia de 81,8%",
        "type": "number",
        "state": "REMOVIDA",
        "note": "sem artefato de medição no repositório",
    }
    base.update(kwargs)
    return base


class TestValidacaoDoManifesto:
    def test_aceita_manifesto_bem_formado(self):
        assert gate.validate_manifest(manifesto([entrada()]), {}) == []

    def test_exige_note_quando_nao_e_provada(self):
        erros = gate.validate_manifest(manifesto([entrada(note="")]), {})
        assert any("exige note" in e for e in erros)

    def test_rejeita_id_repetido(self):
        erros = gate.validate_manifest(manifesto([entrada(), entrada(text="94,5%")]), {})
        assert any("id repetido" in e for e in erros)

    def test_rejeita_estado_desconhecido(self):
        erros = gate.validate_manifest(manifesto([entrada(state="TALVEZ")]), {})
        assert any("state" in e for e in erros)

    def test_rejeita_proof_fora_de_provada(self):
        prova = {"kind": "source", "source_id": "x"}
        erros = gate.validate_manifest(manifesto([entrada(proof=prova)]), {})
        assert any("proof só é aceita em PROVADA" in e for e in erros)

    def test_rejeita_schema_version_diferente(self):
        m = manifesto([entrada()])
        m["schema_version"] = 2
        erros = gate.validate_manifest(m, {})
        assert any("schema_version" in e for e in erros)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -k Validacao -v`
Expected: FAIL com `AttributeError: module 'check_vnext_claims' has no attribute 'validate_manifest'`

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em scripts/check_vnext_claims.py, depois de extract_capabilities

ID_RE = re.compile(r"^VNX-\d{3}$")


def validate_manifest(manifest: dict, sources: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version deve ser {SCHEMA_VERSION}, veio {manifest.get('schema_version')!r}"
        )
    seen: set[str] = set()
    for entry in manifest.get("claims", []):
        cid = entry.get("id", "<sem id>")
        if not ID_RE.match(str(cid)):
            errors.append(f"{cid}: id fora do formato VNX-NNN")
        if cid in seen:
            errors.append(f"{cid}: id repetido")
        seen.add(cid)
        if entry.get("type") not in TYPES:
            errors.append(f"{cid}: type desconhecido: {entry.get('type')!r}")
        state = entry.get("state")
        if state not in STATES:
            errors.append(f"{cid}: state desconhecido: {state!r}")
            continue
        if state == "PROVADA":
            errors.extend(_validate_proof(entry, sources))
        else:
            if not entry.get("note"):
                errors.append(f"{cid}: state {state} exige note com o motivo")
            if entry.get("proof"):
                errors.append(f"{cid}: proof só é aceita em PROVADA")
    return errors
```

- [ ] **Step 4: Run test to verify it fails no ponto seguinte**

Run: `python -m pytest tests/test_vnext_claims.py -k Validacao -v`
Expected: FAIL com `AttributeError: ... has no attribute '_validate_proof'` — a Task 5 fecha isso. Se preferir ver a Task 4 verde antes de seguir, acrescente temporariamente `def _validate_proof(entry, sources): return []` e substitua na Task 5.

- [ ] **Step 5: Commit (junto com a Task 5)**

A validação de manifesto e a de prova formam uma unidade; commite as duas juntas ao fim da Task 5.

---

### Task 5: Validação da prova, com as duas restrições que dão sentido ao tipo

**Files:**
- Modify: `scripts/check_vnext_claims.py`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_vnext_claims.py
class TestValidacaoDaProva:
    def test_artifact_nao_prova_numero(self):
        prova = {"kind": "artifact", "path": "scripts/check_vnext_claims.py", "test": "tests/test_vnext_claims.py"}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="number")]), {}
        )
        assert any("artifact não prova alegação numérica" in e for e in erros)

    def test_artifact_prova_capacidade_quando_path_e_test_existem(self):
        prova = {
            "kind": "artifact",
            "path": "scripts/check_vnext_claims.py",
            "symbol": "audited_docs",
            "test": "tests/test_vnext_claims.py",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="capability")]), {}
        )
        assert erros == []

    def test_artifact_com_path_inexistente_falha(self):
        prova = {"kind": "artifact", "path": "nao/existe.py", "test": "tests/test_vnext_claims.py"}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="capability")]), {}
        )
        assert any("proof.path inexistente" in e for e in erros)

    def test_artifact_cujo_teste_nao_cita_o_simbolo_falha(self):
        prova = {
            "kind": "artifact",
            "path": "scripts/check_vnext_claims.py",
            "symbol": "funcao_que_ninguem_testa",
            "test": "tests/test_vnext_claims.py",
        }
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="capability")]), {}
        )
        assert any("não referencia" in e for e in erros)

    def test_source_exige_id_presente_no_sources_lock(self):
        prova = {"kind": "source", "source_id": "https://exemplo/invalido"}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="external_fact")]),
            {"https://exemplo/valido": {}},
        )
        assert any("fora de knowledge/sources.lock.json" in e for e in erros)

    def test_external_fact_so_aceita_source(self):
        prova = {"kind": "command", "cmd": "python -c \"print(1)\"", "tier": "fast",
                 "expect": {"kind": "contains", "value": "1"}}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="external_fact")]), {}
        )
        assert any("external_fact exige proof source" in e for e in erros)

    def test_command_exige_tier_valido(self):
        prova = {"kind": "command", "cmd": "python -c \"print(1)\"", "tier": "medio",
                 "expect": {"kind": "contains", "value": "1"}}
        erros = gate.validate_manifest(
            manifesto([entrada(state="PROVADA", note="", proof=prova, type="number")]), {}
        )
        assert any("tier" in e for e in erros)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -k Prova -v`
Expected: FAIL — sete testes falhando

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em scripts/check_vnext_claims.py, depois de validate_manifest

EXPECT_KINDS = frozenset({"number", "contains"})


def _validate_proof(entry: dict, sources: dict) -> list[str]:
    cid = entry.get("id", "<sem id>")
    proof = entry.get("proof")
    if not isinstance(proof, dict):
        return [f"{cid}: PROVADA sem proof"]
    kind = proof.get("kind")
    if kind not in PROOF_KINDS:
        return [f"{cid}: proof.kind desconhecido: {kind!r}"]

    errors: list[str] = []
    claim_type = entry.get("type")
    if claim_type == "external_fact" and kind != "source":
        # Versão de serviço e feature de spec se provam por documentação
        # oficial versionada, mecanismo que o repositório já opera.
        errors.append(f"{cid}: external_fact exige proof source")

    if kind == "artifact":
        if claim_type == "number":
            # Apontar o código do cache não prova o percentual de cache hit.
            errors.append(f"{cid}: proof artifact não prova alegação numérica")
        path = proof.get("path", "")
        if not path or not (ROOT / path).exists():
            errors.append(f"{cid}: proof.path inexistente: {path!r}")
        test = proof.get("test", "")
        test_path = ROOT / test if test else None
        if not test or not test_path.exists():
            errors.append(f"{cid}: proof.test inexistente: {test!r}")
        elif proof.get("symbol") and proof["symbol"] not in test_path.read_text(encoding="utf-8"):
            errors.append(f"{cid}: proof.test não referencia {proof['symbol']}")
    elif kind == "source":
        if proof.get("source_id") not in sources:
            errors.append(f"{cid}: source_id fora de knowledge/sources.lock.json: {proof.get('source_id')!r}")
    else:
        if not proof.get("cmd"):
            errors.append(f"{cid}: proof command sem cmd")
        if proof.get("tier") not in TIERS:
            errors.append(f"{cid}: proof.tier deve ser fast ou slow, veio {proof.get('tier')!r}")
        expect = proof.get("expect") or {}
        if expect.get("kind") not in EXPECT_KINDS:
            errors.append(f"{cid}: expect.kind deve ser number ou contains")
        elif expect["kind"] == "number" and not expect.get("pattern"):
            errors.append(f"{cid}: expect number exige pattern com um grupo de captura")
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 22 testes

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "feat(gate): valida manifesto e prova tipada de lastro"
```

---

### Task 6: Órfãos nos dois sentidos e execução das provas `command`

**Files:**
- Modify: `scripts/check_vnext_claims.py`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_vnext_claims.py
class TestOrfaos:
    def _achado(self, text="81,8%", doc="docs/vnext/FINAL-REPORT.md"):
        return {"doc": doc, "line": 1, "text": text, "context": "", "type": "number"}

    def test_alegacao_sem_entrada_no_manifesto_falha(self):
        erros = gate.check_orphans([self._achado()], manifesto([]))
        assert any("sem entrada no manifesto" in e for e in erros)

    def test_entrada_sem_alegacao_no_documento_falha(self):
        erros = gate.check_orphans([], manifesto([entrada(state="SEM_LASTRO", note="pendente")]))
        assert any("órfã no manifesto" in e for e in erros)

    def test_removida_nao_conta_como_orfa(self):
        erros = gate.check_orphans([], manifesto([entrada()]))
        assert erros == []

    def test_removida_que_reaparece_no_documento_falha(self):
        erros = gate.check_orphans([self._achado()], manifesto([entrada()]))
        assert any("marcada REMOVIDA ainda aparece" in e for e in erros)


class TestProvasCommand:
    def _com_prova(self, cmd, expect, tier="fast"):
        prova = {"kind": "command", "cmd": cmd, "tier": tier, "expect": expect}
        return manifesto([entrada(state="PROVADA", note="", proof=prova, type="number")])

    def test_prova_que_reproduz_passa(self):
        m = self._com_prova(
            'python -c "print(41, \'tools\')"',
            {"kind": "number", "pattern": r"(\d+) tools", "value": 41},
        )
        assert gate.run_command_proofs(m, include_slow=False) == []

    def test_prova_que_nao_reproduz_falha_com_os_dois_valores(self):
        m = self._com_prova(
            'python -c "print(5447, \'tests\')"',
            {"kind": "number", "pattern": r"(\d+) tests", "value": 5485},
        )
        erros = gate.run_command_proofs(m, include_slow=False)
        assert any("esperado 5485, obtido 5447" in e for e in erros)

    def test_tier_slow_nao_roda_por_padrao(self):
        m = self._com_prova(
            "comando-que-nao-existe-em-lugar-nenhum",
            {"kind": "contains", "value": "nada"},
            tier="slow",
        )
        assert gate.run_command_proofs(m, include_slow=False) == []
        assert gate.run_command_proofs(m, include_slow=True) != []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -k "Orfaos or ProvasCommand" -v`
Expected: FAIL com `AttributeError: ... has no attribute 'check_orphans'`

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em scripts/check_vnext_claims.py, depois de _validate_proof


def collect_claims(root: Path = VNEXT) -> list[dict]:
    found: list[dict] = []
    for path in audited_docs(root):
        found.extend(extract_numbers(path))
    found.extend(extract_capabilities(root))
    return found


def claim_key(entry: dict) -> tuple[str, str, str]:
    """A chave ignora `line` de propósito: editar prosa não deve quebrar o
    gate, mas mover uma alegação de documento deve."""
    return (entry["doc"], entry["type"], entry["text"])


def check_orphans(found: list[dict], manifest: dict) -> list[str]:
    claims = manifest.get("claims", [])
    in_docs = Counter(claim_key(item) for item in found)
    in_manifest = Counter(claim_key(c) for c in claims if c.get("state") != "REMOVIDA")
    removed = {claim_key(c) for c in claims if c.get("state") == "REMOVIDA"}

    errors: list[str] = []
    for key, count in (in_docs - in_manifest).items():
        if key in removed:
            errors.append(f"alegação marcada REMOVIDA ainda aparece no documento: {key[0]} :: {key[2]}")
        else:
            errors.append(f"alegação sem entrada no manifesto ({count}x): {key[0]} :: {key[2]}")
    for key, count in (in_manifest - in_docs).items():
        errors.append(f"entrada órfã no manifesto ({count}x): {key[0]} :: {key[2]}")
    return errors


def run_command_proofs(manifest: dict, include_slow: bool) -> list[str]:
    errors: list[str] = []
    for entry in manifest.get("claims", []):
        proof = entry.get("proof") or {}
        if proof.get("kind") != "command":
            continue
        if proof.get("tier") == "slow" and not include_slow:
            continue
        cid = entry.get("id", "<sem id>")
        try:
            completed = subprocess.run(
                shlex.split(proof["cmd"]),
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=900,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{cid}: prova command não executou: {exc}")
            continue
        output = completed.stdout + completed.stderr
        expect = proof.get("expect") or {}
        if expect.get("kind") == "contains":
            if expect.get("value") not in output:
                errors.append(f"{cid}: saída não contém {expect.get('value')!r}")
            continue
        match = re.search(expect.get("pattern", ""), output)
        if not match:
            errors.append(f"{cid}: padrão {expect.get('pattern')!r} não casou na saída")
        elif int(match.group(1)) != expect.get("value"):
            errors.append(
                f"{cid}: prova command não reproduz — esperado {expect.get('value')}, "
                f"obtido {int(match.group(1))}"
            )
    return errors
```

`shlex.split` em vez de `shell=True`: o comando vem de arquivo versionado e revisado, mas gate que executa string pelo shell é superfície de execução gratuita, e nenhuma prova precisa de pipe.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 29 testes

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "feat(gate): orfaos nos dois sentidos e execucao de prova command"
```

---

### Task 7: `--seed`, `--report` e `audit`

**Files:**
- Modify: `scripts/check_vnext_claims.py`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_vnext_claims.py
class TestSuperficie:
    def test_seed_produz_uma_entrada_por_alegacao_em_sem_lastro(self, tmp_path, monkeypatch):
        (tmp_path / "adrs").mkdir()
        (tmp_path / "UM.md").write_text("Economia de 81,8% e 5.485 testes.\n", encoding="utf-8")
        destino = tmp_path / "claims.lock.json"
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.seed() == 0
        dados = json.loads(destino.read_text(encoding="utf-8"))
        assert dados["schema_version"] == 1
        assert len(dados["claims"]) == 2
        assert {c["state"] for c in dados["claims"]} == {"SEM_LASTRO"}
        assert [c["id"] for c in dados["claims"]] == ["VNX-001", "VNX-002"]

    def test_report_emite_uma_linha_por_alegacao(self, tmp_path, monkeypatch, capsys):
        destino = tmp_path / "claims.lock.json"
        destino.write_text(json.dumps(manifesto([entrada()])), encoding="utf-8")
        monkeypatch.setattr(gate, "MANIFEST", destino)
        assert gate.report() == 0
        saida = capsys.readouterr().out
        assert "VNX-001" in saida
        assert "REMOVIDA" in saida
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -k Superficie -v`
Expected: FAIL com `AttributeError: ... has no attribute 'seed'`

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em scripts/check_vnext_claims.py, depois de run_command_proofs


def _head_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return "desconhecido"
    return completed.stdout.strip() or "desconhecido"


def load_manifest(path: Path | None = None) -> dict:
    return json.loads((path or MANIFEST).read_text(encoding="utf-8"))


def _load_sources() -> dict:
    return json.loads(SOURCES_LOCK.read_text(encoding="utf-8"))["sources"]


def seed() -> int:
    claims = []
    for index, item in enumerate(collect_claims(VNEXT), start=1):
        entry = dict(item)
        entry["id"] = f"VNX-{index:03d}"
        entry["state"] = "SEM_LASTRO"
        entry["note"] = "classificação pendente"
        claims.append(entry)
    payload = {"schema_version": SCHEMA_VERSION, "extracted_from": _head_commit(), "claims": claims}
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Semente com {len(claims)} alegação(ões) em {rel(MANIFEST)}")
    return 0


def report() -> int:
    manifest = load_manifest()
    print("| id | documento | tipo | estado | prova |")
    print("|---|---|---|---|---|")
    for entry in manifest.get("claims", []):
        proof = entry.get("proof") or {}
        prova = proof.get("kind", "—")
        if prova == "command":
            prova = f"command `{proof.get('cmd')}`"
        elif prova == "artifact":
            prova = f"artifact `{proof.get('path')}`"
        elif prova == "source":
            prova = f"source `{proof.get('source_id')}`"
        print(f"| {entry['id']} | {entry['doc']} | {entry['type']} | {entry['state']} | {prova} |")
    return 0


def audit(include_slow: bool) -> int:
    manifest = load_manifest()
    errors = validate_manifest(manifest, _load_sources())
    errors += check_orphans(collect_claims(VNEXT), manifest)
    errors += run_command_proofs(manifest, include_slow)
    for error in errors:
        print(error)
    print(f"{len(errors)} divergência(s).")
    return 1 if errors else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 31 testes

- [ ] **Step 5: Commit**

```bash
git add scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "feat(gate): seed, report e auditoria completa"
```

---

### Task 8: Manifesto semente sobre os documentos reais

**Files:**
- Create: `docs/vnext/claims.lock.json`

- [ ] **Step 1: Gerar a semente**

Run: `python scripts/check_vnext_claims.py --seed`
Expected: `Semente com N alegação(ões) em docs/vnext/claims.lock.json`, com N entre 60 e 120. Medição anterior à extração: ~85 ocorrências numéricas brutas nos 17 arquivos, antes da allowlist.

- [ ] **Step 2: Conferir que a extração não capturou lixo**

Run: `python -c "import json,io; d=json.load(io.open('docs/vnext/claims.lock.json',encoding='utf-8')); [print(c['id'], c['doc'], '::', c['text'], '::', c['context'][:60]) for c in d['claims']]"`

Leia a saída inteira. Todo item que for evidentemente ruído (número de seção, contagem de coluna de tabela, numeração de lista) indica padrão faltando na allowlist. Nesse caso: acrescente o padrão em `IGNORED_TOKENS` **com a razão escrita**, acrescente um caso no `TestExtracaoNumerica` que prove o novo padrão sendo ignorado, e rode `--seed` de novo.

- [ ] **Step 3: Verificar que o gate acusa o estado inicial**

Run: `python scripts/check_vnext_claims.py`
Expected: exit 0 — o manifesto semente é consistente com os documentos, e toda entrada está em `SEM_LASTRO` com `note`. Nenhuma prova roda ainda porque nenhuma existe.

- [ ] **Step 4: Commit**

```bash
git add docs/vnext/claims.lock.json scripts/check_vnext_claims.py tests/test_vnext_claims.py
git commit -m "chore(vnext): manifesto semente com as alegacoes extraidas"
```

---

### Task 9: Classificar cada alegação e corrigir os documentos

Esta é a tarefa de conteúdo. Ela não inventa código: usa os seis derivadores abaixo, todos medidos e funcionando nesta data.

**Files:**
- Modify: `docs/vnext/claims.lock.json`
- Modify: `docs/vnext/*.md`, `docs/vnext/adrs/*.md` (conforme a classificação)

- [ ] **Step 1: Escrever as provas `command` derivadas**

Para cada alegação de contagem, use o derivador correspondente. Valores medidos em 2026-08-21, na branch `feat/fase6b-sf-cfg`:

| o que | `cmd` | `expect` | medido | `tier` |
|---|---|---|---|---|
| testes coletados | `python -m pytest --collect-only -q` | `{"kind":"number","pattern":"(\\d+) tests collected","value":5505}` | 5505, em 17,5 s | `fast` |
| coordenadores | `python -c "import pathlib;print(len(list(pathlib.Path('agents').glob('*.md'))), 'coordenadores')"` | `{"kind":"number","pattern":"(\\d+) coordenadores","value":38}` | 38 | `fast` |
| executores | `python -c "import pathlib;print(len(list(pathlib.Path('agents/executors').glob('*.md'))), 'executores')"` | `{"kind":"number","pattern":"(\\d+) executores","value":5}` | 5 | `fast` |
| skills | `python -c "import pathlib;print(len(list(pathlib.Path('skills').glob('*/SKILL.md'))), 'skills')"` | `{"kind":"number","pattern":"(\\d+) skills","value":40}` | 40 | `fast` |
| tools MCP | `python -c "from sparkforge.adapters.tools import TOOLS; print(len(TOOLS), 'tools')"` | `{"kind":"number","pattern":"(\\d+) tools","value":41}` | 41 | `fast` |
| regras | `python -c "from sparkforge.rules.loader import load_catalog; print(len(load_catalog()), 'regras')"` | `{"kind":"number","pattern":"(\\d+) regras","value":116}` | 116 | `fast` |

Atenção ao primeiro: `--collect-only` conta teste **coletado**, não teste **passando**. Se o documento afirma "testes passando", ou o texto do documento muda para "coletados", ou a prova vira `python -m pytest -q` com `tier: slow`. Não existe terceira saída — a suíte completa passou de 600 s nesta sessão, e prova de 600 s não roda no gate padrão.

- [ ] **Step 2: Classificar as alegações de capacidade**

Cada entrada `type: capability` recebe `proof artifact` com `path` do módulo que a implementa, `symbol` da função ou classe central e `test` do arquivo que a exercita. Exemplo real do repositório:

```json
{
  "id": "VNX-042",
  "doc": "docs/vnext/CAPABILITY-MATRIX.md",
  "line": 12,
  "text": "Compilador multi-plataforma",
  "context": "| Compilador multi-plataforma | entregue |",
  "type": "capability",
  "state": "PROVADA",
  "proof": {
    "kind": "artifact",
    "path": "sparkforge/adapters/platforms/compiler.py",
    "symbol": "compile",
    "test": "tests/test_platform_compilers.py"
  }
}
```

Se o teste apontado não referencia o símbolo, o gate acusa. Se não existe teste que exercite a capacidade, ela **não** é `PROVADA`: vira `REMOVIDA` com `note` dizendo que o módulo existe mas nada prova o comportamento, ou o autor escreve o teste — e aí vira outra tarefa, fora deste plano.

- [ ] **Step 3: Classificar os cinco KPIs do `FINAL-REPORT.md` §3**

`Task Success Rate 100%`, `Median Tokens / Deterministic Task 0`, `Median Tokens / Specialist Task -78,8%`, `Estimated Cost / 1k Tasks -81,8%`, `Cache Hit Rate 94,5%`.

Para cada um, procure no repositório qualquer comando que produza o número. Se não existir, a entrada vira:

```json
{
  "state": "REMOVIDA",
  "note": "a5b9e96 não commitou artefato de medição; nenhum comando no repositório produz este número. Reabrir quando o motor de medição de token/custo/cache existir."
}
```

e a linha correspondente sai da tabela do `FINAL-REPORT.md`. A tabela inteira sai se todas as linhas caírem — tabela vazia com cabeçalho é pior que ausência.

- [ ] **Step 4: Rodar o gate até ficar verde**

Run: `python scripts/check_vnext_claims.py`
Expected: `0 divergência(s).`, exit 0

Enquanto houver `SEM_LASTRO` no manifesto o gate ainda passa (é estado válido), então confira também:

Run: `python -c "import json,io; d=json.load(io.open('docs/vnext/claims.lock.json',encoding='utf-8')); print(sum(1 for c in d['claims'] if c['state']=='SEM_LASTRO'), 'pendentes')"`
Expected: `0 pendentes`

- [ ] **Step 5: Gerar a tabela de lastro**

Run: `python scripts/check_vnext_claims.py --report > docs/vnext/LASTRO.md`

Acrescente à mão, no topo do arquivo gerado, uma linha dizendo que o arquivo é gerado por `--report` e não deve ser editado.

- [ ] **Step 6: Commit**

```bash
git add docs/vnext/
git commit -m "docs(vnext): classifica cada alegacao e remove o que nao tem lastro"
```

---

### Task 10: Seção da fase vNext no `STATUS.md`

**Files:**
- Modify: `docs/superpowers/STATUS.md`

- [ ] **Step 1: Conferir os números correntes**

Run: `python scripts/check_vnext_claims.py --full`
Expected: `0 divergência(s).` — inclui as provas `tier: slow`, se alguma existir.

Colete os valores das provas `command` do manifesto. Eles, e só eles, entram no `STATUS.md`. Nada é copiado do `FINAL-REPORT.md`.

- [ ] **Step 2: Escrever a seção**

Acrescente ao `STATUS.md`, na lista de fases, uma seção no formato das existentes:

```markdown
### Fase vNext — Agent Factory: registro canônico, economia e compilador — **PARCIAL** (2026-08-21)

Commit `a5b9e96` acrescentou `sparkforge/{registry,economy,context,workflows,evals,observability,providers}`
e os módulos de domínio `migration`, `lakeformation`, `iceberg`, `errors`,
`databases`, `streaming`, `terraform`, `reliability`. Os sete primeiros têm teste
que os exercita; os oito de domínio somam menos de 1200 linhas e cobrem uma
fração do que `docs/vnext/ARCHITECTURE.md` descreve — por isso **PARCIAL**.

A auditoria de lastro de 2026-08-21 (spec `specs/2026-08-21-auditoria-lastro-vnext-design.md`)
classificou toda alegação de `docs/vnext/` em `docs/vnext/claims.lock.json`. Os
KPIs de economia declarados no `FINAL-REPORT.md` original foram removidos: nenhum
comando do repositório os produzia. O gate `scripts/check_vnext_claims.py` impede
a reintrodução.

Números desta data, cada um derivado por comando declarado no manifesto:

| Dimensão | Valor | Prova |
|---|---|---|
| Testes coletados | (valor da prova) | `python -m pytest --collect-only -q` |
| Coordenadores | (valor da prova) | glob em `agents/*.md` |
| Executores | (valor da prova) | glob em `agents/executors/*.md` |
| Skills | (valor da prova) | glob em `skills/*/SKILL.md` |
| Tools MCP | (valor da prova) | `len(sparkforge.adapters.tools.TOOLS)` |
| Regras | (valor da prova) | `len(load_catalog())` |
```

Substitua cada `(valor da prova)` pelo número que a prova correspondente produziu no Step 1. Se algum divergir da tabela **Números correntes** no topo do `STATUS.md`, atualize também aquela tabela — as duas não podem discordar dentro do mesmo arquivo.

- [ ] **Step 3: Conferir que nada quebrou nos testes de documentação**

Run: `python -m pytest tests/test_docs_coverage.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/STATUS.md
git commit -m "docs(status): registra a fase vNext com numeros derivados"
```

---

### Task 11: Ligar o gate no CI e provar que ele barra reincidência

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_vnext_claims.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_vnext_claims.py
class TestGateReal:
    def test_o_manifesto_do_repositorio_esta_consistente(self):
        manifest = gate.load_manifest()
        assert gate.validate_manifest(manifest, gate._load_sources()) == []
        assert gate.check_orphans(gate.collect_claims(), manifest) == []

    def test_nenhuma_alegacao_ficou_pendente(self):
        estados = {c["state"] for c in gate.load_manifest()["claims"]}
        assert "SEM_LASTRO" not in estados

    def test_alegacao_reintroduzida_no_documento_derruba_o_gate(self, tmp_path, monkeypatch):
        (tmp_path / "adrs").mkdir()
        (tmp_path / "NOVO.md").write_text("Ganho de 99,9% em tudo.\n", encoding="utf-8")
        monkeypatch.setattr(gate, "VNEXT", tmp_path)
        erros = gate.check_orphans(gate.collect_claims(tmp_path), manifesto([]))
        assert any("sem entrada no manifesto" in e for e in erros)

    def test_o_gate_roda_no_ci(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "scripts/check_vnext_claims.py" in ci
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vnext_claims.py -k GateReal -v`
Expected: FAIL em `test_o_gate_roda_no_ci` com `AssertionError`; os três primeiros já passam se as Tasks 9 e 10 foram concluídas.

- [ ] **Step 3: Write minimal implementation**

Em `.github/workflows/ci.yml`, no job `test`, depois do passo `Eval corpus consistency`:

```yaml
      - name: vNext claims lastro
        run: python scripts/check_vnext_claims.py
```

O passo usa o modo padrão, que não roda prova `tier: slow`. Se alguma prova `slow` for criada no futuro, ela ganha job próprio — não entra aqui.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vnext_claims.py -v`
Expected: PASS, 35 testes

- [ ] **Step 5: Rodar tudo**

Run: `python -m ruff check sparkforge scripts tests`
Expected: sem violação

Run: `python scripts/check_vnext_claims.py`
Expected: `0 divergência(s).`, exit 0

Run: `python -m pytest -q`
Expected: PASS. A suíte passa de 600 s; rode em background e confira o resultado antes do commit final.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml tests/test_vnext_claims.py
git commit -m "ci: liga o gate de lastro do vNext"
```

---

## Cobertura do spec

| seção do spec | tarefa que a implementa |
|---|---|
| §1 contexto, §2 objetivo | Tasks 8 a 10 |
| §3 D-1 manifesto separado | Task 8 |
| §3 D-2 prova tipada e as duas restrições | Task 5 |
| §3 D-3 `tier` | Tasks 5 e 6 |
| §3 D-4 fail-closed nos dois sentidos | Task 6 |
| §3 D-5 `REMOVIDA` conserva rastro | Tasks 6 e 9 |
| §3 D-6 relatório gerado | Tasks 7 e 9 |
| §4 formato do manifesto | Tasks 4, 5 e 7 |
| §5 extrator e allowlist | Tasks 2, 3 e 8 |
| §6 superfície | Tasks 1 e 7 |
| §7 fluxo da auditoria | Tasks 8, 9 e 10 |
| §8 testes | Tasks 2 a 7 e 11 |
| §9 perguntas em aberto | fechadas no topo deste plano |
| §10 critérios de conclusão | Task 11, Step 5 |
