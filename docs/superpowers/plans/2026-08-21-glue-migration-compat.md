# Compatibilidade de migração Glue por par de versões — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analisar compatibilidade de um job Glue entre um par arbitrário de versões, acumulando os breaking changes de cada degrau do caminho, com o fato de versão vindo de dado com procedência e o julgamento vindo de regras do catálogo.

**Architecture:** A matriz de versões sai do código e vira `knowledge/glue/runtime-matrix.yaml` com `sources` e `retrieved`. Um resolvedor expande `origem → alvo` nos degraus intermediários. Um extrator novo emite facts de migração; regras `SF-MIG` os julgam, cada uma declarando em `runtime_scope` a faixa onde vale. O motor chama o `judge` existente uma vez por degrau e agrega — nenhuma bifurcação do engine.

**Tech Stack:** Python 3.10/3.11 (stdlib + PyYAML, já dependência), pytest, o catálogo de regras e o modelo `Fact`/`Finding` existentes.

**Spec:** [`../specs/2026-08-21-glue-migration-compat-design.md`](../specs/2026-08-21-glue-migration-compat-design.md)

---

## Convenções deste repositório que valem para todas as tasks

- Comentários e docstrings em português, explicando *por quê*, nunca *o quê*.
- `python -m ruff check sparkforge scripts tests` não pode acusar nada novo nos arquivos tocados. Limite de linha 100.
- Nenhum teste afirma contagem copiada (`len(rules) == 9`). Conte derivando, ou asserte estrutura.
- `Fact` é observação ancorada e **nunca** contém juízo nem limiar (`sparkforge/findings/models.py:31`). Limiar mora na regra.
- Todo extrator declara `EMITTED_KINDS` fechado — `tests/test_rules_catalog_reachability.py` usa a união deles para provar que nenhuma regra é inalcançável.
- `runtime_scope` guarda **versão de runtime**. O que gateia por natureza do artefato é `requires_facts`. `rules/catalog/athena.yaml` registra o erro de camada oposto e por que ele apagaria uma área inteira em silêncio.

## File Structure

| arquivo | responsabilidade |
|---|---|
| `knowledge/glue/runtime-matrix.yaml` | criar — matriz de versões com `sources` e `retrieved`. Dado, não código. |
| `sparkforge/facts/runtime_matrix.py` | criar — carrega e valida o YAML. Fonte única da matriz. |
| `sparkforge/facts/runtime_detect.py` | modificar — apagar `GLUE_MATRIX`, consumir o loader. |
| `sparkforge/migration/version_path.py` | criar — expande `origem → alvo` em degraus. |
| `sparkforge/facts/migration.py` | criar — extrator dos oito kinds `mig.*`. |
| `rules/catalog/glue-migration.yaml` | criar — área `SF-MIG`. |
| `sparkforge/migration/assessment.py` | criar — agrega findings por degrau em `MigrationAssessment` com gates. |
| `fixtures/migration/<caso>/` | criar — golden por caso, no formato `meta.yaml` + `input/` + `expected/`. |
| `tests/test_runtime_matrix.py` | criar — paridade YAML↔MD, ausência de versão hardcoded. |
| `tests/test_version_path.py` | criar — degraus, par genérico, alvo desconhecido. |
| `tests/test_facts_migration.py` | criar — um teste por kind. |
| `tests/test_fixtures_golden_migration.py` | criar — runner golden do domínio. |
| `tests/test_migration_assessment.py` | criar — gates e recomendação. |
| `sparkforge/migration/glue/analyzer.py` | decidir na Task 11 — medir consumidor antes de apagar. |

Arquivos pequenos e por responsabilidade: matriz, caminho, extração, julgamento, agregação. O extrator não conhece versões; o resolvedor não conhece regras; o assessment não conhece código de job.

---

### Task 1: Matriz de versões como dado

**Files:**
- Create: `knowledge/glue/runtime-matrix.yaml`
- Create: `sparkforge/facts/runtime_matrix.py`
- Create: `tests/test_runtime_matrix.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runtime_matrix.py
from pathlib import Path

from sparkforge.facts import runtime_matrix

ROOT = Path(__file__).resolve().parents[1]


class TestMatrizDeVersoes:
    def test_carrega_as_versoes_que_o_codigo_conhecia(self):
        matriz = runtime_matrix.load()
        # As quatro que `GLUE_MATRIX` trazia. Nao asserta o total: versao nova
        # entra por dado, e um total copiado quebraria com numero para bumpar.
        for versao in ("3.0", "4.0", "5.0", "5.1"):
            assert versao in matriz, versao

    def test_cada_versao_declara_runtime_e_procedencia(self):
        for versao, linha in runtime_matrix.load().items():
            assert linha["spark"], versao
            assert linha["python"], versao
            assert linha["sources"], f"{versao} sem fonte"
            assert linha["retrieved"], f"{versao} sem data de consulta"

    def test_toda_fonte_esta_no_lock_de_fontes(self):
        vigiadas = runtime_matrix.watched_sources()
        for versao, linha in runtime_matrix.load().items():
            for fonte in linha["sources"]:
                assert fonte in vigiadas, f"{versao}: {fonte} fora do sources.lock.json"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_runtime_matrix.py -v`
Expected: FAIL com `ImportError: cannot import name 'runtime_matrix' from 'sparkforge.facts'`

- [ ] **Step 3: Write the data file**

`knowledge/glue/runtime-matrix.yaml`. Preencha `spark`, `python`, `scala`, `java`, `iceberg` com os valores que `GLUE_MATRIX` já afirmava — eles não estão sendo inventados aqui, estão mudando de lugar. `sources` precisa citar uma URL que **já exista** em `knowledge/sources.lock.json`; leia o lock e use a chave literal. `retrieved` recebe a data em que você conferiu a página.

