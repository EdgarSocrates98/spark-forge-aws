# Métricas de scan por nó do plano — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ler as métricas SQL que o Spark já publica no event log e emitir, por nó de leitura, quantos bytes e quantos arquivos aquela fonte custou — medido, nunca estimado.

**Architecture:** Extrator novo `sparkforge/facts/sql_metrics.py`, que lê o mesmo artefato de event log que `event_log.py` lê, com outra ótica. Passada única em streaming: `SparkListenerSQLExecutionStart` traz a árvore (`sparkPlanInfo`) e o mapa `accumulatorId → (nó, nome de métrica)`; `SparkListenerDriverAccumUpdates` e os `Accumulables` de `SparkListenerTaskEnd` trazem os valores. Nome de métrica fora do mapa canônico de `knowledge/` vira lacuna declarada, nunca palpite.

**Tech Stack:** Python 3, `pytest`, `PyYAML`. Spec: [`../specs/2026-08-28-spark-sql-scan-metrics-design.md`](../specs/2026-08-28-spark-sql-scan-metrics-design.md).

**Convenções do repositório que valem em toda tarefa:**

- Fact nunca aplica limiar, nunca atribui severidade, nunca toca a rede.
- Todo fact declara `subject.type` de um enum fechado (`sparkforge/findings/schemas/fact.schema.json`). Aqui é sempre `plan_node` ou `source_location`.
- Todo comando roda com prefixo `rtk` (ver `CLAUDE.md`): `rtk pytest`, `rtk git commit`.
- Commit em português, Conventional Commits, via `rtk git commit -F <arquivo>` — heredoc dentro de `$(...)` dispara prompt de permissão.
- Não rode a suíte inteira sem alvo (17 minutos). Rode o que cada tarefa pede.

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `knowledge/spark/sql-metrics.yaml` | Mapa canônico nome de métrica → measure, legível por máquina |
| `knowledge/spark/sql-metrics.md` | A prosa que explica o mapa e aponta para o YAML |
| `sparkforge/facts/sql_metric_names.py` | Carregador fail-closed do YAML, no molde de `facts/cloudwatch_retention.py` |
| `sparkforge/facts/sql_metrics.py` | O extrator |
| `tests/test_sql_metric_names.py` | Testes do carregador |
| `tests/test_facts_sql_metrics.py` | Testes do extrator |
| `tests/test_fixtures_golden_sql_metrics.py` | Módulo golden do domínio novo |
| `fixtures/sql_metrics/` | Seis cenários sintéticos |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `knowledge/sources.lock.json` | Fonte do mapa, com `retrieved`, `checked_at`, `sha256` |
| `knowledge/offline-manifest.json` | sha256 do `.md` novo |
| `sparkforge/adapters/_core.py` | `analyze_sql_metrics` |
| `sparkforge/adapters/cli.py` | Parser, handler e entrada de despacho |
| `sparkforge/adapters/tools.py` | Schema da tool, handler e entrada de despacho |
| `manifest.json` | Lista `tools` ganha a nova |
| `parity.yaml` | Capability de análise ganha CLI e tool |
| `agents/` (coordenador ou executor) | Citar a tool nova, senão o gate de órfão reprova |
| `README.md`, `docs/superpowers/STATUS.md` | O verbo novo, a fase, e os números **medidos** |

---

## Task 1: Conhecimento — o mapa canônico de nomes de métrica

**Files:**
- Create: `knowledge/spark/sql-metrics.yaml`
- Create: `knowledge/spark/sql-metrics.md`
- Modify: `knowledge/sources.lock.json`
- Modify: `knowledge/offline-manifest.json`

- [ ] **Step 1: Ler a fonte e anotar os nomes**

Os nomes de métrica não são inventados por este projeto: eles vêm de `SQLMetrics` no código do Spark, e cada operador declara os seus. Consulte a fonte oficial do Spark para a versão corrente da matriz do projeto (`knowledge/glue/runtime-matrix.yaml` diz quais versões importam) e anote, para cada nome, em que versões ele foi verificado.

Os nomes abaixo são o ponto de partida medido em `FileSourceScanExec`. **Se a fonte contradisser qualquer linha, a fonte vence e o YAML se ajusta a ela** — e a divergência entra no relatório da tarefa.

| Nome publicado | Measure | Origem |
|---|---|---|
| `number of files read` | `files_read` | métrica de driver de `FileSourceScanExec` |
| `size of files read` | `bytes_read` | métrica de driver de `FileSourceScanExec` |
| `number of output rows` | `rows_output` | métrica de tarefa, comum a v1 e v2 |
| `number of partitions read` | `partitions_read` | métrica de driver de `FileSourceScanExec` |

- [ ] **Step 2: Escrever o YAML**

`knowledge/spark/sql-metrics.yaml`:

```yaml
# Mapa canonico de nome de metrica SQL do Spark para a measure que o extrator
# emite. LISTA FECHADA de proposito: nome fora daqui vira
# `spark.sql.unresolved` com razao `unknown_metric_name`, nunca palpite.
#
# Casar por substring seria o defeito que este arquivo existe para evitar:
# "bytes" casaria `size of files read` certo e `bytes of shuffle write` errado,
# e o erro sairia com aparencia de medicao.
#
# `verified_in` e a lista de versoes de Spark em que o nome foi conferido na
# fonte. Nome de metrica do Spark nao e constante universal.
version: 1
metrics:
  - published: "number of files read"
    measure: files_read
    metric_type: sum
    verified_in: ["3.3.0", "3.5.4"]
  - published: "size of files read"
    measure: bytes_read
    metric_type: size
    verified_in: ["3.3.0", "3.5.4"]
  - published: "number of output rows"
    measure: rows_output
    metric_type: sum
    verified_in: ["3.3.0", "3.5.4"]
  - published: "number of partitions read"
    measure: partitions_read
    metric_type: sum
    verified_in: ["3.3.0", "3.5.4"]
```

Ajuste `verified_in` para as versões que você realmente conferiu na fonte.

- [ ] **Step 3: Escrever o Markdown que aponta para o YAML**

`knowledge/spark/sql-metrics.md` explica, em prosa: o que é uma métrica SQL do Spark, por que o mapa é lista fechada, e que a tabela legível por máquina está no `.yaml` ao lado. **Não repita a tabela no Markdown** — duas cópias divergem, e a razão está registrada em `docs/gates-por-mudanca.md`. Inclua a seção `## Fontes` com a URL e a data.

- [ ] **Step 4: Registrar a fonte no lock**

```bash
rtk python scripts/refresh_knowledge.py --update --offline
rtk pytest tests/test_refresh_knowledge.py -q
```

- [ ] **Step 5: Regravar o sha256 no manifesto offline**

Documento novo em `knowledge/` exige entrada no `knowledge/offline-manifest.json`, com o hash calculado do mesmo jeito que o gate confere:

```bash
rtk python -c "
import json, pathlib
from sparkforge.tools.offline import _content_sha256
p = pathlib.Path('knowledge/offline-manifest.json')
m = json.loads(p.read_text(encoding='utf-8'))
alvo = pathlib.Path('knowledge/spark/sql-metrics.md')
m['documents'].append({'path': 'knowledge/spark/sql-metrics.md', 'title': 'sql-metrics', 'sha256': _content_sha256(alvo)})
m['documents'].sort(key=lambda d: d['path'])
p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
"
```

Confira o formato real do arquivo antes de rodar — se as entradas tiverem outros campos, reproduza-os.

- [ ] **Step 6: Rodar os gates de conhecimento**

```bash
rtk pytest tests/test_offline_expansion.py -q
rtk python scripts/verify_offline_bundle.py
```

Esperado: PASS nos dois, e `"ok": true` com `"failed": []` no segundo.

- [ ] **Step 7: Commit**

