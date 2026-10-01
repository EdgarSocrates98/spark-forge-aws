---
sdd: 1
feature: DATABRICKS_SPARK
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/DATABRICKS_SPARK/design.md
  sha256: "d6d3d2020ca7a18feedf36880a8b4057b668aa5df4ff23b1aaa55134084502ca"
tasks:
  - id: T1
    files: [knowledge/databricks/runtime-matrix.yaml, knowledge/databricks/runtime-matrix.md, sparkforge/facts/runtime_matrix.py, tests/test_databricks_runtime_matrix.py, knowledge/offline-manifest.json, knowledge/sources.lock.json, docs/surface.lock.json, docs/claims.lock.json]
    covers: [AC2]
    test: {path: tests/test_databricks_runtime_matrix.py, name: test_matriz_tem_fonte_data_e_vocabulario_fechado}
  - id: T2
    files: [sparkforge/findings/models.py, sparkforge/facts/runtime_detect.py, sparkforge/adapters/_core.py, sparkforge/adapters/tools.py, tests/test_databricks_platform.py, fixtures/runtime/databricks_flag_runtime, tests/test_fixtures_golden_runtime.py, fixtures/scan, docs/claims.lock.json]
    covers: [AC1]
    test: {path: tests/test_databricks_platform.py, name: test_flag_declara_plataforma_e_deriva_spark}
  - id: T3
    files: [tests/test_databricks_platform.py, fixtures/runtime/databricks_divergent_spark, tests/test_fixtures_golden_runtime.py]
    covers: [AC4]
    test: {path: tests/test_databricks_platform.py, name: test_divergencia_spark_registrada}
  - id: T4
    files: [sparkforge/adapters/_core.py, tests/test_databricks_platform.py, fixtures/runtime/databricks_event_log_runtime, tests/test_fixtures_golden_runtime.py]
    covers: [AC3]
    test: {path: tests/test_databricks_platform.py, name: test_event_log_declara_plataforma_databricks}
  - id: T5
    files: [sparkforge/facts/runtime_detect.py, sparkforge/adapters/_core.py, sparkforge/rules/engine.py, rules/catalog/env.yaml, manifest.json, tests/test_databricks_platform.py, fixtures/runtime/databricks_flag_runtime, fixtures/runtime/databricks_divergent_spark, fixtures/runtime/databricks_event_log_runtime, knowledge/sources.lock.json, tests/test_rules_catalog_reachability.py, tests/test_fixtures_kind_coverage.py]
    covers: [AC5]
    test: {path: tests/test_databricks_platform.py, name: test_photon_recusa_regra_de_plano}
  - id: T6
    files: [sparkforge/tuning/spark_conf.py, tests/test_databricks_platform.py]
    covers: [AC7]
    test: {path: tests/test_databricks_platform.py, name: test_shuffle_partitions_auto_recusado}
  - id: T7
    files: [tests/test_databricks_rule_audit.py, rules/catalog/env.yaml, rules/catalog/spark-plan.yaml, rules/catalog/parquet.yaml, rules/catalog/pyspark.yaml, rules/catalog/timeout.yaml, rules/catalog/spark-ui.yaml, scripts/regen_fixtures.py, docs/claims.lock.json]
    covers: [AC6]
    test: {path: tests/test_databricks_rule_audit.py, name: test_regra_sem_escopo_nao_remedia_com_termo_aws}
  - id: T8
    files: [fixtures/eventlog/databricks_skewed_stage, tests/test_fixtures_golden_eventlog.py, tests/test_databricks_platform.py]
    covers: [AC8]
    test: {path: tests/test_databricks_platform.py, name: test_fixture_pareada_mesmos_findings_neutros}
  - id: T9
    files: [sparkforge/adapters/cli.py, sparkforge/adapters/tools.py, sparkforge/adapters/_core.py, tests/test_databricks_platform.py, docs/surface.lock.json, docs/guia/referencia]
    covers: [AC9]
    test: {path: tests/test_databricks_platform.py, name: test_flags_seguem_o_emr}
  - id: T10
    files: [README.md, docs/superpowers/STATUS.md, tests/test_databricks_platform.py, tests/test_runtime_detect.py]
    covers: [AC1]
    test: {path: tests/test_databricks_platform.py, name: test_readme_declara_databricks}
---

# DATABRICKS_SPARK — plano

Regras que mordem toda tarefa:

- Edição pela ferramenta de edição, arquivo em UTF-8 com LF.
- `.claude/agents/README.md` fica fora da árvore e fora do índice. Ele faz
  `test_arvore_versionada::test_espelho_gerado_esta_em_dia_no_disco` falhar
  localmente, e isso não é defeito do branch.
- Um commit por tarefa, por `git commit -F <arquivo>` com a mensagem num
  arquivo do scratchpad. Heredoc dentro de `$(...)` dispara prompt de
  permissão.
- **Arquivo `.py` novo move alegações do gate de lastro.** Antes de todo
  commit que cria `.py`, rode `python scripts/check_vnext_claims.py` e
  remedie pelos ids que ele listar, nunca por varredura.
- Arquivo novo entra com `git add` antes de rodar os lotes.
- Os lotes da suíte rodam um por vez, pela constante `LOTES` de
  `tests/test_suite_batches.py`, e nunca com a árvore sendo editada.

## T1 — matriz Databricks Runtime -> Spark

1. Teste, em `tests/test_databricks_runtime_matrix.py`:

```python
"""A matriz Databricks Runtime -> Spark e dado com fonte, nao constante."""
from pathlib import Path

import pytest
import yaml

from sparkforge.facts import runtime_matrix

ROOT = Path(__file__).resolve().parents[1]
PAGINA = "https://docs.databricks.com/aws/en/release-notes/runtime/"


def test_matriz_tem_fonte_data_e_vocabulario_fechado(tmp_path):
    documento = yaml.safe_load(
        (ROOT / "knowledge" / "databricks" / "runtime-matrix.yaml").read_text(encoding="utf-8")
    )
    assert documento["sources"] == [PAGINA]
    assert documento["retrieved"] == "2026-09-17"
    assert runtime_matrix.DATABRICKS_COMPONENTS == frozenset({"spark"})
    assert runtime_matrix.databricks_sources() == (PAGINA,)
    assert runtime_matrix.load_databricks() == {
        "19": {"spark": "4.2.0"},
        "18": {"spark": "4.1.0"},
        "17.3": {"spark": "4.0.0"},
        "16.4": {"spark": "3.5.2"},
        "15.4": {"spark": "3.5.0"},
        "14.3": {"spark": "3.5.0"},
    }

    invalida = tmp_path / "runtime-matrix.yaml"
    invalida.write_text(
        "schema_version: 1\nsources: []\nretrieved: '2026-09-17'\n"
        "versions:\n  '15.4':\n    spark: '3.5.0'\n    python: '3.11'\n",
        encoding="utf-8",
    )
    with pytest.raises(runtime_matrix.RuntimeMatrixError, match="python"):
        runtime_matrix._carrega_matriz_fechada(
            invalida, runtime_matrix.DATABRICKS_COMPONENTS, "Databricks"
        )
```

2. `python -m pytest tests/test_databricks_runtime_matrix.py -q`: falha com
   `AttributeError: module 'sparkforge.facts.runtime_matrix' has no attribute 'DATABRICKS_COMPONENTS'`.

3. Dado, em `knowledge/databricks/runtime-matrix.yaml`:

