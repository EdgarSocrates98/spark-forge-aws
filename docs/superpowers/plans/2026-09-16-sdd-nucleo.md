# SDD próprio — núcleo determinístico: plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** entregar `sparkforge sdd check|status|stamp` (CLI + MCP), que confere o frontmatter dos artefatos de spec em `docs/sdd/<FEATURE>/<phase>.md` e recusa por nome o que não fecha.

**Architecture:** módulo puro `sparkforge/sdd/` (`load.py` lê, `checks.py` julga com JSON Schema + gates por fase, `status.py` resume, `stamp.py` grava o sha256 do upstream). `_core` embrulha, a CLI e o registro `TOOLS` expõem. Nada chama modelo (regra 23).

**Tech Stack:** Python ≥3.10, PyYAML, jsonschema (Draft 2020-12), pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-sdd-nucleo-design.md`.

> **Execução:** feita em 2026-09-16; onde ela divergiu deste plano está no §13 do spec.

---

## Antes de começar

- Branch: `sdd/nucleo-spec` (já existe, a partir de `origin/main`).
- **Mira py310.** Nada de `datetime.UTC`, `tomllib`, `typing.Self`, `StrEnum`.
- **Nunca escreva arquivo de texto com `Path.write_text` em código do pacote que o
  usuário relê por hash**: no Windows ele troca `\n` por `\r\n`. O `stamp` usa
  `write_atomic_bytes` (Task 1).
- `.claude/agents/README.md` não rastreado: copie para o scratchpad antes de rodar
  `scripts/sync_skills.py` ou `tests/test_agents_parity.py`, e devolva depois.
- Commits: `git commit -F <arquivo>` (mensagem num arquivo temporário), terminando com
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- Todos os testes novos moram em **um** arquivo, `tests/test_sdd.py` (a pasta
  `tests/` não é pacote, então não há helper importável entre arquivos). Ele cai no
  lote `g-z` de `tests/test_suite_batches.py` sem mudança em `LOTES`.
- **Imports sobem para o topo.** Cada task mostra os imports junto dos testes que
  os usam; ao colar, mova-os para o bloco de imports de `tests/test_sdd.py` (o
  ruff do projeto cobra `E402`). Na Task 4, `_dump` usa `re`, importado na Task 3.

## Mapa de arquivos

| arquivo | ação | responsabilidade |
|---|---|---|
| `sparkforge/durable.py` | modificar | `write_atomic_bytes`, quarta primitiva |
| `sparkforge/sdd/__init__.py` | criar | `PHASES`, `DEFAULT_ROOT` |
| `sparkforge/sdd/load.py` | criar | frontmatter → `Artifact`; `discover` |
| `sparkforge/sdd/schema/*.json` | criar | um schema por fase + `common.json` |
| `sparkforge/sdd/change_kinds.yaml` | criar | tipo de mudança → seção → registros |
| `sparkforge/sdd/checks.py` | criar | `check()` e os gates |
| `sparkforge/sdd/status.py` | criar | `status()` |
| `sparkforge/sdd/stamp.py` | criar | `stamp()` e `StampError` |
| `sparkforge/adapters/_core.py` | modificar | `sdd_check`, `sdd_status`, `sdd_stamp` |
| `sparkforge/adapters/cli.py` | modificar | verbo `sdd` e despacho |
| `sparkforge/adapters/tools.py` | modificar | 3 entradas em `TOOLS`, handlers, schemas de saída |
| `sparkforge/journal/record.py` | modificar | `sparkforge_sdd_stamp` declara `path` |
| `tests/test_sdd.py` | criar | tudo do núcleo |
| `tests/test_durable.py` | modificar | teste da primitiva nova |
| registros (Task 13) | modificar | listas literais, `parity.yaml`, `manifest.json`, coordenador |
| `CLAUDE.md`, `docs/surface.lock.json`, `docs/guia/referencia/` | modificar | Task 14 |

---

### Task 1: `write_atomic_bytes`

**Files:**
- Modify: `sparkforge/durable.py` (docstring do módulo e depois de `write_atomic`, linha ~65)
- Test: `tests/test_durable.py`

- [ ] **Step 1: teste que falha** — acrescentar ao fim de `tests/test_durable.py`:

```python
def test_write_atomic_bytes_preserva_quebra_de_linha(tmp_path):
    from sparkforge.durable import write_atomic_bytes

    alvo = tmp_path / "sub" / "a.md"
    write_atomic_bytes(alvo, b"um\ndois\r\ntres\n")
    assert alvo.read_bytes() == b"um\ndois\r\ntres\n"
    write_atomic_bytes(alvo, b"novo\n")
    assert alvo.read_bytes() == b"novo\n"
    assert [p.name for p in alvo.parent.iterdir()] == ["a.md"]
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_durable.py -k write_atomic_bytes -q`
Expected: FAIL com `ImportError: cannot import name 'write_atomic_bytes'`

- [ ] **Step 3: implementar** — em `sparkforge/durable.py`, logo depois de `write_atomic`:

```python
def write_atomic_bytes(path: Path | str, data: bytes) -> None:
    """`write_atomic` sem traducao de quebra de linha: grava os bytes como vieram.

    `write_atomic` abre em modo texto, e no Windows isso troca `\\n` por
    `\\r\\n`. Para quem rele o arquivo por hash (o `sdd stamp`), a troca muda o
    conteudo que o proprio hash descreve.
    """
    destino = Path(path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(
        prefix=f".{destino.name}.", suffix=".tmp", dir=destino.parent
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _replace(temporario, destino)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporario)
        raise
```

E na docstring do módulo, trocar `Tres primitivas, e so tres,` por `Quatro primitivas, e so quatro,` e acrescentar depois do item de `write_atomic`:

```
- `write_atomic_bytes` e a mesma troca em modo binario, para arquivo que alguem
  rele por hash e cuja quebra de linha nao pode mudar na gravacao.
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_durable.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/durable.py tests/test_durable.py
git commit -F <msg>   # "feat(durable): write_atomic_bytes keeps line endings as given"
```

---

### Task 2: pacote `sdd` e leitura de artefato

**Files:**
- Create: `sparkforge/sdd/__init__.py`, `sparkforge/sdd/load.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham** — criar `tests/test_sdd.py`:

```python
"""Nucleo do SDD proprio: contrato conferivel e gates com nome.

Nenhuma fixture estatica: hash de upstream gravado em arquivo versionado e o caso
que o checkout do Windows com `core.autocrlf=true` ja quebrou (PR #63). Toda
feature e montada em `tmp_path`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.load import discover, load_artifact, split_frontmatter


def test_fases_e_raiz_padrao():
    assert PHASES == ("explore", "define", "design", "plan", "build_report", "ship")
    assert DEFAULT_ROOT == "docs/sdd"


def test_split_frontmatter_separa_bloco_e_corpo():
    bloco, corpo = split_frontmatter("---\na: 1\n---\ncorpo\n")
    assert bloco == "a: 1\n"
    assert corpo == "corpo\n"


def test_split_frontmatter_sem_cerca_devolve_none():
    assert split_frontmatter("a: 1\n") == (None, "a: 1\n")
    assert split_frontmatter("---\na: 1\n")[0] is None


def test_load_artifact_yaml_quebrado_diz_a_linha(tmp_path):
    arquivo = tmp_path / "define.md"
    arquivo.write_bytes(b"---\nsdd: 1\nfeature: [\n---\n")
    artefato = load_artifact(arquivo)
    assert artefato.meta is None
    assert "YAML invalido" in artefato.error
    assert "linha" in artefato.error


def test_load_artifact_nao_mapeamento(tmp_path):
    arquivo = tmp_path / "define.md"
    arquivo.write_bytes(b"---\n- a\n---\n")
    assert load_artifact(arquivo).error == "frontmatter precisa ser um mapeamento YAML"


def test_discover_so_pega_fase_na_profundidade_certa(tmp_path):
    raiz = tmp_path / "docs" / "sdd"
    (raiz / "F1").mkdir(parents=True)
    (raiz / "F1" / "define.md").write_bytes(b"---\n---\n")
    (raiz / "F1" / "notas.md").write_bytes(b"x")
    (raiz / "templates").mkdir()
    (raiz / "archive" / "F0").mkdir(parents=True)
    (raiz / "archive" / "F0" / "define.md").write_bytes(b"x")
    assert discover(raiz) == {"F1": {"define": raiz / "F1" / "define.md"}}
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.sdd'`

- [ ] **Step 3: implementar**

`sparkforge/sdd/__init__.py`:

```python
"""SDD proprio do SparkForge: contrato conferivel dos artefatos de spec.

Logica pura. Nada aqui chama modelo (regra 23): o agente escreve o artefato, o
pacote confere o que da para conferir e recusa por nome o resto. O corpo em
prosa nunca e julgado.
"""

from __future__ import annotations

PHASES: tuple[str, ...] = ("explore", "define", "design", "plan", "build_report", "ship")
DEFAULT_ROOT = "docs/sdd"
```

`sparkforge/sdd/load.py`:

```python
"""Le um artefato SDD: frontmatter YAML conferivel, corpo livre."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from sparkforge.facts.scan import iter_source_files
from sparkforge.sdd import PHASES

CERCA = "---"


@dataclass(frozen=True)
class Artifact:
    path: Path
    meta: dict[str, Any] | None
    body: str
    error: str | None = None


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """(bloco YAML, corpo); `None` no bloco quando a cerca nao abre ou nao fecha."""
    linhas = text.splitlines(keepends=True)
    if not linhas or linhas[0].rstrip("\r\n") != CERCA:
        return None, text
    for indice in range(1, len(linhas)):
        if linhas[indice].rstrip("\r\n") == CERCA:
            return "".join(linhas[1:indice]), "".join(linhas[indice + 1 :])
    return None, text


def load_artifact(path: Path) -> Artifact:
    try:
        texto = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return Artifact(path, None, "", "arquivo nao e UTF-8")
    bloco, corpo = split_frontmatter(texto)
    if bloco is None:
        return Artifact(
            path,
            None,
            texto,
            "frontmatter ausente: a primeira linha precisa ser '---' e o bloco fecha com '---'",
        )
    try:
        meta = yaml.safe_load(bloco)
    except yaml.YAMLError as exc:
        marca = getattr(exc, "problem_mark", None)
        # +1 porque a marca e 0-based, +1 pela cerca de abertura
        onde = f" na linha {marca.line + 2}" if marca is not None else ""
        problema = getattr(exc, "problem", None) or str(exc)
        return Artifact(path, None, corpo, f"YAML invalido{onde}: {problema}")
    if not isinstance(meta, dict):
        return Artifact(path, None, corpo, "frontmatter precisa ser um mapeamento YAML")
    return Artifact(path, meta, corpo)


def discover(root: Path) -> dict[str, dict[str, Path]]:
    """`{feature: {fase: caminho}}` para `root/<FEATURE>/<fase>.md`, e nada mais fundo."""
    features: dict[str, dict[str, Path]] = {}
    for arquivo in iter_source_files(root, "*.md"):
        partes = arquivo.relative_to(root).parts
        if len(partes) != 2 or arquivo.stem not in PHASES:
            continue
        features.setdefault(partes[0], {})[arquivo.stem] = arquivo
    return features
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS (6 testes). Se `test_discover_so_pega_fase_na_profundidade_certa` falhar por forma de caminho, compare `iter_source_files` com `sorted(root.rglob("*.md"))` — ele promete a mesma sequência (`tests/test_facts_scan.py::test_ordem_reproduz_a_de_rglob_ordenado`).

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/__init__.py sparkforge/sdd/load.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): read SDD artifacts into checkable frontmatter"
```

---

### Task 3: schemas por fase e `change_kinds.yaml`

**Files:**
- Create: `sparkforge/sdd/schema/common.json`, `explore.json`, `define.json`, `design.json`, `plan.json`, `build_report.json`, `ship.json`
- Create: `sparkforge/sdd/change_kinds.yaml`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham** — acrescentar a `tests/test_sdd.py`:

```python
import re

from sparkforge.sdd.checks import change_kinds, schema_for

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("fase", PHASES)
def test_todo_schema_carrega_e_fecha_propriedades(fase):
    schema = schema_for(fase)
    assert schema["additionalProperties"] is False
    for campo in ("sdd", "feature", "phase", "profile", "status"):
        assert campo in schema["required"]


def test_change_kinds_casa_com_os_titulos_do_documento():
    """Deriva nos dois sentidos: titulo sem chave, ou chave sem titulo."""
    texto = (ROOT / "docs" / "gates-por-mudanca.md").read_text(encoding="utf-8")
    linhas = texto.splitlines()
    titulos: set[str] = set()
    for i, linha in enumerate(linhas):
        if not linha.startswith("## "):
            continue
        titulo = linha[3:].strip()
        # o titulo da secao de lastro continua na linha seguinte
        if i + 1 < len(linhas) and linhas[i + 1].startswith("## `"):
            titulo = f"{titulo} {linhas[i + 1][3:].strip()}"
        titulos.add(titulo)
    titulos = {t for t in titulos if not t.startswith("`docs/")}
    titulos.discard("Quando nada acima serve")
    secoes = {v["section"] for v in change_kinds().values()}
    assert secoes == titulos
    for chave, valor in change_kinds().items():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", chave)
        assert valor["registries"], chave
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.sdd.checks'`

- [ ] **Step 3: implementar os dados**

`sparkforge/sdd/schema/common.json`:

```json
{
  "required": ["sdd", "feature", "phase", "profile", "status"],
  "properties": {
    "sdd": {"const": 1},
    "feature": {"type": "string", "pattern": "^[A-Z0-9_]+$"},
    "phase": {"enum": ["explore", "define", "design", "plan", "build_report", "ship"]},
    "profile": {"enum": ["dev", "operator"]},
    "status": {"enum": ["draft", "ready", "done", "superseded"]},
    "upstream": {
      "type": "object",
      "additionalProperties": false,
      "required": ["path", "sha256"],
      "properties": {
        "path": {"type": "string", "minLength": 1},
        "sha256": {"type": "string", "pattern": "^([0-9a-f]{64})?$"}
      }
    }
  }
}
```

`sparkforge/sdd/schema/explore.json`:

```json
{
  "required": ["approaches", "chosen"],
  "properties": {
    "approaches": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "summary"],
        "properties": {
          "id": {"type": "string", "minLength": 1},
          "summary": {"type": "string", "minLength": 1},
          "tradeoffs": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "chosen": {"type": "string", "minLength": 1}
  }
}
```

`sparkforge/sdd/schema/define.json` (`source` fora de `required` de propósito: a falta dele é `success_without_source`, não `schema_invalid`):

```json
{
  "required": ["hypothesis", "acceptance", "success", "out_of_scope", "change_kinds"],
  "properties": {
    "hypothesis": {
      "type": "object",
      "additionalProperties": false,
      "required": ["claim", "prediction", "experiment"],
      "properties": {
        "claim": {"type": "string", "minLength": 1},
        "prediction": {"type": "string", "minLength": 1},
        "experiment": {"type": "string", "minLength": 1}
      }
    },
    "acceptance": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "statement", "verified_by"],
        "properties": {
          "id": {"type": "string", "pattern": "^AC[0-9]+$"},
          "statement": {"type": "string", "minLength": 1},
          "verified_by": {
            "type": "object",
            "additionalProperties": false,
            "required": ["kind", "ref"],
            "properties": {
              "kind": {"enum": ["test", "command", "funcval", "fact"]},
              "ref": {"type": "string", "minLength": 1}
            }
          }
        }
      }
    },
    "success": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "metric"],
        "properties": {
          "id": {"type": "string", "pattern": "^SC[0-9]+$"},
          "metric": {"type": "string", "minLength": 1},
          "source": {"type": "string"}
        }
      }
    },
    "out_of_scope": {"type": "array", "items": {"type": "string"}},
    "unknowns": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "unlock"],
        "properties": {
          "id": {"type": "string", "pattern": "^U[0-9]+$"},
          "blocks": {"type": "array", "items": {"type": "string"}},
          "unlock": {"type": "string", "minLength": 1}
        }
      }
    },
    "case_id": {"type": ["string", "null"]},
    "change_kinds": {"type": "array", "items": {"type": "string"}}
  }
}
```

`sparkforge/sdd/schema/design.json` (`rollback` fora de `required`: a falta é `rollback_missing`):

```json
{
  "required": ["files", "decisions", "covers"],
  "properties": {
    "files": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["path", "action", "reason"],
        "properties": {
          "path": {"type": "string", "minLength": 1},
          "action": {"enum": ["create", "modify", "delete"]},
          "reason": {"type": "string", "minLength": 1}
        }
      }
    },
    "decisions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "choice"],
        "properties": {
          "id": {"type": "string", "pattern": "^D[0-9]+$"},
          "choice": {"type": "string", "minLength": 1},
          "rejected": {"type": "array", "items": {"type": "string"}},
          "rollback": {"type": "string"}
        }
      }
    },
    "covers": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["part", "acceptance"],
        "properties": {
          "part": {"type": "string", "minLength": 1},
          "acceptance": {"type": "array", "items": {"type": "string"}}
        }
      }
    }
  }
}
```

`sparkforge/sdd/schema/plan.json` (`test` fora de `required`: a falta é `task_without_test`):

```json
{
  "required": ["tasks"],
  "properties": {
    "tasks": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "files", "covers"],
        "properties": {
          "id": {"type": "string", "pattern": "^T[0-9]+$"},
          "files": {"type": "array", "items": {"type": "string"}},
          "covers": {"type": "array", "items": {"type": "string"}},
          "test": {
            "type": "object",
            "additionalProperties": false,
            "required": ["path", "name"],
            "properties": {
              "path": {"type": "string", "minLength": 1},
              "name": {"type": "string", "minLength": 1}
            }
          }
        }
      }
    }
  }
}
```

`sparkforge/sdd/schema/build_report.json` (`red` e `evidence_ref` fora de `required`):

```json
{
  "required": ["tasks", "claims"],
  "properties": {
    "tasks": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["id", "status"],
        "properties": {
          "id": {"type": "string", "pattern": "^T[0-9]+$"},
          "status": {"enum": ["done", "skipped", "blocked"]},
          "red": {"$ref": "#/$defs/run"},
          "green": {"$ref": "#/$defs/run"}
        }
      }
    },
    "claims": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["text"],
        "properties": {
          "text": {"type": "string", "minLength": 1},
          "evidence_ref": {"type": "string"}
        }
      }
    },
    "change_id": {"type": ["string", "null"]}
  },
  "$defs": {
    "run": {
      "type": "object",
      "additionalProperties": false,
      "required": ["command", "exit"],
      "properties": {
        "command": {"type": "string", "minLength": 1},
        "exit": {"type": "integer"}
      }
    }
  }
}
```

`sparkforge/sdd/schema/ship.json`:

```json
{
  "required": ["registries", "deviations"],
  "properties": {
    "hypothesis_outcome": {"enum": ["confirmed", "refuted", "abandoned"]},
    "registries": {"type": "array", "items": {"type": "string"}},
    "deviations": {"type": "array", "items": {"type": "string"}}
  }
}
```

`sparkforge/sdd/change_kinds.yaml` — uma chave por seção `## ` de `docs/gates-por-mudanca.md` (exceto "Quando nada acima serve"). Antes de escrever, liste os títulos:

Run: `python -c "import re,pathlib;[print(l) for l in pathlib.Path('docs/gates-por-mudanca.md').read_text(encoding='utf-8').splitlines() if l.startswith('## ')]"`

Com os títulos medidos em 2026-09-16, o arquivo é:

```yaml
# Tipo de mudanca -> secao de docs/gates-por-mudanca.md -> registros que o ship
# precisa listar. `section` e o titulo LITERAL da secao; tests/test_sdd.py trava a
# deriva nos dois sentidos. `registries` sao nomes curtos, nao comandos: o
# comando mora na secao.
rule:
  section: "Acrescentar ou alterar uma REGRA no catálogo"
  registries: [rules_catalog_gates, manifest_rule_count, fixture_kind_coverage]
rule_runtime_scope:
  section: "Dar `runtime_scope` a uma regra — ou seja, **toda regra nova**"
  registries: [runtime_scope_gates]
rule_area:
  section: "Acrescentar uma ÁREA nova (`area:` novo num `rules/catalog/*.yaml`)"
  registries: [routing_yaml, coordinator_rule_areas]
extractor:
  section: "Acrescentar ou alterar um EXTRATOR de facts"
  registries: [reachability_lists, fixture_kind_coverage, snippet_measure]
context_funnel:
  section: "Mexer no funil de contexto (`sparkforge/codeintel/context.py`, `ranking.py`, `budget.py`)"
  registries: [recall_economy_gate]
fixture_corpus:
  section: "Acrescentar um CORPUS de fixture novo (`fixtures/<dominio>/`)"
  registries: [fixture_corpus_gates]
holdout:
  section: "Acrescentar ou alterar um cenário de `evals/holdout/`"
  registries: [holdout_gates]
knowledge_doc:
  section: "Editar um documento em `knowledge/`"
  registries: [offline_manifest, sources_lock]
runtime_matrix:
  section: "Alterar `knowledge/glue/runtime-matrix.yaml`"
  registries: [runtime_matrix_gates]
terraform_blind_spots:
  section: "Pontos cegos medidos do extrator de Terraform"
  registries: [terraform_extractor_gates]
disk_read:
  section: "Ler dado do disco em código de `sparkforge/`"
  registries: [verify_wheel]
dependency:
  section: "Alterar dependência: `pyproject.toml`, `requirements.txt`, `locks/` ou os workflows"
  registries: [requirements_mirror, hash_locks]
agent_or_skill:
  section: "Alterar agent, skill ou seus espelhos"
  registries: [sync_skills, agents_parity]
tool_or_verb:
  section: "Acrescentar ou alterar tool, verbo de CLI, agent ou skill: a referência gerada"
  registries: [surface_lock, generated_reference]
routing:
  section: "Alterar `rules/catalog/routing.yaml`"
  registries: [router_gates]
status_numbers:
  section: "Alterar a tabela *Números correntes* do `STATUS.md`"
  registries: [status_numbers_gate]
claims:
  section: "Alterar `scripts/check_vnext_claims.py`, `docs/claims.lock.json`, ou alegação em `docs/vnext/` ou `docs/harness/`"
  registries: [claims_gate]
```

Se algum título medido diferir do acima (o documento pode ter mudado), use o título medido; o teste do Step 1 é quem decide.

- [ ] **Step 4: implementar o carregamento** — criar `sparkforge/sdd/checks.py` só com isto por enquanto:

```python
"""Os gates do SDD: cada falha e uma recusa com nome e o que a destrava."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_AQUI = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def schema_for(phase: str) -> dict[str, Any]:
    """Schema da fase = campos comuns + campos proprios, sem campo extra."""
    comum = json.loads((_AQUI / "schema" / "common.json").read_text(encoding="utf-8"))
    propria = json.loads((_AQUI / "schema" / f"{phase}.json").read_text(encoding="utf-8"))
    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": [*comum["required"], *propria.get("required", [])],
        "properties": {**comum["properties"], **propria["properties"]},
    }
    if "$defs" in propria:
        schema["$defs"] = propria["$defs"]
    return schema


@lru_cache(maxsize=None)
def change_kinds() -> dict[str, dict[str, Any]]:
    return yaml.safe_load((_AQUI / "change_kinds.yaml").read_text(encoding="utf-8"))
```

- [ ] **Step 5: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 6: commit**

```bash
git add sparkforge/sdd/schema sparkforge/sdd/change_kinds.yaml sparkforge/sdd/checks.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): per-phase schemas and the change-kind map"
```

---

### Task 4: construtor de feature, `check()` e as recusas de estrutura

**Files:**
- Modify: `sparkforge/sdd/checks.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: construtor e testes que falham** — acrescentar a `tests/test_sdd.py`:

```python
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd.checks import check


_LINHA_SHA = re.compile(r"^(?P<recuo>[ \t]+)sha256: ['\"]?(?P<hex>[0-9a-f]*)['\"]?$", re.M)


def _dump(meta: dict) -> str:
    """YAML com a linha do hash no MESMO formato que `stamp` grava.

    `yaml.safe_dump` escolhe sozinho se poe aspas num hex (depende do valor);
    `stamp` sempre grava `sha256: "<hex>"`. Sem alinhar os dois, restampar um
    hash que nao mudou mudaria o texto e deixaria a fase de baixo stale.
    """
    texto = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return _LINHA_SHA.sub(lambda m: f'{m["recuo"]}sha256: "{m["hex"]}"', texto)


def _grava(repo: Path, feature: str, fase: str, meta: dict) -> Path:
    pasta = repo / "docs" / "sdd" / feature
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{fase}.md"
    texto = "---\n" + _dump(meta) + "---\ncorpo livre\n"
    arquivo.write_bytes(texto.encode("utf-8"))
    return arquivo


def _upstream(repo: Path, anterior: Path) -> dict:
    return {"path": anterior.relative_to(repo).as_posix(), "sha256": text_sha256(anterior)}


def feature_limpa(repo: Path, profile: str = "dev", feature: str = "F1") -> dict[str, Path]:
    """Uma feature que passa em tudo. Cada teste de recusa estraga UMA coisa."""
    (repo / "tests").mkdir(parents=True, exist_ok=True)
    (repo / "tests" / "test_alvo.py").write_bytes(b"def test_alvo():\n    assert True\n")
    (repo / "sparkforge").mkdir(exist_ok=True)
    (repo / "sparkforge" / "existente.py").write_bytes(b"x = 1\n")
    comum = {"sdd": 1, "feature": feature, "profile": profile, "status": "done"}
    caminhos: dict[str, Path] = {}
    define = {
        **comum,
        "phase": "define",
        "hypothesis": {"claim": "c", "prediction": "p", "experiment": "e"},
        "acceptance": [
            {
                "id": "AC1",
                "statement": "s",
                "verified_by": {"kind": "test", "ref": "tests/test_alvo.py::test_alvo"},
            }
        ],
        "success": [{"id": "SC1", "metric": "m", "source": "tests/test_alvo.py"}],
        "out_of_scope": [],
        "change_kinds": ["tool_or_verb"],
    }
    if profile == "operator":
        (repo / ".sparkforge").mkdir(exist_ok=True)
        (repo / ".sparkforge" / "case.yaml").write_bytes(b"case_id: C1\n")
        (repo / ".sparkforge" / "sandbox" / "S1").mkdir(parents=True)
        define["case_id"] = "C1"
    caminhos["define"] = _grava(repo, feature, "define", define)
    caminhos["design"] = _grava(repo, feature, "design", {
        **comum,
        "phase": "design",
        "upstream": _upstream(repo, caminhos["define"]),
        "files": [
            {"path": "sparkforge/novo.py", "action": "create", "reason": "r"},
            {"path": "sparkforge/existente.py", "action": "modify", "reason": "r"},
        ],
        "decisions": [{"id": "D1", "choice": "c", "rejected": [], "rollback": "git revert"}],
        "covers": [{"part": "p", "acceptance": ["AC1"]}],
    })
    caminhos["plan"] = _grava(repo, feature, "plan", {
        **comum,
        "phase": "plan",
        "upstream": _upstream(repo, caminhos["design"]),
        "tasks": [{
            "id": "T1",
            "files": ["sparkforge/novo.py"],
            "covers": ["AC1"],
            "test": {"path": "tests/test_alvo.py", "name": "test_alvo"},
        }],
    })
    build = {
        **comum,
        "phase": "build_report",
        "upstream": _upstream(repo, caminhos["plan"]),
        "tasks": [{
            "id": "T1",
            "status": "done",
            "red": {"command": "pytest tests/test_alvo.py", "exit": 1},
            "green": {"command": "pytest tests/test_alvo.py", "exit": 0},
        }],
        "claims": [{"text": "t", "evidence_ref": "tests/test_alvo.py::test_alvo"}],
    }
    if profile == "operator":
        build["change_id"] = "S1"
    caminhos["build_report"] = _grava(repo, feature, "build_report", build)
    caminhos["ship"] = _grava(repo, feature, "ship", {
        **comum,
        "phase": "ship",
        "upstream": _upstream(repo, caminhos["build_report"]),
        "hypothesis_outcome": "confirmed",
        "registries": ["surface_lock", "generated_reference"],
        "deviations": [],
    })
    return caminhos


def _codigos(relatorio: dict) -> tuple[list[str], list[str]]:
    return (
        sorted(r["code"] for r in relatorio["refused"]),
        sorted(r["code"] for r in relatorio["unresolved"]),
    )


def _reescreve(arquivo: Path, **mudancas) -> None:
    """Muda campos do frontmatter e NAO restampa quem esta abaixo."""
    texto = arquivo.read_bytes().decode("utf-8")
    bloco, corpo = split_frontmatter(texto)
    meta = yaml.safe_load(bloco)
    for chave, valor in mudancas.items():
        if valor is None:
            meta.pop(chave, None)
        else:
            meta[chave] = valor
    novo = "---\n" + _dump(meta) + "---\n" + corpo
    arquivo.write_bytes(novo.encode("utf-8"))


@pytest.mark.parametrize("profile", ["dev", "operator"])
def test_feature_limpa_passa_sem_nada(tmp_path, profile):
    feature_limpa(tmp_path, profile)
    relatorio = check(tmp_path)
    assert relatorio["ok"] is True, relatorio
    assert relatorio["features"] == ["F1"]
    assert _codigos(relatorio) == ([], [])


def test_raiz_inexistente_e_lacuna(tmp_path):
    relatorio = check(tmp_path)
    assert relatorio["ok"] is False
    assert _codigos(relatorio) == ([], ["root_missing"])


def test_schema_invalid_campo_desconhecido(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], inventado=1)
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["schema_invalid"]
    assert recusa[0]["path"] == "docs/sdd/F1/ship.md"


def test_schema_invalid_yaml_quebrado(tmp_path):
    caminhos = feature_limpa(tmp_path)
    caminhos["ship"].write_bytes(b"---\nsdd: [\n---\n")
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["schema_invalid"]
    assert "linha" in recusa[0]["unlock"]


def test_schema_invalid_fase_trocada(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], phase="plan")
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("schema_invalid", "phase")]


def test_phase_out_of_order(tmp_path):
    caminhos = feature_limpa(tmp_path)
    caminhos["plan"].unlink()
    assert _codigos(check(tmp_path)) == (["phase_out_of_order", "upstream_missing"], [])


def test_phase_out_of_order_por_status(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], status="draft")
    # ship em draft nao bloqueia ninguem; build_report em draft bloqueia o ship
    assert _codigos(check(tmp_path)) == ([], [])
    _reescreve(caminhos["build_report"], status="draft")
    refused, _ = _codigos(check(tmp_path))
    assert "phase_out_of_order" in refused


def test_feature_filtra(tmp_path):
    feature_limpa(tmp_path, feature="F1")
    feature_limpa(tmp_path, feature="F2")
    assert check(tmp_path, feature="F2")["features"] == ["F2"]
```

**Atenção ao `test_phase_out_of_order`:** com `plan.md` apagado, o `build_report` recusa duas coisas legítimas — a fase anterior sumiu **e** o `upstream.path` dele aponta para um arquivo que não existe. O teste afirma as duas; não é o "só ela" que vale para as demais recusas, porque aqui as duas são a mesma causa vista de dois gates.

**Atenção ao `test_phase_out_of_order_por_status`:** `_reescreve` do `build_report` muda o texto dele, então o `ship` também fica `upstream_stale`. Por isso o teste usa `in` e não igualdade.

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: FAIL com `ImportError: cannot import name 'check'`

- [ ] **Step 3: implementar** — acrescentar a `sparkforge/sdd/checks.py` (imports no topo, resto no fim):

```python
from collections.abc import Callable
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator

from sparkforge.paths import resolve_within
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.load import Artifact, discover, load_artifact

PREDECESSOR: dict[str, str] = {
    "design": "define",
    "plan": "design",
    "build_report": "plan",
    "ship": "build_report",
}
PRONTO = ("ready", "done")


@dataclass
class _Contexto:
    repo: Path
    feature: str
    caminhos: dict[str, Path]
    artefatos: dict[str, Artifact] = field(default_factory=dict)
    refused: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[dict[str, Any]] = field(default_factory=list)

    def rel(self, caminho: Path) -> str:
        try:
            return caminho.resolve().relative_to(self.repo.resolve()).as_posix()
        except ValueError:
            return str(caminho)

    def recusa(self, code: str, caminho: Path, campo: str | None, unlock: str) -> None:
        self.refused.append(
            {"code": code, "feature": self.feature, "path": self.rel(caminho),
             "field": campo, "unlock": unlock}
        )

    def lacuna(self, code: str, caminho: Path, unlock: str) -> None:
        self.unresolved.append(
            {"code": code, "feature": self.feature, "path": self.rel(caminho), "unlock": unlock}
        )


Gate = Callable[[_Contexto, str, Artifact], None]


def _carrega(ctx: _Contexto) -> None:
    for fase in PHASES:
        caminho = ctx.caminhos.get(fase)
        if caminho is None:
            continue
        artefato = load_artifact(caminho)
        if artefato.error is not None:
            ctx.recusa("schema_invalid", caminho, None, artefato.error)
            continue
        erros = sorted(
            Draft202012Validator(schema_for(fase)).iter_errors(artefato.meta),
            key=lambda erro: [str(parte) for parte in erro.absolute_path],
        )
        if erros:
            for erro in erros:
                campo = "/".join(str(parte) for parte in erro.absolute_path) or None
                ctx.recusa("schema_invalid", caminho, campo, erro.message)
            continue
        if artefato.meta["phase"] != fase:
            ctx.recusa("schema_invalid", caminho, "phase",
                       f"o arquivo {fase}.md declara phase {artefato.meta['phase']}")
            continue
        if artefato.meta["feature"] != ctx.feature:
            ctx.recusa("schema_invalid", caminho, "feature",
                       f"o arquivo mora em {ctx.feature}/ e declara feature "
                       f"{artefato.meta['feature']}")
            continue
        ctx.artefatos[fase] = artefato


def _gate_order(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    anterior = PREDECESSOR[fase]
    if anterior in ctx.caminhos and anterior not in ctx.artefatos:
        return  # o anterior existe e ja foi recusado por schema; nao repete a causa
    previo = ctx.artefatos.get(anterior)
    if previo is None or previo.meta["status"] not in PRONTO:
        ctx.recusa("phase_out_of_order", artefato.path, "phase",
                   f"{fase} exige {anterior}.md com status ready ou done")


def _upstream_esperado(ctx: _Contexto, fase: str) -> str | None:
    if fase in PREDECESSOR:
        return PREDECESSOR[fase]
    if fase == "define" and "explore" in ctx.caminhos:
        return "explore"
    return None


def _gate_upstream(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    esperado = _upstream_esperado(ctx, fase)
    declarado = artefato.meta.get("upstream")
    if esperado is None:
        return
    esperado_rel = f"{ctx.rel(ctx.caminhos[esperado])}" if esperado in ctx.caminhos else (
        f"{ctx.rel(artefato.path.parent)}/{esperado}.md"
    )
    if declarado is None:
        ctx.recusa("upstream_missing", artefato.path, "upstream",
                   f"declare upstream.path: {esperado_rel} e rode `sparkforge sdd stamp`")
        return
    alvo = resolve_within(ctx.repo, declarado["path"])
    if alvo is None or not alvo.is_file():
        ctx.recusa("upstream_missing", artefato.path, "upstream/path",
                   f"{declarado['path']} nao existe; o upstream de {fase} e {esperado_rel}")
        return
    if esperado in ctx.caminhos and alvo != ctx.caminhos[esperado].resolve():
        ctx.recusa("upstream_missing", artefato.path, "upstream/path",
                   f"{declarado['path']} nao e o upstream de {fase}; use {esperado_rel}")
        return
    if declarado["sha256"] != text_sha256(alvo):
        ctx.recusa("upstream_stale", artefato.path, "upstream/sha256",
                   f"{declarado['path']} mudou; revise {fase} e rode "
                   f"`sparkforge sdd stamp --repo . {ctx.rel(artefato.path)}`")


_GATES: dict[str, tuple[Gate, ...]] = {
    "explore": (),
    "define": (_gate_upstream,),
    "design": (_gate_order, _gate_upstream),
    "plan": (_gate_order, _gate_upstream),
    "build_report": (_gate_order, _gate_upstream),
    "ship": (_gate_order, _gate_upstream),
}


def check_feature(repo: Path, feature: str, caminhos: dict[str, Path]) -> _Contexto:
    ctx = _Contexto(repo=repo, feature=feature, caminhos=caminhos)
    _carrega(ctx)
    for fase in PHASES:
        artefato = ctx.artefatos.get(fase)
        if artefato is None:
            continue
        for gate in _GATES[fase]:
            gate(ctx, fase, artefato)
    return ctx


def check(repo: Path | str, root: str = DEFAULT_ROOT, feature: str | None = None) -> dict[str, Any]:
    """`{ok, root, features, refused, unresolved}` sobre `repo/root`."""
    raiz_repo = Path(repo)
    raiz = resolve_within(raiz_repo, root)
    if raiz is None or not raiz.is_dir():
        return {
            "ok": False,
            "root": root,
            "features": [],
            "refused": [],
            "unresolved": [{
                "code": "root_missing", "feature": None, "path": root,
                "unlock": f"crie {root}/<FEATURE>/ ou passe --root para a pasta dos artefatos",
            }],
        }
    todas = discover(raiz)
    nomes = sorted(todas) if feature is None else [n for n in sorted(todas) if n == feature]
    refused: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for nome in nomes:
        ctx = check_feature(raiz_repo, nome, todas[nome])
        refused.extend(ctx.refused)
        unresolved.extend(ctx.unresolved)
    return {
        "ok": not refused and not unresolved,
        "root": root,
        "features": nomes,
        "refused": refused,
        "unresolved": unresolved,
    }
```

Remover a variável não usada no `_gate_upstream` se o ruff reclamar (`esperado_rel` é usada; confira com `python -m ruff check sparkforge/sdd`).

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/checks.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): check() with schema, order and upstream gates"
```

---

### Task 5: `stamp` e a cascata

**Files:**
- Create: `sparkforge/sdd/stamp.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
from sparkforge.sdd.stamp import StampError, stamp


def test_upstream_stale_e_stamp_resolve(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["define"], out_of_scope=["mudou"])
    assert _codigos(check(tmp_path)) == (["upstream_stale"], [])
    saida = stamp(tmp_path, "docs/sdd/F1/design.md")
    assert saida["changed"] is True
    assert saida["path"] == "docs/sdd/F1/design.md"
    assert saida["upstream"] == "docs/sdd/F1/define.md"
    # restampar o design muda o texto dele: agora o plan fica stale, e so ele
    assert [r["path"] for r in check(tmp_path)["refused"]] == ["docs/sdd/F1/plan.md"]


def test_stamp_idempotente_nao_regrava(tmp_path):
    caminhos = feature_limpa(tmp_path)
    antes = caminhos["design"].stat().st_mtime_ns
    assert stamp(tmp_path, "docs/sdd/F1/design.md")["changed"] is False
    assert caminhos["design"].stat().st_mtime_ns == antes


def test_stamp_preserva_crlf_e_o_corpo(tmp_path):
    caminhos = feature_limpa(tmp_path)
    original = caminhos["design"].read_bytes().replace(b"\n", b"\r\n")
    original = original.replace(
        text_sha256(caminhos["define"]).encode(), b"0" * 64
    )
    caminhos["design"].write_bytes(original)
    stamp(tmp_path, "docs/sdd/F1/design.md")
    depois = caminhos["design"].read_bytes()
    assert b"\n" not in depois.replace(b"\r\n", b"")
    assert depois.endswith(b"corpo livre\r\n")
    assert _codigos(check(tmp_path))[0] == []


def test_stamp_recusa_sem_upstream(tmp_path):
    caminhos = feature_limpa(tmp_path)
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/define.md")
    assert erro.value.code == "upstream_missing"
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "docs/sdd/F1/nao-existe.md")
    assert erro.value.code == "artifact_missing"
    with pytest.raises(StampError) as erro:
        stamp(tmp_path, "../fora.md")
    assert erro.value.code == "artifact_missing"
    assert caminhos["define"].is_file()
```

Nota do `test_stamp_preserva_crlf_e_o_corpo`: com o arquivo inteiro em CRLF, o `text_sha256` do **design** muda de bytes mas não de texto normalizado, e o `stamp` regrava a linha do hash no mesmo formato que `_dump` usou (`sha256: "<hex>"`). O texto normalizado volta a ser o original, então o `plan` não fica stale — por isso o check sai sem recusa.

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -k stamp -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.sdd.stamp'`

- [ ] **Step 3: implementar** `sparkforge/sdd/stamp.py`:

```python
"""Grava `upstream.sha256` no frontmatter, sem tocar no resto do arquivo.

Existe porque sha256 calculado a mao por agente erra, e cada erro vira
`upstream_stale` falso. So a linha do hash muda; quebra de linha, ordem de
campos e corpo ficam como estavam (`write_atomic_bytes`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.durable import write_atomic_bytes
from sparkforge.paths import resolve_within
from sparkforge.receipt._hash import text_sha256
from sparkforge.sdd.load import CERCA, load_artifact


class StampError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _rel(repo: Path, caminho: Path) -> str:
    return caminho.relative_to(repo.resolve()).as_posix()


def _linha_do_hash(linhas: list[str]) -> int | None:
    dentro = False
    for indice in range(1, len(linhas)):
        crua = linhas[indice].rstrip("\r\n")
        if crua == CERCA:
            return None
        if crua.startswith("upstream:"):
            dentro = True
            continue
        if dentro and crua and not crua[0].isspace():
            dentro = False
        if dentro and crua.lstrip().startswith("sha256:"):
            return indice
    return None


def stamp(repo: Path | str, path: str) -> dict[str, Any]:
    raiz = Path(repo)
    alvo = resolve_within(raiz, path)
    if alvo is None or not alvo.is_file():
        raise StampError("artifact_missing", f"{path} nao existe sob {raiz}")
    artefato = load_artifact(alvo)
    if artefato.error is not None:
        raise StampError("schema_invalid", f"{path}: {artefato.error}")
    upstream = artefato.meta.get("upstream")
    if not isinstance(upstream, dict) or not upstream.get("path"):
        raise StampError("upstream_missing", f"{path} nao declara upstream.path")
    origem = resolve_within(raiz, str(upstream["path"]))
    if origem is None or not origem.is_file():
        raise StampError("upstream_missing", f"{upstream['path']} nao existe sob {raiz}")
    novo = text_sha256(origem)
    anterior = str(upstream.get("sha256") or "")
    linhas = alvo.read_bytes().decode("utf-8").splitlines(keepends=True)
    indice = _linha_do_hash(linhas)
    if indice is None:
        raise StampError(
            "upstream_missing",
            f"{path}: upstream sem a linha sha256 em bloco (escreva `  sha256: \"\"` abaixo de "
            "`upstream:`)",
        )
    if novo != anterior:
        original = linhas[indice]
        sem_quebra = original.rstrip("\r\n")
        quebra = original[len(sem_quebra):]
        recuo = sem_quebra[: len(sem_quebra) - len(sem_quebra.lstrip())]
        linhas[indice] = f'{recuo}sha256: "{novo}"{quebra}'
        write_atomic_bytes(alvo, "".join(linhas).encode("utf-8"))
    return {
        "path": _rel(raiz, alvo),
        "upstream": _rel(raiz, origem),
        "sha256": novo,
        "previous": anterior,
        "changed": novo != anterior,
    }
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/stamp.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): stamp writes the upstream hash and nothing else"
```

---

### Task 6: gates do define

**Files:**
- Modify: `sparkforge/sdd/checks.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
import json


def _define_meta(caminhos):
    bloco, _ = split_frontmatter(caminhos["define"].read_bytes().decode("utf-8"))
    return yaml.safe_load(bloco)


def _so_define(tmp_path):
    """Feature so com define: nada abaixo para ficar stale."""
    caminhos = feature_limpa(tmp_path)
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    return caminhos


def test_success_without_source(tmp_path):
    caminhos = _so_define(tmp_path)
    _reescreve(caminhos["define"], success=[{"id": "SC1", "metric": "m"}])
    assert _codigos(check(tmp_path)) == (["success_without_source"], [])


def test_change_kind_desconhecido_e_schema_invalid(tmp_path):
    caminhos = _so_define(tmp_path)
    _reescreve(caminhos["define"], change_kinds=["inventado"])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["field"]) for r in recusa] == [("schema_invalid", "change_kinds/0")]


def test_test_not_written_antes_do_build(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"]["ref"] = "tests/test_alvo.py::test_futuro"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["test_not_written"])


def test_verified_by_dangling_depois_do_build(tmp_path):
    caminhos = feature_limpa(tmp_path)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(b"def test_outro():\n    pass\n")
    refused, unresolved = _codigos(check(tmp_path))
    # o plan aponta o mesmo teste: as duas referencias penduram
    assert refused == ["verified_by_dangling", "verified_by_dangling"]
    assert unresolved == []


def test_teste_em_classe_conta(tmp_path):
    caminhos = _so_define(tmp_path)
    (tmp_path / "tests" / "test_alvo.py").write_bytes(
        b"class TestX:\n    def test_y(self):\n        pass\n"
    )
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"]["ref"] = "tests/test_alvo.py::TestX::test_y"
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], [])


def test_fact_not_collected_e_fact_encontrado(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "fact", "ref": "facts.json#abc123"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["fact_not_collected"])
    (tmp_path / "facts.json").write_text(json.dumps([{"id": "abc123"}]), encoding="utf-8")
    assert _codigos(check(tmp_path)) == ([], [])


def test_funcval_not_run(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "funcval", "ref": "out/compare.json"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], ["funcval_not_run"])


def test_command_e_declarado_e_nao_conferido(tmp_path):
    caminhos = _so_define(tmp_path)
    meta = _define_meta(caminhos)
    meta["acceptance"][0]["verified_by"] = {"kind": "command", "ref": "make x"}
    _reescreve(caminhos["define"], acceptance=meta["acceptance"])
    assert _codigos(check(tmp_path)) == ([], [])
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: FAIL nos oito testes novos (o gate não existe; `test_verified_by_dangling_depois_do_build` falha com lista vazia)

- [ ] **Step 3: implementar** — acrescentar a `sparkforge/sdd/checks.py` (import `ast` no topo), antes de `_GATES`:

```python
def _nomes_de_teste(arvore: ast.Module) -> set[str]:
    nomes: set[str] = set()
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            nomes.add(no.name)
        elif isinstance(no, ast.ClassDef):
            for membro in no.body:
                if isinstance(membro, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nomes.add(f"{no.name}::{membro.name}")
    return nomes


def _teste_existe(repo: Path, referencia: str) -> bool:
    caminho, _, nome = referencia.partition("::")
    alvo = resolve_within(repo, caminho) if caminho else None
    if alvo is None or not alvo.is_file() or not nome:
        return False
    try:
        arvore = ast.parse(alvo.read_bytes())
    except (SyntaxError, ValueError):
        return False
    return nome in _nomes_de_teste(arvore)


def _conferir_teste(
    ctx: _Contexto, artefato: Artifact, campo: str, referencia: str, dono: str
) -> None:
    if _teste_existe(ctx.repo, referencia):
        return
    if "build_report" in ctx.artefatos:
        ctx.recusa("verified_by_dangling", artefato.path, campo,
                   f"{referencia} nao existe depois do build; escreva o teste ou corrija a "
                   "referencia")
    else:
        ctx.lacuna("test_not_written", artefato.path,
                   f"{referencia} ainda nao existe; o build escreve o teste de {dono} antes do "
                   "codigo")


def _ids_de_fact(arquivo: Path) -> set[str]:
    try:
        dado = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    itens = dado.get("items", []) if isinstance(dado, dict) else dado
    if not isinstance(itens, list):
        return set()
    return {str(item.get("id")) for item in itens if isinstance(item, dict)}


def _gate_success_source(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["success"]):
        if not str(item.get("source") or "").strip():
            ctx.recusa("success_without_source", artefato.path, f"success/{indice}/source",
                       f"diga de onde vem o numero de {item['id']} (regra 24)")


def _gate_change_kinds(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    conhecidos = change_kinds()
    for indice, chave in enumerate(artefato.meta["change_kinds"]):
        if chave not in conhecidos:
            ctx.recusa("schema_invalid", artefato.path, f"change_kinds/{indice}",
                       f"'{chave}' nao existe em sparkforge/sdd/change_kinds.yaml; use uma de: "
                       + ", ".join(sorted(conhecidos)))


def _gate_verified_by(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["acceptance"]):
        prova = item["verified_by"]
        campo = f"acceptance/{indice}/verified_by"
        referencia = prova["ref"]
        if prova["kind"] == "test":
            _conferir_teste(ctx, artefato, campo, referencia, item["id"])
        elif prova["kind"] == "fact":
            caminho, _, fact_id = referencia.partition("#")
            alvo = resolve_within(ctx.repo, caminho) if caminho else None
            if alvo is None or not alvo.is_file() or fact_id not in _ids_de_fact(alvo):
                ctx.lacuna("fact_not_collected", artefato.path,
                           f"{fact_id or referencia} nao esta em {caminho}; colete o artefato e "
                           "rode o `sparkforge analyze` que o extrai")
        elif prova["kind"] == "funcval":
            alvo = resolve_within(ctx.repo, referencia)
            if alvo is None or not alvo.is_file():
                ctx.lacuna("funcval_not_run", artefato.path,
                           f"rode `sparkforge funcval compare --out {referencia}` para "
                           f"{item['id']}")
```

E trocar a entrada `"define"` de `_GATES`:

```python
    "define": (_gate_upstream, _gate_success_source, _gate_change_kinds, _gate_verified_by),
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS nos testes de define. `test_verified_by_dangling_depois_do_build` ainda espera **duas** recusas; a segunda vem do plan, que só é conferido na Task 7 — se ele falhar com uma só, marque-o para rerodar no Step 4 da Task 7 e siga.

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/checks.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): define gates - success source, change kinds, verified_by"
```

---

### Task 7: gates do design e do plan

**Files:**
- Modify: `sparkforge/sdd/checks.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
def _meta(arquivo):
    bloco, _ = split_frontmatter(arquivo.read_bytes().decode("utf-8"))
    return yaml.safe_load(bloco)


def _ate(tmp_path, fase):
    """Feature cortada logo depois de `fase`: nada abaixo fica stale."""
    caminhos = feature_limpa(tmp_path)
    corta = False
    for nome in PHASES:
        if corta and nome in caminhos:
            caminhos[nome].unlink()
        if nome == fase:
            corta = True
    return caminhos


def test_manifest_path_unknown(tmp_path):
    caminhos = _ate(tmp_path, "design")
    meta = _meta(caminhos["design"])
    meta["files"].append({"path": "sparkforge/sumiu.py", "action": "delete", "reason": "r"})
    _reescreve(caminhos["design"], files=meta["files"])
    assert _codigos(check(tmp_path)) == (["manifest_path_unknown"], [])


def test_rollback_missing(tmp_path):
    caminhos = _ate(tmp_path, "design")
    _reescreve(caminhos["design"], decisions=[{"id": "D1", "choice": "c"}])
    assert _codigos(check(tmp_path)) == (["rollback_missing"], [])


def test_acceptance_uncovered_no_design(tmp_path):
    caminhos = _ate(tmp_path, "design")
    _reescreve(caminhos["design"], covers=[{"part": "p", "acceptance": []}])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["path"]) for r in recusa] == [
        ("acceptance_uncovered", "docs/sdd/F1/design.md")
    ]


def test_acceptance_uncovered_no_plan(tmp_path):
    caminhos = _ate(tmp_path, "plan")
    meta = _meta(caminhos["plan"])
    meta["tasks"][0]["covers"] = []
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    recusa = check(tmp_path)["refused"]
    assert [(r["code"], r["path"]) for r in recusa] == [
        ("acceptance_uncovered", "docs/sdd/F1/plan.md")
    ]


def test_task_without_test(tmp_path):
    caminhos = _ate(tmp_path, "plan")
    meta = _meta(caminhos["plan"])
    del meta["tasks"][0]["test"]
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == (["task_without_test"], [])


def test_teste_do_plan_ainda_nao_escrito(tmp_path):
    caminhos = _ate(tmp_path, "plan")
    meta = _meta(caminhos["plan"])
    meta["tasks"][0]["test"]["name"] = "test_futuro"
    _reescreve(caminhos["plan"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == ([], ["test_not_written"])
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: FAIL nos seis testes novos

- [ ] **Step 3: implementar** — antes de `_GATES`:

```python
def _gate_manifest(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, item in enumerate(artefato.meta["files"]):
        if item["action"] == "create":
            continue
        alvo = resolve_within(ctx.repo, item["path"])
        if alvo is None or not alvo.exists():
            ctx.recusa("manifest_path_unknown", artefato.path, f"files/{indice}/path",
                       f"{item['path']} nao existe para {item['action']}; confira o caminho ou "
                       "use action: create")


def _gate_rollback(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, decisao in enumerate(artefato.meta["decisions"]):
        if not str(decisao.get("rollback") or "").strip():
            ctx.recusa("rollback_missing", artefato.path, f"decisions/{indice}/rollback",
                       f"diga como desfazer {decisao['id']}")


def _gate_cobertura(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    define = ctx.artefatos.get("define")
    if define is None:
        return
    if fase == "design":
        cobertos = {ac for parte in artefato.meta["covers"] for ac in parte["acceptance"]}
        campo = "covers"
    else:
        cobertos = {ac for tarefa in artefato.meta["tasks"] for ac in tarefa["covers"]}
        campo = "tasks"
    for item in define.meta["acceptance"]:
        if item["id"] not in cobertos:
            ctx.recusa("acceptance_uncovered", artefato.path, campo,
                       f"{item['id']} do define nao aparece em nenhum covers do {fase}")


def _gate_task_test(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, tarefa in enumerate(artefato.meta["tasks"]):
        teste = tarefa.get("test")
        campo = f"tasks/{indice}/test"
        if not teste:
            ctx.recusa("task_without_test", artefato.path, campo,
                       f"{tarefa['id']} precisa do teste que falha antes do codigo")
            continue
        _conferir_teste(ctx, artefato, campo, f"{teste['path']}::{teste['name']}", tarefa["id"])
```

E em `_GATES`:

```python
    "design": (_gate_order, _gate_upstream, _gate_manifest, _gate_rollback, _gate_cobertura),
    "plan": (_gate_order, _gate_upstream, _gate_cobertura, _gate_task_test),
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS, inclusive `test_verified_by_dangling_depois_do_build`

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/checks.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): design and plan gates - manifest, rollback, coverage, TDD"
```

---

### Task 8: gates do build_report e do ship

**Files:**
- Modify: `sparkforge/sdd/checks.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
def test_red_not_declared_ausente(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    meta = _meta(caminhos["build_report"])
    del meta["tasks"][0]["red"]
    _reescreve(caminhos["build_report"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == (["red_not_declared"], [])


def test_red_not_declared_exit_zero(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    meta = _meta(caminhos["build_report"])
    meta["tasks"][0]["red"]["exit"] = 0
    _reescreve(caminhos["build_report"], tasks=meta["tasks"])
    assert _codigos(check(tmp_path)) == (["red_not_declared"], [])


def test_task_pulada_nao_exige_red(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    _reescreve(caminhos["build_report"], tasks=[{"id": "T1", "status": "skipped"}])
    assert _codigos(check(tmp_path)) == ([], [])


def test_claim_without_evidence(tmp_path):
    caminhos = _ate(tmp_path, "build_report")
    _reescreve(caminhos["build_report"], claims=[{"text": "ficou 3x mais rapido"}])
    assert _codigos(check(tmp_path)) == (["claim_without_evidence"], [])


def test_hypothesis_open_at_ship(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], hypothesis_outcome=None)
    assert _codigos(check(tmp_path)) == (["hypothesis_open_at_ship"], [])


def test_registry_unchecked(tmp_path):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], registries=["surface_lock"])
    recusa = check(tmp_path)["refused"]
    assert [r["code"] for r in recusa] == ["registry_unchecked"]
    assert "generated_reference" in recusa[0]["unlock"]
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: FAIL em cinco (`test_task_pulada_nao_exige_red` já passa)

- [ ] **Step 3: implementar** — antes de `_GATES`:

```python
def _gate_red(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, tarefa in enumerate(artefato.meta["tasks"]):
        if tarefa["status"] != "done":
            continue
        vermelho = tarefa.get("red")
        if not vermelho or vermelho["exit"] == 0:
            ctx.recusa("red_not_declared", artefato.path, f"tasks/{indice}/red",
                       f"registre o comando que falhou antes do codigo de {tarefa['id']} "
                       "(exit diferente de zero)")


def _gate_claims(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    for indice, afirmacao in enumerate(artefato.meta["claims"]):
        if not str(afirmacao.get("evidence_ref") or "").strip():
            ctx.recusa("claim_without_evidence", artefato.path, f"claims/{indice}/evidence_ref",
                       "aponte o arquivo, teste ou fact que sustenta a afirmacao")


def _gate_hypothesis(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if not artefato.meta.get("hypothesis_outcome"):
        ctx.recusa("hypothesis_open_at_ship", artefato.path, "hypothesis_outcome",
                   "feche a hipotese com confirmed, refuted ou abandoned, sem reescrever a "
                   "afirmacao (regra 21)")


def _gate_registries(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    define = ctx.artefatos.get("define")
    if define is None:
        return
    conhecidos = change_kinds()
    marcados = set(artefato.meta["registries"])
    vistos: set[str] = set()
    for chave in define.meta["change_kinds"]:
        tipo = conhecidos.get(chave)
        if tipo is None:
            continue
        for registro in tipo["registries"]:
            if registro in marcados or registro in vistos:
                continue
            vistos.add(registro)
            ctx.recusa("registry_unchecked", artefato.path, "registries",
                       f"{registro} e exigido por '{tipo['section']}' "
                       "(docs/gates-por-mudanca.md); rode o gate e liste-o")
```

E em `_GATES`:

```python
    "build_report": (_gate_order, _gate_upstream, _gate_red, _gate_claims),
    "ship": (_gate_order, _gate_upstream, _gate_hypothesis, _gate_registries),
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/checks.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): build and ship gates - declared red, evidence, closure, registries"
```

---

### Task 9: gates do perfil operador

**Files:**
- Modify: `sparkforge/sdd/checks.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
def test_case_missing_sem_case_id(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    _reescreve(caminhos["define"], case_id=None)
    assert _codigos(check(tmp_path)) == (["case_missing"], [])


def test_case_missing_case_diferente(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    for fase in ("design", "plan", "build_report", "ship"):
        caminhos[fase].unlink()
    (tmp_path / ".sparkforge" / "case.yaml").write_bytes(b"case_id: OUTRO\n")
    assert _codigos(check(tmp_path)) == (["case_missing"], [])


def test_change_missing(tmp_path):
    caminhos = feature_limpa(tmp_path, "operator")
    caminhos["ship"].unlink()
    (tmp_path / ".sparkforge" / "sandbox" / "S1").rmdir()
    assert _codigos(check(tmp_path)) == (["change_missing"], [])


def test_perfil_dev_nao_pede_case_nem_change(tmp_path):
    feature_limpa(tmp_path, "dev")
    assert not (tmp_path / ".sparkforge").exists()
    assert _codigos(check(tmp_path)) == ([], [])
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -k "case_missing or change_missing" -q`
Expected: FAIL nos três

- [ ] **Step 3: implementar** — imports no topo:

```python
from sparkforge.case.store import CASE_DIR, CASE_FILE
from sparkforge.change.sandbox import SANDBOX_DIR
```

Confira antes que `import sparkforge.change.sandbox` não arrasta nada pesado: `python -X importtime -c "import sparkforge.change.sandbox" 2>&1 | tail -3`. Se passar de ~0,3 s, troque o import por `SANDBOX_DIR = ".sparkforge/sandbox"` local com comentário apontando para `sparkforge/change/sandbox.py:40`.

Antes de `_GATES`:

```python
def _case_id_atual(repo: Path) -> str | None:
    arquivo = repo / CASE_DIR / CASE_FILE
    if not arquivo.is_file():
        return None
    try:
        dado = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    return dado.get("case_id") if isinstance(dado, dict) else None


def _gate_case(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if artefato.meta["profile"] != "operator":
        return
    declarado = artefato.meta.get("case_id")
    if not declarado or declarado != _case_id_atual(ctx.repo):
        ctx.recusa("case_missing", artefato.path, "case_id",
                   "abra o case com `sparkforge case open` e copie o case_id dele para o define")


def _gate_change(ctx: _Contexto, fase: str, artefato: Artifact) -> None:
    if artefato.meta["profile"] != "operator":
        return
    ident = artefato.meta.get("change_id")
    alvo = resolve_within(ctx.repo, f"{SANDBOX_DIR}/{ident}") if ident else None
    if alvo is None or not alvo.is_dir():
        ctx.recusa("change_missing", artefato.path, "change_id",
                   "o build do operador passa por `sparkforge change sandbox`; registre o id "
                   "do sandbox em change_id")
```

E em `_GATES`, acrescentar `_gate_case` ao fim de `"define"` e `_gate_change` ao fim de `"build_report"`.

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/checks.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): operator gates - case and sandbox must exist"
```

---

### Task 10: `status`

**Files:**
- Create: `sparkforge/sdd/status.py`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
from sparkforge.sdd.status import status


def test_status_mostra_fase_e_bloqueio(tmp_path):
    feature_limpa(tmp_path, feature="F1")
    caminhos = _ate(tmp_path / "outro", "design")  # repo separado so para montar
    destino = tmp_path / "docs" / "sdd" / "F2"
    destino.mkdir(parents=True)
    for fase in ("define", "design"):
        texto = caminhos[fase].read_bytes().decode("utf-8").replace("feature: F1", "feature: F2")
        texto = texto.replace("docs/sdd/F1/", "docs/sdd/F2/")
        (destino / f"{fase}.md").write_bytes(texto.encode("utf-8"))
    stamp(tmp_path, "docs/sdd/F2/design.md")
    _reescreve(destino / "design.md", decisions=[{"id": "D1", "choice": "c"}])
    saida = status(tmp_path)
    assert saida["root"] == "docs/sdd"
    por_nome = {f["feature"]: f for f in saida["features"]}
    assert por_nome["F1"] == {
        "feature": "F1", "phase": "ship", "status": "done", "profile": "dev",
        "next_phase": None, "refused": [], "unresolved": [],
    }
    assert por_nome["F2"]["phase"] == "design"
    assert por_nome["F2"]["next_phase"] == "plan"
    assert por_nome["F2"]["refused"] == ["rollback_missing"]


def test_status_sem_raiz(tmp_path):
    saida = status(tmp_path)
    assert saida["features"] == []
    assert [u["code"] for u in saida["unresolved"]] == ["root_missing"]
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -k status -q`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.sdd.status'`

- [ ] **Step 3: implementar** `sparkforge/sdd/status.py`:

```python
"""Em que fase cada feature esta, e o que a impede de avancar."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sparkforge.paths import resolve_within
from sparkforge.sdd import DEFAULT_ROOT, PHASES
from sparkforge.sdd.checks import check
from sparkforge.sdd.load import discover, load_artifact


def status(repo: Path | str, root: str = DEFAULT_ROOT) -> dict[str, Any]:
    relatorio = check(repo, root)
    raiz = resolve_within(Path(repo), root)
    if raiz is None or not raiz.is_dir():
        return {"root": root, "features": [], "unresolved": relatorio["unresolved"]}
    itens: list[dict[str, Any]] = []
    for nome, caminhos in sorted(discover(raiz).items()):
        atual = max(caminhos, key=PHASES.index)
        meta = load_artifact(caminhos[atual]).meta or {}
        posicao = PHASES.index(atual)
        itens.append({
            "feature": nome,
            "phase": atual,
            "status": meta.get("status"),
            "profile": meta.get("profile"),
            "next_phase": PHASES[posicao + 1] if posicao + 1 < len(PHASES) else None,
            "refused": sorted({r["code"] for r in relatorio["refused"] if r["feature"] == nome}),
            "unresolved": sorted(
                {u["code"] for u in relatorio["unresolved"] if u["feature"] == nome}
            ),
        })
    return {"root": root, "features": itens, "unresolved": []}
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/sdd/status.py tests/test_sdd.py
git commit -F <msg>   # "feat(sdd): status - current phase and what blocks it"
```

---

### Task 11: `_core` e a CLI

**Files:**
- Modify: `sparkforge/adapters/_core.py` (depois de `debate_referee`, linha ~3345)
- Modify: `sparkforge/adapters/cli.py` (parser depois do bloco `funcval`, linha ~1183; handlers depois de `_cmd_funcval_compare`, linha ~3425; `_DISPATCH` linha ~4545; `_dispatch` linha ~4654)
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
from sparkforge.adapters import _core
from sparkforge.adapters.cli import main


def test_cli_check_ok_e_recusa(tmp_path, capsys):
    caminhos = feature_limpa(tmp_path)
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    _reescreve(caminhos["ship"], hypothesis_outcome=None)
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 1
    saida = json.loads(capsys.readouterr().out)
    assert [r["code"] for r in saida["refused"]] == ["hypothesis_open_at_ship"]


def test_cli_so_lacuna_sai_zero(tmp_path, capsys):
    assert main(["sdd", "check", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_cli_status_e_stamp(tmp_path, capsys):
    caminhos = feature_limpa(tmp_path)
    assert main(["sdd", "status", "--repo", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["features"][0]["phase"] == "ship"
    _reescreve(caminhos["build_report"], claims=[{"text": "t", "evidence_ref": "x"}])
    assert main(["sdd", "stamp", "--repo", str(tmp_path), "docs/sdd/F1/ship.md"]) == 0
    assert json.loads(capsys.readouterr().out)["changed"] is True


def test_core_erros_acionaveis(tmp_path):
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_check(str(tmp_path / "nao-existe"))
    assert "sparkforge" in erro.value.message
    feature_limpa(tmp_path)
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_check(str(tmp_path), feature="NAO_HA")
    assert "sparkforge sdd status" in erro.value.message
    with pytest.raises(_core.AdapterError) as erro:
        _core.sdd_stamp(str(tmp_path), "docs/sdd/F1/define.md")
    assert "sparkforge sdd stamp" in erro.value.message
    assert erro.value.exit_code == 2
```

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -k "cli or core" -q`
Expected: FAIL (`argparse` sai com `SystemExit: 2` por comando desconhecido, e `_core` não tem `sdd_check`)

- [ ] **Step 3: implementar `_core`** — depois de `debate_referee`:

```python
def _raiz_do_repo(repo: str, verbo: str) -> Path:
    raiz = Path(repo)
    if not raiz.is_dir():
        raise AdapterError(
            f"repositorio nao encontrado: {repo}. Rode `sparkforge sdd {verbo} --repo <raiz>` "
            "apontando para a raiz que contem docs/sdd/.",
            exit_code=2,
        )
    return raiz


def sdd_check(
    repo: str, root_path: str = "docs/sdd", feature: str | None = None
) -> dict[str, Any]:
    """Os gates do SDD sobre `repo/root_path`. So le."""
    from sparkforge.sdd.checks import check

    raiz = _raiz_do_repo(repo, "check")
    relatorio = check(raiz, root_path, feature)
    if feature is not None and not relatorio["features"] and not relatorio["unresolved"]:
        raise AdapterError(
            f"feature {feature} nao existe em {root_path}. Rode `sparkforge sdd status --repo "
            f"{repo}` para listar as que existem.",
            exit_code=2,
        )
    return relatorio


def sdd_status(repo: str, root_path: str = "docs/sdd") -> dict[str, Any]:
    from sparkforge.sdd.status import status

    return status(_raiz_do_repo(repo, "status"), root_path)


def sdd_stamp(repo: str, path: str) -> dict[str, Any]:
    """Grava `upstream.sha256` em `path`. Unica escrita do SDD."""
    from sparkforge.sdd.stamp import StampError, stamp

    raiz = _raiz_do_repo(repo, "stamp")
    try:
        return stamp(raiz, path)
    except StampError as exc:
        raise AdapterError(
            f"{exc.code}: {exc.message}. Corrija o frontmatter e rode "
            f"`sparkforge sdd stamp --repo {repo} {path}` de novo.",
            exit_code=2,
        ) from exc
```

- [ ] **Step 4: implementar a CLI** — em `build_parser`, depois do bloco `funcval`:

```python
    # sdd -------------------------------------------------------------------
    sdd_p = sub.add_parser(
        "sdd",
        help=(
            "Confere os artefatos de spec em docs/sdd/<FEATURE>/<fase>.md: recusa por nome o "
            "que nao fecha, sem julgar a prosa."
        ),
    )
    sdd_sub = sdd_p.add_subparsers(dest="sdd_action", required=True)
    for nome, ajuda in (
        ("check", "Roda os gates. Sai 1 se houver recusa; lacuna sozinha sai 0."),
        ("status", "Fase atual de cada feature e o que a impede de avancar."),
    ):
        sdd_verbo_p = sdd_sub.add_parser(nome, help=ajuda)
        sdd_verbo_p.add_argument("--repo", required=True, help="Raiz do repositorio.")
        sdd_verbo_p.add_argument(
            "--root", default="docs/sdd", help="Pasta dos artefatos, relativa a --repo."
        )
        if nome == "check":
            sdd_verbo_p.add_argument("--feature", help="Confere so esta feature.")
    sdd_stamp_p = sdd_sub.add_parser(
        "stamp", help="Grava upstream.sha256 do artefato. Escreve so a linha do hash."
    )
    sdd_stamp_p.add_argument("--repo", required=True, help="Raiz do repositorio.")
    sdd_stamp_p.add_argument("path", help="Artefato, relativo a --repo.")
```

Handlers, depois de `_cmd_funcval_compare`:

```python
def _cmd_sdd_check(args: argparse.Namespace) -> int:
    relatorio = _core.sdd_check(args.repo, args.root, args.feature)
    _print(relatorio)
    return 1 if relatorio["refused"] else 0


def _cmd_sdd_status(args: argparse.Namespace) -> int:
    _print(_core.sdd_status(args.repo, args.root))
    return 0


def _cmd_sdd_stamp(args: argparse.Namespace) -> int:
    _print(_core.sdd_stamp(args.repo, args.path))
    return 0
```

Em `_DISPATCH`, depois das linhas de `funcval`:

```python
    ("sdd", "check"): _cmd_sdd_check,
    ("sdd", "status"): _cmd_sdd_status,
    ("sdd", "stamp"): _cmd_sdd_stamp,
```

Em `_dispatch`, depois de `or getattr(args, "funcval_action", None)`:

```python
        or getattr(args, "sdd_action", None)
```

`_tool_da_cli("sdd", "stamp")` já devolve `sparkforge_sdd_stamp`; o journal passa a valer para ele quando a Task 12 o registrar como escrita.

- [ ] **Step 5: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS. Se `test_cli_status_e_stamp` falhar dentro do journal (a Task 12 ainda não existe), é porque `journaled()` só conhece tools de `TOOLS`: sem a entrada, a CLI chama o handler direto — o teste deve passar mesmo assim.

- [ ] **Step 6: commit**

```bash
git add sparkforge/adapters/_core.py sparkforge/adapters/cli.py tests/test_sdd.py
git commit -F <msg>   # "feat(cli): sparkforge sdd check|status|stamp"
```

---

### Task 12: tools MCP e o journal

**Files:**
- Modify: `sparkforge/adapters/tools.py` (schemas de saída perto de `_DEBATE_REFEREE_SCHEMA`; entradas em `TOOLS` depois de `sparkforge_funcval_compare`; handlers depois de `_h_funcval_compare`; registro depois de `"sparkforge_funcval_compare": _h_funcval_compare,`)
- Modify: `sparkforge/journal/record.py:44-47`
- Test: `tests/test_sdd.py`

- [ ] **Step 1: testes que falham**

```python
from sparkforge.adapters.tools import TOOLS, call_tool
from sparkforge.journal import journaled


def _estruturado(resposta):
    # Antes de confiar nisto, veja como os testes existentes leem o retorno de
    # `call_tool` (`rtk proxy grep -n "call_tool(" tests/test_adapters_tools.py | head`)
    # e use o MESMO acesso: se o envelope trouxer chaves extras (`_meta`,
    # proveniencia), a paridade compara so o payload do verbo.
    return resposta.get("structuredContent", resposta)


def test_paridade_cli_mcp(tmp_path, capsys):
    caminhos = feature_limpa(tmp_path)
    _reescreve(caminhos["ship"], registries=[])
    main(["sdd", "check", "--repo", str(tmp_path)])
    pela_cli = json.loads(capsys.readouterr().out)
    pelo_mcp = _estruturado(call_tool("sparkforge_sdd_check", {"repo": str(tmp_path)}))
    assert pelo_mcp == pela_cli
    main(["sdd", "status", "--repo", str(tmp_path)])
    assert _estruturado(
        call_tool("sparkforge_sdd_status", {"repo": str(tmp_path)})
    ) == json.loads(capsys.readouterr().out)


def test_classes_das_tools():
    assert TOOLS["sparkforge_sdd_check"]["annotations"]["readOnlyHint"] is True
    assert TOOLS["sparkforge_sdd_status"]["annotations"]["readOnlyHint"] is True
    assert TOOLS["sparkforge_sdd_stamp"]["annotations"]["readOnlyHint"] is False
    assert "sparkforge_sdd_stamp" in journaled()
    assert "sparkforge_sdd_check" not in journaled()


def test_stamp_pelo_mcp_grava_no_journal(tmp_path):
    caminhos = feature_limpa(tmp_path)
    (tmp_path / ".sparkforge").mkdir(exist_ok=True)
    (tmp_path / ".sparkforge" / "case.yaml").write_bytes(b"case_id: C1\n")
    _reescreve(caminhos["build_report"], claims=[{"text": "t", "evidence_ref": "x"}])
    resposta = _estruturado(
        call_tool("sparkforge_sdd_stamp", {"repo": str(tmp_path), "path": "docs/sdd/F1/ship.md"})
    )
    assert resposta["changed"] is True
    linhas = (tmp_path / ".sparkforge" / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    eventos = [json.loads(linha) for linha in linhas]
    assert [e.get("event") for e in eventos][-2:] == ["started", "finished"]
    assert "docs/sdd/F1/ship.md" in json.dumps(eventos[-1]["outputs"])
```

Antes de escrever o último teste, confira os nomes de campo do evento: `python -c "import sparkforge.journal.record as r, inspect; print(inspect.getsource(r.Registro))" | head -60`. Se o campo não se chamar `event`, ajuste o teste ao nome real — não o código.

- [ ] **Step 2: rodar e ver falhar**

Run: `python -m pytest tests/test_sdd.py -k "paridade or classes or journal" -q`
Expected: FAIL com `KeyError: 'sparkforge_sdd_check'`

- [ ] **Step 3: implementar** — em `tools.py`, perto de `_DEBATE_REFEREE_SCHEMA`:

```python
_SDD_ITEM = {
    "type": "object",
    "required": ["code", "feature", "path", "unlock"],
    "properties": {
        "code": {"type": "string"},
        "feature": {"type": ["string", "null"]},
        "path": {"type": "string"},
        "field": {"type": ["string", "null"]},
        "unlock": {"type": "string"},
    },
}

_SDD_CHECK_SCHEMA = {
    "type": "object",
    "required": ["ok", "root", "features", "refused", "unresolved"],
    "properties": {
        "ok": {"type": "boolean"},
        "root": {"type": "string"},
        "features": {"type": "array", "items": {"type": "string"}},
        "refused": {"type": "array", "items": _SDD_ITEM},
        "unresolved": {"type": "array", "items": _SDD_ITEM},
    },
}

_SDD_STATUS_SCHEMA = {
    "type": "object",
    "required": ["root", "features", "unresolved"],
    "properties": {
        "root": {"type": "string"},
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["feature", "phase", "status", "profile", "next_phase",
                             "refused", "unresolved"],
                "properties": {
                    "feature": {"type": "string"},
                    "phase": {"type": "string"},
                    "status": {"type": ["string", "null"]},
                    "profile": {"type": ["string", "null"]},
                    "next_phase": {"type": ["string", "null"]},
                    "refused": {"type": "array", "items": {"type": "string"}},
                    "unresolved": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "unresolved": {"type": "array", "items": _SDD_ITEM},
    },
}

_SDD_STAMP_SCHEMA = {
    "type": "object",
    "required": ["path", "upstream", "sha256", "previous", "changed"],
    "properties": {
        "path": {"type": "string"},
        "upstream": {"type": "string"},
        "sha256": {"type": "string"},
        "previous": {"type": "string"},
        "changed": {"type": "boolean"},
    },
}
```

Confira se as outras tools declaram `outputSchema` com `oneOf` para o ramo de erro (`rtk proxy grep -n "_DEBATE_REFEREE_SCHEMA =" -A12 sparkforge/adapters/tools.py`); se sim, use o mesmo embrulho que elas usam em vez do objeto nu.

Entradas em `TOOLS`, depois de `sparkforge_funcval_compare`:

```python
    "sparkforge_sdd_check": {
        "description": (
            "Confere os artefatos de spec do SDD proprio (docs/sdd/<FEATURE>/<fase>.md: "
            "explore, define, design, plan, build_report, ship). Julga so o frontmatter: "
            "schema, ordem das fases, hash do upstream (cascata), cobertura dos acceptance "
            "tests, teste por task (TDD), rollback, red declarado, evidencia de afirmacao, "
            "hipotese fechada, registros exigidos pelo tipo de mudanca e, no perfil operator, "
            "case e sandbox existentes. Cada falha sai em `refused` com `code` e `unlock`; o "
            "que ele nao consegue decidir sai em `unresolved`. NAO julga a prosa e nao "
            "chama modelo."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string", "description": "Raiz do repositorio."},
                "root_path": {
                    "type": "string",
                    "description": "Pasta dos artefatos relativa a `repo` (padrao docs/sdd).",
                },
                "feature": {"type": "string", "description": "Confere so esta feature."},
            },
        },
        "outputSchema": _SDD_CHECK_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_sdd_status": {
        "description": (
            "Fase atual de cada feature do SDD, o status declarado, a proxima fase e os "
            "codigos de recusa e lacuna que a impedem de avancar. Mesmos gates de "
            "`sparkforge_sdd_check`, agrupados por feature."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo"],
            "properties": {
                "repo": {"type": "string", "description": "Raiz do repositorio."},
                "root_path": {
                    "type": "string",
                    "description": "Pasta dos artefatos relativa a `repo` (padrao docs/sdd).",
                },
            },
        },
        "outputSchema": _SDD_STATUS_SCHEMA,
        "annotations": _READ_ONLY,
    },
    "sparkforge_sdd_stamp": {
        "description": (
            "Grava `upstream.sha256` no frontmatter de um artefato SDD, com o hash de texto "
            "do upstream declarado. Muda so a linha do hash, preserva quebra de linha e "
            "corpo, e nao regrava quando o hash ja confere. Use depois de revisar uma fase "
            "cujo upstream mudou (`upstream_stale`)."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["repo", "path"],
            "properties": {
                "repo": {"type": "string", "description": "Raiz do repositorio."},
                "path": {"type": "string", "description": "Artefato, relativo a `repo`."},
            },
        },
        "outputSchema": _SDD_STAMP_SCHEMA,
        "annotations": _WRITE_IDEMPOTENT,
    },
```

Handlers, depois de `_h_funcval_compare`:

```python
def _h_sdd_check(args: dict[str, Any]) -> dict[str, Any]:
    return _core.sdd_check(
        args["repo"], args.get("root_path", "docs/sdd"), args.get("feature")
    )


def _h_sdd_status(args: dict[str, Any]) -> dict[str, Any]:
    return _core.sdd_status(args["repo"], args.get("root_path", "docs/sdd"))


def _h_sdd_stamp(args: dict[str, Any]) -> dict[str, Any]:
    return _core.sdd_stamp(args["repo"], args["path"])
```

Registro de handlers, depois de `"sparkforge_funcval_compare": _h_funcval_compare,`:

```python
    "sparkforge_sdd_check": _h_sdd_check,
    "sparkforge_sdd_status": _h_sdd_status,
    "sparkforge_sdd_stamp": _h_sdd_stamp,
```

Em `sparkforge/journal/record.py`, `_SAIDAS_POR_CHAVE`:

```python
_SAIDAS_POR_CHAVE: dict[str, tuple[str, ...]] = {
    "sparkforge_scan": ("outputs",),
    "sparkforge_receipt_emit": ("receipt_path",),
    "sparkforge_sdd_stamp": ("path",),
}
```

- [ ] **Step 4: rodar e ver passar**

Run: `python -m pytest tests/test_sdd.py -q`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add sparkforge/adapters/tools.py sparkforge/journal/record.py tests/test_sdd.py
git commit -F <msg>   # "feat(mcp): sdd check, status and stamp tools; stamp is journaled"
```

---

### Task 13: os registros manuais

Cada item abaixo é uma lista literal que cai vermelha com tool nova. Rode primeiro, veja cair, conserte:

Run: `python -m pytest tests/test_adapters_tools.py tests/test_harness_authorization.py tests/test_capability_parity.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_adapters_code_surface.py tests/test_fixtures_golden_mcp_parity.py -q`
Expected: FAIL nos pontos listados abaixo

**Files e edições:**

- [ ] **`tests/test_adapters_tools.py:~98`** — na lista literal da superfície, depois de `"sparkforge_funcval_compare",`:

```python
            "sparkforge_sdd_check",
            "sparkforge_sdd_status",
            "sparkforge_sdd_stamp",
```

- [ ] **`tests/test_adapters_tools.py` — `test_only_case_and_report_writers_are_not_read_only`** — no conjunto esperado, depois de `"sparkforge_scan",`:

```python
            # `sparkforge_sdd_stamp` grava `upstream.sha256` no artefato SDD, e so
            # essa linha. Idempotente: com o hash ja certo, nao regrava.
            "sparkforge_sdd_stamp",
```

- [ ] **`tests/test_adapters_tools.py` — construtor de argumentos reais** (a função que tem `if name == "sparkforge_debate_referee":`, linha ~2132), antes desse `if`:

```python
    if name in ("sparkforge_sdd_check", "sparkforge_sdd_status"):
        # Raiz sem docs/sdd de proposito: sai `root_missing` em `unresolved`, e o
        # payload valida contra o schema igual.
        return call_tool(name, {"repo": str(tmp_path)})

    if name == "sparkforge_sdd_stamp":
        pasta = tmp_path / "docs" / "sdd" / "F1"
        pasta.mkdir(parents=True)
        (pasta / "define.md").write_bytes(b"---\nsdd: 1\n---\n")
        (pasta / "design.md").write_bytes(
            b"---\nupstream:\n  path: docs/sdd/F1/define.md\n  sha256: \"\"\n---\n"
        )
        return call_tool(name, {"repo": str(tmp_path), "path": "docs/sdd/F1/design.md"})
```

- [ ] **`tests/test_adapters_tools.py:~3178`** — na lista de chamadas que falham com mensagem acionável, depois da linha de `sparkforge_receipt_verify`:

```python
        ("sparkforge_sdd_check", {"repo": "<tmp>/nao-existe"}),
        ("sparkforge_sdd_status", {"repo": "<tmp>/nao-existe"}),
        ("sparkforge_sdd_stamp", {"repo": "<tmp>", "path": "nao-existe.md"}),
```

- [ ] **`tests/test_harness_authorization.py`** — a contagem de tools com caminho sobe 3 (as três declaram `repo`; `stamp` também `path`). Troque o número afirmado por `+3` e acrescente ao bloco de comentários:

```python
        # N -> N+3 com `sdd_check`, `sdd_status` e `sdd_stamp` (2026-09-16): as
        # tres declaram `repo`, e `stamp` tambem `path`. As duas primeiras sao
        # `_READ_ONLY`, a terceira `_WRITE_IDEMPOTENT`. O conjunto de excecao nao
        # se move.
```

(N é o número que o teste imprime ao falhar.)

- [ ] **`tests/test_fixtures_golden_mcp_parity.py` — `NOVAS_DEPOIS_DO_GOLDEN`**, no fim do dicionário:

```python
    "sparkforge_sdd_check": "2026-09-16: gates do SDD proprio sobre docs/sdd",
    "sparkforge_sdd_status": "2026-09-16: fase e bloqueio de cada feature do SDD",
    "sparkforge_sdd_stamp": "2026-09-16: hash do upstream de um artefato SDD",
```

- [ ] **`parity.yaml`** — depois da capacidade de `funcval compare` (linha ~563):

```yaml
  - name: check spec artifacts against the SDD contract
    tools: [sparkforge_sdd_check, sparkforge_sdd_status]
    cli: [sdd check, sdd status]
    knowledge: [docs/gates-por-mudanca.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]

  - name: record the upstream hash of a spec artifact
    tools: [sparkforge_sdd_stamp]
    cli: [sdd stamp]
    knowledge: [docs/gates-por-mudanca.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      codex: [cli, files]
      copilot_ci: [cli, files]
```

Se `tests/test_capability_parity.py` recusar `knowledge: [docs/gates-por-mudanca.md]` (ele pode exigir caminho sob `knowledge/` ou `rules/`), use o que as capacidades vizinhas usam: `rules/catalog/README.md`.

- [ ] **`manifest.json`** — na lista `tools` (ordem alfabética), entre `sparkforge_scan` e `sparkforge_simulate`:

```json
    "sparkforge_sdd_check",
    "sparkforge_sdd_stamp",
    "sparkforge_sdd_status",
```

- [ ] **Coordenador** — `agents/sf-orchestrator.md` (fonte; nunca o espelho), acrescentar antes de `## Não faz`:

```markdown
## Spec da mudanca (SDD)

Quando o caso pede mudanca de codigo ou de job, a spec mora em
`docs/sdd/<FEATURE>/<fase>.md`. Antes de avancar de fase, rode
`sparkforge_sdd_check` (ou `sparkforge_sdd_status` para ver onde cada feature
esta). Depois de revisar uma fase cujo upstream mudou, rode
`sparkforge_sdd_stamp`. Recusa do check bloqueia a fase seguinte; lacuna diz o
que coletar. No perfil operator, o build passa por `sparkforge_change_sandbox`.
```

Depois:

```bash
cp .claude/agents/README.md "$TEMP/claude_agents_README.bak.md" 2>/dev/null || true
python scripts/sync_skills.py
cp "$TEMP/claude_agents_README.bak.md" .claude/agents/README.md 2>/dev/null || true
python scripts/sync_skills.py --check
```

- [ ] **Rodar de novo**

Run: `python -m pytest tests/test_adapters_tools.py tests/test_harness_authorization.py tests/test_capability_parity.py tests/test_agent_coverage.py tests/test_docs_coverage.py tests/test_adapters_code_surface.py tests/test_fixtures_golden_mcp_parity.py tests/test_agents_parity.py tests/test_sync_render.py -q`
Expected: PASS. Se cair algo fora desta lista, a memória `tool-nova-move-registros-manuais` lista os outros dezoito pontos conhecidos; conserte pelo motivo, nunca editando a expectativa sem provar que a tool mudou de lado.

- [ ] **Commit**

```bash
git add tests/ parity.yaml manifest.json agents/ .claude/agents .agents .github/agents
git commit -F <msg>   # "chore(sdd): register the three sdd tools in the manual registries"
```

---

### Task 14: superfície, referência gerada, `CLAUDE.md` e documentos

**Files:**
- Modify: `CLAUDE.md` (tabela de verbos), `docs/surface.lock.json`, `docs/guia/referencia/**`, `docs/claims.lock.json` e `docs/harness/*.md` (só se o gate pedir), `STATUS.md`, spec

- [ ] **Step 1: linha no `CLAUDE.md`** — na tabela "Os verbos que compõem", depois da linha de `funcval`:

```markdown
| A spec desta mudança está bem posta? | `sdd check` / `sdd status` / `sdd stamp` | o frontmatter de `docs/sdd/<FEATURE>/<fase>.md`; julga contrato, cascata por hash, cobertura e TDD declarado, nunca a prosa |
```

Run: `python -m pytest tests/test_bootstrap_budget.py -q`
Expected: PASS. Se o teto estourar, encurte a coluna da direita — não mexa no teto.

- [ ] **Step 2: referência gerada**

Run: `python scripts/gen_reference_docs.py && python -m pytest tests/test_reference_docs.py -q`
Expected: PASS

- [ ] **Step 3: superfície**

Run: `python scripts/check_surface_lock.py --update && git diff --stat docs/surface.lock.json`
Anote o crescimento em bytes que o script imprime; ele vai na mensagem de commit (regra 26).

- [ ] **Step 4: gate de lastro**

Run: `python scripts/check_vnext_claims.py`
Expected: lista de ids de alegação que mudaram (arquivo `.py` novo e tool nova movem `len(TOOLS)`). Remedie **pela lista de ids**, nunca por varredura. Se precisar de `--seed`, guarde só as entradas novas e restaure o resto (memória item 18).

- [ ] **Step 5: `STATUS.md` e spec** — em `STATUS.md`, registrar o subprojeto A do SDD próprio como entregue na seção de frentes (siga o formato das linhas vizinhas), com o número de tools **medido** (`python -c "from sparkforge.adapters.tools import TOOLS; print(len(TOOLS))"`). No spec, trocar `**Estado:** desenho aprovado, implementação não iniciada` por `**Estado:** implementado (subprojeto A)` e acrescentar ao fim uma seção `## 13. Desvios na implementação` listando qualquer diferença do que foi escrito (no mínimo: `explore` é opcional e só vira upstream do define quando existe; `feature` inexistente é erro de uso e não código do §5).

Run: `python -m pytest tests/test_docs_coverage.py -q` e, se a tabela de números do `STATUS.md` mudou, os gates da seção "Alterar a tabela *Números correntes*" de `docs/gates-por-mudanca.md`.

- [ ] **Step 6: commit**

```bash
git add CLAUDE.md docs/ STATUS.md
git commit -F <msg>
# "docs(sdd): verb row, generated reference and surface lock
#
#  Surface grows by <N> bytes: three tools (sdd check, status, stamp)."
```

---

### Task 15: verificação de fechamento

- [ ] **Step 1: gates rápidos**

```bash
git add -A sparkforge/sdd tests/test_sdd.py
python -m ruff check sparkforge/sdd sparkforge/adapters sparkforge/durable.py tests/test_sdd.py
python -m pytest tests/test_codeintel_security.py tests/test_arvore_versionada.py tests/test_facts_scan.py tests/test_sdd.py tests/test_durable.py -q
```

Expected: PASS. `test_facts_scan.py` reprova `glob`/`rglob` cru em `sparkforge/`; `sdd` usa `iter_source_files`, então deve passar. `test_arvore_versionada.py` exige `git add` nos arquivos novos (feito acima).

- [ ] **Step 2: regra 23**

Run: `python -c "import pathlib,re;t=''.join(p.read_text(encoding='utf-8') for p in pathlib.Path('sparkforge/sdd').rglob('*.py'));print(bool(re.search(r'\b(anthropic|openai|bedrock|litellm)\b',t)))"`
Expected: `False`

- [ ] **Step 3: wheel** (o `sdd` lê `schema/*.json` e `change_kinds.yaml` do disco)

Run: `python scripts/verify_wheel.py`
Expected: PASS. Se o wheel não levar os `.json`/`.yaml`, o conserto é no `pyproject.toml` (`[tool.hatch.build.targets.wheel]`), e aí vale também a seção de dependência de `docs/gates-por-mudanca.md`.

- [ ] **Step 4: lotes** — um processo de background por lote, nunca editando a árvore enquanto rodam (`tests/test_suite_batches.py::LOTES`): `a-c`, `d-e`, `f-sem-golden`, `g-z`, e `goldens-1` a `goldens-5` (a superfície MCP mudou). Com `.claude/agents/README.md` fora da árvore durante o lote `a-c`.

Expected: todos verdes. Vermelho que não seja do SDD: confira se já estava vermelho em `origin/main` antes de consertar.

- [ ] **Step 5: fechar** — use superpowers:finishing-a-development-branch.
