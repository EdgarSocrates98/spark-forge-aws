# SparkForge Fase 3a — Distribuição pip: Implementation Plan

> **Status: CONCLUÍDO em 2026-07-31.** As 9 tasks abaixo estão implementadas e
> verdes: 1792 → 1882 testes. Faixa de commits `a06d7f5` … `937799f`.
>
> Documento é registro histórico. Para o estado atual do repositório, leia
> [`../STATUS.md`](../STATUS.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** fazer `pip install sparkforge-aws` entregar o ciclo determinístico inteiro — extrair, julgar, rotear, retomar — em máquina que nunca viu o repositório, provado por paridade byte a byte com os goldens em Linux e Windows.

**Architecture:** o defeito central (catálogo ausente do artefato) se resolve trocando o backend de build para `hatchling` com `force-include`, que copia `rules/catalog/` e `knowledge/` para dentro do pacote no momento do build, sem duplicar arquivo em git. Nenhuma mudança no loader: `catalog_dir()` já resolve `env → raiz do repo → fallback no pacote`, e o fallback sempre existiu no código e nunca em disco. O trabalho de código é aditivo — localizar `knowledge/` a partir do pacote instalado. O gate de paridade reaproveita os 15 módulos `test_fixtures_golden_*.py` já existentes, executados sob o Python do venv, em vez de reimplementar a lógica de corpus.

**Tech Stack:** hatchling, `python -m build`, `twine`, pytest, GitHub Actions.

**Spec:** [`../specs/2026-07-31-sparkforge-fase3a-pip-design.md`](../specs/2026-07-31-sparkforge-fase3a-pip-design.md)

---

## Fatos do ambiente verificados antes de escrever este plano

- Backend atual: `setuptools>=68`. Wheel produzido hoje tem **43 arquivos**, zero de `rules/catalog/` ou `knowledge/`.
- Conversão para hatchling **já foi testada ponta a ponta**: wheel foi para 72 arquivos (11 catálogo, 19 knowledge), instalado em venv limpo fora do repo devolveu 48 regras e respondeu `rules lookup`. O `pyproject.toml` foi restaurado.
- `pyproject.toml` não tem `readme`, `license`, `authors`, `classifiers` nem `urls`.
- `.claude-plugin/plugin.json` declara `homepage` de `sparkforge-aws/spark-forge-aws`; o repositório real é `EdgarSocrates98/spark-forge-aws`.
- `knowledge/` tem **19 arquivos**; **23 das 48 regras** citam **11 arquivos distintos**, todos existentes. Formato da citação: `knowledge/<caminho>.md`.
- `pyproject.toml` tem `pythonpath = ["."]` em `[tool.pytest.ini_options]`. **É o que faz o repo vencer o site-packages** — o gate precisa sobrescrever para vazio.
- Suíte atual: 1792 testes. Rodar com `python -m pytest`, nunca `pytest` puro.
- `nomes sparkforge-aws` e `sparkforge` livres no PyPI em 2026-07-31.

---

## File Structure

**Criados:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/knowledge_ref.py` | Resolver a raiz de `knowledge/` e conter caminho de arquivo dentro dela |
| `scripts/verify_wheel.py` | Orquestrar build → venv → install → gate de paridade |
| `tests/test_knowledge_ref.py` | Resolução e contenção de caminho de knowledge |
| `tests/test_installed_provenance.py` | Opt-in: afirma que `sparkforge` veio do site-packages |
| `tests/test_packaging_metadata.py` | Metadata de publicação e URLs reais |
| `.github/workflows/release.yml` | Build + prova + rascunho de release; não publica |

**Modificados:**

| Arquivo | Mudança |
|---|---|
| `pyproject.toml` | Metadata (Task 1); backend hatchling + force-include (Task 2) |
| `.claude-plugin/plugin.json` | `homepage` real (Task 1) |
| `sparkforge/adapters/cli.py` | Verbo `knowledge path` (Task 4) |
| `sparkforge/adapters/_core.py` | `knowledge_path()`; `rules_lookup` devolve caminhos (Tasks 4 e 5) |
| `sparkforge/adapters/tools.py` | Tool `sparkforge_knowledge_path` (Task 4) |
| `.github/workflows/ci.yml` | Job `wheel` com matriz de SO (Task 7) |
| `parity.yaml`, `manifest.json` | Capacidade e tool novas (Task 4) |
| `README.md`, `docs/superpowers/STATUS.md` | Instalação por pip (Task 9) |

---

## Task 1: Metadata de publicação e URL real

Primeiro porque é independente do backend e porque `plugin.json` aponta hoje para um repositório que não existe — qualquer canal herda esse 404.

**Files:**
- Modify: `pyproject.toml`, `.claude-plugin/plugin.json`
- Test: `tests/test_packaging_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging_metadata.py
"""Metadata que o PyPI e o marketplace leem.

Sem `readme`, o pacote publicado aparece sem descricao. Sem `license`
declarado, o LICENSE do disco nao e legivel por ferramenta. Sem `urls`
correto, o link do pacote leva a lugar nenhum -- que e o estado de hoje no
plugin.json.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/EdgarSocrates98/spark-forge-aws"


def _pyproject() -> str:
    return (ROOT / "pyproject.toml").read_text(encoding="utf-8")


class TestPyprojectMetadata:
    def test_declares_readme(self):
        assert re.search(r'^readme\s*=\s*"README\.md"', _pyproject(), re.MULTILINE)

    def test_declares_license(self):
        assert re.search(r"^license\s*=", _pyproject(), re.MULTILINE)
        assert (ROOT / "LICENSE").is_file()

    def test_declares_authors(self):
        assert re.search(r"^authors\s*=", _pyproject(), re.MULTILINE)

    def test_declares_the_supported_pythons_as_classifiers(self):
        text = _pyproject()
        assert "Programming Language :: Python :: 3.10" in text
        assert "Programming Language :: Python :: 3.11" in text

    def test_urls_point_at_the_real_repository(self):
        assert REPO_URL in _pyproject()


class TestPluginManifest:
    def test_homepage_points_at_the_real_repository(self):
        data = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        assert data["homepage"] == REPO_URL

    def test_no_manifest_mentions_the_nonexistent_org(self):
        """`sparkforge-aws/spark-forge-aws` nao existe no GitHub. Instalar o
        plugin por esse link da 404, em silencio."""
        for name in ("pyproject.toml", ".claude-plugin/plugin.json", "manifest.json"):
            text = (ROOT / name).read_text(encoding="utf-8")
            assert "github.com/sparkforge-aws/" not in text, name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_packaging_metadata.py -v`
Expected: FAIL — `test_declares_readme`, `test_declares_license`, `test_declares_authors`, `test_declares_the_supported_pythons_as_classifiers`, `test_urls_point_at_the_real_repository`, `test_homepage_points_at_the_real_repository`, `test_no_manifest_mentions_the_nonexistent_org`

- [ ] **Step 3: Add the metadata to `pyproject.toml`**

Substitua o bloco `[project]` (linhas 5 a 13) por:

```toml
[project]
name = "sparkforge-aws"
version = "0.5.0"
description = "Agent skills and deterministic analyzers for AWS Glue PySpark, Parquet, Iceberg and Athena performance engineering"
readme = "README.md"
license = { file = "LICENSE" }
authors = [{ name = "Edgar Socrates Caria" }]
requires-python = ">=3.10"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Topic :: Software Development :: Quality Assurance",
    "Topic :: System :: Monitoring",
]
dependencies = [
    "PyYAML>=6.0",
    "jsonschema>=4.0",
]

[project.urls]
Homepage = "https://github.com/EdgarSocrates98/spark-forge-aws"
Repository = "https://github.com/EdgarSocrates98/spark-forge-aws"
Issues = "https://github.com/EdgarSocrates98/spark-forge-aws/issues"
```

- [ ] **Step 4: Corrigir a homepage do plugin**

Em `.claude-plugin/plugin.json`, troque a linha da `homepage`:

```json
  "homepage": "https://github.com/EdgarSocrates98/spark-forge-aws"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_packaging_metadata.py -v`
Expected: PASS, 7 tests

- [ ] **Step 6: A suíte inteira continua verde**

Run: `python -m pytest -q`
Expected: tudo verde, sem falha nova. A contagem sobe de 1792 para ~1799 (7 testes novos)

Se `test_requirements_mirror.py` falhar, o recorte do gerador pegou algo do bloco novo. Rode `python scripts/gen_requirements.py --check` para ver, e confira que `requirements.txt` não ganhou linha de `classifiers` ou `urls`.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .claude-plugin/plugin.json tests/test_packaging_metadata.py
git commit -m "build: declara metadata de publicacao e corrige a URL do repositorio"
```

---

## Task 2: Backend hatchling com force-include

O núcleo do spec. Depois desta task o artefato carrega catálogo e knowledge.

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_artifact_contents.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_artifact_contents.py
"""O artefato tem que carregar catalogo e knowledge.

Sem isto, `pip install` entrega `analyze` sem `judge` -- a camada `facts/`
embarca e a camada `rules/` nao. O teste constroi o wheel de verdade porque
inspecionar `pyproject.toml` provaria a intencao, nao o resultado: e o backend
que decide o que entra no zip.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> zipfile.ZipFile:
    out = tmp_path_factory.mktemp("dist")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out), str(ROOT)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"`python -m build` indisponivel ou falhou: {result.stderr[-400:]}")
    built = sorted(out.glob("*.whl"))
    assert built, "build terminou com sucesso e nao produziu wheel"
    return zipfile.ZipFile(built[0])