```yaml
# Matriz Databricks Runtime -> Apache Spark. Dado, nunca constante em Python.
#
# FONTE: a pagina de versoes suportadas do Databricks Runtime, que publica,
# por versao, a versao do Apache Spark, a data de lancamento e o fim de
# suporte. So a coluna Spark entra aqui: e a unica que alguma regra ou
# derivacao consome. Python e Scala nao estao nesta pagina, e componente sem
# fonte e eixo inventado -- o loader estoura com chave fora de `spark`.
#
# CHAVE: o numero da versao como a pagina o escreve ("15.4", "18"), sem
# "LTS". O rotulo que a Clusters API e a Jobs API carregam
# ("15.4.x-scala2.12") e normalizado para a chave em
# `sparkforge/facts/runtime_detect.py::_databricks_key`; ver
# `runtime-matrix.md` secao 2.
#
# Pagina atualizada em 2026-09-11 e lida em 2026-09-17.
schema_version: 1
sources:
  - "https://docs.databricks.com/aws/en/release-notes/runtime/"
retrieved: "2026-09-17"
versions:
  "19":
    spark: "4.2.0"
  "18":
    spark: "4.1.0"
  "17.3":
    spark: "4.0.0"
  "16.4":
    spark: "3.5.2"
  "15.4":
    spark: "3.5.0"
  "14.3":
    spark: "3.5.0"
```

4. Documento, em `knowledge/databricks/runtime-matrix.md`:

```markdown
# Matriz de runtime do Databricks

Esta página responde uma pergunta: dado o número do Databricks Runtime de um
cluster ou job, qual Apache Spark ele roda? O espelho executável é
[`runtime-matrix.yaml`](runtime-matrix.yaml), com a coluna `spark` e nada mais.

## 1. O que a fonte publica

A página de versões suportadas lista, por versão, a versão do Apache Spark, a
data de lançamento e o fim de suporte. Lida em 2026-09-17, atualizada pela
Databricks em 2026-09-11:

| Databricks Runtime | Apache Spark | Lançamento | Fim de suporte |
|---|---|---|---|
| 19 | 4.2.0 | 2026-06-15 | definido na transição para LTS |
| 18 LTS | 4.1.0 | 2026-06-10 | 2029-06-10 |
| 17.3 LTS | 4.0.0 | 2025-10-22 | 2028-10-22 |
| 16.4 LTS | 3.5.2 | 2025-05-09 | 2028-05-09 |
| 15.4 LTS | 3.5.0 | 2024-08-19 | 2027-08-19 |
| 14.3 LTS | 3.5.0 | 2024-02-01 | 2027-02-01 |

A página não publica Python, Scala nem Delta por versão. Esses eixos ficam
fora da matriz.

## 2. A chave e o rótulo

A matriz é indexada pelo número como a página o escreve. O rótulo que a
Clusters API e a Jobs API carregam em `spark_version` tem outra forma
(`15.4.x-scala2.12`). A normalização guarda os segmentos numéricos iniciais
(`15.4`). Quando o rótulo termina em `.0` e a matriz tem só o número maior
(`18.0` contra `18`), a busca tenta o número maior. Versão fora da matriz
deixa `spark` vazio: a derivação não inventa.

## 3. O que ainda não se sabe

- **U1.** A chave `spark.databricks.clusterUsageTags.sparkVersion` é
  documentada como propriedade local de TaskContext, com valor como `16.3`, no
  Databricks Runtime 16.3 ou mais novo. Não há fonte oficial dizendo que ela
  aparece nas `Spark Properties` do event log entregue por cluster log
  delivery. O SparkForge lê a chave quando ela está lá; a presença em log real
  continua a confirmar.
- **U2.** A página do Photon documenta a cor dos operadores na interface e o
  `runtime_engine = PHOTON` nas APIs, não como Photon aparece no event log. Por
  isso Photon é declarado (`--photon on|off`), não detectado.
- `spark.sql.shuffle.partitions = auto` liga o auto-optimized shuffle, que
  escolhe o número de partições pelo plano e pelo volume. É opt-in; o default
  é `200`. O `tune` recusa derivar número fixo por cima de `auto`.

## Fontes

- Databricks Runtime release notes versions and compatibility. https://docs.databricks.com/aws/en/release-notes/runtime/ (retrieved 2026-09-17)
- Get task context in a UDF. https://docs.databricks.com/aws/en/udf/udf-task-context (retrieved 2026-09-17)
- What is Photon? https://docs.databricks.com/aws/en/compute/photon (retrieved 2026-09-17)
- Adaptive query execution. https://docs.databricks.com/aws/en/optimizations/aqe (retrieved 2026-09-17)
```

5. Loader, em `sparkforge/facts/runtime_matrix.py`. Logo depois de
   `_emr_serverless_path()`:

```python
_DATABRICKS_RELATIVE = "databricks/runtime-matrix.yaml"


def _databricks_path() -> Path:
    return safe_knowledge_file(knowledge_dir(), _DATABRICKS_RELATIVE)
```

   E no fim do arquivo:

```python
# --------------------------------------------------------------------------- #
# Databricks Runtime
# --------------------------------------------------------------------------- #

# Um componente so: a pagina de versoes suportadas publica Apache Spark por
# versao do Databricks Runtime, e nenhum outro eixo que alguma regra consuma.
DATABRICKS_COMPONENTS = frozenset({"spark"})


@lru_cache(maxsize=1)
def load_databricks() -> dict[str, dict[str, str]]:
    """Matriz do Databricks Runtime, indexada pelo numero como a pagina o
    escreve (`"15.4"`, `"18"`). A normalizacao do rotulo da API
    (`15.4.x-scala2.12`) mora em `runtime_detect._databricks_key`."""
    return _carrega_matriz_fechada(_databricks_path(), DATABRICKS_COMPONENTS, "Databricks")


@lru_cache(maxsize=1)
def databricks_sources() -> tuple[str, ...]:
    return _fontes_declaradas(_databricks_path())
```

6. `python -m pytest tests/test_databricks_runtime_matrix.py -q`: verde.

7. Gates vizinhos, na ordem:

```bash
python -c "from sparkforge.tools.offline import _content_sha256; from pathlib import Path; print(_content_sha256(Path('knowledge/databricks/runtime-matrix.md')))"
```

   Acrescente a `knowledge/offline-manifest.json`, na lista `documents` e na
   ordem alfabética dos vizinhos, a entrada
   `{"path": "knowledge/databricks/runtime-matrix.md", "title": "runtime-matrix", "sha256": "<o hash impresso>"}`.
   Se o manifesto também lista `.yaml`, faça o mesmo para o YAML.

```bash
python scripts/refresh_knowledge.py --update --offline
python -m pytest tests/test_offline_expansion.py tests/test_refresh_knowledge.py -q
python scripts/verify_offline_bundle.py
python scripts/check_surface_lock.py --update
python -m pytest tests/test_surface_lock.py -q
python scripts/check_vnext_claims.py
```

8. Commit: `feat(knowledge): Databricks Runtime to Spark matrix with source`.

## T2 — plataforma databricks declarada pela flag

1. Teste, em `tests/test_databricks_platform.py` (arquivo novo):