```bash
rtk git add knowledge/spark/sql-metrics.yaml knowledge/spark/sql-metrics.md knowledge/sources.lock.json knowledge/offline-manifest.json
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `docs(knowledge): mapa canonico de metrica SQL do Spark, com fonte e data`

---

## Task 2: Carregador fail-closed do mapa

**Files:**
- Create: `sparkforge/facts/sql_metric_names.py`
- Test: `tests/test_sql_metric_names.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_sql_metric_names.py`:

```python
"""Testes do carregador do mapa canonico de metricas SQL."""
from __future__ import annotations

import pytest

from sparkforge.facts.sql_metric_names import MetricMapError, measure_for, load_map


class TestLoad:
    def test_known_name_maps_to_a_measure(self):
        assert measure_for("size of files read") == "bytes_read"
        assert measure_for("number of files read") == "files_read"

    def test_unknown_name_returns_none_instead_of_guessing(self):
        assert measure_for("bytes of shuffle write") is None
        assert measure_for("") is None

    def test_the_map_is_not_empty(self):
        assert len(load_map()) >= 4

    def test_every_entry_declares_where_it_was_verified(self):
        for entry in load_map().values():
            assert entry["verified_in"], entry


class TestFailClosed:
    def test_missing_file_raises_instead_of_returning_empty(self, monkeypatch, tmp_path):
        from sparkforge.facts import sql_metric_names

        monkeypatch.setattr(sql_metric_names, "_MAP_PATH", tmp_path / "nao-existe.yaml")
        sql_metric_names.load_map.cache_clear()
        with pytest.raises(MetricMapError, match="nao encontrado"):
            sql_metric_names.load_map()
        sql_metric_names.load_map.cache_clear()

    def test_malformed_file_raises_instead_of_returning_empty(self, monkeypatch, tmp_path):
        from sparkforge.facts import sql_metric_names

        alvo = tmp_path / "sql-metrics.yaml"
        alvo.write_text("metrics: nao-e-lista\n", encoding="utf-8")
        monkeypatch.setattr(sql_metric_names, "_MAP_PATH", alvo)
        sql_metric_names.load_map.cache_clear()
        with pytest.raises(MetricMapError):
            sql_metric_names.load_map()
        sql_metric_names.load_map.cache_clear()

    def test_duplicate_published_name_raises(self, monkeypatch, tmp_path):
        from sparkforge.facts import sql_metric_names

        alvo = tmp_path / "sql-metrics.yaml"
        alvo.write_text(
            "version: 1\n"
            "metrics:\n"
            "  - {published: 'x', measure: a, metric_type: sum, verified_in: ['3.5.4']}\n"
            "  - {published: 'x', measure: b, metric_type: sum, verified_in: ['3.5.4']}\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(sql_metric_names, "_MAP_PATH", alvo)
        sql_metric_names.load_map.cache_clear()
        with pytest.raises(MetricMapError, match="duplicad"):
            sql_metric_names.load_map()
        sql_metric_names.load_map.cache_clear()
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_sql_metric_names.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.sql_metric_names'`.

- [ ] **Step 3: Implementar**

Antes de escrever, **leia `sparkforge/facts/cloudwatch_retention.py`** e siga a forma dele: mesmo tipo de exceção, mesmo uso de cache, mesma disciplina de fail-closed.

`sparkforge/facts/sql_metric_names.py`:

```python
"""Carregador do mapa canonico de nome de metrica SQL do Spark.

Fail-closed pelo mesmo motivo que `facts/cloudwatch_retention.py`: mapa que
some vira dicionario vazio, todo nome de metrica vira desconhecido, e a
extracao inteira sai sem uma unica measure -- sem erro nenhum. Silencio que
se parece com "esta execucao nao publicou metrica" e o pior modo de falha
possivel para este extrator, porque e indistinguivel do caso legitimo.

O mapa e LISTA FECHADA. Nome fora dele nao recebe palpite: quem chama recebe
`None` e emite a lacuna com o nome cru.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_MAP_PATH = Path(__file__).resolve().parents[2] / "knowledge" / "spark" / "sql-metrics.yaml"

_CAMPOS = ("published", "measure", "metric_type", "verified_in")


class MetricMapError(RuntimeError):
    """O mapa nao pode ser lido ou nao tem a forma esperada."""


@lru_cache(maxsize=1)
def load_map() -> dict[str, dict[str, Any]]:
    """Devolve `{nome publicado: entrada}`. Levanta em vez de devolver vazio."""
    if not _MAP_PATH.is_file():
        raise MetricMapError(
            f"mapa de metricas SQL nao encontrado em {_MAP_PATH}. Ele e dado, nao "
            f"codigo: sem ele o extrator nao sabe qual nome vira qual measure."
        )
    try:
        cru = yaml.safe_load(_MAP_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MetricMapError(f"mapa de metricas SQL ilegivel: {exc}") from exc

    entradas = (cru or {}).get("metrics")
    if not isinstance(entradas, list) or not entradas:
        raise MetricMapError(
            f"{_MAP_PATH}: a chave `metrics` precisa ser uma lista nao vazia."
        )

    mapa: dict[str, dict[str, Any]] = {}
    for entrada in entradas:
        if not isinstance(entrada, dict) or any(c not in entrada for c in _CAMPOS):
            raise MetricMapError(
                f"{_MAP_PATH}: entrada sem os campos {_CAMPOS}: {entrada!r}"
            )
        nome = entrada["published"]
        if nome in mapa:
            raise MetricMapError(
                f"{_MAP_PATH}: nome publicado duplicado {nome!r}. Duas measures para o "
                f"mesmo nome tornaria a atribuicao dependente da ordem do arquivo."
            )
        mapa[nome] = entrada
    return mapa


def measure_for(published: str) -> str | None:
    """Nome da measure para um nome publicado, ou `None` se ele nao esta no mapa."""
    entrada = load_map().get(published)
    return entrada["measure"] if entrada else None
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_sql_metric_names.py -v
```

Esperado: PASS, 7 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/sql_metric_names.py tests/test_sql_metric_names.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): carregador fail-closed do mapa de metricas SQL`

---

## Task 3: A árvore do plano e o mapa de acumuladores

**Files:**
- Create: `sparkforge/facts/sql_metrics.py`
- Test: `tests/test_facts_sql_metrics.py`

Esta tarefa lê a árvore e monta o mapa. **Nenhum valor ainda** — os valores são a Task 4.

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_facts_sql_metrics.py`:

```python
"""Testes do extrator de metricas SQL por no do plano."""
from __future__ import annotations

import json

from sparkforge.facts.sql_metrics import extract_sql_metrics

SQL_START = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart"


def _scan_node(node_name="Scan parquet ", simple="FileScan parquet db.clientes[id#1]", metrics=None):
    return {
        "nodeName": node_name,
        "simpleString": simple,
        "children": [],
        "metadata": {"Format": "Parquet", "Location": "InMemoryFileIndex[s3://bucket/x]"},
        "metrics": metrics if metrics is not None else [],
    }


def _start(execution_id=0, plan=None, description="save at Job.scala:1"):
    return json.dumps(
        {
            "Event": SQL_START,
            "executionId": execution_id,
            "description": description,
            "details": "",
            "physicalPlanDescription": "== Physical Plan ==",
            "sparkPlanInfo": plan,
            "time": 1600000000000,
        }
    )


class TestPlanTree:
    def test_scan_node_becomes_a_fact_anchored_on_plan_node(self):
        plano = {
            "nodeName": "Project",
            "simpleString": "Project [id#1]",
            "metadata": {},
            "metrics": [],
            "children": [_scan_node()],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")

        scans = [f for f in facts if f.kind == "spark.sql.scan"]
        assert len(scans) == 1
        assert scans[0].subject["type"] == "plan_node"
        assert scans[0].subject["execution_id"] == 0
        assert scans[0].subject["relation"] == "db.clientes"
        assert scans[0].attrs["scan_api"] == "v1"
        assert scans[0].attrs["format"] == "parquet"

    def test_node_id_is_the_preorder_index(self):
        plano = {
            "nodeName": "Project",
            "simpleString": "Project",
            "metadata": {},
            "metrics": [],
            "children": [_scan_node()],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        # raiz = 0, primeiro filho em preorder = 1
        assert scan.subject["node_id"] == 1

    def test_symbol_separates_the_same_node_across_executions(self):
        plano = _scan_node()
        facts = extract_sql_metrics(
            [_start(execution_id=0, plan=plano), _start(execution_id=1, plan=plano)],
            "log.jsonl",
        )
        simbolos = {f.subject["symbol"] for f in facts if f.kind == "spark.sql.scan"}

        assert len(simbolos) == 2

    def test_batch_scan_is_marked_v2(self):
        plano = _scan_node(node_name="BatchScan", simple="BatchScan db.eventos[id#1]")
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert scan.attrs["scan_api"] == "v2"
        assert scan.subject["relation"] == "db.eventos"

    def test_execution_fact_counts_the_nodes(self):
        plano = {
            "nodeName": "Project",
            "simpleString": "Project",
            "metadata": {},
            "metrics": [],
            "children": [_scan_node(), _scan_node(simple="FileScan parquet db.pedidos[id#2]")],
        }
        facts = extract_sql_metrics([_start(plan=plano)], "log.jsonl")
        execucao = [f for f in facts if f.kind == "spark.sql.execution"][0]

        assert execucao.measures == {"scan_nodes": 2, "nodes_total": 3}
        assert execucao.attrs["plan_source"] == "initial"


class TestNoLeak:
    def test_s3_location_never_enters_any_fact(self):
        facts = extract_sql_metrics([_start(plan=_scan_node())], "log.jsonl")
        blob = json.dumps([f.to_dict() for f in facts])

        assert "s3://bucket/x" not in blob
        assert "InMemoryFileIndex" not in blob
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.sql_metrics'`.

- [ ] **Step 3: Implementar**

`sparkforge/facts/sql_metrics.py`:

```python
"""Extrator de metricas SQL por no do plano, a partir do Spark event log.

O MESMO artefato que `facts/event_log.py` le, com outra pergunta. Aquele
responde "quanto cada stage custou"; este responde "quanto cada FONTE custou".
Modulo separado pelo precedente que o repositorio ja tem: `data_quality` e
`graph` leem o mesmo `.py` que `pyspark_ast`, cada um com o seu vocabulario.

O que liga os dois lados ja esta dentro do arquivo, e ninguem lia:
`SparkListenerSQLExecutionStart` carrega `sparkPlanInfo`, a arvore do plano com
os `accumulatorId` de cada metrica; os valores chegam depois, em
`SparkListenerDriverAccumUpdates` e nos `Accumulables` de `SparkListenerTaskEnd`.

Streaming, uma passada, como `extract_event_log`: o insumo pode ter centenas de
MB, e uma unica linha de `SQLExecutionStart` carrega o
`physicalPlanDescription` inteiro.

Puro e deterministico: nunca aplica limiar, nunca atribui severidade, nunca
toca a rede.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from sparkforge.facts.secrets import redact
from sparkforge.facts.sql_metric_names import measure_for
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "sql_metrics@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "spark.sql.scan",
        "spark.sql.execution",
        "spark.sql.unresolved",
        "spark.sql.analyzed",
    }
)

_SQL_START = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart"
_SQL_AQE = "org.apache.spark.sql.execution.ui.SparkListenerSQLAdaptiveExecutionUpdate"
_SQL_END = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd"
_DRIVER_ACCUM = "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates"
_TASK_END = "SparkListenerTaskEnd"

# Mesma distincao que `spark_plan.py` faz sobre o texto do `explain`, aplicada
# aqui sobre `simpleString`. Reescrita em vez de importada pela razao ja
# registrada em `iceberg_metadata.py`: os extratores sao modulos independentes
# por desenho, e o que garante que os dois concordam e teste, nao import.
# O token de formato precisa comecar em MINUSCULA: `Scan` tambem prefixa
# operadores que nao leem arquivo (`Scan ExistingRDD`, `Scan OneRowRelation`).
_SCAN_V1_RE = re.compile(r"^(?:File)?Scan\s+([a-z][\w-]*)\s+([^\[\s]+)")
_SCAN_V2_RE = re.compile(r"^BatchScan\s+([^\[\s]+)")


def _scan_of(node: dict[str, Any]) -> tuple[str, str, str] | None:
    """Devolve `(scan_api, relation, format)` se o no le arquivo, senao `None`."""
    simple = str(node.get("simpleString") or "").strip()
    formato = str((node.get("metadata") or {}).get("Format") or "").lower()

    casou_v2 = _SCAN_V2_RE.match(simple)
    if casou_v2:
        return "v2", casou_v2.group(1), formato

    casou_v1 = _SCAN_V1_RE.match(simple)
    if casou_v1:
        return "v1", casou_v1.group(2), formato or casou_v1.group(1)

    return None


def _walk(node: dict[str, Any], proximo: list[int]) -> Iterator[tuple[int, dict[str, Any]]]:
    """Percorre a arvore em preorder, numerando os nos.

    O `sparkPlanInfo` NAO carrega id de no. O indice de preorder e a
    identidade que este extrator constroi, e ela e estavel para a mesma
    arvore: raiz = 0, e cada filho na ordem em que o Spark os escreveu.
    Numerar de outro jeito -- por hash do texto, por exemplo -- faria dois
    nos identicos em ramos diferentes colidirem.
    """
    meu = proximo[0]
    proximo[0] += 1
    yield meu, node
    for filho in node.get("children") or []:
        yield from _walk(filho, proximo)


class _Execution:
    """Estado acumulado de uma execucao SQL durante a passada."""

    def __init__(self, execution_id: int, description: str) -> None:
        self.execution_id = execution_id
        self.description, self.redacted = redact("description", description)
        self.plan_source = "initial"
        self.nodes: dict[int, dict[str, Any]] = {}
        self.nodes_total = 0
        # accumulatorId -> (node_id, nome publicado da metrica)
        self.accum: dict[int, tuple[int, str]] = {}
        self.reassigned: set[int] = set()
        self.unknown: list[tuple[int, str]] = []
        self.ended = False

    def absorb_plan(self, plano: dict[str, Any], source: str) -> None:
        self.plan_source = source
        self.nodes = {}
        self.nodes_total = 0
        for node_id, node in _walk(plano, [0]):
            self.nodes_total += 1
            scan = _scan_of(node)
            if scan is None:
                continue
            api, relation, formato = scan
            self.nodes[node_id] = {
                "node_name": str(node.get("nodeName") or "").strip(),
                "relation": relation,
                "scan_api": api,
                "format": formato,
            }

        for node_id, node in _walk(plano, [0]):
            for metrica in node.get("metrics") or []:
                accum_id = metrica.get("accumulatorId")
                nome = str(metrica.get("name") or "")
                if not isinstance(accum_id, int):
                    continue
                anterior = self.accum.get(accum_id)
                if anterior is not None and anterior[0] != node_id:
                    # O mesmo acumulador em dois nos: atribuir a qualquer um
                    # poria bytes no no errado, e o relatorio ficaria plausivel
                    # e falso.
                    self.reassigned.add(accum_id)
                    continue
                self.accum[accum_id] = (node_id, nome)
```

O restante do módulo — `extract_sql_metrics` e a emissão dos facts — entra em pedaços nas tarefas seguintes. Para esta tarefa, acrescente ao final:

```python
def _plan_node_subject(
    execution_id: int, node_id: int, operator: str, relation: str
) -> dict[str, Any]:
    """Subject de no de plano, na forma que o schema de Fact exige.

    `symbol` inclui o `execution_id` porque `same_subject` agrupa por ele: duas
    execucoes do mesmo plano tem o mesmo `node_id`, e sem o prefixo elas cairiam
    no mesmo grupo -- os bytes de uma vazariam para o achado da outra.
    """
    return {
        "type": "plan_node",
        "node_id": node_id,
        "operator": operator,
        "relation": relation,
        "symbol": f"{execution_id}:{node_id}",
        "execution_id": execution_id,
    }


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def extract_sql_metrics(lines: Iterable[str], path: str) -> list[Fact]:
    """Extrai Facts de um Spark event log dado como `Iterable[str]`."""
    execucoes: dict[int, _Execution] = {}

    for linha in lines:
        texto = linha.strip()
        if not texto:
            continue
        try:
            evento = json.loads(texto)
        except (ValueError, TypeError):
            continue
        nome = evento.get("Event")

        if nome in (_SQL_START, _SQL_AQE):
            execution_id = evento.get("executionId")
            plano = evento.get("sparkPlanInfo")
            if not isinstance(execution_id, int) or not isinstance(plano, dict):
                continue
            execucao = execucoes.get(execution_id)
            if execucao is None:
                execucao = _Execution(execution_id, str(evento.get("description") or ""))
                execucoes[execution_id] = execucao
            execucao.absorb_plan(plano, "final_aqe" if nome == _SQL_AQE else "initial")

    facts: list[Fact] = []
    for execucao in sorted(execucoes.values(), key=lambda e: e.execution_id):
        for node_id, node in sorted(execucao.nodes.items()):
            facts.append(
                Fact(
                    kind="spark.sql.scan",
                    subject=_plan_node_subject(
                        execucao.execution_id, node_id, node["node_name"], node["relation"]
                    ),
                    attrs={
                        "format": node["format"],
                        "scan_api": node["scan_api"],
                        "node_name": node["node_name"],
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        facts.append(
            Fact(
                kind="spark.sql.execution",
                subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                attrs={
                    "plan_source": execucao.plan_source,
                    "description": execucao.description,
                    "redacted": execucao.redacted,
                },
                measures={
                    "scan_nodes": len(execucao.nodes),
                    "nodes_total": execucao.nodes_total,
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )

    facts.append(
        Fact(
            kind="spark.sql.analyzed",
            subject=_file_subject(path),
            measures={
                "executions": len(execucoes),
                "scan_nodes": sum(len(e.nodes) for e in execucoes.values()),
                "unattributed_accumulators": 0,
                "malformed_lines": 0,
            },
            provenance={"extractor": EXTRACTOR_ID, "artifact": path},
        )
    )
    return sort_facts(facts)
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS, 6 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/sql_metrics.py tests/test_facts_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): arvore do plano e mapa de acumuladores do event log SQL`

---

## Task 4: Os valores — driver e tarefa

**Files:**
- Modify: `sparkforge/facts/sql_metrics.py`
- Test: `tests/test_facts_sql_metrics.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_sql_metrics.py`:

```python
DRIVER_ACCUM = "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates"


def _metric(name, accumulator_id, metric_type="sum"):
    return {"name": name, "accumulatorId": accumulator_id, "metricType": metric_type}


def _driver_update(execution_id, pares):
    return json.dumps(
        {"Event": DRIVER_ACCUM, "executionId": execution_id, "accumUpdates": pares}
    )


def _task_end(accumulables):
    return json.dumps(
        {
            "Event": "SparkListenerTaskEnd",
            "Stage ID": 1,
            "Task Info": {"Accumulables": accumulables},
        }
    )


def _accumulable(accumulator_id, name, update, value):
    return {
        "ID": accumulator_id,
        "Name": name,
        "Update": str(update),
        "Value": str(value),
        "Internal": False,
        "Count Failed Values": True,
    }


class TestValues:
    def test_driver_metric_becomes_a_measure(self):
        plano = _scan_node(metrics=[_metric("number of files read", 11)])
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 7]])], "log.jsonl"
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert scan.measures["files_read"] == 7

    def test_task_metric_sums_the_updates_not_the_running_value(self):
        plano = _scan_node(metrics=[_metric("size of files read", 12, "size")])
        facts = extract_sql_metrics(
            [
                _start(plan=plano),
                _task_end([_accumulable(12, "size of files read", 1000, 1000)]),
                _task_end([_accumulable(12, "size of files read", 500, 1500)]),
            ],
            "log.jsonl",
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        # 1000 + 500. Somar `Value` daria 2500, que conta o total duas vezes.
        assert scan.measures["bytes_read"] == 1500

    def test_metric_the_execution_never_published_is_absent_not_zero(self):
        plano = _scan_node(metrics=[_metric("number of files read", 11)])
        facts = extract_sql_metrics([_start(plan=plano), _driver_update(0, [[11, 3]])], "log.jsonl")
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert scan.measures["files_read"] == 3
        assert "bytes_read" not in scan.measures
        assert "rows_output" not in scan.measures

    def test_unknown_metric_name_becomes_unresolved_never_a_guess(self):
        plano = _scan_node(metrics=[_metric("bytes of shuffle write", 13)])
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[13, 999]])], "log.jsonl"
        )
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "unknown_metric_name"
        ]

        assert scan.measures == {}
        assert len(lacunas) == 1
        assert lacunas[0].attrs["metric_name"] == "bytes of shuffle write"

    def test_accumulator_of_no_sql_node_is_counted_not_discarded(self):
        plano = _scan_node(metrics=[_metric("number of files read", 11)])
        facts = extract_sql_metrics(
            [
                _start(plan=plano),
                _task_end([_accumulable(9999, "internal.metrics.executorRunTime", 5, 5)]),
            ],
            "log.jsonl",
        )
        sentinela = [f for f in facts if f.kind == "spark.sql.analyzed"][0]

        assert sentinela.measures["unattributed_accumulators"] == 1
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_sql_metrics.py::TestValues -v
```

Esperado: FAIL — nenhuma measure é emitida ainda.

- [ ] **Step 3: Implementar**

Em `_Execution.__init__`, acrescente:

```python
        self.values: dict[int, float] = {}
```

Acrescente a `_Execution`:

```python
    def add_value(self, accum_id: int, valor: float) -> bool:
        """Soma um valor a um acumulador conhecido. Devolve se ele foi atribuido."""
        if accum_id in self.reassigned or accum_id not in self.accum:
            return False
        self.values[accum_id] = self.values.get(accum_id, 0.0) + valor
        return True

    def measures_by_node(self) -> tuple[dict[int, dict[str, Any]], list[tuple[int, str]]]:
        """`{node_id: {measure: valor}}` e a lista de nomes fora do mapa."""
        por_no: dict[int, dict[str, Any]] = {}
        desconhecidos: list[tuple[int, str]] = []
        for accum_id, (node_id, nome) in sorted(self.accum.items()):
            if node_id not in self.nodes:
                continue
            measure = measure_for(nome)
            if measure is None:
                desconhecidos.append((node_id, nome))
                continue
            if accum_id not in self.values:
                # Metrica declarada no plano e nunca publicada. Ausencia, nao zero.
                continue
            valor = self.values[accum_id]
            por_no.setdefault(node_id, {})[measure] = (
                int(valor) if float(valor).is_integer() else valor
            )
        return por_no, desconhecidos
```

No laço de eventos de `extract_sql_metrics`, depois do bloco de `_SQL_START`/`_SQL_AQE`, acrescente:

```python
        elif nome == _DRIVER_ACCUM:
            execucao = execucoes.get(evento.get("executionId"))
            if execucao is None:
                continue
            for par in evento.get("accumUpdates") or []:
                if not isinstance(par, (list, tuple)) or len(par) != 2:
                    continue
                accum_id, valor = par
                if not isinstance(accum_id, int):
                    continue
                try:
                    numero = float(valor)
                except (TypeError, ValueError):
                    continue
                if not execucao.add_value(accum_id, numero):
                    nao_atribuidos += 1

        elif nome == _TASK_END:
            acumulaveis = ((evento.get("Task Info") or {}).get("Accumulables")) or []
            for acumulavel in acumulaveis:
                accum_id = acumulavel.get("ID")
                if not isinstance(accum_id, int):
                    continue
                try:
                    # `Update` e a contribuicao DESTA task; `Value` e o total
                    # corrente do acumulador. Somar `Value` contaria o total uma
                    # vez por task.
                    numero = float(acumulavel.get("Update"))
                except (TypeError, ValueError):
                    continue
                atribuido = any(e.add_value(accum_id, numero) for e in execucoes.values())
                if not atribuido:
                    nao_atribuidos += 1
```

Declare `nao_atribuidos = 0` antes do laço.

Troque a emissão do fact de scan para incluir measures e as lacunas:

```python
    for execucao in sorted(execucoes.values(), key=lambda e: e.execution_id):
        por_no, desconhecidos = execucao.measures_by_node()
        for node_id, node in sorted(execucao.nodes.items()):
            facts.append(
                Fact(
                    kind="spark.sql.scan",
                    subject=_plan_node_subject(
                        execucao.execution_id, node_id, node["node_name"], node["relation"]
                    ),
                    measures=por_no.get(node_id, {}),
                    attrs={
                        "format": node["format"],
                        "scan_api": node["scan_api"],
                        "node_name": node["node_name"],
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        for node_id, metric_name in desconhecidos:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(
                        execucao.execution_id,
                        node_id,
                        execucao.nodes[node_id]["node_name"],
                        execucao.nodes[node_id]["relation"],
                    ),
                    attrs={
                        "reason": "unknown_metric_name",
                        "metric_name": metric_name,
                        "detail": (
                            "Nome de metrica fora de knowledge/spark/sql-metrics.yaml. "
                            "Casar por substring produziria numero com aparencia de "
                            "medido; o nome cru fica aqui para quem for atualizar o mapa."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
```

E troque `"unattributed_accumulators": 0` por `"unattributed_accumulators": nao_atribuidos`.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS, 11 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/sql_metrics.py tests/test_facts_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): bytes e arquivos por no de leitura, medidos pelo Spark`

---

## Task 5: AQE, reatribuição e as recusas restantes

**Files:**
- Modify: `sparkforge/facts/sql_metrics.py`
- Test: `tests/test_facts_sql_metrics.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_sql_metrics.py`:

```python
SQL_AQE = "org.apache.spark.sql.execution.ui.SparkListenerSQLAdaptiveExecutionUpdate"
SQL_END = "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionEnd"


def _aqe(execution_id, plan):
    return json.dumps(
        {
            "Event": SQL_AQE,
            "executionId": execution_id,
            "physicalPlanDescription": "== Physical Plan ==",
            "sparkPlanInfo": plan,
        }
    )


def _end(execution_id):
    return json.dumps({"Event": SQL_END, "executionId": execution_id, "time": 1600000000001})


class TestAQE:
    def test_replanned_execution_declares_the_final_source(self):
        inicial = _scan_node(metrics=[_metric("number of files read", 11)])
        final = _scan_node(
            simple="FileScan parquet db.clientes[id#1]",
            metrics=[_metric("number of files read", 21)],
        )
        facts = extract_sql_metrics(
            [_start(plan=inicial), _aqe(0, final), _driver_update(0, [[21, 4]]), _end(0)],
            "log.jsonl",
        )
        execucao = [f for f in facts if f.kind == "spark.sql.execution"][0]
        scan = [f for f in facts if f.kind == "spark.sql.scan"][0]

        assert execucao.attrs["plan_source"] == "final_aqe"
        assert scan.measures["files_read"] == 4

    def test_same_accumulator_in_two_nodes_refuses_to_attribute(self):
        plano = {
            "nodeName": "Union",
            "simpleString": "Union",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(metrics=[_metric("number of files read", 11)]),
                _scan_node(
                    simple="FileScan parquet db.pedidos[id#2]",
                    metrics=[_metric("number of files read", 11)],
                ),
            ],
        }
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 9]]), _end(0)], "log.jsonl"
        )
        scans = [f for f in facts if f.kind == "spark.sql.scan"]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "accumulator_reassigned"
        ]

        assert all("files_read" not in s.measures for s in scans)
        assert len(lacunas) == 1


class TestRefusals:
    def test_log_without_sql_events_says_so_instead_of_looking_broken(self):
        facts = extract_sql_metrics(
            [json.dumps({"Event": "SparkListenerApplicationStart", "App Name": "x"})],
            "log.jsonl",
        )
        sentinela = [f for f in facts if f.kind == "spark.sql.analyzed"][0]
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved" and f.attrs["reason"] == "no_sql_events"
        ]

        assert sentinela.measures["executions"] == 0
        assert len(lacunas) == 1
        assert not [f for f in facts if f.kind == "spark.sql.scan"]

    def test_malformed_line_is_counted_and_the_pass_continues(self):
        facts = extract_sql_metrics(
            ["{nao e json", _start(plan=_scan_node()), _end(0)], "log.jsonl"
        )
        sentinela = [f for f in facts if f.kind == "spark.sql.analyzed"][0]

        assert sentinela.measures["malformed_lines"] == 1
        assert len([f for f in facts if f.kind == "spark.sql.scan"]) == 1

    def test_execution_without_an_end_event_is_declared_incomplete(self):
        facts = extract_sql_metrics([_start(plan=_scan_node())], "log.jsonl")
        lacunas = [
            f
            for f in facts
            if f.kind == "spark.sql.unresolved"
            and f.attrs["reason"] == "incomplete_execution"
        ]

        assert len(lacunas) == 1

    def test_missing_file_becomes_a_fact_never_an_exception(self, tmp_path):
        from sparkforge.facts.sql_metrics import extract_sql_metrics_path

        facts = extract_sql_metrics_path(tmp_path / "nao-existe.jsonl")
        assert [f.attrs["reason"] for f in facts] == ["read_error"]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_sql_metrics.py::TestAQE tests/test_facts_sql_metrics.py::TestRefusals -v
```

Esperado: FAIL — nenhuma das recusas existe ainda.

- [ ] **Step 3: Implementar**

**Duas sutilezas do AQE que o código de Task 3 já decide, e que você precisa preservar:**

`absorb_plan` reescreve `self.nodes` mas **não** limpa `self.accum`. É deliberado, e é o que a spec §3.5 manda: valor já acumulado continua atribuído ao nó que declarou aquele acumulador, porque foi medido sob aquele plano. Limpar o mapa perderia os bytes lidos antes da reposta do AQE.

Por consequência, a checagem de `accumulator_reassigned` compara contra o mapa acumulado das duas árvores. Isso é correto quando o AQE reusa um id em outro nó — é exatamente a colisão que a recusa existe para pegar — e inofensivo no caso normal, em que o AQE emite ids novos. Se um cenário real mostrar o contrário, o teste `test_replanned_execution_declares_the_final_source` é onde a evidência entra.

No laço de eventos, conte as linhas malformadas: troque o `except (ValueError, TypeError): continue` por

```python
        except (ValueError, TypeError):
            malformadas += 1
            continue
```

e declare `malformadas = 0` antes do laço.

Trate o fim de execução, junto dos outros eventos:

```python
        elif nome == _SQL_END:
            execucao = execucoes.get(evento.get("executionId"))
            if execucao is not None:
                execucao.ended = True