```yaml
# Matriz de runtime do AWS Glue. Dado, nunca constante em Python.
#
# POR QUE ESTE ARQUIVO EXISTE: o fato de versao morava em dois lugares --
# `GLUE_MATRIX` compilado em `sparkforge/facts/runtime_detect.py` e a prosa de
# `knowledge/glue/runtime-matrix.md` -- sem nada que forcasse os dois a
# concordarem. Versao e fato externo: ela muda por decisao da AWS, nao do
# repositorio, entao precisa carregar fonte e data de consulta como qualquer
# outro fato externo deste projeto.
schema_version: 1
versions:
  "5.1":
    spark: "3.5.6"
    python: "3.11"
    iceberg: "1.10.0"
    sources: ["<URL literal presente em knowledge/sources.lock.json>"]
    retrieved: "<AAAA-MM-DD em que voce conferiu>"
  "5.0":
    spark: "3.5.4"
    python: "3.11"
    iceberg: "1.7.1"
    sources: ["<mesma URL ou outra ja vigiada>"]
    retrieved: "<AAAA-MM-DD>"
  "4.0":
    spark: "3.3.0"
    python: "3.10"
    iceberg: "1.0.0"
    sources: ["<...>"]
    retrieved: "<AAAA-MM-DD>"
  "3.0":
    spark: "3.1.1"
    python: "3.7"
    iceberg: "0.13.1"
    sources: ["<...>"]
    retrieved: "<AAAA-MM-DD>"
```

Se nenhuma URL de release notes do Glue estiver no lock, acrescente-a ao lock pelo mecanismo que o repositório já usa para fontes vigiadas, e diga no relatório qual foi.

- [ ] **Step 4: Write the loader**

```python
# sparkforge/facts/runtime_matrix.py
"""Fonte unica da matriz de runtime do Glue.

O dado mora em `knowledge/glue/runtime-matrix.yaml` porque versao e fato
EXTERNO: muda por decisao da AWS e precisa carregar fonte e data. Constante em
Python nao carrega procedencia e envelhece sem que nada acuse -- o mesmo defeito
que `tests/test_docs_coverage.py` combate em outra superficie.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "knowledge" / "glue" / "runtime-matrix.yaml"
SOURCES_LOCK = ROOT / "knowledge" / "sources.lock.json"


@lru_cache(maxsize=1)
def load() -> dict[str, dict[str, Any]]:
    dados = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8"))
    versoes = dados.get("versions")
    if not isinstance(versoes, dict) or not versoes:
        raise ValueError(f"{MATRIX_PATH} sem bloco `versions` utilizavel")
    return versoes


@lru_cache(maxsize=1)
def watched_sources() -> frozenset[str]:
    dados = json.loads(SOURCES_LOCK.read_text(encoding="utf-8"))
    return frozenset(dados["sources"])


def known_versions() -> tuple[str, ...]:
    """Versoes ordenadas da mais antiga para a mais nova."""
    return tuple(sorted(load(), key=lambda v: tuple(int(p) for p in v.split("."))))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_runtime_matrix.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add knowledge/glue/runtime-matrix.yaml sparkforge/facts/runtime_matrix.py tests/test_runtime_matrix.py
git commit -m "feat(migration): matriz de runtime do Glue como dado com procedencia"
```

Stage apenas esses três caminhos. A árvore tem alterações não commitadas de outro trabalho — nunca `git add -A` nem `git add .`.

---

### Task 2: Apagar `GLUE_MATRIX` do código

**Files:**
- Modify: `sparkforge/facts/runtime_detect.py:51`
- Modify: `tests/test_runtime_matrix.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_runtime_matrix.py
class TestSemVersaoNoCodigo:
    def test_nenhuma_versao_de_glue_hardcoded_fora_do_loader(self):
        import re

        # A matriz e dado. Se uma versao voltar a ser constante em Python, ela
        # volta a envelhecer sem fonte e sem data -- exatamente o arranjo que a
        # Task 1 desfez.
        alvo = re.compile(r'"(?:3|4|5|6)\.\d+"\s*:\s*\{')
        ofensores = []
        for arquivo in (ROOT / "sparkforge").rglob("*.py"):
            if arquivo.name == "runtime_matrix.py":
                continue
            if alvo.search(arquivo.read_text(encoding="utf-8")):
                ofensores.append(str(arquivo.relative_to(ROOT)))
        assert ofensores == [], f"matriz de versao em codigo: {ofensores}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_runtime_matrix.py::TestSemVersaoNoCodigo -v`
Expected: FAIL apontando `sparkforge/facts/runtime_detect.py`, e possivelmente as matrizes de EMR do mesmo arquivo.

Se o teste acusar as matrizes de EMR, **não as apague**: elas estão fora do escopo desta fase. Restrinja o padrão do teste ao dicionário de Glue nomeadamente, e escreva no comentário que EMR fica como dívida registrada, com a razão — a mesma disciplina que `sparkforge/facts/secrets.py` aplicou ao não migrar as três cópias existentes.

- [ ] **Step 3: Substituir a constante pelo loader**

Em `sparkforge/facts/runtime_detect.py`, apague o bloco `GLUE_MATRIX = {...}` e troque cada leitura por uma consulta ao loader:

```python
from sparkforge.facts import runtime_matrix

# `GLUE_MATRIX` saiu daqui na fase SF-MIG: versao e fato externo e agora mora em
# `knowledge/glue/runtime-matrix.yaml`, com fonte e data. Ver o docstring de
# `sparkforge/facts/runtime_matrix.py`.
def _glue_row(versao: str) -> dict[str, str]:
    return runtime_matrix.load().get(versao, {})
```

Ajuste os pontos de uso para `_glue_row(...)`. Não mude o comportamento observável: os mesmos inputs devem produzir os mesmos facts.

- [ ] **Step 4: Run the affected suites**

Run: `python -m pytest tests/test_runtime_matrix.py tests/test_facts_runtime.py -v`
Expected: PASS. Se `tests/test_facts_runtime.py` não existir com esse nome, descubra o arquivo real com `python -m pytest tests -k runtime --collect-only -q` e rode-o.

Run: `python -m pytest -q -k "runtime or golden"`
Expected: PASS — os goldens gravados provam que o comportamento não mudou.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/runtime_detect.py tests/test_runtime_matrix.py
git commit -m "refactor(migration): runtime_detect le a matriz do dado, nao de constante"
```

---

### Task 3: Resolvedor de caminho de versão

**Files:**
- Create: `sparkforge/migration/version_path.py`
- Create: `tests/test_version_path.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_version_path.py
import pytest

from sparkforge.migration import version_path