```python
"""Databricks como plataforma declarada, com fronteira onde o significado muda."""
from pathlib import Path

from sparkforge.adapters._core import build_runtime
from sparkforge.facts.runtime_detect import _collect

ROOT = Path(__file__).resolve().parents[1]


def test_flag_declara_plataforma_e_deriva_spark():
    context, facts = build_runtime(databricks="15.4.x-scala2.12")
    assert context.databricks == "15.4"
    assert context.spark == "3.5.0"
    assert context.detected_from == ["cli"]
    assert context.to_dict()["databricks"] == "15.4"
    plataforma = next(f for f in facts if f.kind == "env.platform")
    assert plataforma.attrs["resolved"] == "databricks"
    _, observacoes, _, _ = _collect({"cli": {"databricks_runtime": "15.4.x-scala2.12"}})
    assert observacoes["spark"] == [("3.5.0", "cli:matrix")]
    maior, _ = build_runtime(databricks="18.0.x-scala2.13")
    assert (maior.databricks, maior.spark) == ("18.0", "4.1.0")
    fora, _ = build_runtime(databricks="9.1.x-scala2.12")
    assert (fora.databricks, fora.spark) == ("9.1", "")
```

2. `python -m pytest tests/test_databricks_platform.py::test_flag_declara_plataforma_e_deriva_spark -q`:
   falha com `TypeError: build_runtime() got an unexpected keyword argument 'databricks'`.

3. `sparkforge/findings/models.py`, em `RuntimeContext`: depois de
   `emr: str = ""` acrescente

```python
    # Numero do Databricks Runtime ("15.4"), nunca o rotulo da API
    # ("15.4.x-scala2.12"): `in_scope` compara este valor com `_parse`.
    databricks: str = ""
```

   depois de `athena: str = ""` acrescente

```python
    # Declaracao do operador, "on" ou "off"; vazio e "nao declarado". Nao e
    # versao: nenhuma regra o poe em `runtime_scope`. Quem le e o engine.
    photon: str = ""
```

   e troque o corpo de `to_dict` por:

```python
        return {
            "glue": self.glue,
            "emr": self.emr,
            "databricks": self.databricks,
            "spark": self.spark,
            "python": self.python,
            "iceberg": self.iceberg,
            "athena": self.athena,
            "photon": self.photon,
            "detected_from": list(self.detected_from),
            "divergences": list(self.divergences),
        }
```

4. `sparkforge/facts/runtime_detect.py`:

   Logo depois da linha `EMR_SERVERLESS_MATRIX: dict[str, dict[str, str]] = runtime_matrix.load_emr_serverless()`:

```python
# Matriz Databricks Runtime -> Spark, com um componente so. Fonte e data em
# `knowledge/databricks/runtime-matrix.yaml`.
DATABRICKS_MATRIX: dict[str, dict[str, str]] = runtime_matrix.load_databricks()
```

   Troque o bloco de `_PLATFORM_KEYS` por:

```python
_DATABRICKS_KEY = "databricks_runtime"

_PLATFORM_KEYS: dict[str, tuple[str, ...]] = {
    "emr": ("emr_release", "emr_version", "emr", _EMR_SERVERLESS_KEY),
    "glue": ("glue_version",),
    "databricks": (_DATABRICKS_KEY,),
}
```

   Logo depois de `_emr_key`:

```python
def _databricks_key(value: str) -> str:
    """`15.4.x-scala2.12` -> `15.4`; `16.4 LTS` -> `16.4`; `18` -> `18`.

    Guarda os segmentos numericos iniciais do rotulo e para no primeiro que nao
    e numero. E a chave da matriz e o valor de `RuntimeContext.databricks`.
    """
    text = str(value).strip()
    head = text.split()[0] if text else ""
    parts: list[str] = []
    for chunk in head.split("-", 1)[0].split("."):
        if not chunk.isdigit():
            break
        parts.append(chunk)
    return ".".join(parts)


def _databricks_row(value: str) -> dict[str, Any] | None:
    """A pagina escreve `18` onde a API escreve `18.0.x-...`: sem linha para
    `18.0`, tenta o numero maior. Fora disso, nenhuma linha -- sem inventar."""
    key = _databricks_key(value)
    row = DATABRICKS_MATRIX.get(key)
    if row is None and key.endswith(".0"):
        row = DATABRICKS_MATRIX.get(key[:-2])
    return row
```

   Troque `_IDENTITY_NORMALIZE: dict[str, Any] = {"emr": _emr_key}` por:

```python
_IDENTITY_NORMALIZE: dict[str, Any] = {"emr": _emr_key, "databricks": _databricks_key}
```

   Em `_matrix_row`, antes do `return None` final:

```python
    if platform == "databricks":
        return _databricks_row(value)
```

   Em `_build_context`, no dict `all_components`, depois de
   `"emr": platforms.get("emr", []),`:

```python
        "databricks": platforms.get("databricks", []),
```

   troque `identity = {"glue", "emr", "platform"}` por
   `identity = {"glue", "emr", "databricks", "platform"}`, logo depois de
   `emr_resolvido = _resolve(platforms.get("emr", []))` acrescente
   `databricks_resolvido = _resolve(platforms.get("databricks", []))`, e na
   chamada `RuntimeContext(...)`, depois da linha `emr=...`:

```python
        databricks=_databricks_key(databricks_resolvido) if databricks_resolvido else "",
```

5. `sparkforge/adapters/_core.py`, em `build_runtime`: acrescente
   `databricks: str | None = None,` depois de `emr: str | None = None,` na
   assinatura, e no dict `raw`, depois da linha `chave_do_release: emr,`:

```python
        # Numero ou rotulo do Databricks Runtime. DECLARACAO, fonte `cli`, como
        # `--emr`: perde para o event log e discordar vira divergencia.
        "databricks_runtime": databricks,
```

   Em `build_runtime_context`: o mesmo parâmetro na assinatura, e a chamada vira
   `build_runtime(glue, spark, python, iceberg, athena, facts=facts, emr=emr, databricks=databricks)`.

6. `sparkforge/adapters/tools.py`, em `_RUNTIME_CONTEXT`: acrescente
   `"databricks"` e `"photon"` a `required`, logo depois de `"emr"` e de
   `"athena"`, e em `properties`:

```python
        "databricks": {
            "type": "string",
            "description": (
                "Numero do Databricks Runtime ('15.4'), vazio fora do Databricks. "
                "Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml."
            ),
        },
        "photon": {
            "type": "string",
            "description": (
                "Declaracao do operador: 'on', 'off', ou vazio quando nao declarado. "
                "Com 'on' sob Databricks, regra de plano sai em skipped com "
                "databricks.photon.unresolved."
            ),
        },
```

7. Fixture `fixtures/runtime/databricks_flag_runtime/`:
   `input/sources.json`:

```json
{
  "cli": {
    "databricks_runtime": "15.4.x-scala2.12"
  }
}
```

   `meta.yaml`:

```yaml
name: databricks_flag_runtime
proves: >
  Databricks declarado pela flag. O rotulo da API (15.4.x-scala2.12) vira o
  numero da matriz (15.4), e spark deriva 3.5.0 da matriz, com origem
  cli:matrix. Uma plataforma so: env.platform com distinct_platforms 1 e
  SF-ENV-005 avaliada e calada.
runtime:
  databricks: "15.4"
  spark: "3.5.0"
expects_kinds:
  - env.platform
  - env.runtime_signal
expects_rules: []
```

   Em `tests/test_fixtures_golden_runtime.py`, acrescente
   `"databricks_flag_runtime",` a `REQUIRED_FIXTURES`.

8. Goldens:

```bash
mkdir -p fixtures/runtime/databricks_flag_runtime/expected
python scripts/regen_fixtures.py databricks_flag_runtime
SPARKFORGE_REGEN_SCAN=1 python -m pytest tests/test_fixtures_golden_scan.py -q
python -m pytest tests/test_fixtures_golden_scan.py tests/test_fixtures_golden_runtime.py tests/test_runtime_detect.py -q
```

   `git diff --stat fixtures/scan` mostra os `summary.json` com as chaves
   `databricks` e `photon`, e só elas.

9. `python -m pytest tests/test_databricks_platform.py::test_flag_declara_plataforma_e_deriva_spark -q`: verde.

10. Gates vizinhos: `python -m pytest tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py tests/test_runtime_glue_versions.py tests/test_adapters_tools.py -q`,
    os lotes da suíte, e `python scripts/check_vnext_claims.py`. Golden que
    serializa `RuntimeContext` e apareça vermelho nos lotes regenera pelo
    runner do próprio corpus, nunca à mão.

11. Commit: `feat(runtime): declare Databricks as a platform with matrix-derived Spark`.

## T3 — divergência entre event log e matriz

1. Teste, em `tests/test_databricks_platform.py`:

```python
from sparkforge.facts.runtime_detect import detect_runtime


def test_divergencia_spark_registrada():
    context, facts = detect_runtime(
        {"event_log": {"spark_version": "3.5.2"}, "cli": {"databricks_runtime": "15.4"}}
    )
    assert context.databricks == "15.4"
    assert context.spark == "3.5.2"
    assert any(texto.startswith("spark:") for texto in context.divergences)
    sinal = next(
        f for f in facts if f.kind == "env.runtime_signal" and f.attrs["component"] == "spark"
    )
    assert sinal.measures["distinct_versions"] == 2
    golden = ROOT / "fixtures" / "runtime" / "databricks_divergent_spark" / "expected"
    disparadas = {f["rule_id"] for f in json.loads((golden / "findings.json").read_text(encoding="utf-8"))}
    assert "SF-ENV-001" in disparadas
```

   (`import json` junto dos imports do arquivo.)

2. `python -m pytest tests/test_databricks_platform.py::test_divergencia_spark_registrada -q`:
   `FileNotFoundError` sobre `databricks_divergent_spark/expected/findings.json`.
   A divergência em si já sai do caminho genérico de `_divergent_count` com T2
   aplicada; o que falta é o golden que a prova de ponta a ponta.

3. Fixture `fixtures/runtime/databricks_divergent_spark/`:
   `input/sources.json`:

```json
{
  "cli": {
    "databricks_runtime": "15.4"
  },
  "event_log": {
    "spark_version": "3.5.2"
  }
}
```

   `meta.yaml`:

```yaml
name: databricks_divergent_spark
proves: >
  O event log diz Spark 3.5.2 e a flag declara Databricks Runtime 15.4, que a
  matriz liga a Spark 3.5.0. A leitura direta vence a derivacao, e a
  diferenca vira divergencia registrada e SF-ENV-001, nunca resolucao
  silenciosa.
runtime:
  databricks: "15.4"
  spark: "3.5.2"
expects_kinds:
  - env.platform
  - env.runtime_signal
expects_rules:
  - SF-ENV-001
```

   Em `tests/test_fixtures_golden_runtime.py`, acrescente
   `"databricks_divergent_spark",` a `REQUIRED_FIXTURES`.

4. Golden:

```bash
mkdir -p fixtures/runtime/databricks_divergent_spark/expected
python scripts/regen_fixtures.py databricks_divergent_spark
python -m pytest tests/test_fixtures_golden_runtime.py tests/test_databricks_platform.py -q
```

5. Commit: `test(runtime): Databricks spark divergence is recorded, not resolved`.

## T4 — a versão do Databricks Runtime lida do event log

1. Teste, em `tests/test_databricks_platform.py`:

```python
from sparkforge.adapters._core import runtime_sources_from_facts
from sparkforge.findings.models import Fact

_CHAVE_VERSAO = "spark.databricks.clusterUsageTags.sparkVersion"


def _conf(chave: str, valor: str) -> Fact:
    return Fact(
        kind="spark.conf_effective",
        subject={"type": "job_run", "symbol": chave},
        attrs={"key": chave, "value": valor, "source_event": "SparkListenerEnvironmentUpdate"},
        provenance={"extractor": "event_log@0.1.0"},
    )


def test_event_log_declara_plataforma_databricks():
    fatos = [_conf(_CHAVE_VERSAO, "15.4.x-scala2.12")]
    assert runtime_sources_from_facts(fatos) == {
        "event_log": {"databricks_runtime": "15.4.x-scala2.12"}
    }
    context, facts = build_runtime(facts=fatos)
    assert (context.databricks, context.spark) == ("15.4", "3.5.0")
    plataforma = next(f for f in facts if f.kind == "env.platform")
    assert plataforma.attrs["origins"] == {"databricks": ["event_log"]}
    assert runtime_sources_from_facts([_conf("spark.app.name", "x")]) == {}
```

2. `python -m pytest tests/test_databricks_platform.py::test_event_log_declara_plataforma_databricks -q`:
   `AssertionError` no primeiro `assert` (`{} == {'event_log': ...}`).

3. `sparkforge/adapters/_core.py`: logo acima de `def _runtime_reading`:

```python
# Chave que carrega o numero do Databricks Runtime. Documentada como
# propriedade local de TaskContext (DBR 16.3+); a presenca nas `Spark
# Properties` do event log e a lacuna U1 de knowledge/databricks/runtime-matrix.md.
# Quando esta la, e observacao do artefato, e por isso a fonte e `event_log`.
_DATABRICKS_VERSION_KEY = "spark.databricks.clusterUsageTags.sparkVersion"
```

   E dentro de `_runtime_reading`, logo depois do bloco de
   `spark.runtime_version`:

```python
    if fact.kind == "spark.conf_effective" and fact.attrs.get("key") == _DATABRICKS_VERSION_KEY:
        value = str(fact.attrs.get("value") or "").strip()
        return ("event_log", "databricks_runtime", value) if value else None
```

4. Fixture `fixtures/runtime/databricks_event_log_runtime/`:
   `input/sources.json`:

```json
{
  "event_log": {
    "databricks_runtime": "15.4.x-scala2.12",
    "spark_version": "3.5.0"
  }
}
```

   `meta.yaml`:

```yaml
name: databricks_event_log_runtime
proves: >
  A versao do Databricks Runtime chega do proprio event log, sem flag, e
  concorda com o Spark que o log declara: uma observacao, nenhuma
  divergencia. Se um event log real traz a chave e a lacuna U1.
runtime:
  databricks: "15.4"
  spark: "3.5.0"
expects_kinds:
  - env.platform
  - env.runtime_signal
expects_rules: []
```

   Em `tests/test_fixtures_golden_runtime.py`, acrescente
   `"databricks_event_log_runtime",` a `REQUIRED_FIXTURES`.

```bash
mkdir -p fixtures/runtime/databricks_event_log_runtime/expected
python scripts/regen_fixtures.py databricks_event_log_runtime
python -m pytest tests/test_databricks_platform.py tests/test_fixtures_golden_runtime.py tests/test_runtime_inferred_from_facts.py -q
```

5. Commit: `feat(runtime): read the Databricks Runtime version from the event log`.

## T5 — Photon declarado, e a recusa das regras de plano

1. Teste, em `tests/test_databricks_platform.py`:

```python
from sparkforge.facts.spark_plan import extract_plan_path
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