```

Emita as três recusas restantes. Depois do laço de execuções, e antes do fact `spark.sql.analyzed`:

```python
    for execucao in sorted(execucoes.values(), key=lambda e: e.execution_id):
        for accum_id in sorted(execucao.reassigned):
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "accumulator_reassigned",
                        "accumulator_id": accum_id,
                        "detail": (
                            "O mesmo accumulatorId aparece em dois nos do plano. Nenhum "
                            "dos dois recebe o valor: escolher um poria bytes no no "
                            "errado, e o relatorio ficaria plausivel e falso."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )
        if not execucao.ended:
            facts.append(
                Fact(
                    kind="spark.sql.unresolved",
                    subject=_plan_node_subject(execucao.execution_id, 0, "execution", ""),
                    attrs={
                        "reason": "incomplete_execution",
                        "detail": (
                            "Nenhum SparkListenerSQLExecutionEnd para esta execucao. O log "
                            "foi cortado antes do fim, e as measures sao parciais."
                        ),
                    },
                    provenance={"extractor": EXTRACTOR_ID, "artifact": path},
                )
            )

    if not execucoes:
        facts.append(
            Fact(
                kind="spark.sql.unresolved",
                subject=_file_subject(path),
                attrs={
                    "reason": "no_sql_events",
                    "detail": (
                        "Nenhum evento do namespace org.apache.spark.sql.execution.ui neste "
                        "log. Job que usa so RDD nao publica metrica de plano SQL -- e outra "
                        "coisa, nao um defeito."
                    ),
                },
                provenance={"extractor": EXTRACTOR_ID, "artifact": path},
            )
        )