def _names(wheel: zipfile.ZipFile, prefix: str) -> list[str]:
    return [n for n in wheel.namelist() if n.startswith(prefix)]


class TestWheelCarriesTheKnowledgeLayer:
    def test_catalog_yaml_is_inside_the_package(self, wheel):
        found = _names(wheel, "sparkforge/rules/catalog/")
        assert [n for n in found if n.endswith(".yaml")], sorted(wheel.namelist())[:20]

    def test_routing_is_included_too(self, wheel):
        """`next_step` fica inerte sem routing.yaml, e o sintoma seria um
        roteamento vazio em vez de um erro."""
        assert "sparkforge/rules/catalog/routing.yaml" in wheel.namelist()

    def test_knowledge_is_inside_the_package(self, wheel):
        assert _names(wheel, "sparkforge/knowledge/")

    def test_schemas_survived_the_backend_swap(self, wheel):
        """`package-data` do setuptools embarcava os JSON Schemas. Se a troca de
        backend os perder, `validate_output` quebra no pacote instalado -- e a
        secao 5.2 da Fase 0 diz que finding sem schema nao e recusado."""
        assert _names(wheel, "sparkforge/findings/schemas/")

    def test_the_counts_are_not_zero(self, wheel):
        """Asserção de contagem: `force-include` sumindo num upgrade do
        hatchling nao quebraria import nenhum -- so devolveria catalogo
        vazio."""
        assert len(_names(wheel, "sparkforge/rules/catalog/")) >= 8
        assert len(_names(wheel, "sparkforge/knowledge/")) >= 15
```

- [ ] **Step 2: Instalar o `build` e rodar o teste para vê-lo falhar**

Run: `python -m pip install --quiet build && python -m pytest tests/test_artifact_contents.py -v`
Expected: FAIL — o wheel constrói, mas `sparkforge/rules/catalog/` e `sparkforge/knowledge/` não existem nele.

- [ ] **Step 3: Trocar o backend em `pyproject.toml`**

Substitua o bloco `[build-system]` (linhas 1 a 3):

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"
```

Substitua os dois blocos do setuptools:

```toml
[tool.setuptools.packages.find]
include = ["sparkforge*"]

[tool.setuptools.package-data]
sparkforge = ["findings/schemas/*.json"]
```

por:

```toml
[tool.hatch.build.targets.wheel]
packages = ["sparkforge"]

# `rules/catalog` e `knowledge` moram na RAIZ por decisao D-A da Fase 0: sao o
# terceiro degrau da escada de portabilidade, o YAML que um agente sem Python
# le direto. `force-include` os copia para dentro do pacote no momento do build,
# sem duplicar arquivo em git -- que e a unica forma de servir o pip sem corroer
# aquela decisao.
[tool.hatch.build.targets.wheel.force-include]
"rules/catalog" = "sparkforge/rules/catalog"
"knowledge" = "sparkforge/knowledge"

# O sdist recebe o MESMO mapeamento. `force-include` do target `wheel` nao cobre
# o sdist, e quem instalar a partir da fonte ficaria sem catalogo -- a mesma
# falha, um caminho adiante.
[tool.hatch.build.targets.sdist]
include = [
    "sparkforge",
    "rules/catalog",
    "knowledge",
    "README.md",
    "LICENSE",
    "pyproject.toml",
]

[tool.hatch.build.targets.sdist.force-include]
"rules/catalog" = "sparkforge/rules/catalog"
"knowledge" = "sparkforge/knowledge"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_artifact_contents.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Provar que o pacote instalado julga**

```bash
python -m build --wheel --outdir /tmp/sfdist .
python -m venv /tmp/sfvenv
/tmp/sfvenv/bin/python -m pip install --quiet /tmp/sfdist/*.whl
cd /tmp && /tmp/sfvenv/bin/python -c "from sparkforge.rules.loader import load_catalog; print(len(load_catalog()), 'regras')"
```

Expected: `48 regras`
No Windows, troque `/tmp/sfvenv/bin/python` por `/tmp/sfvenv/Scripts/python.exe`.

- [ ] **Step 6: A suíte inteira continua verde**

Run: `python -m pytest -q`
Expected: tudo verde. Contagem sobe ~5 (testes de artefato)

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/test_artifact_contents.py
git commit -m "build: hatchling com force-include embarca catalogo e knowledge"
```

---

## Task 3: Resolver a raiz de `knowledge/` a partir do pacote

`knowledge/` é citado em 7 pontos do código, **todos comentário ou docstring**. Nenhuma função lê aqueles arquivos. Sem esta task, os 19 arquivos embarcados na Task 2 são inalcançáveis.

**Files:**
- Create: `sparkforge/knowledge_ref.py`
- Test: `tests/test_knowledge_ref.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_knowledge_ref.py
"""Resolucao da raiz de knowledge, com a mesma disciplina do catalogo.

`knowledge_dir()` espelha `catalog_dir()` de proposito: mesma ordem de
precedencia, mesma recusa de caminho que escapa. Duas resolucoes com regras
diferentes no mesmo pacote seria a origem do proximo bug de path.
"""
from pathlib import Path

import pytest

from sparkforge.knowledge_ref import KnowledgeError, knowledge_dir, safe_knowledge_file

ROOT = Path(__file__).resolve().parents[1]


class TestResolution:
    def test_finds_the_repo_root_knowledge(self):
        assert knowledge_dir() == ROOT / "knowledge"

    def test_env_var_overrides(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(tmp_path))
        assert knowledge_dir() == tmp_path.resolve()

    def test_env_var_pointing_at_a_file_is_rejected(self, tmp_path, monkeypatch):
        target = tmp_path / "nao-e-diretorio.md"
        target.write_text("x", encoding="utf-8")
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(target))
        with pytest.raises(KnowledgeError, match="diretorio"):
            knowledge_dir()

    def test_env_var_pointing_nowhere_is_rejected(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SPARKFORGE_KNOWLEDGE", str(tmp_path / "ausente"))
        with pytest.raises(KnowledgeError, match="diretorio"):
            knowledge_dir()


class TestContainment:
    """`base` vem de variavel de ambiente e `name` pode vir de uma citacao no
    catalogo, que e dado editavel. Mesma superficie que obriga o avaliador de
    `expr` a ter whitelist."""

    def test_resolves_a_file_inside_the_root(self):
        target = safe_knowledge_file(ROOT / "knowledge", "glue/runtime-matrix.md")
        assert target.is_file()

    def test_rejects_parent_traversal(self):
        with pytest.raises(KnowledgeError, match="fora do diretorio"):
            safe_knowledge_file(ROOT / "knowledge", "../pyproject.toml")

    def test_rejects_absolute_path(self):
        with pytest.raises(KnowledgeError, match="fora do diretorio"):
            safe_knowledge_file(ROOT / "knowledge", str(ROOT / "pyproject.toml"))

    def test_missing_file_is_an_actionable_error(self):
        """Erro generico obriga o operador a adivinhar. A secao 7.3 da Fase 0
        exige causa, o que falta e o que resolve."""
        with pytest.raises(KnowledgeError, match="nao existe"):
            safe_knowledge_file(ROOT / "knowledge", "glue/arquivo-que-nao-existe.md")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_knowledge_ref.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sparkforge.knowledge_ref'`

- [ ] **Step 3: Write the implementation**

```python
# sparkforge/knowledge_ref.py
"""Localizacao dos arquivos de `knowledge/` a partir do pacote.

Existe porque `knowledge/` passou a ser embarcado no artefato (Fase 3a) e
nenhum codigo sabia encontra-lo: as referencias no pacote eram todas comentario
e docstring. Empacotar 19 arquivos que ninguem consegue localizar seria peso sem
consumidor.

Espelha `sparkforge/rules/loader.py` na ordem de precedencia e na contencao de
caminho. Duas resolucoes com regras diferentes no mesmo pacote seriam a origem
do proximo bug de path.
"""
from __future__ import annotations

import os
from pathlib import Path


class KnowledgeError(ValueError):
    """Raiz de knowledge inexistente, ou caminho que escapa dela."""


def knowledge_dir() -> Path:
    """Raiz de knowledge: env var -> raiz do repo -> pacote.

    A mesma ordem de `catalog_dir()`. No repositorio a raiz vence, e o
    comportamento e identico ao de sempre; instalado por pip, so o fallback
    existe.
    """
    override = os.environ.get("SPARKFORGE_KNOWLEDGE")
    if override:
        resolved = Path(override).expanduser().resolve()
        if not resolved.is_dir():
            raise KnowledgeError(
                f"SPARKFORGE_KNOWLEDGE aponta para {resolved}, que nao e um diretorio existente"
            )
        return resolved

    repo_root = Path(__file__).resolve().parents[1]
    candidate = repo_root / "knowledge"
    if candidate.is_dir():
        return candidate

    return Path(__file__).resolve().parent / "knowledge"


def safe_knowledge_file(base: Path, name: str) -> Path:
    """Resolve `name` dentro de `base` e recusa o que escapar dele."""
    root = Path(base).expanduser().resolve()
    target = (root / name).resolve()
    if root != target and root not in target.parents:
        raise KnowledgeError(f"caminho fora do diretorio de knowledge: {target}")
    if not target.exists():
        raise KnowledgeError(
            f"{name} nao existe em {root}. "
            f"Liste o que ha com: sparkforge knowledge path"
        )
    return target
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_knowledge_ref.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add sparkforge/knowledge_ref.py tests/test_knowledge_ref.py
git commit -m "feat(knowledge): resolve a raiz de knowledge a partir do pacote"
```

---

## Task 4: Verbo `knowledge path` na CLI e no MCP

**Files:**
- Modify: `sparkforge/adapters/_core.py`, `sparkforge/adapters/cli.py`, `sparkforge/adapters/tools.py`, `parity.yaml`, `manifest.json`
- Test: `tests/test_adapters_knowledge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapters_knowledge.py
"""Superficie de knowledge na CLI e no MCP.

Escape hatch barato: qualquer consumidor que precise LER um arquivo de
knowledge precisa primeiro saber onde ele esta, e num pacote instalado isso
esta dentro do site-packages.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from sparkforge.adapters import _core  # noqa: E402
from sparkforge.adapters.tools import TOOLS, call_tool  # noqa: E402


class TestCore:
    def test_without_file_returns_the_root(self):
        result = _core.knowledge_path()
        assert Path(result["root"]).is_dir()
        assert result["file"] is None

    def test_with_file_returns_the_resolved_path(self):
        result = _core.knowledge_path(file="glue/runtime-matrix.md")
        assert Path(result["file"]).is_file()
        assert result["file"].endswith("runtime-matrix.md")

    def test_lists_available_files_relative_to_the_root(self):
        """Listar e o que torna o verbo utilizavel sem adivinhacao."""
        result = _core.knowledge_path()
        assert "glue/runtime-matrix.md" in result["available"]
        assert all(not f.startswith("/") for f in result["available"])

    def test_missing_file_raises_adapter_error_not_a_traceback(self):
        with pytest.raises(_core.AdapterError) as excinfo:
            _core.knowledge_path(file="glue/nao-existe.md")
        assert "nao existe" in str(excinfo.value)

    def test_traversal_is_refused(self):
        with pytest.raises(_core.AdapterError):
            _core.knowledge_path(file="../pyproject.toml")


class TestCli:
    def test_knowledge_path_prints_json_with_the_root(self):
        result = subprocess.run(
            [sys.executable, "-m", "sparkforge.adapters.cli", "knowledge", "path"],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        assert Path(json.loads(result.stdout)["root"]).is_dir()

    def test_knowledge_path_with_file(self):
        result = subprocess.run(
            [
                sys.executable, "-m", "sparkforge.adapters.cli",
                "knowledge", "path", "--file", "glue/runtime-matrix.md",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        assert result.returncode == 0, result.stderr
        assert Path(json.loads(result.stdout)["file"]).is_file()


class TestMcpTool:
    def test_the_tool_is_declared(self):
        assert "sparkforge_knowledge_path" in TOOLS

    def test_the_tool_answers(self):
        payload = call_tool("sparkforge_knowledge_path", {})
        assert Path(payload["root"]).is_dir()


class TestManifestsAgree:
    def test_manifest_lists_the_new_tool(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        assert "sparkforge_knowledge_path" in manifest["tools"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters_knowledge.py -v`
Expected: FAIL — `AttributeError: module 'sparkforge.adapters._core' has no attribute 'knowledge_path'`

- [ ] **Step 3: Implementar em `_core.py`**

Acrescente o import no topo do arquivo, junto dos outros imports de `sparkforge`:

```python
from sparkforge.knowledge_ref import KnowledgeError, knowledge_dir, safe_knowledge_file
```

E acrescente a função logo após `rules_lookup` (a seção termina no comentário `# validate`):

```python
def knowledge_path(file: str | None = None) -> dict[str, Any]:
    """Resolve a raiz de knowledge, e opcionalmente um arquivo dentro dela.

    Sem `file`, devolve a raiz e a lista do que ha. Um consumidor instalado por
    pip nao tem como adivinhar o caminho dentro do site-packages, e listar e o
    que torna o verbo utilizavel sem tentativa e erro.
    """
    try:
        root = knowledge_dir()
    except KnowledgeError as exc:
        raise AdapterError(str(exc), exit_code=2) from exc

    available = sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )

    resolved: str | None = None
    if file:
        try:
            resolved = str(safe_knowledge_file(root, file))
        except KnowledgeError as exc:
            raise AdapterError(str(exc), exit_code=2) from exc

    return {"root": str(root), "file": resolved, "available": available}
```

- [ ] **Step 4: Acrescentar o verbo na CLI**

Em `sparkforge/adapters/cli.py`, logo antes do bloco `# rules lookup`, acrescente:

```python
    # knowledge path --------------------------------------------------------
    knowledge_p = sub.add_parser(
        "knowledge", help="Localiza os arquivos de conhecimento versionado."
    )
    knowledge_sub = knowledge_p.add_subparsers(dest="knowledge_action", required=True)
    knowledge_path_p = knowledge_sub.add_parser(
        "path", help="Imprime a raiz de knowledge e, com --file, um arquivo dentro dela."
    )
    knowledge_path_p.add_argument("--file")
```

Acrescente o handler junto dos outros `_cmd_*`, logo depois de `_cmd_rules_lookup`
(linha 812):

```python
def _cmd_knowledge_path(args: argparse.Namespace) -> int:
    _print(_core.knowledge_path(file=args.file))
    return 0
```

`_print` é o emissor único do módulo (`json.dumps(..., indent=2,
ensure_ascii=False)`, linha 57). Usar `print` direto aqui quebraria os acentos do
catálogo no Windows, que é exatamente o defeito que `_ensure_utf8_streams`
existe para evitar.

Registre no `_DISPATCH` (linha 882), junto de `("rules", "lookup")`:

```python
    ("knowledge", "path"): _cmd_knowledge_path,
```

E acrescente `knowledge_action` à cadeia de `sub_action` em `_dispatch` (linha 916):

```python
        or getattr(args, "knowledge_action", None)
```

Sem essa última linha o despacho procura `("knowledge", None)`, não acha, e cai
no erro de comando desconhecido — com o parser aceitando o comando. Falha
confusa, e é o passo que se esquece.

- [ ] **Step 5: Declarar a tool MCP**

Em `sparkforge/adapters/tools.py`, acrescente a entrada em `TOOLS`, seguindo a forma das vizinhas:

```python
    "sparkforge_knowledge_path": {
        "description": (
            "Resolve a raiz dos arquivos de conhecimento versionado e, "
            "opcionalmente, um arquivo dentro dela. Use antes de tentar LER "
            "knowledge: num pacote instalado por pip o caminho fica dentro do "
            "site-packages e nao e adivinhavel."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Caminho relativo, ex.: glue/runtime-matrix.md",
                }
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "root": {"type": "string"},
                "file": {"type": ["string", "null"]},
                "available": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["root", "available"],
        },
        "annotations": {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    },
```

E o handler, junto dos outros `_h_*`:

```python
def _h_knowledge_path(args: dict[str, Any]) -> dict[str, Any]:
    return _core.knowledge_path(file=args.get("file"))
```

E registre no mapa de handlers:

```python
    "sparkforge_knowledge_path": _h_knowledge_path,
```

- [ ] **Step 6: Atualizar `manifest.json` e `parity.yaml`**

Em `manifest.json`, acrescente `"sparkforge_knowledge_path"` à lista `tools` — `tests/test_docs_coverage.py` compara essa lista com `TOOLS.keys()` e falha se divergirem.

Em `parity.yaml`, acrescente a capacidade:

```yaml
  - name: localizar os arquivos de conhecimento versionado
    tools: [sparkforge_knowledge_path]
    cli: [knowledge path]
    knowledge: [knowledge/INDEX.md]
    platforms:
      claude_code: [mcp, cli, files]
      devin_desktop: [mcp, cli, files]
      devin_cli: [mcp, cli, files]
      copilot_ci: [cli, files]
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_adapters_knowledge.py tests/test_docs_coverage.py tests/test_capability_parity.py -v`
Expected: PASS

- [ ] **Step 8: A suíte inteira continua verde**

Run: `python -m pytest -q`
Expected: tudo verde. Contagem sobe ~10

- [ ] **Step 9: Commit**

```bash
git add sparkforge/adapters manifest.json parity.yaml tests/test_adapters_knowledge.py
git commit -m "feat(adapters): expoe knowledge path na CLI e no MCP"
```

---

## Task 5: `rules lookup` devolve os caminhos de knowledge citados

23 das 48 regras citam knowledge na `explanation`. A regra 4 do `AGENT_PROTOCOL` já obriga o agente a chamar `rules_lookup` em vez de lembrar limiar — o caminho chega junto, sem etapa nova no protocolo.

**Files:**
- Modify: `sparkforge/adapters/_core.py`
- Test: `tests/test_adapters_rules_knowledge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapters_rules_knowledge.py
"""`rules lookup` entrega o caminho do knowledge que a regra cita.

A regra 4 do AGENT_PROTOCOL obriga consultar em vez de lembrar. Se a consulta
devolve a citacao `knowledge/glue/runtime-matrix.md` como texto solto, o agente
instalado por pip nao consegue abrir o arquivo -- ele esta no site-packages.
Devolver o caminho resolvido fecha isso sem passo novo.
"""
from pathlib import Path

from sparkforge.adapters import _core


def _rule(payload: dict, rule_id: str) -> dict:
    for rule in payload["rules"]:
        if rule["id"] == rule_id:
            return rule
    raise AssertionError(f"{rule_id} ausente na resposta")


class TestKnowledgeRefsAreResolved:
    def test_a_rule_that_cites_knowledge_gets_resolved_paths(self):
        payload = _core.rules_lookup(id=["SF-ENV-001"])
        rule = _rule(payload, "SF-ENV-001")
        refs = rule["knowledge_refs"]
        assert refs, "SF-ENV-001 cita knowledge/glue/runtime-matrix.md"
        assert refs[0]["ref"] == "knowledge/glue/runtime-matrix.md"
        assert Path(refs[0]["path"]).is_file()

    def test_a_rule_without_citation_gets_an_empty_list_not_a_missing_key(self):
        """Chave ausente obriga o consumidor a usar `.get`; lista vazia e um
        contrato estavel."""
        payload = _core.rules_lookup(limit=100)
        for rule in payload["rules"]:
            assert isinstance(rule["knowledge_refs"], list)

    def test_every_resolved_path_exists(self):
        payload = _core.rules_lookup(limit=100)
        for rule in payload["rules"]:
            for ref in rule["knowledge_refs"]:
                assert Path(ref["path"]).is_file(), (rule["id"], ref)

    def test_a_citation_pointing_nowhere_is_reported_not_silently_dropped(self):
        """Citacao quebrada e defeito de catalogo. Sumir com ela esconderia o
        defeito; `path: null` o mostra ao operador."""
        rule = {
            "id": "SF-X-001",
            "explanation": "Ver knowledge/glue/arquivo-inexistente.md secao 1.",
        }
        refs = _core.knowledge_refs_of(rule)
        assert refs == [{"ref": "knowledge/glue/arquivo-inexistente.md", "path": None}]

    def test_the_same_file_cited_twice_appears_once(self):
        rule = {
            "id": "SF-X-002",
            "explanation": "Ver knowledge/glue/runtime-matrix.md.",
            "validation": ["Conferir knowledge/glue/runtime-matrix.md de novo."],
        }
        assert len(_core.knowledge_refs_of(rule)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_adapters_rules_knowledge.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'knowledge_refs_of'`

- [ ] **Step 3: Write the implementation**

Em `sparkforge/adapters/_core.py`, acrescente o import de `re` no topo se ainda não houver, e a função antes de `rules_lookup`:

```python
# Citacao de knowledge no catalogo tem sempre a forma `knowledge/<caminho>.<ext>`.
# Ancorar no prefixo literal evita casar caminho de outra coisa que termine em
# `.md`, como um link externo dentro da mesma frase.
_KNOWLEDGE_REF = re.compile(r"knowledge/[A-Za-z0-9_\-/]+\.(?:md|sql)")

# Campos onde a citacao aparece hoje. Varrer a regra inteira pegaria tambem o
# corpo de `sources`, cujo `url` nao e caminho local.
_KNOWLEDGE_FIELDS = ("explanation", "proposed_change", "validation", "risks", "tradeoffs")


def knowledge_refs_of(rule: dict[str, Any]) -> list[dict[str, Any]]:
    """Citacoes de knowledge da regra, com o caminho resolvido de cada uma.

    `path: None` significa citacao que nao resolve -- defeito de catalogo, e o
    relatorio precisa mostra-lo em vez de sumir com a citacao.
    """
    blob = " ".join(str(rule.get(field, "")) for field in _KNOWLEDGE_FIELDS)

    seen: set[str] = set()
    refs: list[dict[str, Any]] = []
    for ref in _KNOWLEDGE_REF.findall(blob):
        if ref in seen:
            continue
        seen.add(ref)

        path: str | None = None
        try:
            root = knowledge_dir()
            path = str(safe_knowledge_file(root, ref[len("knowledge/") :]))
        except KnowledgeError:
            path = None
        refs.append({"ref": ref, "path": path})

    return sorted(refs, key=lambda r: r["ref"])
```

- [ ] **Step 4: Ligar em `rules_lookup`**

Em `rules_lookup`, substitua a linha que monta `clean`:

```python
    clean = [{k: v for k, v in r.items() if k != "_source_file"} for r in filtered]
```

por:

```python
    clean = []
    for rule in filtered:
        entry = {k: v for k, v in rule.items() if k != "_source_file"}
        entry["knowledge_refs"] = knowledge_refs_of(rule)
        clean.append(entry)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_adapters_rules_knowledge.py -v`
Expected: PASS, 5 tests

- [ ] **Step 6: Declarar o campo em `_RULE_ITEM`**

`sparkforge_rules_lookup` usa `outputSchema: _RULES_LOOKUP_SCHEMA`, cuja lista
`rules` tem `"items": _RULE_ITEM` — schema **fechado**, definido em
`sparkforge/adapters/tools.py:757`. Sem declarar o campo novo, o SDK reprova o
`structuredContent` e toda chamada da tool falha.

Acrescente em `_RULE_ITEM["properties"]`:

```python
        "knowledge_refs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["ref", "path"],
                "properties": {
                    "ref": {"type": "string"},
                    "path": {"type": ["string", "null"]},
                },
            },
        },
```

Não acrescente a `required` de `_RULE_ITEM`: `validate_output` valida findings
que vêm do LLM, e exigir um campo que só o adaptador preenche reprovaria
recomendação legítima.

- [ ] **Step 7: A suíte inteira continua verde**

Run: `python -m pytest -q`
Expected: tudo verde. Contagem sobe ~5

Se `tests/test_adapters_tools.py` reprovar por validação de `structuredContent`,
o Step 6 não foi aplicado no lugar certo — o campo tem que estar em `_RULE_ITEM`,
não no `_RULES_LOOKUP_SCHEMA` de fora.

- [ ] **Step 8: Commit**

```bash
git add sparkforge/adapters tests/test_adapters_rules_knowledge.py
git commit -m "feat(rules): lookup devolve o caminho resolvido do knowledge citado"
```

---

## Task 6: A asserção de procedência

Sem esta task, o gate da Task 7 compara o repositório consigo mesmo e passa sempre. É a mesma classe de defeito do transporte HTTP na Fase 1 e do `_call_tool`: teste que exercita a camada errada.

**Files:**
- Create: `tests/test_installed_provenance.py`

- [ ] **Step 1: Write the test**

Este teste não segue o ciclo vermelho-verde: ele é um *skip* por default e só tem sentido sob o gate. O que se prova aqui é que ele **pula** no repositório e **exigiria** site-packages quando ligado.

```python
# tests/test_installed_provenance.py
"""Afirma que `sparkforge` veio do pacote instalado, nao do repositorio.

Opt-in por `SPARKFORGE_VERIFY_INSTALLED=1`. Sem isto o gate de paridade e
teatro: se o repositorio estiver no sys.path, `import sparkforge` pega o
codigo-fonte, os goldens batem com eles mesmos, e o teste passa sem provar que
o ARTEFATO funciona.

Nao basta configurar `cwd` e `PYTHONSAFEPATH`. Configuracao se perde num
refactor de workflow; assercao nao.
"""
import os
from pathlib import Path

import pytest

import sparkforge

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("SPARKFORGE_VERIFY_INSTALLED") != "1",
    reason="so roda sob o gate do artefato (scripts/verify_wheel.py)",
)


def _package_root() -> Path:
    assert sparkforge.__file__, "sparkforge sem __file__: import de namespace package?"
    return Path(sparkforge.__file__).resolve().parent


class TestProvenance:
    def test_sparkforge_is_not_imported_from_the_repository(self):
        package = _package_root()
        assert ROOT not in package.parents and package != ROOT / "sparkforge", (
            f"sparkforge foi importado de {package}, que esta dentro do repositorio "
            f"{ROOT}. O gate estaria comparando o repo consigo mesmo. "
            f"Rode a partir de um cwd fora do repo e com PYTHONSAFEPATH=1."
        )

    def test_sparkforge_lives_in_site_packages(self):
        package = _package_root()
        assert "site-packages" in package.parts, (
            f"sparkforge veio de {package}, fora de site-packages"
        )

    def test_the_catalog_comes_from_inside_the_package(self):
        """Se o catalogo vier da raiz de um repo qualquer que exista no cwd, o
        artefato nao esta sendo exercitado."""
        from sparkforge.rules.loader import catalog_dir

        assert _package_root() in catalog_dir().parents

    def test_the_packaged_catalog_is_complete(self):
        from sparkforge.rules.loader import load_catalog

        rules = load_catalog()
        assert len(rules) >= 48, f"catalogo embarcado com {len(rules)} regras"
        assert not [r for r in rules if r.get("blocked_on")]

    def test_knowledge_comes_from_inside_the_package(self):
        from sparkforge.knowledge_ref import knowledge_dir

        assert _package_root() in knowledge_dir().parents
```

- [ ] **Step 2: Verificar que ele pula no repositório**

Run: `python -m pytest tests/test_installed_provenance.py -v`
Expected: 5 skipped

- [ ] **Step 3: Verificar que ele reprova quando ligado dentro do repositório**

Run: `SPARKFORGE_VERIFY_INSTALLED=1 python -m pytest tests/test_installed_provenance.py -q`
Expected: FAIL — é o comportamento correto: dentro do repositório, `sparkforge` vem do repositório. Prova que a asserção morde.

No Windows: `$env:SPARKFORGE_VERIFY_INSTALLED=1; python -m pytest tests/test_installed_provenance.py -q`

- [ ] **Step 4: Commit**

```bash
git add tests/test_installed_provenance.py
git commit -m "test: asserção de procedência para o gate do artefato"
```

---

## Task 7: O gate de paridade

Reaproveita os 15 módulos `test_fixtures_golden_*.py`. Reimplementar a lógica de corpus seria um segundo contrato para manter divergir do primeiro.

**Files:**
- Create: `scripts/verify_wheel.py`
- Test: `tests/test_verify_wheel.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verify_wheel.py
"""Testes do orquestrador do gate.

O gate em si constroi artefato e cria venv -- caro demais para a suite. Aqui se
prova a MONTAGEM do comando, que e onde os erros silenciosos moram: um
`-o pythonpath=` esquecido faz o pytest do venv importar o repositorio, e o gate
inteiro vira teatro.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_wheel import GOLDEN_MODULES, pytest_command  # noqa: E402


class TestPytestCommand:
    def test_overrides_pythonpath_to_empty(self):
        """`pyproject.toml` declara `pythonpath = ["."]`. Sem sobrescrever, o
        repositorio entra no sys.path e vence o site-packages."""
        cmd = pytest_command(Path("/venv/bin/python"), ROOT)
        assert "-o" in cmd
        assert "pythonpath=" in cmd

    def test_runs_the_provenance_module_first(self):
        """Se a procedencia falha, comparar golden nao tem sentido."""
        cmd = pytest_command(Path("/venv/bin/python"), ROOT)
        modules = [c for c in cmd if "test_" in str(c)]
        assert "provenance" in str(modules[0])

    def test_runs_every_golden_module(self):
        cmd = " ".join(str(c) for c in pytest_command(Path("/venv/bin/python"), ROOT))
        for module in GOLDEN_MODULES:
            assert module in cmd, module

    def test_uses_the_venv_python_not_the_current_one(self):
        cmd = pytest_command(Path("/venv/bin/python"), ROOT)
        assert str(cmd[0]) == str(Path("/venv/bin/python"))


class TestGoldenModuleDiscovery:
    def test_discovers_every_golden_module_on_disk(self):
        """Corpus novo sem entrada aqui sairia do gate em silencio."""
        on_disk = {p.name for p in (ROOT / "tests").glob("test_fixtures_golden*.py")}
        assert set(GOLDEN_MODULES) == on_disk

    def test_there_is_more_than_one(self):
        assert len(GOLDEN_MODULES) >= 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_verify_wheel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.verify_wheel'`

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Gate do artefato: o pacote instalado reproduz os goldens byte a byte?

Constroi sdist e wheel, instala o wheel num venv limpo, e roda os modulos de
golden ja existentes SOB O PYTHON DO VENV. Se o pacote instalado produz os
mesmos facts e findings que o repositorio, o canal pip esta em paridade.

Por que reaproveitar os modulos de golden em vez de reimplementar a comparacao:
as 74 fixtures ja sao o contrato, verificado no CI a cada commit. Um comparador
proprio seria um segundo contrato para manter divergir do primeiro -- e o
primeiro a divergir seria o novo, porque ninguem o le.

A guarda que sustenta tudo esta em `tests/test_installed_provenance.py`, ligada
aqui por `SPARKFORGE_VERIFY_INSTALLED=1`. Sem ela, um `sys.path` errado faria o
pytest importar o repositorio e comparar o codigo-fonte consigo mesmo.

Uso:
    python scripts/verify_wheel.py                # constroi, instala e verifica
    python scripts/verify_wheel.py --keep         # nao apaga o diretorio temporario
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GOLDEN_MODULES = sorted(p.name for p in (ROOT / "tests").glob("test_fixtures_golden*.py"))
PROVENANCE_MODULE = "test_installed_provenance.py"


def venv_python(venv: Path) -> Path:
    """Interpretador do venv, nos dois layouts."""
    windows = venv / "Scripts" / "python.exe"
    return windows if windows.exists() else venv / "bin" / "python"


def pytest_command(python: Path, root: Path) -> list[str]:
    """Comando do gate.

    `-o pythonpath=` sobrescreve o `pythonpath = ["."]` do pyproject. Sem isso o
    repositorio entra no sys.path e vence o site-packages -- e o gate passaria
    comparando o repo consigo mesmo.

    A procedencia vem PRIMEIRO: se o import veio do lugar errado, comparar
    golden nao significa nada.
    """
    modules = [str(root / "tests" / PROVENANCE_MODULE)]
    modules += [str(root / "tests" / name) for name in GOLDEN_MODULES]
    return [str(python), "-m", "pytest", "-q", "-o", "pythonpath=", *modules]


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    printable = " ".join(str(c) for c in command)
    print(f"$ {printable}", flush=True)
    return subprocess.run(command, check=False, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--keep", action="store_true", help="Nao apaga o diretorio temporario.")
    args = parser.parse_args(argv)

    workdir = Path(tempfile.mkdtemp(prefix="sparkforge-gate-"))
    dist = workdir / "dist"
    venv = workdir / "venv"

    try:
        if _run([sys.executable, "-m", "build", "--outdir", str(dist), str(ROOT)]).returncode:
            print("build falhou", file=sys.stderr)
            return 1

        wheels = sorted(dist.glob("*.whl"))
        sdists = sorted(dist.glob("*.tar.gz"))
        if not wheels or not sdists:
            print(f"esperava wheel e sdist em {dist}, achei {[p.name for p in dist.iterdir()]}",
                  file=sys.stderr)
            return 1

        if _run([sys.executable, "-m", "venv", str(venv)]).returncode:
            return 1

        python = venv_python(venv)
        install = [str(python), "-m", "pip", "install", "--quiet", str(wheels[0]), "pytest"]
        if _run(install).returncode:
            return 1

        # `cwd` fora do repositorio e a primeira guarda; a assercao de
        # procedencia e a que sustenta. As duas, porque configuracao se perde.
        env = dict(os.environ)
        env["SPARKFORGE_VERIFY_INSTALLED"] = "1"
        env["PYTHONSAFEPATH"] = "1"
        env.pop("SPARKFORGE_CATALOG", None)
        env.pop("SPARKFORGE_KNOWLEDGE", None)

        result = _run(pytest_command(python, ROOT), cwd=str(workdir), env=env)
        if result.returncode:
            print("gate de paridade REPROVOU", file=sys.stderr)
            return 1

        if _run([str(python), "-m", "pip", "install", "--quiet", "twine"]).returncode:
            return 1
        if _run([str(python), "-m", "twine", "check", str(wheels[0]), str(sdists[0])]).returncode:
            print("twine check reprovou", file=sys.stderr)
            return 1

        print(f"\nOK: {wheels[0].name} e {sdists[0].name} em paridade com os goldens.")
        return 0
    finally:
        if args.keep:
            print(f"artefatos preservados em {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_verify_wheel.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Rodar o gate de verdade**

Run: `python scripts/verify_wheel.py`
Expected: termina com `OK: sparkforge_aws-0.5.0-py3-none-any.whl e sparkforge_aws-0.5.0.tar.gz em paridade com os goldens.` e código de saída 0.

Se reprovar em `test_installed_provenance`, o `sys.path` está trazendo o repositório — confira que `-o pythonpath=` está no comando.
Se reprovar num golden, o pacote instalado produz resultado diferente do repositório: é o defeito que este gate existe para pegar, e a causa está no que o `force-include` embarcou.

- [ ] **Step 6: Commit**

```bash
git add scripts/verify_wheel.py tests/test_verify_wheel.py
git commit -m "test: gate de paridade do artefato contra os goldens"
```

---

## Task 8: CI com matriz Linux e Windows, e o workflow de release

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Test: `tests/test_ci_workflow.py` (acrescentar classes)

- [ ] **Step 1: Write the failing test**

Acrescente ao final de `tests/test_ci_workflow.py`:

```python
RELEASE = ROOT / ".github" / "workflows" / "release.yml"


def _load_release():
    return yaml.safe_load(RELEASE.read_text(encoding="utf-8"))


class TestWheelGateJob:
    """O gate do artefato roda nos dois sistemas operacionais.

    Golden e gravado com LF forcado e path de subject e normalizado para `/`. O
    que escapar disso so aparece no Windows.
    """

    def test_ci_has_a_wheel_job(self):
        assert "wheel" in _load()["jobs"]

    def test_the_wheel_job_runs_on_both_operating_systems(self):
        matrix = _load()["jobs"]["wheel"]["strategy"]["matrix"]
        assert "ubuntu-latest" in matrix["os"]
        assert "windows-latest" in matrix["os"]

    def test_the_wheel_job_calls_the_gate(self):
        runs = [
            step.get("run", "")
            for step in _load()["jobs"]["wheel"]["steps"]
        ]
        assert any("verify_wheel.py" in run for run in runs)

    def test_the_wheel_job_is_separate_from_the_test_job(self):
        """Construir artefato e criar venv custa mais de um minuto e nao depende
        da versao de Python. Dentro da matriz 3.10/3.11 rodaria quatro vezes."""
        assert "verify_wheel" not in str(_load()["jobs"]["test"])


class TestReleaseWorkflow:
    def test_exists_and_is_valid_yaml(self):
        assert RELEASE.is_file()
        assert _load_release() is not None

    def test_is_manual_only(self):
        """Release automatico em push publicaria por acidente, e versao no PyPI
        nao se reescreve -- so se yanka."""
        triggers = _load_release().get("on", _load_release().get(True))
        assert "workflow_dispatch" in triggers
        assert "push" not in triggers
        assert "pull_request" not in triggers

    def test_does_not_publish_to_pypi(self):
        text = RELEASE.read_text(encoding="utf-8")
        assert "twine upload" not in text
        assert "pypa/gh-action-pypi-publish" not in text

    def test_refuses_a_tag_that_disagrees_with_the_package_version(self):
        text = RELEASE.read_text(encoding="utf-8")
        assert "sparkforge.__version__" in text or "__version__" in text

    def test_runs_the_gate_before_producing_anything(self):
        runs = [
            step.get("run", "")
            for job in _load_release()["jobs"].values()
            for step in job.get("steps", [])
        ]
        assert any("verify_wheel.py" in run for run in runs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ci_workflow.py -v`
Expected: FAIL — `KeyError: 'wheel'` e `assert RELEASE.is_file()`

- [ ] **Step 3: Acrescentar o job ao `ci.yml`**

Ao final de `.github/workflows/ci.yml`, depois do job `test`:

```yaml
  wheel:
    # Job proprio, fora da matriz 3.10/3.11: construir artefato e criar venv
    # custa mais de um minuto e o resultado nao depende da versao de Python.
    # Depende do sistema operacional -- golden e gravado com LF forcado e path
    # de subject e normalizado para `/`.
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install build tooling
        run: python -m pip install --quiet build
      - name: Artifact parity gate
        run: python scripts/verify_wheel.py
```

- [ ] **Step 4: Criar o `release.yml`**

```yaml
name: release

# Constroi, prova e PARA. Nao publica no PyPI.
#
# Publicar e ato humano: versao publicada no PyPI nao se reescreve, so se yanka.
# Este workflow prepara o artefato e o anexa a um release em rascunho; o
# `twine upload` fica com o mantenedor, com credencial dele. Quando houver
# Trusted Publishing configurado, vira um job a mais aqui -- nao um redesenho.
on:
  workflow_dispatch:
    inputs:
      tag:
        description: "Tag do release, ex.: v0.5.0"
        required: true

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install build tooling
        run: python -m pip install --quiet build

      - name: Tag agrees with the package version
        # Guarda no unico passo irreversivel do desenho. Sem ela e possivel
        # publicar 0.5.0 sob a tag v0.6.0, e o PyPI nao aceita reescrita.
        run: |
          PKG=$(python -c "import sys; sys.path.insert(0,'.'); import sparkforge; print(sparkforge.__version__)")
          TAG="${{ github.event.inputs.tag }}"
          if [ "v$PKG" != "$TAG" ]; then
            echo "tag $TAG diverge da versao do pacote v$PKG" >&2
            exit 1
          fi
          echo "versao confirmada: $PKG"

      - name: Artifact parity gate
        run: python scripts/verify_wheel.py

      - name: Build artifacts to publish
        run: python -m build --outdir dist .

      - name: Draft GitHub Release with the artifacts
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "${{ github.event.inputs.tag }}" \
            --draft \
            --title "${{ github.event.inputs.tag }}" \
            --notes "Artefatos construidos e verificados pelo gate de paridade. Publicacao no PyPI e manual." \
            dist/*
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ci_workflow.py -v`
Expected: PASS, 23 tests

- [ ] **Step 6: A suíte inteira continua verde**

Run: `python -m pytest -q`
Expected: tudo verde. Contagem sobe ~9 (testes de workflow)

- [ ] **Step 7: Commit**

```bash
git add .github/workflows tests/test_ci_workflow.py
git commit -m "ci: gate do artefato em Linux e Windows, e release que nao publica"
```

---

## Task 9: Varredura de aceitação e documentação

**Files:**
- Modify: `README.md`, `docs/superpowers/STATUS.md`
- Test: `tests/test_docs_coverage.py` (acrescentar)

- [ ] **Step 1: Write the failing test**

Acrescente à classe `TestReadme` em `tests/test_docs_coverage.py`:

```python
    def test_documents_pip_install(self):
        """O canal pip da secao 9 so vale se estiver documentado; agente que
        nao sabe instalar nao instala."""
        assert "pip install sparkforge-aws" in self.README

    def test_documents_that_the_installed_package_carries_the_catalog(self):
        lowered = self.README.lower()
        assert "catálogo" in lowered or "catalogo" in lowered
        assert "knowledge" in lowered
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_coverage.py -v`
Expected: FAIL — `test_documents_pip_install`

- [ ] **Step 3: Documentar no README**

Na seção de canais de distribuição do `README.md`, acrescente:

```markdown
### Instalação por pip

```bash
pip install sparkforge-aws            # nucleo: analisar e julgar
pip install "sparkforge-aws[aws]"     # + coletores AWS (boto3)
pip install "sparkforge-aws[mcp]"     # + servidor MCP (stdio e HTTP)
```

O pacote instalado carrega o **catálogo de regras** e a base de **knowledge**
dentro dele, então o ciclo inteiro — `analyze`, `judge`, `next-step`, `resume`,
`rules lookup` — funciona sem o repositório em disco. É o que permite a um
agente autônomo trabalhar num sandbox efêmero.

Para localizar os arquivos de knowledge dentro do pacote instalado:

```bash
sparkforge knowledge path
sparkforge knowledge path --file glue/runtime-matrix.md
```

A paridade entre o pacote instalado e o repositório é verificada no CI: o wheel
é construído, instalado num venv limpo e reproduz as 74 fixtures byte a byte, em
Linux e Windows.
```

- [ ] **Step 4: Atualizar o `STATUS.md`**

Em `docs/superpowers/STATUS.md`, na seção de fases, substitua o bloco da Fase 3 por:

```markdown
### Fase 3a — distribuição pip — **CONCLUÍDA** (2026-07-31)

Documentos: [spec](../specs/2026-07-31-sparkforge-fase3a-pip-design.md) ·
[plan](2026-07-31-sparkforge-fase3a-pip.md).

`pip install sparkforge-aws` entrega o ciclo determinístico inteiro sem o
repositório em disco. Backend `hatchling` com `force-include` embarca
`rules/catalog/` e `knowledge/` no artefato sem duplicar arquivo em git,
preservando a decisão D-A da Fase 0. Gate de paridade byte a byte contra os
goldens, em Linux e Windows.

### Fase 3b, 3c, 3d — **NÃO INICIADAS**

Marketplace de plugin, export de Playbook/Knowledge Devin, MCP HTTP hospedado.
Cada um com spec próprio.

### Cobertura de EMR — **NÃO INICIADA**, próxima na fila

Fora da §16. `RuntimeContext` conhece `glue`, `spark`, `python`, `iceberg` e
`athena`, e não `emr`. Num runtime sem chave `glue`, 44 das 48 regras ainda são
avaliadas — a análise de código e execução é agnóstica por construção. Falta o
eixo de infraestrutura: release label, instance fleets, EMR Serverless, EMR on
EKS, e a área `SF-EMR`.
```

Atualize também a tabela **Números correntes** com os valores reais após esta fase.

- [ ] **Step 5: Varredura dos 11 critérios de aceitação do spec**

Rode e confira um a um:

```bash
python -m pytest -q                          # 11: suite verde e maior
python scripts/verify_wheel.py               # 1,2,3,4,7: artefato, paridade, procedencia, twine
python -m pip install -e . --quiet           # 8: editable sem regressao
python -c "from sparkforge.rules.loader import load_catalog; print(len(load_catalog()))"
python -m ruff check sparkforge scripts tests
python scripts/gen_requirements.py --check
python scripts/sync_skills.py --check
```

Critério 5 e 6, a partir do venv que `--keep` preserva:

```bash
python scripts/verify_wheel.py --keep
# no diretorio impresso ao final:
<workdir>/venv/bin/sparkforge knowledge path --file glue/runtime-matrix.md
<workdir>/venv/bin/sparkforge rules lookup --id SF-ENV-001
```

Critério 9: `grep -r "sparkforge-aws/spark-forge-aws" .` não pode devolver nada fora de `docs/`.
Critério 10: coberto por `tests/test_ci_workflow.py::TestReleaseWorkflow`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest -q`
Expected: tudo verde. Total final em torno de 1840

- [ ] **Step 7: Commit**

```bash
git add README.md docs/superpowers/STATUS.md tests/test_docs_coverage.py
git commit -m "docs: documenta o canal pip e fecha a Fase 3a no STATUS"
```

---

## Resultado esperado

| | Antes | Depois |
|---|---|---|
| Arquivos no wheel | 43 | ~72 |
| Catálogo no artefato | 0 | 11 arquivos |
| Knowledge no artefato | 0 | 19 arquivos |
| `judge` a partir do pip | falha | funciona |
| Tools MCP | 28 | 29 |
| Testes | 1792 | ~1839 |
| Gate de artefato | nenhum | Linux + Windows |