PLANO = ROOT / "fixtures" / "plan" / "cartesian_join" / "input"


def test_photon_recusa_regra_de_plano():
    fatos = extract_plan_path(PLANO / "plan.txt", repo_root=PLANO)
    base = {"databricks": "15.4", "spark": "3.5.0"}
    ligado, pulados = judge(fatos, load_catalog(), {**base, "photon": "on"}, return_skipped=True)
    desligado = judge(fatos, load_catalog(), {**base, "photon": "off"})
    sem_databricks = judge(fatos, load_catalog(), {"spark": "3.5.0", "photon": "on"})
    assert "SF-PLAN-003" in {f.rule_id for f in desligado}
    assert "SF-PLAN-003" in {f.rule_id for f in sem_databricks}
    assert "SF-PLAN-003" not in {f.rule_id for f in ligado}
    assert {"rule_id": "SF-PLAN-003", "reason": "databricks.photon.unresolved"} in pulados

    context, facts = build_runtime(databricks="15.4")
    assert context.photon == ""
    assert next(f for f in facts if f.kind == "databricks.photon").attrs["state"] == "undeclared"
    assert "SF-ENV-006" in {f.rule_id for f in judge(facts, load_catalog(), context.to_dict())}

    context_on, facts_on = build_runtime(databricks="15.4", photon="on")
    assert context_on.photon == "on"
    assert next(f for f in facts_on if f.kind == "databricks.photon").attrs["state"] == "on"
    assert "SF-ENV-006" not in {f.rule_id for f in judge(facts_on, load_catalog(), context_on.to_dict())}

    _, facts_glue = build_runtime(glue="5.0", photon="on")
    assert not any(f.kind == "databricks.photon" for f in facts_glue)
```

2. `python -m pytest tests/test_databricks_platform.py::test_photon_recusa_regra_de_plano -q`:
   `AssertionError` em `"SF-PLAN-003" not in ...` (a regra ainda dispara com
   Photon ligado).

3. `sparkforge/rules/engine.py`: logo acima de `def judge`:

```python
# Kinds de PLANO. Sob Databricks com Photon ligado, os operadores fisicos tem
# outros nomes e o fallback para o Spark e por operacao (knowledge/databricks/
# runtime-matrix.md secao 3): uma regra que procura um operador JVM pode ficar
# calada sem que o problema tenha sumido. A regra sai em `skipped` com nome, e o
# silencio deixa de ler como "nada encontrado".
_PLAN_KIND_PREFIXES = ("plan.", "spark.sql.")


def _photon_recusa(rule: dict[str, Any], runtime: dict[str, str]) -> bool:
    if not runtime.get("databricks") or runtime.get("photon") != "on":
        return False
    return any(
        str(kind).startswith(_PLAN_KIND_PREFIXES) for kind in rule.get("requires_facts") or []
    )
```

   E em `judge`, logo depois do bloco de `runtime_scope`
   (`skipped.append({... "reason": "runtime_scope" ...}); continue`):

```python
        if _photon_recusa(rule, runtime):
            skipped.append({"rule_id": rule["id"], "reason": "databricks.photon.unresolved"})
            continue
```

4. `sparkforge/facts/runtime_detect.py`: `from dataclasses import replace`
   junto dos imports, `EMITTED_KINDS` passa a
   `frozenset({"env.runtime_signal", "env.platform", "databricks.photon"})`, e
   logo acima de `def detect_runtime`:

```python
_PHOTON_STATES = frozenset({"on", "off"})


def _photon(sources: dict[str, dict[str, Any]]) -> str:
    """A declaracao de Photon, `on`/`off`, ou vazio. Duas declaracoes que
    discordam, ou valor fora do vocabulario, contam como nao declarado."""
    declarado = {
        str(data.get("photon")).strip().lower()
        for data in sources.values()
        if isinstance(data, dict) and data.get("photon")
    }
    if len(declarado) == 1 and declarado <= _PHOTON_STATES:
        return next(iter(declarado))
    return ""


def _photon_fact(photon: str) -> Fact:
    """`databricks.photon`: so existe quando a plataforma databricks foi
    detectada. `undeclared` e o gatilho de SF-ENV-006."""
    return Fact(
        kind="databricks.photon",
        subject={"type": "job_run", "symbol": "photon"},
        attrs={"state": photon or "undeclared", "source": "cli" if photon else "none"},
        provenance={"extractor": DETECTOR_ID},
    )
```

   O corpo de `detect_runtime` vira:

```python
    platforms, observations, detected_from, derived = _collect(sources or {})
    context = _build_context(platforms, observations, detected_from, derived)
    photon = _photon(sources or {})
    if photon:
        context = replace(context, photon=photon)
    facts = _build_facts(platforms, observations, derived)
    if platforms.get("databricks"):
        facts.append(_photon_fact(photon))
    return context, sort_facts(facts)
```

5. `sparkforge/adapters/_core.py`: `build_runtime` e `build_runtime_context`
   ganham `photon: str | None = None,` depois de `databricks`; no dict `raw`
   de `build_runtime`, depois de `"databricks_runtime": databricks,`, entra
   `"photon": photon,`; e a chamada de `build_runtime_context` passa
   `databricks=databricks, photon=photon`.

6. Regra, em `rules/catalog/env.yaml`, no fim da lista `rules`:

```yaml
  - id: SF-ENV-006
    category: environment
    title: Databricks sem declaração de Photon, e regra de plano calada não é evidência
    requires_facts: [databricks.photon]
    when:
      all:
        - fact: databricks.photon
          where: {attrs.state: undeclared}
    status: confirmed
    severity_default: P2
    runtime_scope: {}
    explanation: >
      O job roda no Databricks e ninguém declarou se o Photon está ligado. Com
      Photon, os operadores físicos têm outros nomes e o fallback para o Spark
      acontece por operação — com UDF, com API de RDD ou Dataset, com streaming
      com estado, e em consulta que termina em menos de dois segundos. Uma regra
      que procura um operador JVM no plano pode ficar calada sem que o problema
      tenha sumido. Enquanto Photon não é declarado, a ausência de achado de
      plano não é evidência de plano saudável.
    proposed_change:
      - Declarar `--photon on` ou `--photon off` conforme o `runtime_engine` do cluster ou do job (`PHOTON` ou `STANDARD` na Clusters API e na Jobs API).
      - Com Photon ligado, ler as regras de plano em `skipped` com `databricks.photon.unresolved`, nunca como plano sem achado.
    action:
      kind: measurement.collect_baseline
      target: databricks.photon
      direction: investigate
      requires_absent: []
      moves: []
      depends_on: []
    risks:
      - Declarar `off` num cluster com Photon faz as regras de plano julgarem operadores que não rodaram.
    tradeoffs:
      - Nenhum. Declarar Photon é contexto do job, não mudança nele.
    validation:
      - "`databricks.photon` com `attrs.state` em `on` ou `off` na execução seguinte."
    rollback: [Não aplicável; é declaração de contexto, não mudança de comportamento do job.]
    sources:
      - {url: "https://docs.databricks.com/aws/en/compute/photon", retrieved: 2026-09-17}