```

Troque `"malformed_lines": 0` por `"malformed_lines": malformadas`.

Acrescente ao final do módulo o leitor de arquivo, no molde de `event_log.extract_event_log_path`:

```python
def extract_sql_metrics_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Le o event log do disco em streaming e delega para `extract_sql_metrics`.

    Falha ao abrir vira um unico `spark.sql.unresolved` com razao `read_error`,
    nunca uma excecao que derruba quem chamou -- mesma convencao de
    `event_log.extract_event_log_path`.
    """
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")
    try:
        with path.open(encoding="utf-8-sig") as handle:
            return extract_sql_metrics(handle, anchor)
    except OSError as exc:
        return [
            Fact(
                kind="spark.sql.unresolved",
                subject=_file_subject(anchor),
                attrs={"reason": "read_error", "detail": str(exc)},
                provenance={"extractor": EXTRACTOR_ID, "artifact": anchor},
            )
        ]
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS, 17 testes.

- [ ] **Step 5: Provar que todo fact valida contra o schema**

Acrescente a `tests/test_facts_sql_metrics.py`:

```python
class TestSchema:
    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact

        plano = {
            "nodeName": "Union",
            "simpleString": "Union",
            "metadata": {},
            "metrics": [],
            "children": [
                _scan_node(metrics=[_metric("number of files read", 11)]),
                _scan_node(
                    simple="BatchScan db.eventos[id#2]",
                    metrics=[_metric("metrica que nao existe", 12)],
                ),
            ],
        }
        facts = extract_sql_metrics(
            [_start(plan=plano), _driver_update(0, [[11, 2], [12, 3]])], "log.jsonl"
        )

        assert facts
        for fact in facts:
            validate_fact(fact.to_dict())

    def test_every_emitted_kind_is_declared(self):
        from sparkforge.facts.sql_metrics import EMITTED_KINDS

        facts = extract_sql_metrics([_start(plan=_scan_node())], "log.jsonl")
        assert {f.kind for f in facts} <= EMITTED_KINDS
```

```bash
rtk pytest tests/test_facts_sql_metrics.py -v
```

Esperado: PASS, 19 testes. Este é o gate que a entrega anterior não tinha e por isso emitiu oito kinds inválidos.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/facts/sql_metrics.py tests/test_facts_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): AQE, reatribuicao de acumulador e as recusas nomeadas`

---

## Task 6: Camada `_core` e CLI

**Files:**
- Modify: `sparkforge/adapters/_core.py`
- Modify: `sparkforge/adapters/cli.py`
- Test: `tests/test_adapters_cli.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_adapters_cli.py`:

```python
class TestSqlMetricsCommand:
    def _log(self, tmp_path):
        alvo = tmp_path / "eventlog.jsonl"
        alvo.write_text(
            json.dumps(
                {
                    "Event": "org.apache.spark.sql.execution.ui.SparkListenerSQLExecutionStart",
                    "executionId": 0,
                    "description": "save",
                    "physicalPlanDescription": "== Physical Plan ==",
                    "sparkPlanInfo": {
                        "nodeName": "Scan parquet ",
                        "simpleString": "FileScan parquet db.clientes[id#1]",
                        "children": [],
                        "metadata": {"Format": "Parquet"},
                        "metrics": [
                            {
                                "name": "number of files read",
                                "accumulatorId": 11,
                                "metricType": "sum",
                            }
                        ],
                    },
                    "time": 1,
                }
            )
            + "\n"
            + json.dumps(
                {
                    "Event": "org.apache.spark.sql.execution.ui.SparkListenerDriverAccumUpdates",
                    "executionId": 0,
                    "accumUpdates": [[11, 6]],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return alvo

    def test_analyze_sql_metrics_prints_scan_facts(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        assert main(["analyze", "sql-metrics", "--path", str(self._log(tmp_path))]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["by_kind"]["spark.sql.scan"] == 1

    def test_out_file_carries_the_measured_bytes(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        out = tmp_path / "facts.json"
        code = main(
            ["analyze", "sql-metrics", "--path", str(self._log(tmp_path)), "--out", str(out)]
        )

        assert code == 0
        facts = json.loads(out.read_text(encoding="utf-8"))
        scan = [f for f in facts if f["kind"] == "spark.sql.scan"][0]
        assert scan["measures"]["files_read"] == 6
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_cli.py::TestSqlMetricsCommand -v
```

Esperado: FAIL com `SystemExit: 2` — argparse não conhece `sql-metrics`.

- [ ] **Step 3: Implementar em `_core.py`**

Import no topo, junto dos outros extratores:

```python
from sparkforge.facts.sql_metrics import extract_sql_metrics_path
```

E, junto dos outros `analyze_*`:

```python
def analyze_sql_metrics(
    path: str,
    kind: list[str] | None = None,
    limit: int | None = DEFAULT_LIMIT,
    cursor: str | None = None,
    detail_level: str = "full",
) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        raise AdapterError(
            f"Caminho nao encontrado para analise: {path}\n"
            f"  Aponte para um Spark event log (JSON Lines):\n"
            f"    sparkforge analyze sql-metrics --path .sparkforge/artifacts/eventlog/app.jsonl",
            exit_code=2,
        )
    facts = extract_sql_metrics_path(target)
    return _facts_page(facts, "spark.sql.unresolved", kind, limit, cursor, detail_level)
```

- [ ] **Step 4: Implementar em `cli.py`**

Parser, junto dos outros de `analyze`:

```python
    sqlm_p = analyze_sub.add_parser(
        "sql-metrics",
        help="Extrai metrica por no do plano de um Spark event log ja coletado.",
    )
    sqlm_p.add_argument("--path", required=True, help="Event log em JSON Lines.")
    sqlm_p.add_argument("--out", help="Escreve a lista completa de facts (JSON).")
    sqlm_p.add_argument("--kind", action="append", help="Filtra por kind. Repetivel.")
    sqlm_p.add_argument("--limit", type=int, default=_core.DEFAULT_LIMIT)
    sqlm_p.add_argument("--cursor")
    _add_detail_level(sqlm_p)
```

Handler, junto dos vizinhos:

```python
def _cmd_analyze_sql_metrics(args: argparse.Namespace) -> int:
    full = _core.analyze_sql_metrics(args.path, kind=args.kind, limit=None)
    if args.out:
        Path(args.out).write_text(
            json.dumps(full["items"], indent=2, ensure_ascii=False), encoding="utf-8"
        )
    page, next_cursor = _core.paginate_items(full["items"], args.limit, args.cursor)
    payload = {
        "total_count": full["total_count"],
        "returned_count": len(page),
        "next_cursor": next_cursor,
        "filters_applied": {"kind": args.kind, "limit": args.limit, "cursor": args.cursor},
        "by_kind": full["by_kind"],
        "unresolved": full["unresolved"],
        "unresolved_at": full["unresolved_at"],
        "items": page,
    }
    _print(_apply_detail_level(payload, args.detail_level))
    return 0
```

E a entrada no dicionário de despacho:

```python
    ("analyze", "sql-metrics"): _cmd_analyze_sql_metrics,
```

- [ ] **Step 5: Rodar e ver passar**

```bash
rtk pytest tests/test_adapters_cli.py -v
```

Esperado: PASS. Reporte a contagem real.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/adapters/_core.py sparkforge/adapters/cli.py tests/test_adapters_cli.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(cli): analyze sql-metrics`

---

## Task 7: Tool MCP, manifesto, paridade e o gate de órfão

**Files:**
- Modify: `sparkforge/adapters/tools.py`
- Modify: `manifest.json`
- Modify: `parity.yaml`
- Modify: um arquivo de `agents/`
- Test: `tests/test_adapters_tools.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_adapters_tools.py`:

```python
class TestSqlMetricsTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_analyze_sql_metrics" in tools.TOOLS
        assert "sparkforge_analyze_sql_metrics" in tools._HANDLERS

    def test_the_tool_is_listed_in_the_manifest(self):
        import json
        from pathlib import Path

        manifest = json.loads(Path("manifest.json").read_text(encoding="utf-8"))
        assert "sparkforge_analyze_sql_metrics" in set(manifest["tools"])
```

Confirme os nomes reais dos dicionários (`TOOLS`, `_HANDLERS`) antes de rodar — a asserção é sobre o conteúdo.

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_tools.py::TestSqlMetricsTool -v
```

Esperado: FAIL com `AssertionError`.

- [ ] **Step 3: Declarar a tool**

Em `sparkforge/adapters/tools.py`, junto das outras tools de `analyze`. Use `_ANALYZE_FACTS_SCHEMA` — o schema padrão, porque o subject deste extrator declara `type: plan_node`, que já está no enum:

```python
    "sparkforge_analyze_sql_metrics": {
        "description": (
            "Extrai metrica por NO DO PLANO de um Spark event log ja coletado: quantos "
            "bytes e quantos arquivos cada fonte custou, medidos pelo proprio Spark. "
            "Responde o que `analyze event-log` nao responde -- aquele mede por stage, e "
            "stage agrega todas as leituras que caem nele. Metrica que a execucao nao "
            "publicou fica AUSENTE, nunca zero; nome de metrica fora do mapa canonico "
            "vira `spark.sql.unresolved` com o nome cru, nunca palpite."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {"type": "string"},
                "kind": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "cursor": {"type": "string"},
                "detail_level": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(_ANALYZE_FACTS_SCHEMA, "Pagina de facts, ou erro de fronteira."),
        "annotations": _READ_ONLY,
    },
```

Handler, junto dos vizinhos, e a entrada no dicionário de despacho:

```python
def _h_analyze_sql_metrics(args: dict[str, Any]) -> dict[str, Any]:
    return _core.analyze_sql_metrics(
        args["path"],
        kind=args.get("kind"),
        limit=args.get("limit"),
        cursor=args.get("cursor"),
        detail_level=args.get("detail_level", "full"),
    )
```

`tests/test_adapters_tools.py` tem asserções **exaustivas** sobre o conjunto de tools e sobre `_real_output_for`. Elas não estão no Step 1 e vão reprovar assim que a tool existir. Atualize-as: é o que o gate cobra, não escopo extra.

- [ ] **Step 4: Manifesto e paridade**

- `manifest.json`, lista `tools`: acrescente `sparkforge_analyze_sql_metrics` em ordem alfabética.
- `parity.yaml`, capability de análise (a que lista `analyze event-log`): acrescente `sparkforge_analyze_sql_metrics` à lista `tools` e `analyze sql-metrics` à lista `cli`. Acrescente `knowledge/spark/sql-metrics.yaml` à lista `knowledge` dessa capability.

- [ ] **Step 5: Citar a tool onde um agente a alcança**

`tests/test_agent_coverage.py::test_no_tool_is_orphan` reprova tool que nenhum coordenador, skill ou executor cita. Acrescente a menção onde ela pertence — o coordenador de performance de Spark é o lugar natural, junto de onde `sparkforge_analyze_event_log` já aparece. Escreva **por que** ela existe, não só o nome: métrica por stage não separa a fonte cara da barata.

Depois, sincronize os espelhos:

```bash
rtk python scripts/sync_skills.py
rtk pytest tests/test_arvore_versionada.py -v
```

O `sync_skills.py` grava em `.claude/`, `.agents/` e `.github/` — todos entram no mesmo commit que o arquivo de origem.

- [ ] **Step 6: Gates de superfície**

```bash
rtk pytest tests/test_adapters_tools.py tests/test_adapters_mcp.py tests/test_capability_parity.py tests/test_canonical_registry.py tests/test_agent_coverage.py -v
```

Esperado: PASS.

`tests/test_harness_authorization.py` tem uma contagem fixa de tools que declaram caminho. A tool nova declara `path`, então o número sobe em um. Rode e atualize o valor:

```bash
rtk pytest tests/test_harness_authorization.py -q
```

- [ ] **Step 7: Commit**

```bash
rtk git add sparkforge/adapters/tools.py manifest.json parity.yaml tests/test_adapters_tools.py tests/test_harness_authorization.py agents .claude .agents .github
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(mcp): tool de metrica SQL, com manifesto, paridade e agente fechados`

---

## Task 8: Fixtures golden

**Files:**
- Create: `fixtures/sql_metrics/` (seis cenários)
- Create: `tests/test_fixtures_golden_sql_metrics.py`

- [ ] **Step 1: Criar os cenários**

Um diretório por cenário, cada um com `input/eventlog.jsonl`, `meta.yaml` e `expected/`. Leia `fixtures/eventlog/skewed_stage/` para a forma exata de `meta.yaml` e de `expected/` antes de escrever.

Nada de nome, número ou particularidade de ambiente real. Use `db.clientes`, `db.pedidos`, `db.eventos`.

| Cenário | O que ele prova |
|---|---|
| `scan_parquet_measured` | `FileSourceScanExec` com `number of files read` e `size of files read` publicados |
| `scan_iceberg_batchscan` | `BatchScan`, com `number of output rows` (no mapa) e uma métrica custom fora do mapa |
| `aqe_replans_the_scan` | árvore inicial e final, `accumulatorId` distintos, `plan_source: final_aqe` |
| `unknown_metric` | nome fora do mapa vira `unresolved`, e o scan sai sem measure inventada |
| `no_sql_events` | log só com eventos de Task e Stage: `executions: 0`, nenhum falso defeito |
| `truncated_log` | `SQLExecutionStart` sem `SQLExecutionEnd`: `incomplete_execution` |

`meta.yaml` de cada um declara `runtime`, `expects_kinds` e `expects_rules: []` — nenhuma regra do catálogo consome estes kinds hoje, e a lista vazia diz isso explicitamente em vez de omitir.

- [ ] **Step 2: Escrever o módulo golden**

`tests/test_fixtures_golden_sql_metrics.py`, no molde de `tests/test_fixtures_golden_s3.py`:

```python
"""Golden do corpus de metricas SQL por no do plano.

Dominio proprio, e nao mais cenarios dentro de `fixtures/eventlog/`, pelo mesmo
motivo que `data_quality` e `graph` tem dominio proprio embora leiam o mesmo
`.py` que `pyspark_ast`: o artefato e um, a pergunta e outra.