class TestCaminhoDeVersao:
    def test_expande_os_degraus_intermediarios(self):
        assert version_path.steps("4.0", "5.1") == [("4.0", "5.0"), ("5.0", "5.1")]

    def test_par_adjacente_tem_um_degrau_so(self):
        assert version_path.steps("5.0", "5.1") == [("5.0", "5.1")]

    def test_origem_igual_ao_alvo_nao_tem_degrau(self):
        assert version_path.steps("5.1", "5.1") == []

    def test_alvo_anterior_a_origem_e_erro_nomeado(self):
        with pytest.raises(ValueError, match="alvo anterior"):
            version_path.steps("5.1", "4.0")

    def test_versao_desconhecida_diz_qual_e_o_que_existe(self):
        with pytest.raises(ValueError) as erro:
            version_path.steps("4.0", "9.9")
        assert "9.9" in str(erro.value)
        assert "5.1" in str(erro.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_version_path.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.migration.version_path'`

- [ ] **Step 3: Write minimal implementation**

```python
# sparkforge/migration/version_path.py
"""Expande um par origem/alvo nos degraus intermediarios da matriz.

POR QUE ISSO EXISTE SEPARADO DO PLANO DE EXECUCAO: o §6.2 do prompt de migracao
distingue migracao direta OPERACIONAL de analise CUMULATIVA obrigatoria. Quem
migra pode saltar 4.0 para 6.0 num movimento so; quem ANALISA nao pode, porque
os breaking changes se acumulam degrau a degrau e um salto esconde os do meio.
"""
from __future__ import annotations

from sparkforge.facts import runtime_matrix


def steps(source: str, target: str) -> list[tuple[str, str]]:
    conhecidas = runtime_matrix.known_versions()
    for versao in (source, target):
        if versao not in conhecidas:
            raise ValueError(
                f"versao {versao!r} fora da matriz; conhecidas: {', '.join(conhecidas)}"
            )
    inicio = conhecidas.index(source)
    fim = conhecidas.index(target)
    if fim < inicio:
        raise ValueError(f"alvo anterior a origem: {source!r} -> {target!r}")
    return [(conhecidas[i], conhecidas[i + 1]) for i in range(inicio, fim)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_version_path.py -v`
Expected: PASS, 5 testes

- [ ] **Step 5: Commit**

```bash
git add sparkforge/migration/version_path.py tests/test_version_path.py
git commit -m "feat(migration): resolvedor de caminho cumulativo entre versoes"
```

---

### Task 4: Extrator de migração — primeiro kind, `mig.sdk_import`

**Files:**
- Create: `sparkforge/facts/migration.py`
- Create: `tests/test_facts_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_facts_migration.py
from sparkforge.facts import migration

JOB_COM_SDK_V1 = '''
from awsglue.context import GlueContext
import com.amazonaws.services.s3.AmazonS3ClientBuilder as Builder

def main():
    pass
'''

JOB_LIMPO = '''
from awsglue.context import GlueContext

def main():
    pass
'''


class TestSdkImport:
    def test_reconhece_import_do_sdk_v1(self, tmp_path):
        alvo = tmp_path / "job.py"
        alvo.write_text(JOB_COM_SDK_V1, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        sdk = [f for f in facts if f.kind == "mig.sdk_import"]
        assert len(sdk) == 1
        assert sdk[0].attrs["package"] == "com.amazonaws"
        assert sdk[0].attrs["generation"] == "v1"

    def test_job_sem_sdk_nao_emite_o_kind(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_LIMPO, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        assert [f for f in facts if f.kind == "mig.sdk_import"] == []

    def test_o_fact_nao_carrega_juizo(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_SDK_V1, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        for fact in facts:
            texto = str(fact.attrs) + str(fact.measures)
            for palavra in ("severidade", "risco", "deve", "incompativel"):
                assert palavra not in texto.lower(), f"{fact.kind} julga: {texto}"

    def test_kinds_emitidos_sao_vocabulario_fechado(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_SDK_V1, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        assert {f.kind for f in facts} <= migration.EMITTED_KINDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_facts_migration.py -v`
Expected: FAIL com `ImportError: cannot import name 'migration' from 'sparkforge.facts'`

- [ ] **Step 3: Write minimal implementation**

```python
# sparkforge/facts/migration.py
"""Observacoes de migracao entre versoes de Glue.

O extrator OBSERVA e nunca julga. Um import `com.amazonaws.*` e observacao; que
ele seja bloqueante para um alvo especifico e juizo de regra, com faixa de versao
declarada em `runtime_scope`. Essa divisao e o que permite julgar facts antigos
com catalogo novo sem reparsear artefato.
"""
from __future__ import annotations

import re
from pathlib import Path

from sparkforge.findings.models import Fact

EMITTED_KINDS = frozenset(
    {
        "mig.sdk_import",
        "mig.emrfs_config",
        "mig.ansi_risk",
        "mig.jar_binary",
        "mig.python_dep",
        "mig.table_format",
        "mig.legacy_conf",
        "mig.deprecated_api",
    }
)

_SDK_V1_RE = re.compile(r"\bcom\.amazonaws\b")
_SDK_V2_RE = re.compile(r"\bsoftware\.amazon\.awssdk\b")


def _rel(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _sdk_imports(text: str, origem: str) -> list[Fact]:
    achados: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        for regex, geracao, pacote in (
            (_SDK_V1_RE, "v1", "com.amazonaws"),
            (_SDK_V2_RE, "v2", "software.amazon.awssdk"),
        ):
            if regex.search(linha):
                achados.append(
                    Fact(
                        kind="mig.sdk_import",
                        subject={"file": origem},
                        attrs={"package": pacote, "generation": geracao},
                        provenance={"file": origem, "line": lineno},
                    )
                )
    return achados


def extract_migration_tree(root: Path, repo_root: Path) -> list[Fact]:
    facts: list[Fact] = []
    for arquivo in sorted(root.rglob("*.py")):
        origem = _rel(arquivo, repo_root)
        texto = arquivo.read_text(encoding="utf-8")
        facts.extend(_sdk_imports(texto, origem))
    return facts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_facts_migration.py -v`
Expected: PASS, 4 testes

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/migration.py tests/test_facts_migration.py
git commit -m "feat(migration): extrator de migracao com kind mig.sdk_import"
```

---

### Task 5: Kinds de configuração — `mig.emrfs_config`, `mig.legacy_conf`, `mig.deprecated_api`

**Files:**
- Modify: `sparkforge/facts/migration.py`
- Modify: `tests/test_facts_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_facts_migration.py
JOB_COM_EMRFS = '''
spark.conf.set("fs.s3.consistent", "true")
spark.conf.set("fs.s3.consistent.retryCount", "5")
spark.conf.set("spark.sql.legacy.timeParserPolicy", "LEGACY")
sql_context = SQLContext(sc)
'''


class TestConfiguracaoLegada:
    def _facts(self, tmp_path, texto=JOB_COM_EMRFS):
        (tmp_path / "job.py").write_text(texto, encoding="utf-8")
        return migration.extract_migration_tree(tmp_path, repo_root=tmp_path)

    def test_reconhece_configuracao_de_emrfs(self, tmp_path):
        chaves = sorted(
            f.attrs["key"] for f in self._facts(tmp_path) if f.kind == "mig.emrfs_config"
        )
        assert chaves == ["fs.s3.consistent", "fs.s3.consistent.retryCount"]

    def test_reconhece_configuracao_legada_do_spark(self, tmp_path):
        legadas = [f for f in self._facts(tmp_path) if f.kind == "mig.legacy_conf"]
        assert [f.attrs["key"] for f in legadas] == ["spark.sql.legacy.timeParserPolicy"]

    def test_reconhece_api_depreciada(self, tmp_path):
        apis = [f for f in self._facts(tmp_path) if f.kind == "mig.deprecated_api"]
        assert [f.attrs["symbol"] for f in apis] == ["SQLContext"]

    def test_registra_a_linha_de_origem(self, tmp_path):
        for fact in self._facts(tmp_path):
            assert fact.provenance["line"] > 0
            assert fact.provenance["file"] == "job.py"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_facts_migration.py::TestConfiguracaoLegada -v`
Expected: FAIL — as listas saem vazias porque nenhum dos três kinds é emitido ainda.

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em sparkforge/facts/migration.py, antes de extract_migration_tree

# Prefixo exclusivo do EMRFS. O S3A do Glue 5+ nao le nenhuma destas chaves, entao
# elas sobrevivem no codigo sem efeito -- silencio, que e pior que erro.
_EMRFS_PREFIXES = ("fs.s3.consistent", "fs.s3.enableServerSideEncryption", "fs.s3.maxRetries")
_CONF_KEY_RE = re.compile(r'["\']([\w.\-]+)["\']')
_LEGACY_CONF_RE = re.compile(r'["\'](spark\.sql\.legacy\.[\w.]+)["\']')
_DEPRECATED_SYMBOLS = ("SQLContext", "HiveContext")


def _config_facts(text: str, origem: str) -> list[Fact]:
    achados: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        for chave in _CONF_KEY_RE.findall(linha):
            if chave.startswith(_EMRFS_PREFIXES):
                achados.append(
                    Fact(
                        kind="mig.emrfs_config",
                        subject={"file": origem},
                        attrs={"key": chave},
                        provenance={"file": origem, "line": lineno},
                    )
                )
        for chave in _LEGACY_CONF_RE.findall(linha):
            achados.append(
                Fact(
                    kind="mig.legacy_conf",
                    subject={"file": origem},
                    attrs={"key": chave},
                    provenance={"file": origem, "line": lineno},
                )
            )
        for simbolo in _DEPRECATED_SYMBOLS:
            if re.search(rf"\b{simbolo}\b", linha):
                achados.append(
                    Fact(
                        kind="mig.deprecated_api",
                        subject={"file": origem},
                        attrs={"symbol": simbolo},
                        provenance={"file": origem, "line": lineno},
                    )
                )
    return achados
```

E dentro de `extract_migration_tree`, depois de `facts.extend(_sdk_imports(texto, origem))`:

```python
        facts.extend(_config_facts(texto, origem))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_facts_migration.py -v`
Expected: PASS — os 4 testes da Task 4 mais os 4 desta.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/facts/migration.py tests/test_facts_migration.py
git commit -m "feat(migration): kinds de EMRFS, configuracao legada e API depreciada"
```

---

### Task 6: Kinds de dependência e formato — `mig.jar_binary`, `mig.python_dep`, `mig.table_format`, `mig.ansi_risk`

**Files:**
- Modify: `sparkforge/facts/migration.py`
- Modify: `tests/test_facts_migration.py`

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/test_facts_migration.py
REQUIREMENTS = "pandas==2.0.3\npyarrow==14.0.1\nrequests==2.31.0\n"
JOB_COM_CAST = '''
df = df.withColumn("valor", col("texto").cast("int"))
tabela = spark.sql("SELECT CAST(x AS DECIMAL(10,2)) FROM t")
seguro = df.withColumn("v", try_cast(col("texto"), "int"))
'''


class TestDependenciaEFormato:
    def test_reconhece_jar_com_scala_no_nome(self, tmp_path):
        (tmp_path / "conector_2.12-1.4.0.jar").write_bytes(b"")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        jars = [f for f in facts if f.kind == "mig.jar_binary"]
        assert len(jars) == 1
        assert jars[0].attrs["scala"] == "2.12"

    def test_reconhece_dependencia_python_declarada(self, tmp_path):
        (tmp_path / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        deps = {f.attrs["package"]: f.attrs["version"] for f in facts if f.kind == "mig.python_dep"}
        assert deps == {"pandas": "2.0.3", "pyarrow": "14.0.1", "requests": "2.31.0"}

    def test_reconhece_cast_sem_guarda_e_ignora_try_cast(self, tmp_path):
        (tmp_path / "job.py").write_text(JOB_COM_CAST, encoding="utf-8")
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        riscos = [f for f in facts if f.kind == "mig.ansi_risk"]
        assert len(riscos) == 2, [f.provenance["line"] for f in riscos]
        assert all(f.attrs["form"] == "cast" for f in riscos)

    def test_formato_de_tabela_separa_biblioteca_de_formato(self, tmp_path):
        (tmp_path / "job.py").write_text(
            'spark.sql("ALTER TABLE t SET TBLPROPERTIES (\\'format-version\\'=\\'2\\')")\n',
            encoding="utf-8",
        )
        facts = migration.extract_migration_tree(tmp_path, repo_root=tmp_path)
        formatos = [f for f in facts if f.kind == "mig.table_format"]
        assert len(formatos) == 1
        assert formatos[0].attrs["format_version"] == "2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_facts_migration.py::TestDependenciaEFormato -v`
Expected: FAIL — nenhum dos quatro kinds é emitido ainda.

- [ ] **Step 3: Write minimal implementation**

```python
# acrescentar em sparkforge/facts/migration.py

_JAR_SCALA_RE = re.compile(r"_(\d+\.\d+)-")
_REQUIREMENT_RE = re.compile(r"^([A-Za-z0-9_.\-]+)==([^\s#]+)")
# `cast(` sem `try_` na frente. O `(?<!try_)` e o que separa o cast que estoura
# sob ANSI do cast que devolve null -- os dois sao a mesma palavra no fonte.
_CAST_RE = re.compile(r"(?<!try_)\bcast\s*\(", re.IGNORECASE)
_FORMAT_VERSION_RE = re.compile(r"format-version['\"]?\s*=\s*['\"]?(\d+)")


def _ansi_facts(text: str, origem: str) -> list[Fact]:
    achados: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        for _ in _CAST_RE.finditer(linha):
            achados.append(
                Fact(
                    kind="mig.ansi_risk",
                    subject={"file": origem},
                    attrs={"form": "cast"},
                    provenance={"file": origem, "line": lineno},
                )
            )
        for versao in _FORMAT_VERSION_RE.findall(linha):
            achados.append(
                Fact(
                    kind="mig.table_format",
                    subject={"file": origem},
                    attrs={"format_version": versao},
                    provenance={"file": origem, "line": lineno},
                )
            )
    return achados


def _dependency_facts(root: Path, repo_root: Path) -> list[Fact]:
    achados: list[Fact] = []
    for jar in sorted(root.rglob("*.jar")):
        origem = _rel(jar, repo_root)
        encontrado = _JAR_SCALA_RE.search(jar.name)
        achados.append(
            Fact(
                kind="mig.jar_binary",
                subject={"file": origem},
                attrs={"scala": encontrado.group(1) if encontrado else ""},
                provenance={"file": origem},
            )
        )
    for req in sorted(root.rglob("requirements*.txt")):
        origem = _rel(req, repo_root)
        for lineno, linha in enumerate(req.read_text(encoding="utf-8").split("\n"), start=1):
            casado = _REQUIREMENT_RE.match(linha.strip())
            if casado:
                achados.append(
                    Fact(
                        kind="mig.python_dep",
                        subject={"file": origem},
                        attrs={"package": casado.group(1), "version": casado.group(2)},
                        provenance={"file": origem, "line": lineno},
                    )
                )
    return achados
```

E em `extract_migration_tree`, dentro do laço de `.py` acrescente `facts.extend(_ansi_facts(texto, origem))`, e antes do `return` acrescente `facts.extend(_dependency_facts(root, repo_root))`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_facts_migration.py -v`
Expected: PASS, 12 testes

- [ ] **Step 5: Verificar que todo kind declarado é emitido por algo**

Run: `python -c "from sparkforge.facts import migration; print(sorted(migration.EMITTED_KINDS))"`

Compare com os kinds que seus testes provaram emitir. Se algum kind do `EMITTED_KINDS` não tem teste que o produza, ou escreva o teste, ou remova o kind — kind declarado e nunca emitido torna inalcançável qualquer regra que dependa dele, e `tests/test_rules_catalog_reachability.py` vai acusar na Task 7.

- [ ] **Step 6: Commit**

```bash
git add sparkforge/facts/migration.py tests/test_facts_migration.py
git commit -m "feat(migration): kinds de JAR, dependencia Python, cast ANSI e formato de tabela"
```

---

### Task 7: Catálogo `SF-MIG`

**Files:**
- Create: `rules/catalog/glue-migration.yaml`

- [ ] **Step 1: Escrever o catálogo**

Cabeçalho com a razão da área e a decisão de camada, no estilo dos catálogos existentes. Depois as regras. Comece por três, uma por natureza diferente de evidência:

```yaml
# Catalogo de regras — migracao entre versoes de Glue (SF-MIG).
#
# POR QUE ESTA AREA EXISTE: as demais areas julgam um runtime PARADO. Esta julga
# a TRANSICAO entre dois. O que muda de mecanismo e so isto: `runtime_scope`
# declara a faixa em que o breaking change vale, e o motor de migracao aplica o
# catalogo uma vez por DEGRAU do caminho (ver `sparkforge/migration/version_path.py`).
#
# CAMADA, como em `rules/catalog/athena.yaml`: `runtime_scope` guarda VERSAO.
# O que gateia por natureza do artefato e `requires_facts`. Uma regra de migracao
# sem `requires_facts` disparia em qualquer job, inclusive nos que nao tocam o
# assunto.

catalog_version: 1
schema_version: 1

rules:

  - id: SF-MIG-001
    category: glue-migration
    title: Import do AWS SDK for Java v1 em runtime que nao o embarca
    requires_facts: [mig.sdk_import]
    when:
      all:
        - fact: mig.sdk_import
          where: {attrs.generation: "v1"}
    status: confirmed
    severity_default: P0
    runtime_scope: {glue: ">=5.0"}
    explanation: >
      O import `com.amazonaws.*` resolve contra o AWS SDK for Java v1. A partir do
      degrau em que o runtime deixa de embarca-lo, a classe some em tempo de
      execucao e o job falha com NoClassDefFoundError na primeira chamada -- nao no
      submit, o que faz a falha aparecer depois de minutos de processamento.
    proposed_change:
      - Migrar o import para `software.amazon.awssdk.*` e ajustar a construcao de cliente.
      - Quando o SDK v1 vier de dependencia transitiva de JAR, recompilar o JAR.
    risks:
      - A API do v2 difere em construcao de cliente e em tratamento de credencial; a troca nao e textual.
    tradeoffs:
      - Empacotar o v1 como `--extra-jars` adia a migracao e cria conflito de classpath com o v2 do runtime.
    validation:
      - Executar o job em runtime alvo e confirmar ausencia de NoClassDefFoundError.
      - Conferir que nenhum JAR do job traz `com/amazonaws` no conteudo.
    rollback:
      - Voltar o job para a versao de origem, que embarca o v1.
    sources:
      - "<URL de release notes ou de migracao do Glue, ja vigiada no sources.lock.json>"

  - id: SF-MIG-002
    category: glue-migration
    title: Configuracao exclusiva de EMRFS sobrevivendo em runtime S3A
    requires_facts: [mig.emrfs_config]
    when:
      all:
        - fact: mig.emrfs_config
    status: confirmed
    severity_default: P2
    runtime_scope: {glue: ">=5.0"}
    explanation: >
      Chaves `fs.s3.consistent.*` pertencem ao EMRFS. O S3A nao as le e nao reclama
      delas: a configuracao permanece no codigo sem efeito nenhum. O risco nao e
      quebrar, e acreditar que um comportamento esta configurado quando nao esta.
    proposed_change:
      - Remover a chave e, se o comportamento pretendido importa, configurar o equivalente em `fs.s3a.*`.
    risks:
      - Remover sem substituir muda comportamento se alguma chave tinha efeito colateral no runtime de origem.
    tradeoffs:
      - Manter a chave nao custa execucao, mas mantem uma afirmacao falsa no codigo.
    validation:
      - Conferir no Spark UI que a configuracao efetiva do filesystem e a esperada.
    rollback:
      - Reintroduzir a chave no job da versao de origem.
    sources:
      - "<URL ja vigiada>"

  - id: SF-MIG-003
    category: glue-migration
    title: Cast sem guarda em runtime com ANSI mode ligado por padrao
    requires_facts: [mig.ansi_risk]
    when:
      all:
        - fact: mig.ansi_risk
          where: {attrs.form: "cast"}
    status: blocked
    blocked_on: >
      Exige a linha da matriz para a versao em que o ANSI passa a vir ligado por
      padrao, com fonte oficial e data. Enquanto `knowledge/glue/runtime-matrix.yaml`
      nao trouxer essa versao com procedencia, a regra nao tem faixa honesta para
      declarar em `runtime_scope` -- e chutar a faixa e o defeito que esta fase existe
      para eliminar.
    severity_default: P1
    explanation: >
      Sob ANSI mode, cast invalido levanta excecao em vez de devolver null. Um job que
      dependia do null silencioso muda de resultado ou passa a falhar.
    proposed_change:
      - Trocar por `try_cast` onde o null era intencional.
      - Validar ou quarentenar o registro invalido antes do cast quando ele nao era intencional.
    risks:
      - Desligar ANSI globalmente mascara o problema e adia a descoberta para producao.
    tradeoffs:
      - `try_cast` preserva o comportamento antigo e esconde dado sujo que o ANSI revelaria.
    validation:
      - Comparar contagem de nulos na coluna afetada entre origem e alvo.
    rollback:
      - Reverter para a versao de origem do job.
    sources:
      - "<URL ja vigiada>"
```

Nas `sources`, use URLs que já estejam em `knowledge/sources.lock.json`. Se precisar de uma nova, acrescente-a pelo mecanismo existente e diga no relatório qual foi.

- [ ] **Step 2: Rodar os gates do catálogo**

Run: `python -c "from sparkforge.rules.loader import load_catalog; print(len(load_catalog()), 'regras')"`
Expected: o total cresce em relação a 116, e nenhuma exceção de schema.

Run: `python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py tests/test_rules_result_axis.py -q`
Expected: PASS. Se a reachability acusar SF-MIG-003, confirme que é por `blocked_on` declarado — que é o estado pretendido — e não por kind inexistente.

- [ ] **Step 3: Commit**

```bash
git add rules/catalog/glue-migration.yaml
git commit -m "feat(migration): area SF-MIG com as tres primeiras regras"
```

---

### Task 8: Motor — aplicar o catálogo por degrau

**Files:**
- Create: `sparkforge/migration/assessment.py`
- Create: `tests/test_migration_assessment.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_migration_assessment.py
from pathlib import Path

from sparkforge.facts import migration as facts_migration
from sparkforge.migration import assessment

JOB = 'import com.amazonaws.services.s3.AmazonS3\nspark.conf.set("fs.s3.consistent", "true")\n'


def _facts(tmp_path):
    (tmp_path / "job.py").write_text(JOB, encoding="utf-8")
    return facts_migration.extract_migration_tree(tmp_path, repo_root=tmp_path)


class TestAvaliacaoPorDegrau:
    def test_cada_finding_registra_em_que_degrau_nasceu(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert resultado.findings, "esperava finding de SF-MIG"
        for finding, degrau in resultado.by_step:
            assert degrau in (("4.0", "5.0"), ("5.0", "5.1"))

    def test_par_sem_degrau_nao_produz_finding(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="5.1", target="5.1")
        assert resultado.findings == []

    def test_gate_sem_evidencia_e_blocked_nunca_pass(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        for nome in ("dados", "performance", "custo", "canary"):
            assert resultado.gates[nome] == "BLOCKED", nome
            assert resultado.missing_evidence[nome], f"{nome} sem evidencia nomeada"

    def test_recomendacao_nao_e_go_com_gate_bloqueado(self, tmp_path):
        resultado = assessment.assess(_facts(tmp_path), source="4.0", target="5.1")
        assert resultado.recommendation in ("CONDITIONAL_GO", "NO_GO")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_migration_assessment.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'sparkforge.migration.assessment'`

- [ ] **Step 3: Write minimal implementation**

```python
# sparkforge/migration/assessment.py
"""Aplica o catalogo uma vez por degrau e agrega o resultado.

NAO bifurca o motor: chama o `judge` existente com o runtime de cada degrau. O
que esta fase acrescenta e a AGREGACAO -- qual finding nasce em qual salto -- e a
declaracao honesta do que nao pode ser avaliado sem AWS viva.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sparkforge.facts import runtime_matrix
from sparkforge.findings.models import Fact, Finding
from sparkforge.migration import version_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

# Gates que exigem execucao real. Sem job vivo e sem AWS nao existe evidencia
# para eles, e gate sem evidencia e BLOCKED -- nunca PASS. Declarar PASS aqui
# seria repetir exatamente o defeito que a auditoria de lastro documentou.
_GATES_QUE_EXIGEM_EXECUCAO = {
    "dados": "reconciliacao entre origem e alvo sobre a mesma entrada",
    "performance": "metricas de execucao nos dois runtimes",
    "custo": "DPU-hours medidos nos dois runtimes",
    "canary": "execucao paralela controlada em producao",
}


@dataclass
class MigrationAssessment:
    source: str
    target: str
    steps: list[tuple[str, str]]
    findings: list[Finding] = field(default_factory=list)
    by_step: list[tuple[Finding, tuple[str, str]]] = field(default_factory=list)
    gates: dict[str, str] = field(default_factory=dict)
    missing_evidence: dict[str, str] = field(default_factory=dict)
    recommendation: str = "NO_GO"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_runtime": self.source,
            "target_runtime": self.target,
            "steps": [list(s) for s in self.steps],
            "findings": [f.to_dict() for f in self.findings],
            "gates": self.gates,
            "missing_evidence": self.missing_evidence,
            "recommendation": self.recommendation,
        }


def _runtime_for(versao: str) -> dict[str, str]:
    linha = runtime_matrix.load()[versao]
    runtime = {"glue": versao}
    for chave in ("spark", "python", "iceberg"):
        if linha.get(chave):
            runtime[chave] = linha[chave]
    return runtime


def assess(facts: list[Fact], source: str, target: str) -> MigrationAssessment:
    degraus = version_path.steps(source, target)
    catalogo = load_catalog()
    resultado = MigrationAssessment(source=source, target=target, steps=degraus)

    for degrau in degraus:
        _, alvo = degrau
        for finding in judge(facts, catalogo, _runtime_for(alvo)):
            resultado.findings.append(finding)
            resultado.by_step.append((finding, degrau))

    for nome, evidencia in _GATES_QUE_EXIGEM_EXECUCAO.items():
        resultado.gates[nome] = "BLOCKED"
        resultado.missing_evidence[nome] = evidencia

    resultado.gates["compatibilidade"] = "FAIL" if resultado.findings else "PASS"
    resultado.recommendation = "NO_GO" if resultado.findings else "CONDITIONAL_GO"
    return resultado
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_migration_assessment.py -v`
Expected: PASS, 4 testes

Se um mesmo finding aparecer duas vezes por nascer em dois degraus, isso é o comportamento pretendido — a informação de qual salto o produziu está em `by_step`. Se você preferir deduplicar, escreva o teste que fixa a escolha antes de mudar o código.

- [ ] **Step 5: Commit**

```bash
git add sparkforge/migration/assessment.py tests/test_migration_assessment.py
git commit -m "feat(migration): avaliacao por degrau com gates fail-closed"
```

---

### Task 9: Fixtures golden do domínio `migration`

**Files:**
- Create: `fixtures/migration/sdk_v1_em_glue5/{meta.yaml,input/,expected/}`
- Create: `fixtures/migration/emrfs_sobrevivente/{meta.yaml,input/,expected/}`
- Create: `fixtures/migration/job_limpo/{meta.yaml,input/,expected/}`
- Create: `tests/test_fixtures_golden_migration.py`

- [ ] **Step 1: Criar a primeira fixture**

`fixtures/migration/sdk_v1_em_glue5/meta.yaml`, no formato do domínio `iceberg`:

```yaml
name: sdk_v1_em_glue5
proves: >
  Job que importa `com.amazonaws.*` avaliado contra Glue 5.0. Deve produzir
  SF-MIG-001 em P0. Prova que o kind mig.sdk_import chega a regra e que o
  runtime_scope `>=5.0` inclui o degrau.
runtime:
  glue: "5.0"
  spark: "3.5.4"
  python: "3.11"
expects_kinds:
  - mig.sdk_import
expects_rules:
  - SF-MIG-001
```

`input/job.py`:

```python
from awsglue.context import GlueContext
from com.amazonaws.services.s3 import AmazonS3ClientBuilder


def main(glue_context: GlueContext) -> None:
    AmazonS3ClientBuilder.defaultClient()
```

O `job_limpo` é a fixture negativa: job sem nenhum dos oito kinds, `expects_rules: []`. Sem ela, nada prova que o catálogo cala quando deve — o repositório já usa fixtures assim, sete delas existem só para provar silêncio.

- [ ] **Step 2: Escrever o runner golden**

```python
# tests/test_fixtures_golden_migration.py
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.migration import extract_migration_tree
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "migration"


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    entrada = directory / "input"
    facts = extract_migration_tree(entrada, repo_root=entrada)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


# ids pre-computados, nunca `ids=lambda`: com o diretorio vazio o pytest 8.x
# invoca o callable sobre o sentinela interno e aborta a sessao inteira. Mesma
# guarda de `tests/test_fixtures_golden_emr.py`.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
class TestGolden:
    def test_kinds_declarados_aparecem(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        emitidos = {f.kind for f in facts}
        assert set(meta["expects_kinds"]) <= emitidos

    def test_regras_declaradas_disparam(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        disparadas = {f.rule_id for f in findings}
        assert set(meta["expects_rules"]) <= disparadas

    def test_nenhuma_regra_alem_das_declaradas(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert {f.rule_id for f in findings} == set(meta["expects_rules"])

    def test_extracao_e_deterministica(self, directory):
        _, primeira, _, _ = run_fixture(directory)
        _, segunda, _, _ = run_fixture(directory)
        assert [f.id for f in primeira] == [f.id for f in segunda]

    def test_facts_batem_com_o_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        golden = directory / "expected" / "facts.json"
        atual = [f.to_dict() for f in facts]
        if not golden.exists():
            golden.write_text(
                json.dumps(atual, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            pytest.skip("golden gravado nesta execucao; rode de novo para valer")
        assert atual == json.loads(golden.read_text(encoding="utf-8"))
```

- [ ] **Step 3: Gravar e conferir os goldens**

Run: `python -m pytest tests/test_fixtures_golden_migration.py -v`
Expected: primeira execução grava os `expected/facts.json` e reporta skip.

Run de novo: `python -m pytest tests/test_fixtures_golden_migration.py -v`
Expected: PASS, sem skip.

**Abra cada `expected/facts.json` gravado e leia.** Golden aceito sem leitura é golden que congela um defeito. Se algum fact tiver `attrs` errado ou linha errada, corrija o extrator e apague o golden para regravar.

- [ ] **Step 4: Commit**

```bash
git add fixtures/migration tests/test_fixtures_golden_migration.py
git commit -m "test(migration): fixtures golden do dominio migration"
```

---

### Task 10: O teste que prova a generalidade

**Files:**
- Modify: `tests/test_migration_assessment.py`

- [ ] **Step 1: Write the failing test**

Este é o teste que decide se a fase cumpriu o objetivo. Sem ele, o motor pode estar preso ao par `4.0 → 6.0` e ninguém saberia.

```python
# acrescentar em tests/test_migration_assessment.py
class TestParGenerico:
    def test_pares_diferentes_selecionam_regras_diferentes(self, tmp_path):
        facts = _facts(tmp_path)
        curto = assessment.assess(facts, source="5.0", target="5.1")
        longo = assessment.assess(facts, source="4.0", target="5.1")
        assert len(longo.steps) > len(curto.steps)
        assert len(longo.by_step) >= len(curto.by_step)

    def test_par_que_nao_cruza_a_faixa_nao_dispara_a_regra(self, tmp_path):
        # SF-MIG-001 declara `glue: ">=5.0"`. Um caminho que termina em 4.0 nao
        # cruza a faixa, entao a regra nao deve aparecer.
        facts = _facts(tmp_path)
        resultado = assessment.assess(facts, source="3.0", target="4.0")
        assert "SF-MIG-001" not in {f.rule_id for f in resultado.findings}

    def test_nenhum_par_de_versao_aparece_no_codigo_do_motor(self):
        import re
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[1] / "sparkforge" / "migration"
        proibido = re.compile(r'"[3-9]\.\d+"')
        ofensores = [
            str(p) for p in raiz.rglob("*.py") if proibido.search(p.read_text(encoding="utf-8"))
        ]
        assert ofensores == [], f"par de versao embutido no motor: {ofensores}"
```

- [ ] **Step 2: Run test to verify it fails or passes, and understand which**

Run: `python -m pytest tests/test_migration_assessment.py::TestParGenerico -v`

Se passar de primeira, ótimo — mas confirme que não passa por vacuidade: apague temporariamente o `runtime_scope` de SF-MIG-001 e veja `test_par_que_nao_cruza_a_faixa_nao_dispara_a_regra` ficar vermelho. Se ele continuar verde sem o escopo, ele não está provando nada e precisa ser reescrito. Relate o que observou.

- [ ] **Step 3: Corrigir o que o teste acusar**

Se `test_nenhum_par_de_versao_aparece_no_codigo_do_motor` falhar, mova a constante ofensora para o dado ou para o parâmetro da função.

- [ ] **Step 4: Run the full suite**

Run: `python -m ruff check sparkforge tests`
Expected: nada novo nos arquivos tocados.

Run: `python -m pytest -q`
Expected: PASS. A suíte passa de 600 segundos; rode em background e confira antes do commit.

- [ ] **Step 5: Commit**

```bash
git add tests/test_migration_assessment.py
git commit -m "test(migration): prova que o motor e generico sobre pares de versao"
```

---

### Task 11: Glue 6.0 e o destino do analisador antigo

**Files:**
- Modify: `knowledge/glue/runtime-matrix.yaml`
- Modify: `rules/catalog/glue-migration.yaml`
- Decide: `sparkforge/migration/glue/analyzer.py`

- [ ] **Step 1: Pesquisar a linha do Glue 6.0**

Consulte as páginas oficiais de release notes e de migração do AWS Glue. Se a versão 6.0 existir e a página declarar Spark, Python, Scala, Java e Iceberg, acrescente a linha ao YAML com `sources` e `retrieved` da data de hoje, e acrescente a URL ao `knowledge/sources.lock.json` pelo mecanismo existente.

**Se a informação não estiver disponível ou não puder ser confirmada em fonte oficial, não escreva a linha.** Registre no relatório o que procurou e o que encontrou. O critério §10.7 do spec prevê exatamente esse desfecho: a fase fecha com as regras de 6.0 em `blocked_on`, declarando o que falta.

Não use a tabela do `prompt_migrations_glue.md` §4 como fonte: ela é ponto de partida e o próprio documento manda validar antes de cada trabalho.

- [ ] **Step 2: Ajustar SF-MIG-003 conforme o resultado**

Se a matriz ganhou a versão em que o ANSI passa a vir ligado por padrão, troque `status: blocked` por `status: confirmed`, remova `blocked_on` e declare o `runtime_scope` correspondente. Acrescente uma fixture que prove a regra disparando e outra que prove o silêncio no degrau anterior.

Se não ganhou, deixe como está e diga por quê no relatório.

- [ ] **Step 3: Decidir o destino do analisador antigo**

Run: `TOKENSAVE_DISABLE_GREP_HOOK=1 grep -rn "migration.glue.analyzer\|analyze_script" --include=*.py --include=*.yaml --include=*.json . | grep -v "^./.git/"`

Se ninguém o consome fora dos próprios testes, apague `sparkforge/migration/glue/analyzer.py` e o teste dele, e diga no commit que a área SF-MIG o substitui. Se houver consumidor, deixe-o e registre a dívida no `STATUS.md` com o consumidor nomeado — o padrão que `sparkforge/facts/secrets.py` já usa para dívida medida em vez de implícita.

- [ ] **Step 4: Fechar os critérios**

Run: `python -m pytest -q`
Expected: PASS.

Run: `python -c "from sparkforge.rules.loader import load_catalog; c=load_catalog(); print(len(c), 'regras'); print(sum(1 for r in c if r.get('blocked_on')), 'bloqueadas')"`

Relate os dois números. Regra bloqueada não é falha: é a fase declarando o que não pode julgar ainda.

- [ ] **Step 5: Commit**

```bash
git add knowledge/glue/runtime-matrix.yaml rules/catalog/glue-migration.yaml
git commit -m "feat(migration): linha do Glue 6.0 conforme evidencia encontrada"
```

Se nada foi acrescentado à matriz, o commit desta task é só a decisão sobre o analisador antigo, e a mensagem diz isso.

---

## Cobertura do spec

| seção do spec | tarefa |
|---|---|
| §1 contexto, §2 objetivo | Tasks 1 a 10 |
| §3 D-1 matriz como dado | Tasks 1 e 2 |
| §3 D-2 Glue 6.0 por pesquisa, `blocked_on` até lá | Tasks 7 e 11 |
| §3 D-3 `runtime_scope` é versão | Tasks 7 e 10 |
| §3 D-4 análise cumulativa | Tasks 3 e 8 |
| §3 D-5 extrator observa, regra julga | Tasks 4 a 6 |
| §4 facts | Tasks 4, 5 e 6 |
| §5 regras SF-MIG | Task 7 |
| §6 assessment e gates | Task 8 |
| §7 testes e fixtures | Tasks 9 e 10 |
| §8 encontro com o harness | fora de escopo por decisão; o critério está no spec |
| §9 perguntas em aberto | Task 8 Step 4 (dedup), Task 11 Step 3 (analisador), Task 6 (subtipo de `ansi_risk`) |
| §10 critérios de conclusão | Tasks 10 e 11 |