```

   `manifest.json`: `rule_count` sobe de `191` para `192`.

7. Os três casos Databricks do corpus de runtime passam a disparar SF-ENV-006
   (nenhum declara Photon). Em `meta.yaml`, `expects_kinds` ganha
   `databricks.photon` nos três, `expects_rules` vira `[SF-ENV-006]` em
   `databricks_flag_runtime` e `databricks_event_log_runtime`, e
   `[SF-ENV-001, SF-ENV-006]` em `databricks_divergent_spark`.

```bash
python scripts/regen_fixtures.py databricks_flag_runtime databricks_divergent_spark databricks_event_log_runtime
python scripts/refresh_knowledge.py --update --offline
python -m pytest tests/test_databricks_platform.py tests/test_fixtures_golden_runtime.py tests/test_rules_engine.py -q
```

8. Gates vizinhos da regra nova e do extrator:

```bash
python -m pytest tests/test_rules_loader.py tests/test_rules_catalog_reachability.py \
  tests/test_rules_result_axis.py tests/test_rules_engine.py \
  tests/test_agent_coverage.py tests/test_router_agents.py \
  tests/test_docs_coverage.py tests/test_fixtures_kind_coverage.py \
  tests/test_refresh_knowledge.py tests/test_rules_threshold_mutation.py \
  tests/test_rule_scope_by_nature.py tests/test_runtime_inferred_from_facts.py \
  tests/test_runtime_glue_versions.py -q
```

   `test_rules_engine` é alarme deliberado de motivo de pulo novo; a mensagem
   dele diz onde registrar a decisão, e o registro entra neste commit.

9. Commit: `feat(rules): refuse plan rules under declared Photon, warn when undeclared`.

## T6 — `tune` recusa `shuffle.partitions = auto`

1. Teste, em `tests/test_databricks_platform.py`:

```python
from sparkforge.tuning.spark_conf import build_conf_advice


def test_shuffle_partitions_auto_recusado():
    fatos = [
        _conf("spark.sql.shuffle.partitions", "auto"),
        Fact(
            kind="spark.stage.shuffle",
            subject={"type": "stage", "symbol": "1"},
            measures={"write_bytes": 10 * 1024**3},
            provenance={"extractor": "event_log@0.1.0"},
        ),
    ]
    conselho = build_conf_advice(fatos, runtime={"databricks": "15.4", "spark": "3.5.0"})
    recusa = next(
        r for r in conselho["refused"] if r["property"] == "spark.sql.shuffle.partitions"
    )
    assert recusa["reason"] == "shuffle_partitions_auto"
    assert all(p["key"] != "spark.sql.shuffle.partitions" for p in conselho["properties"])

    numerico = build_conf_advice(
        [_conf("spark.sql.shuffle.partitions", "400"), fatos[1]],
        runtime={"databricks": "15.4", "spark": "3.5.0"},
    )
    assert any(p["key"] == "spark.sql.shuffle.partitions" for p in numerico["properties"])
```

2. `python -m pytest tests/test_databricks_platform.py::test_shuffle_partitions_auto_recusado -q`:
   `StopIteration` (nenhuma recusa para a propriedade).

3. `sparkforge/tuning/spark_conf.py`, em `build_conf_advice`: logo antes de
   `if not spark_version:` do bloco de shuffle, acrescente

```python
    atual_shuffle, _classe_shuffle, _evidencia_shuffle = _procedencia(
        _CHAVE_SHUFFLE, efetivo, codigo, terraform
    )
```

   troque `if not spark_version:` por `elif not spark_version:` e insira,
   imediatamente antes dele:

```python
    if atual_shuffle.strip().lower() == "auto":
        # `auto` liga o auto-optimized shuffle do Databricks, que escolhe o
        # numero pelo plano e pelo volume. Derivar um numero fixo aqui seria
        # propor desliga-lo sem dizer. Fonte: docs.databricks.com/aws/en/
        # optimizations/aqe (opt-in; default 200).
        recusas.append(
            _recusa(
                "shuffle_partitions_auto",
                _CHAVE_SHUFFLE,
                "O valor atual e `auto`: o auto-optimized shuffle ja escolhe o numero "
                "de particoes pelo plano e pelo volume. Trocar por um numero fixo e "
                "desliga-lo, e isso e decisao do operador, nao derivacao da medida.",
            )
        )
```

4. `python -m pytest tests/test_databricks_platform.py::test_shuffle_partitions_auto_recusado tests/test_tuning_spark_conf.py -q`:
   verde. Se `tests/test_tuning_spark_conf.py` não existir,
   `python -m pytest tests -q -k "tune or spark_conf"` é o gate vizinho.

5. Commit: `fix(tune): refuse to derive a fixed shuffle.partitions over auto`.

## T7 — auditoria da remediação sem escopo

1. Teste, em `tests/test_databricks_rule_audit.py`:

```python
"""Regra sem escopo que um job Databricks alcanca nao remedia so para AWS.

O conjunto e recalculado dos EMITTED_KINDS dos extratores que um job Spark no
Databricks produz, nunca de uma lista de regras escrita a mao.
"""
import importlib

from sparkforge.rules.loader import load_catalog

EXTRATORES = (
    "event_log", "spark_plan", "sql_metrics", "pyspark_ast", "parquet_footer",
    "timeout_diagnosis", "bridge", "exception", "call_graph", "utilization",
    "workload", "runtime_detect",
)
TERMOS_AWS = ("Glue", "DPU", "G.1X", "G.2X", "EMR", "Lake Formation", "Athena", "DynamicFrame")
CAMPOS = ("proposed_change", "rollback", "validation", "explanation", "expected_effect", "risks", "tradeoffs")
EXCECOES = {
    "SF-PQ-002": (
        "o passo com DynamicFrame e condicional a leitura via DynamicFrame, que so "
        "existe no Glue; os demais passos da regra sao neutros"
    ),
}


def _kinds() -> set[str]:
    kinds: set[str] = set()
    for nome in EXTRATORES:
        kinds |= set(importlib.import_module(f"sparkforge.facts.{nome}").EMITTED_KINDS)
    return kinds


def _texto(regra: dict) -> str:
    return " ".join(str(regra.get(campo, "")) for campo in CAMPOS)


def _alcancaveis() -> list[dict]:
    kinds = _kinds()
    saida = []
    for regra in load_catalog():
        if regra.get("runtime_scope") or regra.get("executable") is False:
            continue
        exigidos = set(regra.get("requires_facts") or [])
        if exigidos and exigidos <= kinds:
            saida.append(regra)
    return saida


def test_regra_sem_escopo_nao_remedia_com_termo_aws():
    violadoras = {}
    for regra in _alcancaveis():
        texto = _texto(regra)
        termos = [t for t in TERMOS_AWS if t in texto]
        if termos and "Databricks" not in texto and regra["id"] not in EXCECOES:
            violadoras[regra["id"]] = termos
    assert violadoras == {}
    mortas = set(EXCECOES) - {r["id"] for r in _alcancaveis() if any(t in _texto(r) for t in TERMOS_AWS)}
    assert mortas == set()