`test_every_fixture_domain_has_a_golden_module` cobra este arquivo. Sem ele o
corpus existe, parece cobertura, e `scripts/verify_wheel.py` nunca o executa
contra o pacote instalado.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.sql_metrics import extract_sql_metrics_path
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "sql_metrics"

REQUIRED_FIXTURES = {
    "scan_parquet_measured",
    "scan_iceberg_batchscan",
    "aqe_replans_the_scan",
    "unknown_metric",
    "no_sql_events",
    "truncated_log",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    entrada = directory / "input"
    facts = []
    for log in sorted(entrada.glob("*.jsonl")):
        facts.extend(extract_sql_metrics_path(log, repo_root=entrada))
    return facts


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        assert [f.to_dict() for f in _extract(directory)] == [
            f.to_dict() for f in _extract(directory)
        ]


class TestOQueOCorpusInteiroGarante:
    def test_no_scan_carries_a_measure_the_execution_never_published(self):
        """A garantia que separa medido de inferido, sobre o corpus INTEIRO.

        Todo `spark.sql.scan` so pode carregar measure cujo nome de metrica
        aparece no `sparkPlanInfo` daquela execucao E teve valor publicado. Um
        default que preenchesse zero passaria em cada cenario isolado e
        quebraria aqui -- e e disto que depende a confiabilidade do fingerprint
        que vem depois.
        """
        from sparkforge.facts.sql_metric_names import measure_for

        for directory in fixture_dirs():
            publicadas: dict[int, set[str]] = {}
            for log in sorted((directory / "input").glob("*.jsonl")):
                for linha in log.read_text(encoding="utf-8").splitlines():
                    if not linha.strip():
                        continue
                    try:
                        evento = json.loads(linha)
                    except ValueError:
                        continue
                    plano = evento.get("sparkPlanInfo")
                    if not isinstance(plano, dict):
                        continue
                    pilha = [plano]
                    while pilha:
                        no = pilha.pop()
                        pilha.extend(no.get("children") or [])
                        for metrica in no.get("metrics") or []:
                            medida = measure_for(str(metrica.get("name") or ""))
                            if medida:
                                publicadas.setdefault(
                                    evento.get("executionId"), set()
                                ).add(medida)

            for fact in _extract(directory):
                if fact.kind != "spark.sql.scan":
                    continue
                disponiveis = publicadas.get(fact.subject["execution_id"], set())
                assert set(fact.measures) <= disponiveis, (directory.name, fact.measures)
```

- [ ] **Step 3: Gerar os goldens e rodar**

Rode o extrator sobre cada cenário e grave `expected/facts.json` e `expected/findings.json` com a saída real — depois **leia** cada arquivo e confira que ele descreve o que o nome do cenário promete. Golden gravado sem leitura é golden que trava o defeito junto com o comportamento.

```bash
rtk pytest tests/test_fixtures_golden_sql_metrics.py -v
rtk pytest tests/test_fixtures_kind_coverage.py -q
```

Esperado: PASS nos dois, inclusive `test_every_fixture_domain_has_a_golden_module`.

- [ ] **Step 4: Commit**

```bash
rtk git add fixtures/sql_metrics tests/test_fixtures_golden_sql_metrics.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `test(fixtures): seis cenarios sinteticos de metrica SQL por no`

---

## Task 9: Documentação, suíte completa e os gates que mordem

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/STATUS.md`
- Possivelmente: `docs/harness/*.md`, `docs/claims.lock.json`

- [ ] **Step 1: Rodar a suíte inteira**

```bash
rtk pytest -q
```

Leva cerca de 17 minutos. Qualquer falha aqui é regressão desta entrega — corrija antes de documentar.

- [ ] **Step 2: Documentar o verbo no README**

Na tabela "O que pode ser extraído", acrescente a linha no formato exato das vizinhas (três colunas: Artefato | Verbo | Lê):

```markdown
| Métricas SQL do plano | `analyze sql-metrics` | o mesmo event log, pela ótica de quanto cada fonte custou |
```

Atualize também os números de extratores e de kinds da frase que abre a seção. **Meça**, não copie:

```bash
rtk python -c "
import importlib, pkgutil
import sparkforge.facts as F
mods, kinds = [], set()
for m in pkgutil.iter_modules(F.__path__):
    mod = importlib.import_module(f'sparkforge.facts.{m.name}')
    ek = getattr(mod, 'EMITTED_KINDS', None)
    if ek:
        mods.append(m.name); kinds |= set(ek)
print(len(mods), 'extratores,', len(kinds), 'kinds')
"
```

- [ ] **Step 3: Registrar a fase no STATUS**

Acrescente a `docs/superpowers/STATUS.md`, no formato das fases existentes, uma entrada que declare:

- o verbo novo e a tool nova;
- os quatro kinds novos e o extrator novo;
- o número de testes que a entrega acrescentou, medido com
  `rtk pytest tests/test_facts_sql_metrics.py tests/test_sql_metric_names.py tests/test_fixtures_golden_sql_metrics.py -q`;
- a referência à spec `docs/superpowers/specs/2026-08-28-spark-sql-scan-metrics-design.md`;
- o que ficou de fora: métrica de shuffle e de join por nó (o mesmo mecanismo as alcança, e não há consumidor ainda), o objeto `WorkloadFingerprint` (é o recorte seguinte de C), a correlação com `plan.file_scan` (adiada de propósito, §3.2 da spec), e nenhuma regra nova no catálogo.

Atualize também a tabela "Números correntes" com os valores medidos no Step 2.

- [ ] **Step 4: Rodar o gate de números**

```bash
rtk python scripts/check_vnext_claims.py
```

Leva cerca de dois minutos. Este gate mede alegações numéricas em `docs/vnext/` e `docs/harness/` reexecutando a prova de cada uma. Uma tool nova e um extrator novo deslocam contagens ali (número de tools, número de módulos golden, tamanho de arquivos). Para cada divergência, o gate imprime `esperado X, obtido Y`: corrija o texto do documento para **Y**, que é a medição atual, e ajuste `docs/claims.lock.json` na mesma entrada. Itere até `0 divergencia(s).` e exit 0.

- [ ] **Step 5: Commit**

```bash
rtk git add README.md docs/superpowers/STATUS.md docs/claims.lock.json docs/harness
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `docs: analyze sql-metrics, a fase e o que ficou de fora`

- [ ] **Step 6: Suíte inteira, de novo**

```bash
rtk pytest -q
```

Esperado: 0 failed. Esta é a última prova da entrega.

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §2 extrator novo, módulo separado | 3 |
| §2 mapa canônico em `knowledge/` | 1, 2 |
| §3.2 fonte é o event log, não o plano colado | 3 |
| §3.3 measure ausente é ausência, nunca zero | 4 |
| §3.4 nome desconhecido vira lacuna | 4 |
| §3.5 AQE e reatribuição de acumulador | 5 |
| §3.6 redação e `Location` fora do fact | 3 |
| §3.7 streaming, uma passada, não-atribuídos contados | 3, 4 |
| §4.1 `spark.sql.scan` | 3, 4 |
| §4.2 `spark.sql.execution` | 3 |
| §4.3 `spark.sql.unresolved` | 4, 5 |
| §4.4 `spark.sql.analyzed` | 3, 4, 5 |
| §5.1 CLI | 6 |
| §5.2 MCP com o schema padrão | 7 |
| §6 erros, cada um com o seu nome | 5 |
| §7.1 domínio de fixture e módulo golden | 8 |
| §7.2 o teste que vale mais que os seis | 8 |
| §8 documentação | 9 |
| §9 critérios de aceite 1–6 | 3, 4, 5, 8 |
| §9 critério de aceite 7 (os quatro gates) | 1, 7, 9 |