```

2. `python -m pytest tests/test_databricks_rule_audit.py -q`: `AssertionError`
   com as 13 regras fora da exceção (SF-ENV-001, 004 e 005, SF-PLAN-004,
   SF-PY-008, 009, 010 e 012, SF-TIMEOUT-001, SF-UI-003, 004, 005 e 006).

3. Textos. `Runtime e DPU-hours antes e depois` vira
   `Runtime e custo de compute medido antes e depois` em
   `rules/catalog/pyspark.yaml` (linhas 398, 462, 512 e 597) e em
   `rules/catalog/spark-ui.yaml` (linhas 179, 223 e 321). As linhas de
   `parquet.yaml` e `glue-infra.yaml` com a mesma frase não entram: são de
   regra fora do conjunto, e o teste é quem decide o conjunto.

   `rules/catalog/spark-plan.yaml`, linha 244:
   `- Obter o plano final exige executar o job, o que custa tempo e DPU.` vira
   `- Obter o plano final exige executar o job, o que custa tempo e compute.`

   `rules/catalog/spark-ui.yaml`, linha 299:
   `Cores alocados e ociosos são DPU-hours pagas sem trabalho. Causas mais comuns:`
   vira
   `Cores alocados e ociosos são horas de compute pagas sem trabalho. Causas mais comuns:`

   `rules/catalog/spark-ui.yaml`, linha 271, depois de
   `      - Categoria de erro do Glue Observability sem OUT_OF_MEMORY_ERROR.`
   entra a linha
   `      - No Databricks, e em qualquer Spark sem Glue Observability, nenhum executor removido por OOM no event log do run seguinte.`

   `rules/catalog/timeout.yaml`, linha 58:
   ``      para broadcast; `wall_clock` é o relógio do Glue, que é consequência e não``
   vira
   ``      para broadcast; `wall_clock` é o limite de tempo do job na plataforma, que é consequência e não``

   `rules/catalog/env.yaml`, linha 74:
   `      - Versão de Iceberg confirmada no classpath, não inferida da versão de Glue.`
   vira
   `      - Versão de Iceberg confirmada no classpath, não inferida da versão da plataforma (Glue, EMR ou Databricks).`

   `rules/catalog/env.yaml`, SF-ENV-004, a linha
   `      knowledge/cross-service-constraints.md secao 4.` seguida de
   `    proposed_change:` ganha, entre as duas:

```yaml
      No Databricks, toda versão suportada do Databricks Runtime roda Spark 3.5 ou
      mais novo (knowledge/databricks/runtime-matrix.md).
```

   `rules/catalog/env.yaml`, linha 353:
   `      Um job roda numa plataforma só — ou AWS Glue, ou EMR, nunca as duas ao mesmo`
   vira
   `      Um job roda numa plataforma só — AWS Glue, EMR ou Databricks, nunca duas ao mesmo`

4. `python -m pytest tests/test_databricks_rule_audit.py -q`: verde.

5. Goldens das regras reescritas: `python scripts/regen_fixtures.py` sem
   argumento regenera todos os corpora; `git diff --stat fixtures` deve mostrar
   só `findings.json` das fixtures que disparam as 13 regras, e o diff de cada
   um só no texto trocado. Se `scripts/regen_fixtures.py` não regenera algum
   corpus que falhar nos lotes, o regen dele entra neste commit.

6. Gates vizinhos: o bloco de pytest da seção de regra de
   `docs/gates-por-mudanca.md` (o mesmo de T5, passo 8), os lotes, e
   `python scripts/check_vnext_claims.py`.

7. Commit: `fix(rules): platform-neutral remediation for rules a Databricks job reaches`.

## T8 — par de fixtures Glue e Databricks

1. Fixture `fixtures/eventlog/databricks_skewed_stage/`: copie
   `fixtures/eventlog/skewed_stage/input/eventlog.jsonl` para
   `fixtures/eventlog/databricks_skewed_stage/input/eventlog.jsonl` e mude só
   duas linhas: em `SparkListenerLogStart`, `"Spark Version":"3.5.4"` vira
   `"Spark Version":"3.5.0"`; em `SparkListenerEnvironmentUpdate`, dentro de
   `"Spark Properties"`, acrescente
   `"spark.databricks.clusterUsageTags.sparkVersion":"15.4.x-scala2.12"`.

   `meta.yaml`:

```yaml
name: databricks_skewed_stage
proves: >
  O par de skewed_stage sob Databricks Runtime 15.4: o mesmo event log, com a
  versao do runtime nas Spark Properties e Spark 3.5.0. As seis regras
  spark-ui disparam iguais, porque nenhuma depende de plataforma, e o texto
  delas nao cita so a AWS.
runtime:
  databricks: "15.4"
  spark: 3.5.0
expects_kinds:
- spark.cluster.cores
- spark.conf_effective
- spark.conf_excluded
- spark.executor.lost
- spark.job.spill_summary
- spark.log_analyzed
- spark.runtime_version
- spark.stage.callsite
- spark.stage.gc
- spark.stage.shuffle
- spark.stage.slow_tasks
- spark.stage.spill
- spark.stage.task_count
- spark.stage.task_duration
- spark.stage.task_input
- spark.unresolved
expects_rules:
- SF-UI-001
- SF-UI-002
- SF-UI-003
- SF-UI-004
- SF-UI-005
- SF-UI-006
```

   Em `tests/test_fixtures_golden_eventlog.py`, acrescente
   `"databricks_skewed_stage",` a `REQUIRED_FIXTURES`.

2. Teste, em `tests/test_databricks_platform.py`:

```python
import yaml

from sparkforge.facts.event_log import extract_event_log_path

EVENTLOG = ROOT / "fixtures" / "eventlog"


def _achados(caso: str) -> set[tuple]:
    entrada = EVENTLOG / caso / "input"
    fatos = []
    for jsonl in sorted(entrada.glob("*.jsonl")):
        fatos.extend(extract_event_log_path(jsonl, repo_root=entrada))
    meta = yaml.safe_load((EVENTLOG / caso / "meta.yaml").read_text(encoding="utf-8"))
    return {
        (f.rule_id, f.severity, repr(sorted(f.subject.items())))
        for f in judge(fatos, load_catalog(), meta["runtime"])
    }


def test_fixture_pareada_mesmos_findings_neutros():
    glue = _achados("skewed_stage")
    databricks = _achados("databricks_skewed_stage")
    assert glue
    assert databricks == glue
```

3. `python -m pytest tests/test_databricks_platform.py::test_fixture_pareada_mesmos_findings_neutros -q`:
   falha com `FileNotFoundError` sobre `databricks_skewed_stage/meta.yaml`
   antes do passo 1, e passa depois dele.

4. Golden: `mkdir -p fixtures/eventlog/databricks_skewed_stage/expected` e
   `python scripts/regen_fixtures.py databricks_skewed_stage`; depois
   `python -m pytest tests/test_fixtures_golden_eventlog.py tests/test_databricks_platform.py -q`.

5. Commit: `test(eventlog): Databricks pair of skewed_stage fires the same rules`.

## T9 — flags `--databricks` e `--photon` onde `--emr` já está

1. Teste, em `tests/test_databricks_platform.py`:

```python
import argparse
import inspect
import json

from sparkforge.adapters import _core, cli, tools


def _subparsers(parser):
    for acao in parser._actions:
        if isinstance(acao, argparse._SubParsersAction):
            for nome, sub in acao.choices.items():
                yield nome, sub
                yield from _subparsers(sub)


def test_flags_seguem_o_emr(capsys):
    faltando = []
    for nome, sub in _subparsers(cli.build_parser()):
        opcoes = {o for acao in sub._actions for o in acao.option_strings}
        if "--emr" in opcoes and not {"--databricks", "--photon"} <= opcoes:
            faltando.append(("cli", nome))
    for nome, spec in tools.TOOLS.items():
        propriedades = spec.get("inputSchema", {}).get("properties", {})
        if "emr" in propriedades and not {"databricks", "photon"} <= set(propriedades):
            faltando.append(("mcp", nome))
    for nome, funcao in inspect.getmembers(_core, inspect.isfunction):
        if nome.startswith("_"):
            continue
        parametros = inspect.signature(funcao).parameters
        if "emr" in parametros and not {"databricks", "photon"} <= set(parametros):
            faltando.append(("core", nome))
    assert faltando == []

    assert cli.main(["runtime", "detect", "--databricks", "15.4", "--photon", "on"]) == 0
    saida = json.loads(capsys.readouterr().out)
    assert (saida["databricks"], saida["spark"], saida["photon"]) == ("15.4", "3.5.0", "on")
    mcp = tools.call_tool("sparkforge_runtime_detect", {"databricks": "15.4", "photon": "off"})
    assert (mcp["databricks"], mcp["photon"]) == ("15.4", "off")
```

2. `python -m pytest tests/test_databricks_platform.py::test_flags_seguem_o_emr -q`:
   `AssertionError` listando os parsers, schemas e funções que têm `emr` e não
   têm as duas novas.

3. `sparkforge/adapters/cli.py`, logo depois de `_EMR_FLAG_HELP`:

```python
_DATABRICKS_FLAG_HELP = (
    "Versao do Databricks Runtime, como numero ('15.4') ou como o rotulo da "
    "Clusters API ('15.4.x-scala2.12'). E DECLARACAO, nao observacao: perde "
    "para a versao que o event log traz, e discordar vira divergencia reportada. "
    "Deriva spark pela matriz de knowledge/databricks/runtime-matrix.yaml."
)

_PHOTON_FLAG_HELP = (
    "Photon ligado ('on') ou desligado ('off') no cluster ou job Databricks. Com "
    "'on', regra que depende de plano sai em skipped com "
    "databricks.photon.unresolved; sem declaracao, SF-ENV-006 avisa que regra de "
    "plano calada nao e evidencia."
)
```

   Edições mecânicas, conferidas pelo teste do passo 1:

   - Depois de cada `X.add_argument("--emr", help=_EMR_FLAG_HELP)` (`judge_p`,
     `arbitrate_p`, `open_p`, `detect_p`, `deb_start`):
     `X.add_argument("--databricks", help=_DATABRICKS_FLAG_HELP)` e
     `X.add_argument("--photon", choices=("on", "off"), help=_PHOTON_FLAG_HELP)`.
   - Depois de `rc_p.add_argument("--emr")`:
     `rc_p.add_argument("--databricks")` e
     `rc_p.add_argument("--photon", choices=("on", "off"))`.
   - Nos três laços `for flag in ("--glue", "--spark", "--python", "--iceberg", "--athena", "--emr"):`
     a tupla ganha `"--databricks", "--photon"` no fim.
   - Em cada chamada com `emr=args.emr,` (nove), acrescente
     `databricks=args.databricks, photon=args.photon,` logo depois.

   `sparkforge/adapters/_core.py`:

   - Em toda função pública com `emr: str | None = None,` na assinatura,
     acrescente logo depois `databricks: str | None = None,` e
     `photon: str | None = None,`.
   - Em toda chamada que repassa `emr=emr` (a `build_runtime`,
     `build_runtime_context` ou a outra função daqui), acrescente
     `databricks=databricks, photon=photon` ao lado.

   `sparkforge/adapters/tools.py`, logo depois de `_EMR_INPUT`:

```python
_DATABRICKS_INPUT: dict[str, Any] = {
    "type": "string",
    "description": (
        "Versao do Databricks Runtime ('15.4' ou '15.4.x-scala2.12'). DECLARACAO, "
        "nao observacao: perde para o event log, e discordar vira divergencia "
        "reportada em `runtime.divergences`."
    ),
}

_PHOTON_INPUT: dict[str, Any] = {
    "type": "string",
    "enum": ["on", "off"],
    "description": (
        "Photon ligado ou desligado no Databricks. Com 'on', regra de plano sai em "
        "skipped com databricks.photon.unresolved."
    ),
}
```

   - Depois de cada `"emr": _EMR_INPUT,` (cinco):
     `"databricks": _DATABRICKS_INPUT,` e `"photon": _PHOTON_INPUT,`.
   - Depois de cada `"emr": {"type": "string"},` (três):
     `"databricks": {"type": "string"},` e `"photon": _PHOTON_INPUT,`.
   - No bloco `**{eixo: ... for eixo in ("glue", "spark", "python", "iceberg", "athena", "emr")}`,
     a tupla ganha `"databricks"`, e logo depois do bloco entra
     `"photon": _PHOTON_INPUT,`.
   - Na chamada `**{e: args.get(e) for e in ("glue", "spark", "python", "iceberg", "athena", "emr")}`,
     a tupla ganha `"databricks", "photon"`.
   - Depois de cada `emr=args.get("emr"),` (oito):
     `databricks=args.get("databricks"),` e `photon=args.get("photon"),`.

4. `python -m pytest tests/test_databricks_platform.py::test_flags_seguem_o_emr -q`: verde.

5. Gates vizinhos:

```bash
python scripts/check_surface_lock.py --update
python scripts/gen_reference_docs.py
python -m pytest tests/test_surface_lock.py tests/test_reference_docs.py tests/test_adapters_tools.py -q
```

   Mais os lotes da suíte, porque parser e schema MCP têm testes de paridade
   espalhados (`fixtures/mcp_parity`).

6. Commit: `feat(cli): --databricks and --photon wherever --emr is accepted`, com
   o crescimento do surface lock declarado no corpo (regra 26).

## T10 — documentação

1. Teste, em `tests/test_databricks_platform.py`:

```python
def test_readme_declara_databricks():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "--databricks" in readme
    assert "knowledge/databricks/runtime-matrix.md" in readme
    status = (ROOT / "docs" / "superpowers" / "STATUS.md").read_text(encoding="utf-8")
    assert "DATABRICKS_SPARK" in status
```

2. `python -m pytest tests/test_databricks_platform.py::test_readme_declara_databricks -q`:
   `AssertionError` sobre `--databricks`.

3. `README.md`: na seção que lista as plataformas de runtime (a que cita
   `--emr`), um parágrafo:

```markdown
**Databricks.** `--databricks <versão>` declara o Databricks Runtime (`15.4` ou
`15.4.x-scala2.12`) e deriva a versão do Spark pela matriz em
`knowledge/databricks/runtime-matrix.md`; a versão também é lida do event log
quando ele traz `spark.databricks.clusterUsageTags.sparkVersion`.
`--photon on|off` declara o Photon: ligado, as regras de plano saem em `skipped`
com `databricks.photon.unresolved`; não declarado, SF-ENV-006 avisa. Fora deste
incremento: `_delta_log`, Jobs API, billing em DBU e coleta pela REST API.
```

   `docs/superpowers/STATUS.md`: uma linha na tabela de frentes, no formato
   das vizinhas, com `DATABRICKS_SPARK`, a data de 2026-09-17, o estado e o
   que ficou aberto (U1 e U2).

4. `python -m pytest tests/test_databricks_platform.py::test_readme_declara_databricks tests/test_docs_coverage.py tests/test_runtime_detect.py -q`:
   verde. `python scripts/check_status_numbers.py` se a linha tocar a tabela de
   números correntes.

5. Commit: `docs: Databricks as a declared platform, and what stays out`.
