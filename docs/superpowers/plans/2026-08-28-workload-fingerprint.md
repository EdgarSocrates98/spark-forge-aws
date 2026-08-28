# WorkloadFingerprint — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o perfil por número de registros por um perfil de eixos independentes — scan, shuffle, memória, skew, arquivos, join — onde cada eixo carrega o valor, de onde ele veio, e o quanto se pode confiar nele.

**Architecture:** Três camadas. A medição que falta entra em `facts/event_log.py` (`spark.stage.shuffle`). A declaração entra por `facts/workload.py`, lendo um `workload.yaml` versionado. E o julgamento — classificar `scan` como `extreme` — mora em `sparkforge/workload/`, mecanismo próprio, porque fact não aplica limiar. A escala de cada eixo de volume vem do histórico do próprio job, que o subprojeto B já coleta.

**Tech Stack:** Python 3, `pytest`, `PyYAML`. Spec: [`../specs/2026-08-28-workload-fingerprint-design.md`](../specs/2026-08-28-workload-fingerprint-design.md).

**Convenções do repositório que valem em toda tarefa:**

- Fact nunca aplica limiar, nunca atribui severidade, nunca toca a rede. O `Fingerprint` **não é fact** — é onde o limiar mora.
- Todo fact declara `subject.type` de um enum fechado (`sparkforge/findings/schemas/fact.schema.json`). Módulo golden novo **tem** que chamar `validate_fact`: foi a ausência disso que deixou oito kinds inválidos passarem na entrega de B.
- Lint ruff `E,F,I,UP,B,S`, linha máxima 100.
- Todo comando roda com prefixo `rtk`. Commit em português, Conventional Commits, via `rtk git commit -F <arquivo>` — heredoc dentro de `$(...)` dispara prompt de permissão.
- Não rode a suíte inteira sem alvo (17 minutos), exceto onde a tarefa pedir.
- Não faça `git add` dos untracked pré-existentes na raiz. Cuidado com `git add .claude` — ele varre um `.bak`.

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/workload.py` | Extrator do inventário declarado `workload.yaml` |
| `sparkforge/workload/__init__.py` | Export de `Axis`, `WorkloadFingerprint`, `build_fingerprint` |
| `sparkforge/workload/axis.py` | O `Axis`: valor, confiança, base, evidência, lacuna |
| `sparkforge/workload/fingerprint.py` | A montagem dos eixos a partir dos facts |
| `tests/test_facts_workload.py` | Testes do inventário |
| `tests/test_workload_axis.py` | Testes do contrato do eixo |
| `tests/test_workload_fingerprint.py` | Testes da montagem |
| `tests/test_fixtures_golden_workload.py` | Módulo golden do domínio novo |
| `fixtures/workload/` | Seis cenários sintéticos |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/facts/event_log.py` | `spark.stage.shuffle` em `EMITTED_KINDS`, acumulador e fact |
| `sparkforge/adapters/_core.py` | `workload_fingerprint` |
| `sparkforge/adapters/cli.py` | Verbo de topo `workload` |
| `sparkforge/adapters/tools.py` | `sparkforge_workload` |
| `manifest.json`, `parity.yaml` | A tool nova |
| `agents/` | Citar a tool, senão o gate de órfão reprova |
| `tests/test_fixtures_kind_coverage.py`, `tests/test_rules_catalog_reachability.py` | Registrar `workload` nas DUAS listas |
| `README.md`, `docs/superpowers/STATUS.md` | O verbo, a fase, e os números medidos |

---

## Task 1: Métrica de shuffle por stage

**Files:**
- Modify: `sparkforge/facts/event_log.py`
- Test: `tests/test_facts_event_log.py`

- [ ] **Step 1: Escrever o teste que falha**

Leia `tests/test_facts_event_log.py` e siga a forma dos helpers que ele já tem para montar um `TaskEnd`. Acrescente:

```python
class TestShuffleMetrics:
    def _task_end(self, stage_id, read_bytes=None, write_bytes=None):
        metrics = {
            "Executor Run Time": 1000,
            "JVM GC Time": 10,
            "Memory Bytes Spilled": 0,
            "Disk Bytes Spilled": 0,
            "Input Metrics": {"Bytes Read": 100},
        }
        if read_bytes is not None:
            metrics["Shuffle Read Metrics"] = {
                "Remote Bytes Read": read_bytes,
                "Local Bytes Read": 0,
                "Total Records Read": 7,
                "Fetch Wait Time": 3,
            }
        if write_bytes is not None:
            metrics["Shuffle Write Metrics"] = {
                "Shuffle Bytes Written": write_bytes,
                "Shuffle Records Written": 5,
                "Shuffle Write Time": 2_000_000,
            }
        return json.dumps(
            {
                "Event": "SparkListenerTaskEnd",
                "Stage ID": stage_id,
                "Task Info": {"Launch Time": 0, "Finish Time": 500, "Failed": False},
                "Task Metrics": metrics,
            }
        )

    def _stage_completed(self, stage_id):
        return json.dumps(
            {
                "Event": "SparkListenerStageCompleted",
                "Stage Info": {"Stage ID": stage_id, "Stage Name": "stage-x", "Number of Tasks": 1},
            }
        )

    def test_stage_that_moved_data_gets_a_shuffle_fact(self):
        facts = extract_event_log(
            [self._task_end(1, read_bytes=4096, write_bytes=8192), self._stage_completed(1)],
            "log.jsonl",
        )
        shuffle = [f for f in facts if f.kind == "spark.stage.shuffle"]

        assert len(shuffle) == 1
        assert shuffle[0].subject["type"] == "stage"
        assert shuffle[0].measures["read_bytes"] == 4096
        assert shuffle[0].measures["write_bytes"] == 8192
        assert shuffle[0].measures["read_records"] == 7
        assert shuffle[0].measures["write_records"] == 5

    def test_stage_without_shuffle_produces_no_fact(self):
        facts = extract_event_log([self._task_end(1), self._stage_completed(1)], "log.jsonl")

        assert not [f for f in facts if f.kind == "spark.stage.shuffle"]

    def test_bytes_are_summed_across_tasks(self):
        facts = extract_event_log(
            [
                self._task_end(1, write_bytes=1000),
                self._task_end(1, write_bytes=500),
                self._stage_completed(1),
            ],
            "log.jsonl",
        )
        shuffle = [f for f in facts if f.kind == "spark.stage.shuffle"][0]

        assert shuffle.measures["write_bytes"] == 1500

    def test_read_only_stage_omits_the_write_measures(self):
        facts = extract_event_log(
            [self._task_end(1, read_bytes=2048), self._stage_completed(1)], "log.jsonl"
        )
        shuffle = [f for f in facts if f.kind == "spark.stage.shuffle"][0]

        assert shuffle.measures["read_bytes"] == 2048
        assert "write_bytes" not in shuffle.measures
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_event_log.py::TestShuffleMetrics -v
```

Esperado: FAIL — nenhum fact `spark.stage.shuffle` é emitido.

- [ ] **Step 3: Implementar**

Em `EMITTED_KINDS`, acrescente `"spark.stage.shuffle",`.

Em `_StageAccumulator.__slots__`, acrescente os seis campos novos; em `__init__`, inicialize-os:

```python
        self.shuffle_read_bytes = 0
        self.shuffle_read_records = 0
        self.shuffle_remote_bytes = 0
        self.shuffle_local_bytes = 0
        self.shuffle_fetch_wait_ms = 0
        self.shuffle_write_bytes = 0
        self.shuffle_write_records = 0
        self.shuffle_write_time_ns = 0
        self.shuffle_read_seen = False
        self.shuffle_write_seen = False
```

Em `_StageAccumulator.add`, ao final:

```python
        # `Shuffle Read Metrics` e `Shuffle Write Metrics` estao dentro do
        # MESMO `Task Metrics` que este acumulador ja le para input e spill.
        # A presenca de cada bloco e o que distingue "stage sem shuffle" de
        # "shuffle de zero byte": o primeiro nao produz fact nenhum, o segundo
        # produz um fact com zero medido.
        leitura = metrics.get("Shuffle Read Metrics")
        if isinstance(leitura, dict):
            self.shuffle_read_seen = True
            self.shuffle_remote_bytes += int(leitura.get("Remote Bytes Read") or 0)
            self.shuffle_local_bytes += int(leitura.get("Local Bytes Read") or 0)
            self.shuffle_read_records += int(leitura.get("Total Records Read") or 0)
            self.shuffle_fetch_wait_ms += int(leitura.get("Fetch Wait Time") or 0)

        escrita = metrics.get("Shuffle Write Metrics")
        if isinstance(escrita, dict):
            self.shuffle_write_seen = True
            self.shuffle_write_bytes += int(escrita.get("Shuffle Bytes Written") or 0)
            self.shuffle_write_records += int(escrita.get("Shuffle Records Written") or 0)
            self.shuffle_write_time_ns += int(escrita.get("Shuffle Write Time") or 0)
```

`shuffle_read_bytes` é derivado: `remote + local`. Calcule na emissão, não no acumulador.

Em `_stage_facts`, depois do bloco de `spark.stage.spill`:

```python
    if acc.shuffle_read_seen or acc.shuffle_write_seen:
        medidas: dict[str, Any] = {}
        if acc.shuffle_read_seen:
            medidas.update(
                {
                    "read_bytes": acc.shuffle_remote_bytes + acc.shuffle_local_bytes,
                    "remote_read_bytes": acc.shuffle_remote_bytes,
                    "local_read_bytes": acc.shuffle_local_bytes,
                    "read_records": acc.shuffle_read_records,
                    "fetch_wait_ms": acc.shuffle_fetch_wait_ms,
                }
            )
        if acc.shuffle_write_seen:
            medidas.update(
                {
                    "write_bytes": acc.shuffle_write_bytes,
                    "write_records": acc.shuffle_write_records,
                    # `Shuffle Write Time` vem em NANOSSEGUNDOS no event log,
                    # ao contrario de `Fetch Wait Time`, que vem em ms. Converter
                    # aqui e o que impede um consumidor de comparar os dois como
                    # se fossem a mesma unidade.
                    "write_time_ms": acc.shuffle_write_time_ns // 1_000_000,
                }
            )
        facts.append(
            Fact(
                kind="spark.stage.shuffle",
                subject=subject,
                measures=medidas,
                provenance=provenance,
            )
        )
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_event_log.py -v
```

Esperado: PASS, incluindo os quatro casos novos. Reporte a contagem real.

- [ ] **Step 5: Confirmar que os goldens de event log não mudaram sem querer**

O corpus de `fixtures/eventlog/` tem `expected/facts.json` byte-exato. Se algum cenário tiver métrica de shuffle nos `TaskEnd`, o golden muda — e a mudança é legítima, mas tem que ser **vista**:

```bash
rtk pytest tests/test_fixtures_golden_eventlog.py -v
```

Se falhar, leia o diff, confirme que o fact novo é o único acréscimo, regrave o golden e diga no relatório quais cenários mudaram e por quê.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/facts/event_log.py tests/test_facts_event_log.py fixtures/eventlog
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): volume de shuffle por stage, que o event log ja publicava`

---

## Task 2: O inventário declarado

**Files:**
- Create: `sparkforge/facts/workload.py`
- Test: `tests/test_facts_workload.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_facts_workload.py`:

```python
"""Testes do extrator do inventario declarado de workload."""
from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.facts.workload import extract_workload_path


def _inventario(tmp_path: Path, payload) -> Path:
    alvo = tmp_path / "workload.yaml"
    alvo.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return alvo


class TestDeclared:
    def test_declares_sla_and_primary_source(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {"jobs": [{"name": "etl-clientes", "sla_minutes": 45, "primary_source": "db.clientes"}]},
        )

        facts = extract_workload_path(alvo)
        declarado = [f for f in facts if f.kind == "workload.declared"][0]

        assert declarado.subject["symbol"] == "etl-clientes"
        assert declarado.measures["sla_minutes"] == 45
        assert declarado.attrs["primary_source"] == "db.clientes"

    def test_partial_entry_declares_only_what_it_has(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": [{"name": "etl-parcial", "sla_minutes": 30}]})

        declarado = [
            f for f in extract_workload_path(alvo) if f.kind == "workload.declared"
        ][0]

        assert declarado.measures["sla_minutes"] == 30
        assert "primary_source" not in declarado.attrs

    def test_sentinel_counts_the_jobs(self, tmp_path):
        alvo = _inventario(
            tmp_path, {"jobs": [{"name": "a", "sla_minutes": 1}, {"name": "b", "sla_minutes": 2}]}
        )

        sentinela = [
            f for f in extract_workload_path(alvo) if f.kind == "workload.declared_analyzed"
        ][0]

        assert sentinela.measures["jobs_declared"] == 2


class TestMalformed:
    def test_entry_without_name_is_unresolved_not_silence(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": [{"sla_minutes": 10}]})

        lacunas = [f for f in extract_workload_path(alvo) if f.kind == "workload.unresolved"]

        assert len(lacunas) == 1
        assert lacunas[0].attrs["reason"] == "entry_without_name"

    def test_entry_that_is_not_an_object_is_unresolved(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": ["isto-nao-e-um-objeto"]})

        lacunas = [f for f in extract_workload_path(alvo) if f.kind == "workload.unresolved"]

        assert [f.attrs["reason"] for f in lacunas] == ["entry_not_an_object"]

    def test_same_job_declared_twice_is_unresolved(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {"jobs": [{"name": "dup", "sla_minutes": 1}, {"name": "dup", "sla_minutes": 2}]},
        )
        facts = extract_workload_path(alvo)

        declarados = [f for f in facts if f.kind == "workload.declared"]
        lacunas = [
            f
            for f in facts
            if f.kind == "workload.unresolved" and f.attrs["reason"] == "job_declared_twice"
        ]

        # A primeira declaracao vale; a segunda vira lacuna. Aceitar as duas
        # faria o fingerprint depender da ordem do arquivo.
        assert len(declarados) == 1
        assert len(lacunas) == 1

    def test_valid_entries_survive_a_malformed_neighbour(self, tmp_path):
        alvo = _inventario(
            tmp_path, {"jobs": [{"sla_minutes": 10}, {"name": "bom", "sla_minutes": 20}]}
        )

        declarados = [f for f in extract_workload_path(alvo) if f.kind == "workload.declared"]

        assert [f.subject["symbol"] for f in declarados] == ["bom"]


class TestAbsent:
    def test_missing_file_is_not_an_error(self, tmp_path):
        facts = extract_workload_path(tmp_path / "nao-existe.yaml")
        sentinela = [f for f in facts if f.kind == "workload.declared_analyzed"][0]

        assert sentinela.measures["jobs_declared"] == 0
        assert not [f for f in facts if f.kind == "workload.declared"]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_workload.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.workload'`.

- [ ] **Step 3: Implementar**

Leia `sparkforge/facts/consumers.py` primeiro — ele é o irmão direto: também lê inventário YAML versionado, também trata entrada malformada como `unresolved` em vez de exceção. Siga a forma dele.

`sparkforge/facts/workload.py`:

```python
"""Extrator do inventario declarado de workload.

O que este modulo carrega NAO e medicao, e e por isso que ele existe separado:
`sla_minutes` e uma decisao de negocio, e `primary_source` exige alguem dizer
qual das fontes dirige o batch -- o extrator ve cinco scans e nao sabe qual e o
principal. Nenhum artefato responde nenhum dos dois.

Molde de `facts/consumers.py`, o outro inventario declarado do projeto: YAML
versionado, entrada malformada vira `unresolved` com razao nomeada, e a
extracao segue com o que sobrar.

Arquivo ausente NAO e erro -- e o caso comum. A sentinela declara zero, e quem
monta o fingerprint marca os eixos declarados como `unknown`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "workload@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "workload.declared",
        "workload.unresolved",
        "workload.declared_analyzed",
    }
)


def _job_subject(name: str) -> dict[str, Any]:
    return {"type": "job_run", "symbol": name}


def _file_subject(path: str) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": path,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _unresolved(path: str, reason: str, detail: str, **extra: Any) -> Fact:
    return Fact(
        kind="workload.unresolved",
        subject=_file_subject(path),
        attrs={"reason": reason, "detail": detail, **extra},
        provenance={"extractor": EXTRACTOR_ID, "artifact": path},
    )


def extract_workload(payload: Any, path: str) -> list[Fact]:
    """Extrai Facts de um inventario ja carregado."""
    facts: list[Fact] = []
    vistos: set[str] = set()
    provenance = {"extractor": EXTRACTOR_ID, "artifact": path}

    entradas = (payload or {}).get("jobs") if isinstance(payload, dict) else None
    if entradas is None:
        entradas = []
    elif not isinstance(entradas, list):
        facts.append(
            _unresolved(
                path,
                "jobs_not_a_list",
                "A chave `jobs` precisa ser uma lista de objetos.",
            )
        )
        entradas = []

    for entrada in entradas:
        if not isinstance(entrada, dict):
            facts.append(
                _unresolved(
                    path,
                    "entry_not_an_object",
                    f"Entrada que nao e objeto: {entrada!r}.",
                )
            )
            continue
        nome = entrada.get("name")
        if not isinstance(nome, str) or not nome:
            facts.append(
                _unresolved(
                    path,
                    "entry_without_name",
                    "Entrada sem `name`: sem ele nao ha como casar a declaracao com um job.",
                )
            )
            continue
        if nome in vistos:
            facts.append(
                _unresolved(
                    path,
                    "job_declared_twice",
                    f"O job {nome!r} aparece duas vezes. A primeira declaracao vale; "
                    f"aceitar as duas faria o perfil depender da ordem do arquivo.",
                    job_name=nome,
                )
            )
            continue
        vistos.add(nome)

        measures: dict[str, Any] = {}
        sla = entrada.get("sla_minutes")
        if isinstance(sla, int | float):
            measures["sla_minutes"] = sla

        attrs: dict[str, Any] = {}
        fonte = entrada.get("primary_source")
        if isinstance(fonte, str) and fonte:
            attrs["primary_source"] = fonte

        facts.append(
            Fact(
                kind="workload.declared",
                subject=_job_subject(nome),
                measures=measures,
                attrs=attrs,
                provenance=provenance,
            )
        )

    facts.append(
        Fact(
            kind="workload.declared_analyzed",
            subject=_file_subject(path),
            measures={"jobs_declared": len(vistos)},
            provenance=provenance,
        )
    )
    return sort_facts(facts)


def extract_workload_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Le o inventario do disco. Arquivo ausente devolve a sentinela em zero."""
    alvo = Path(path)
    rel = str(alvo.relative_to(repo_root)) if repo_root else str(alvo)
    anchor = rel.replace("\\", "/")
    if not alvo.is_file():
        return extract_workload(None, anchor)
    try:
        payload = yaml.safe_load(alvo.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [_unresolved(anchor, "read_error", str(exc))]
    return extract_workload(payload, anchor)
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_workload.py -v
```

Esperado: PASS, 9 testes.

- [ ] **Step 5: Provar que todo fact valida contra o schema**

Acrescente a `tests/test_facts_workload.py`:

```python
class TestSchema:
    def test_every_emitted_fact_validates(self, tmp_path):
        from sparkforge.findings.validate import validate_fact

        alvo = _inventario(
            tmp_path,
            {
                "jobs": [
                    {"name": "bom", "sla_minutes": 10, "primary_source": "db.clientes"},
                    {"sla_minutes": 5},
                    "isto-nao-e-um-objeto",
                ]
            },
        )
        facts = extract_workload_path(alvo)

        assert facts
        for fact in facts:
            validate_fact(fact.to_dict())
```

```bash
rtk pytest tests/test_facts_workload.py -v
```

Esperado: PASS, 10 testes.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/facts/workload.py tests/test_facts_workload.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): inventario declarado de SLA e fonte principal`

---

## Task 3: O contrato do eixo

**Files:**
- Create: `sparkforge/workload/__init__.py`
- Create: `sparkforge/workload/axis.py`
- Test: `tests/test_workload_axis.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_workload_axis.py`:

```python
"""Testes do contrato do eixo do fingerprint."""
from __future__ import annotations

import pytest

from sparkforge.workload.axis import Axis, unknown_axis


class TestContrato:
    def test_measured_axis_carries_basis_and_evidence(self):
        eixo = Axis(value="extreme", confidence="measured", basis="history_p99", evidence=["a1"])

        assert eixo.value == "extreme"
        assert eixo.confidence == "measured"
        assert eixo.to_dict()["basis"] == "history_p99"

    def test_measured_without_evidence_is_refused(self):
        with pytest.raises(ValueError, match="evidence"):
            Axis(value="high", confidence="measured", basis="history_p95", evidence=[])

    def test_measured_without_basis_is_refused(self):
        with pytest.raises(ValueError, match="basis"):
            Axis(value="high", confidence="measured", basis="", evidence=["a1"])

    def test_unknown_axis_carries_what_is_missing(self):
        eixo = unknown_axis("glue.job_run.distribution", "sparkforge collect glue-job-runs ...")

        assert eixo.value == "unknown"
        assert eixo.confidence == "unknown"
        assert eixo.to_dict()["missing"] == "glue.job_run.distribution"
        assert "collect glue-job-runs" in eixo.to_dict()["collect_command"]

    def test_a_value_other_than_unknown_cannot_have_unknown_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            Axis(value="high", confidence="unknown", basis="", evidence=[])

    def test_unknown_value_never_carries_evidence(self):
        with pytest.raises(ValueError, match="unknown"):
            Axis(value="unknown", confidence="unknown", basis="", evidence=["a1"])

    def test_declared_axis_never_claims_to_be_measured(self):
        eixo = Axis(value="critical", confidence="declared", basis="declared", evidence=["d1"])

        assert eixo.confidence == "declared"
        assert eixo.to_dict()["confidence"] != "measured"
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_workload_axis.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.workload'`.

- [ ] **Step 3: Implementar**

`sparkforge/workload/axis.py`:

```python
"""O eixo do fingerprint: o valor, de onde ele veio, e quanto vale confiar.

Um eixo com valor e sem procedencia e a forma mais cara de errar neste
projeto, porque parece resposta. Por isso as invariantes abaixo sao impostas na
CONSTRUCAO, e nao conferidas depois: um eixo invalido nunca chega a existir.

  - `measured` exige `basis` e `evidence`. Classe sem lastro nao e classe.
  - valor diferente de `unknown` exige confianca diferente de `unknown`.
  - `unknown` nao carrega evidencia: se ha evidencia, o eixo nao e desconhecido.

`declared` e um valor de confianca DISTINTO de `measured`, e nunca e promovido.
Quem le `sla = critical` precisa saber, sem procurar, que alguem escreveu isso
e nada mediu.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALORES = ("extreme", "high", "medium", "low", "critical", "unknown")
CONFIANCAS = ("measured", "declared", "unknown")


@dataclass(frozen=True)
class Axis:
    value: str
    confidence: str
    basis: str = ""
    evidence: tuple[str, ...] = field(default_factory=tuple)
    missing: str = ""
    collect_command: str = ""

    def __post_init__(self) -> None:
        if self.value not in VALORES:
            raise ValueError(f"valor de eixo desconhecido: {self.value!r}")
        if self.confidence not in CONFIANCAS:
            raise ValueError(f"confidence desconhecida: {self.confidence!r}")
        if self.value != "unknown" and self.confidence == "unknown":
            raise ValueError(
                f"eixo com valor {self.value!r} nao pode ter confidence 'unknown': "
                f"valor sem procedencia parece resposta."
            )
        if self.value == "unknown" and self.evidence:
            raise ValueError(
                "eixo 'unknown' nao carrega evidence: se ha evidencia, ele nao e desconhecido."
            )
        if self.confidence == "measured":
            if not self.basis:
                raise ValueError("eixo 'measured' exige basis: classe sem base nao e classe.")
            if not self.evidence:
                raise ValueError(
                    "eixo 'measured' exige evidence: classe sem lastro parece medicao."
                )

    def to_dict(self) -> dict[str, Any]:
        saida: dict[str, Any] = {
            "value": self.value,
            "confidence": self.confidence,
            "basis": self.basis,
            "evidence": list(self.evidence),
        }
        if self.missing:
            saida["missing"] = self.missing
        if self.collect_command:
            saida["collect_command"] = self.collect_command
        return saida


def unknown_axis(missing: str, collect_command: str = "") -> Axis:
    """Eixo sem lastro, com o que falta e -- quando existe -- o comando que resolve."""
    return Axis(
        value="unknown",
        confidence="unknown",
        missing=missing,
        collect_command=collect_command,
    )
```

`sparkforge/workload/__init__.py`:

```python
"""Perfil de workload: os eixos, e a confianca de cada um.

NAO e um extrator. Extrator emite fact, e fact nunca aplica limiar -- dizer que
`scan` e `extreme` e exatamente aplicar limiar. Este pacote e o mecanismo
proprio de julgamento, no molde de `MigrationAssessment` e do `benchmark`, que
tambem nao cabem em regra do catalogo e tambem declaram o que garantem.
"""
from sparkforge.workload.axis import Axis, unknown_axis

__all__ = ["Axis", "unknown_axis"]
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_workload_axis.py -v
```

Esperado: PASS, 7 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/workload tests/test_workload_axis.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(workload): o eixo, com a procedencia imposta na construcao`

---

## Task 4: A montagem do fingerprint

**Files:**
- Create: `sparkforge/workload/fingerprint.py`
- Modify: `sparkforge/workload/__init__.py`
- Test: `tests/test_workload_fingerprint.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_workload_fingerprint.py`:

```python
"""Testes da montagem do fingerprint a partir dos facts."""
from __future__ import annotations

from sparkforge.findings.models import Fact
from sparkforge.workload.fingerprint import build_fingerprint


def _scan(bytes_read=1000, files_read=10, execution_id=0, node_id=1):
    return Fact(
        kind="spark.sql.scan",
        subject={
            "type": "plan_node",
            "node_id": node_id,
            "operator": "Scan parquet",
            "relation": "db.clientes",
            "symbol": f"{execution_id}:{node_id}",
            "execution_id": execution_id,
        },
        measures={"bytes_read": bytes_read, "files_read": files_read},
        attrs={"format": "parquet", "scan_api": "v1", "node_name": "Scan parquet"},
    )


def _history(*totais_de_bytes):
    """Um "run anterior" por elemento, cada um como a lista de facts daquele run.

    `glue.job_run.distribution` NAO serve aqui: ele carrega duracao e DPU, nunca
    bytes -- `glue.get_job_runs` nao publica volume lido. O historico de uma
    metrica de volume so pode vir da mesma medicao repetida.
    """
    return [[_scan(bytes_read=total)] for total in totais_de_bytes]


def _task_duration(p50_ms=100, p95_ms=1000):
    return Fact(
        kind="spark.stage.task_duration",
        subject={"type": "stage", "symbol": "stage-1", "stage_id": 1},
        measures={"p50_ms": p50_ms, "p95_ms": p95_ms, "task_count": 20},
    )


class TestEixosMedidos:
    def test_scan_above_p99_is_extreme(self):
        fp = build_fingerprint(
            [_scan(bytes_read=5000)],
            history=_history(100, 200, 300, 400, 500),
            job_name="etl",
            job_run_id="jr_1",
        )

        assert fp.axes["scan_intensity"].value == "extreme"
        assert fp.axes["scan_intensity"].confidence == "measured"
        assert fp.axes["scan_intensity"].evidence

    def test_scan_below_p50_is_low(self):
        fp = build_fingerprint(
            [_scan(bytes_read=100)],
            history=_history(1000, 2000, 3000, 4000, 5000),
            job_name="etl",
            job_run_id="jr_1",
        )

    def test_history_shorter_than_three_runs_refuses_to_claim_a_p99(self):
        fp = build_fingerprint(
            [_scan(bytes_read=5000)],
            history=_history(100, 200),
            job_name="etl",
            job_run_id="jr_1",
        )
        eixo = fp.axes["scan_intensity"]

        assert eixo.value == "unknown"
        assert eixo.missing == "history_too_short"

        assert fp.axes["scan_intensity"].value == "low"

    def test_skew_uses_the_run_itself_not_the_history(self):
        fp = build_fingerprint(
            [_task_duration(p50_ms=100, p95_ms=1000)], job_name="etl", job_run_id="jr_1"
        )
        eixo = fp.axes["skew_risk"]

        # p95/p50 = 10x. Sem historico nenhum nos facts, e mesmo assim medido.
        assert eixo.confidence == "measured"
        assert eixo.value in ("high", "extreme")


class TestSemLastro:
    def test_no_history_leaves_volume_axes_unknown_with_the_command(self):
        fp = build_fingerprint([_scan()], job_name="etl", job_run_id="jr_1")
        eixo = fp.axes["scan_intensity"]

        assert eixo.value == "unknown"
        assert eixo.missing
        assert "collect glue-job-runs" in eixo.collect_command

    def test_axes_that_do_not_need_history_stay_filled(self):
        fp = build_fingerprint(
            [_scan(), _task_duration()], job_name="etl", job_run_id="jr_1"
        )

        assert fp.axes["scan_intensity"].value == "unknown"
        assert fp.axes["skew_risk"].value != "unknown"
        assert fp.axes["file_pressure"].value != "unknown"

    def test_no_axis_is_medium_by_omission(self):
        fp = build_fingerprint([], job_name="etl", job_run_id="jr_1")

        for nome, eixo in fp.axes.items():
            assert eixo.value == "unknown" or eixo.basis, nome

    def test_unknown_axes_are_listed_so_nobody_has_to_scan_field_by_field(self):
        fp = build_fingerprint([], job_name="etl", job_run_id="jr_1")

        assert set(fp.unknown_axes()) == set(fp.axes)


class TestDeclarado:
    def _declared(self, primary="db.clientes"):
        attrs = {"primary_source": primary} if primary else {}
        return Fact(
            kind="workload.declared",
            subject={"type": "job_run", "symbol": "etl"},
            measures={"sla_minutes": 45},
            attrs=attrs,
        )

    def test_declared_axis_is_never_measured(self):
        fp = build_fingerprint(
            [self._declared(), _scan()],
            history=_history(100, 200, 300),
            job_name="etl",
            job_run_id="jr_1",
        )

        assert fp.axes["sla_class"].confidence == "declared"
        assert fp.axes["sla_class"].confidence != "measured"

    def test_declaration_for_another_job_is_ignored(self):
        outro = self._declared()
        outro = Fact(
            kind="workload.declared",
            subject={"type": "job_run", "symbol": "outro-job"},
            measures={"sla_minutes": 45},
        )
        fp = build_fingerprint([outro], job_name="etl", job_run_id="jr_1")

        assert fp.axes["sla_class"].value == "unknown"

    def test_declared_source_that_no_scan_matches_is_a_named_gap(self):
        fp = build_fingerprint(
            [self._declared(primary="db.inexistente"), _scan()],
            job_name="etl",
            job_run_id="jr_1",
        )
        eixo = fp.axes["primary_input_class"]

        assert eixo.value == "unknown"
        assert eixo.missing == "declared_source_not_observed"


class TestSerializacao:
    def test_to_dict_carries_every_axis_and_the_run(self):
        fp = build_fingerprint(
            [_scan()], history=_history(100, 200, 300), job_name="etl", job_run_id="jr_1"
        )
        saida = fp.to_dict()

        assert saida["job_name"] == "etl"
        assert saida["job_run_id"] == "jr_1"
        assert set(saida["axes"]) == set(fp.axes)
        assert saida["source_count"] == 1
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_workload_fingerprint.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.workload.fingerprint'`.

- [ ] **Step 3: Implementar**

`sparkforge/workload/fingerprint.py`:

```python
"""Montagem do fingerprint a partir de facts ja extraidos.

Puro sobre Facts: nao le artefato, nao toca a rede, nao mede relogio -- mesma
disciplina de `facts/benchmark.py`, que tambem opera sobre a saida de outros
verbos.

A ESCALA DE CADA EIXO DE VOLUME VEM DO HISTORICO DO PROPRIO JOB. `extreme` e o
run acima do p99 dos runs ANTERIORES daquele job, e nao um limiar universal:
nao existe fonte da AWS ou do Spark dizendo que 1 TB de varredura e muito, e
inventar o numero seria `field-heuristic` aplicada igual a um job de dez
minutos e a um de dez horas.

O historico de volume NAO vem de `glue.job_run.distribution`: aquele fact
carrega duracao e DPU, nunca bytes, porque `glue.get_job_runs` nao publica
volume lido. Ele vem da mesma medicao repetida -- um conjunto de facts por run
anterior, que `--history` entrega como um arquivo por run. Separar por arquivo
e o que identifica cada run: `execution_id` e por aplicacao, e dois event logs
diferentes colidem nele.

O custo dessa escolha e declarado, nao escondido: job sem historico coletado
nao classifica os eixos de volume. Eles saem `unknown` com o comando que
resolve, e os eixos que NAO dependem de historico -- skew e densidade de
arquivo, que ja sao razoes -- saem preenchidos assim mesmo.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sparkforge.findings.models import Fact
from sparkforge.workload.axis import Axis, unknown_axis

# O historico de volume e produzido rodando o extrator sobre os event logs
# anteriores, um arquivo por run. Nao ha comando unico que o produza de uma vez,
# e dizer o contrario mandaria o operador a um caminho que nao existe.
_PRODUZ_HISTORICO = (
    "para cada run anterior: sparkforge analyze sql-metrics "
    "--path <event-log-do-run>.jsonl --out <dir-de-historico>/<run>.json"
)

# Menos de tres runs nao sustenta a afirmacao de um p99. Anunciar percentil
# sobre dois pontos e teatro de precisao, e o eixo prefere recusar.
_MINIMO_DE_RUNS = 3
_ANALISA_SQL = "sparkforge analyze sql-metrics --path <event-log.jsonl> --out <facts.json>"

# Razao p95/p50 de duracao de tarefa. Sao razoes, e nao volumes: comparar uma
# razao com o historico dela seria uma segunda derivada sem consumidor.
_SKEW_FAIXAS = ((10.0, "extreme"), (4.0, "high"), (2.0, "medium"))

# Arquivos por MiB lido. Densidade alta e o sintoma de small files.
_FILE_FAIXAS = ((4.0, "extreme"), (1.0, "high"), (0.25, "medium"))


def _classe_por_faixa(valor: float, faixas: tuple[tuple[float, str], ...]) -> str:
    for limite, classe in faixas:
        if valor >= limite:
            return classe
    return "low"


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n).

    Mesma formula de `event_log._nearest_rank` e dos irmaos, reescrita aqui em
    vez de importada pela razao ja registrada em `iceberg_metadata.py`: os
    modulos sao independentes por desenho, e o que garante que continuam iguais
    e teste, nao import.
    """
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


def _classe_por_historico(valor: float, anteriores: list[float]) -> str:
    ordenados = sorted(anteriores)
    if valor >= _nearest_rank(ordenados, 99):
        return "extreme"
    if valor >= _nearest_rank(ordenados, 95):
        return "high"
    if valor >= _nearest_rank(ordenados, 50):
        return "medium"
    return "low"


def _totais_por_run(
    history: Sequence[Sequence[Fact]], kind: str, measure: str
) -> list[float]:
    """Um total por run anterior, somando a measure dentro de cada arquivo."""
    totais: list[float] = []
    for run in history:
        soma = sum(f.measures.get(measure, 0) for f in run if f.kind == kind)
        if soma:
            totais.append(float(soma))
    return totais


@dataclass(frozen=True)
class WorkloadFingerprint:
    job_name: str
    job_run_id: str
    axes: dict[str, Axis]
    source_count: int

    def unknown_axes(self) -> list[str]:
        """Os eixos que NAO foram respondidos, nomeados.

        Existe para que quem le o perfil saiba o que falta sem varrer campo a
        campo -- a mesma razao pela qual o manifesto lista o que nao coletou.
        """
        return sorted(nome for nome, eixo in self.axes.items() if eixo.value == "unknown")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "job_run_id": self.job_run_id,
            "source_count": self.source_count,
            "axes": {nome: eixo.to_dict() for nome, eixo in self.axes.items()},
            "unknown_axes": self.unknown_axes(),
        }


def _fact_id(fact: Fact) -> str:
    return fact.to_dict().get("id", "")


def _scan_axes(
    scans: list[Fact], history: Sequence[Sequence[Fact]], job: str
) -> dict[str, Axis]:
    eixos: dict[str, Axis] = {}

    if not scans:
        eixos["scan_intensity"] = unknown_axis("spark.sql.scan", _ANALISA_SQL)
        eixos["file_pressure"] = unknown_axis("spark.sql.scan", _ANALISA_SQL)
        return eixos

    total_bytes = sum(f.measures.get("bytes_read", 0) for f in scans)
    total_files = sum(f.measures.get("files_read", 0) for f in scans)
    evidencia = tuple(_fact_id(f) for f in scans)

    anteriores = _totais_por_run(history, "spark.sql.scan", "bytes_read")
    if not anteriores:
        eixos["scan_intensity"] = unknown_axis("history_absent", _PRODUZ_HISTORICO)
    elif len(anteriores) < _MINIMO_DE_RUNS:
        eixos["scan_intensity"] = unknown_axis("history_too_short", _PRODUZ_HISTORICO)
    else:
        eixos["scan_intensity"] = Axis(
            value=_classe_por_historico(total_bytes, anteriores),
            confidence="measured",
            basis="history_percentile",
            evidence=evidencia,
        )

    # Densidade de arquivo e razao interna: responde no PRIMEIRO run, sem
    # historico nenhum.
    densidade = (total_files / (total_bytes / 1_048_576)) if total_bytes else 0.0
    eixos["file_pressure"] = Axis(
        value=_classe_por_faixa(densidade, _FILE_FAIXAS),
        confidence="measured",
        basis="files_per_mib",
        evidence=evidencia,
    )
    return eixos


def build_fingerprint(
    facts: Sequence[Fact],
    *,
    job_name: str,
    job_run_id: str,
    history: Sequence[Sequence[Fact]] = (),
) -> WorkloadFingerprint:
    """Monta o fingerprint. Eixo sem lastro sai `unknown`, nunca um default.

    `history` e uma sequencia de conjuntos de facts, UM POR RUN ANTERIOR. A
    separacao por conjunto e o que identifica cada run.
    """
    por_kind: dict[str, list[Fact]] = {}
    for fact in facts:
        por_kind.setdefault(fact.kind, []).append(fact)

    scans = por_kind.get("spark.sql.scan") or []

    eixos: dict[str, Axis] = {}
    eixos.update(_scan_axes(scans, history, job_name))

    # Shuffle: mesma ancora de historico do scan, e a mesma recusa.
    shuffles = por_kind.get("spark.stage.shuffle") or []
    anteriores_shuffle = _totais_por_run(history, "spark.stage.shuffle", "write_bytes")
    if not shuffles:
        eixos["shuffle_intensity"] = unknown_axis(
            "spark.stage.shuffle",
            "sparkforge analyze event-log --path <event-log.jsonl> --out <facts.json>",
        )
    elif not anteriores_shuffle:
        eixos["shuffle_intensity"] = unknown_axis("history_absent", _PRODUZ_HISTORICO)
    elif len(anteriores_shuffle) < _MINIMO_DE_RUNS:
        eixos["shuffle_intensity"] = unknown_axis("history_too_short", _PRODUZ_HISTORICO)
    else:
        total = sum(f.measures.get("write_bytes", 0) for f in shuffles)
        eixos["shuffle_intensity"] = Axis(
            value=_classe_por_historico(total, anteriores_shuffle),
            confidence="measured",
            basis="history_percentile",
            evidence=tuple(_fact_id(f) for f in shuffles),
        )

    # Skew: razao interna ao run, nao depende de historico.
    duracoes = por_kind.get("spark.stage.task_duration") or []
    razoes = [
        f.measures["p95_ms"] / f.measures["p50_ms"]
        for f in duracoes
        if f.measures.get("p50_ms")
    ]
    if razoes:
        eixos["skew_risk"] = Axis(
            value=_classe_por_faixa(max(razoes), _SKEW_FAIXAS),
            confidence="measured",
            basis="task_p95_over_p50",
            evidence=tuple(_fact_id(f) for f in duracoes),
        )
    else:
        eixos["skew_risk"] = unknown_axis(
            "spark.stage.task_duration",
            "sparkforge analyze event-log --path <event-log.jsonl> --out <facts.json>",
        )

    # Memoria: spill contra input, razao interna.
    spills = por_kind.get("spark.stage.spill") or []
    razoes_spill = [
        (f.measures.get("memory_spill_bytes", 0) + f.measures.get("disk_spill_bytes", 0))
        / f.measures["input_bytes"]
        for f in spills
        if f.measures.get("input_bytes")
    ]
    if razoes_spill:
        eixos["memory_pressure"] = Axis(
            value=_classe_por_faixa(max(razoes_spill), ((1.0, "extreme"), (0.25, "high"), (0.05, "medium"))),
            confidence="measured",
            basis="spill_over_input",
            evidence=tuple(_fact_id(f) for f in spills),
        )
    else:
        eixos["memory_pressure"] = unknown_axis(
            "spark.stage.spill",
            "sparkforge analyze event-log --path <event-log.jsonl> --out <facts.json>",
        )

    # Join: estrutural. O `basis` diz isso -- CartesianProduct e fato do plano,
    # nao volume.
    joins = por_kind.get("plan.join") or []
    if joins:
        caros = [f for f in joins if f.attrs.get("strategy") in ("CartesianProduct", "BroadcastNestedLoopJoin")]
        valor = "extreme" if caros else ("high" if len(joins) >= 3 else "medium" if joins else "low")
        eixos["join_intensity"] = Axis(
            value=valor,
            confidence="measured",
            basis="plan_structure",
            evidence=tuple(_fact_id(f) for f in joins),
        )
    else:
        eixos["join_intensity"] = unknown_axis(
            "plan.join",
            "sparkforge analyze plan --path <explain.txt> --out <facts.json>",
        )

    # Declarados: nunca promovidos a `measured`.
    declarados = [
        f for f in (por_kind.get("workload.declared") or []) if f.subject.get("symbol") == job_name
    ]
    declarado = declarados[0] if declarados else None
    if declarado is not None and "sla_minutes" in declarado.measures:
        eixos["sla_class"] = Axis(
            value="critical" if declarado.measures["sla_minutes"] <= 60 else "medium",
            confidence="declared",
            basis="declared",
            evidence=(_fact_id(declarado),),
        )
    else:
        eixos["sla_class"] = unknown_axis(
            "workload.declared:sla_minutes",
            "declare o job em workload.yaml com `sla_minutes`",
        )

    fonte = declarado.attrs.get("primary_source") if declarado is not None else None
    if not fonte:
        eixos["primary_input_class"] = unknown_axis(
            "workload.declared:primary_source",
            "declare o job em workload.yaml com `primary_source`",
        )
    else:
        casados = [f for f in scans if f.subject.get("relation") == fonte]
        if not casados:
            eixos["primary_input_class"] = unknown_axis("declared_source_not_observed")
        else:
            bytes_fonte = sum(f.measures.get("bytes_read", 0) for f in casados)
            total = sum(f.measures.get("bytes_read", 0) for f in scans) or 1
            eixos["primary_input_class"] = Axis(
                value=_classe_por_faixa(
                    bytes_fonte / total, ((0.75, "extreme"), (0.4, "high"), (0.1, "medium"))
                ),
                confidence="declared",
                basis="declared_source_share",
                evidence=tuple(_fact_id(f) for f in casados) + (_fact_id(declarado),),
            )

    return WorkloadFingerprint(
        job_name=job_name,
        job_run_id=job_run_id,
        axes=eixos,
        source_count=len(scans),
    )
```

Acrescente a `sparkforge/workload/__init__.py`:

```python
from sparkforge.workload.fingerprint import WorkloadFingerprint, build_fingerprint

__all__ = ["Axis", "WorkloadFingerprint", "build_fingerprint", "unknown_axis"]
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_workload_fingerprint.py tests/test_workload_axis.py -v
```

Esperado: PASS. Reporte a contagem real.

**Não tente ancorar volume em `glue.job_run.distribution`.** Medido em 2026-08-28, aquele fact carrega `runtime_min_s`, `runtime_p50_s`, `runtime_p95_s`, `runtime_p99_s`, `runtime_max_s`, `dpu_seconds_p50`, `dpu_seconds_p95` e `n` — nenhum byte, porque `glue.get_job_runs` não publica volume lido. O histórico de volume vem de `history`, um conjunto de facts por run anterior. Se você se pegar procurando um campo de bytes naquele fact, é sinal de que voltou ao desenho errado.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/workload tests/test_workload_fingerprint.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(workload): fingerprint com a escala ancorada no historico do job`

---

## Task 5: Superfície — verbo de topo e tool

**Files:**
- Modify: `sparkforge/adapters/_core.py`, `cli.py`, `tools.py`
- Modify: `manifest.json`, `parity.yaml`, um arquivo de `agents/`
- Test: `tests/test_adapters_cli.py`, `tests/test_adapters_tools.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_adapters_cli.py`:

```python
class TestWorkloadCommand:
    def _facts(self, tmp_path):
        alvo = tmp_path / "facts.json"
        alvo.write_text(
            json.dumps(
                [
                    {
                        "id": "a" * 16,
                        "schema_version": 1,
                        "kind": "spark.stage.task_duration",
                        "subject": {"type": "stage", "symbol": "stage-1", "stage_id": 1},
                        "measures": {"p50_ms": 100, "p95_ms": 1000, "task_count": 20},
                        "attrs": {},
                        "provenance": {},
                    }
                ]
            ),
            encoding="utf-8",
        )
        return alvo

    def test_workload_is_a_top_level_verb(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        code = main(
            ["workload", "--facts", str(self._facts(tmp_path)), "--job-name", "etl",
             "--job-run", "jr_1"]
        )

        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["job_name"] == "etl"
        assert payload["axes"]["skew_risk"]["confidence"] == "measured"

    def test_axes_without_evidence_are_listed_as_unknown(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        main(
            ["workload", "--facts", str(self._facts(tmp_path)), "--job-name", "etl",
             "--job-run", "jr_1"]
        )
        payload = json.loads(capsys.readouterr().out)

        assert "scan_intensity" in payload["unknown_axes"]
```

E a `tests/test_adapters_tools.py`:

```python
class TestWorkloadTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_workload" in tools.TOOLS
        assert "sparkforge_workload" in tools._HANDLERS
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_cli.py::TestWorkloadCommand tests/test_adapters_tools.py::TestWorkloadTool -v
```

Esperado: FAIL — `SystemExit: 2` e `AssertionError`.

- [ ] **Step 3: Implementar em `_core.py`**

Leia `benchmark_runs` primeiro: ele é o molde exato, inclusive no uso de `_load_facts_file` com um `producer` que diz qual comando produz o arquivo.

```python
from sparkforge.workload import build_fingerprint

_FACTS_FROM_SQL_METRICS = (
    "sparkforge analyze sql-metrics --path <event-log.jsonl> --out {path}"
)


def workload_fingerprint(
    facts_path: str,
    job_name: str,
    job_run_id: str,
    history_path: str = "",
) -> dict[str, Any]:
    """Monta o WorkloadFingerprint a partir de facts ja extraidos.

    Verbo de TOPO, e nao `analyze workload`, pela mesma razao de `benchmark` e
    `fuse`: os verbos sob `analyze` extraem facts de um artefato, e este nao
    extrai nada -- ele classifica o que outros verbos ja extrairam.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_SQL_METRICS, "--facts")
    if history_path:
        facts = list(facts) + list(
            _load_facts_file(
                history_path,
                "sparkforge analyze glue-job-runs --path <dir> --job-name <job> --out {path}",
                "--history",
            )
        )
    fingerprint = build_fingerprint(facts, job_name=job_name, job_run_id=job_run_id)
    return fingerprint.to_dict()
```

- [ ] **Step 4: Implementar em `cli.py`**

Parser de topo, junto de onde `benchmark` e `fuse` são declarados:

```python
    workload_p = sub.add_parser(
        "workload",
        help="Perfil de workload por eixos, a partir de facts ja extraidos.",
    )
    workload_p.add_argument("--facts", required=True, help="Arquivo de facts (--out de analyze).")
    workload_p.add_argument("--job-name", required=True)
    workload_p.add_argument("--job-run", required=True, help="Id do run que este perfil descreve.")
    workload_p.add_argument("--history", help="Facts de `analyze glue-job-runs`, para a escala.")
    workload_p.add_argument("--out", help="Escreve o fingerprint completo (JSON).")
```

Confira o nome real do subparser de topo (`sub`, `subparsers`, …) lendo como `benchmark` é declarado.

Handler:

```python
def _cmd_workload(args: argparse.Namespace) -> int:
    payload = _core.workload_fingerprint(
        args.facts,
        job_name=args.job_name,
        job_run_id=args.job_run,
        history_path=args.history or "",
    )
    if args.out:
        Path(args.out).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    _print(payload)
    return 0
```

E a entrada no despacho. Verbo de topo não tem subcomando — veja como `benchmark` aparece no dicionário e siga a mesma forma.

- [ ] **Step 5: Implementar a tool em `tools.py`**

```python
    "sparkforge_workload": {
        "description": (
            "Perfil de workload por eixos independentes -- scan, shuffle, memoria, skew, "
            "arquivos, join -- a partir de facts ja extraidos. Cada eixo carrega o valor, a "
            "BASE que o produziu e a CONFIANCA: `measured` sai de artefato, `declared` sai do "
            "inventario versionado e nunca e promovido, e `unknown` carrega o comando que "
            "fecha a lacuna. A escala vem do historico do proprio job, nao de limiar "
            "universal: sem `history`, os eixos de volume saem `unknown` de proposito."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["facts", "job_name", "job_run"],
            "properties": {
                "facts": {"type": "string"},
                "job_name": {"type": "string"},
                "job_run": {"type": "string"},
                "history": {"type": "string"},
            },
        },
        "outputSchema": _may_fail(
            {
                "type": "object",
                "properties": {
                    "job_name": {"type": "string"},
                    "job_run_id": {"type": "string"},
                    "source_count": {"type": "integer"},
                    "axes": {"type": "object"},
                    "unknown_axes": {"type": "array", "items": {"type": "string"}},
                },
            },
            "Fingerprint, ou erro de fronteira.",
        ),
        "annotations": _READ_ONLY,
    },
```

Handler e entrada no despacho, no molde dos vizinhos.

- [ ] **Step 6: Manifesto, paridade e o gate de órfão**

- `manifest.json`, lista `tools`: `sparkforge_workload`, em ordem alfabética.
- `parity.yaml`: a capability que lista `benchmark` ganha `sparkforge_workload` e `workload`.
- `agents/`: cite a tool onde `sparkforge_analyze_sql_metrics` já aparece, dizendo **por que** ela existe — os eixos separam workloads que o volume de entrada não separa.

```bash
rtk python scripts/sync_skills.py
rtk pytest tests/test_arvore_versionada.py tests/test_agent_coverage.py tests/test_capability_parity.py tests/test_canonical_registry.py tests/test_adapters_tools.py tests/test_adapters_mcp.py -v
```

`tests/test_harness_authorization.py` tem contagem fixa de tools que declaram caminho. A tool nova declara `facts`, que **pode não ser reconhecido** pelo predicado `_e_chave_de_caminho`. Rode e leia o que ele diz:

```bash
rtk pytest tests/test_harness_authorization.py -q
```

Se `sparkforge_workload` cair no conjunto `SEM_CAMINHO`, isso é decisão consciente que o teste existe para forçar: ou o parâmetro passa a se chamar como os outros caminhos do projeto, ou a tool entra na lista com a razão escrita. Relate qual das duas você escolheu e por quê.

- [ ] **Step 7: Commit**

```bash
rtk git add sparkforge/adapters manifest.json parity.yaml tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_harness_authorization.py agents .claude .agents .github
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(cli): verbo workload e a tool do fingerprint`

---

## Task 6: Fixtures golden

**Files:**
- Create: `fixtures/workload/` (seis cenários)
- Create: `tests/test_fixtures_golden_workload.py`
- Modify: `tests/test_fixtures_kind_coverage.py`, `tests/test_rules_catalog_reachability.py`

- [ ] **Step 1: Registrar `workload` nas DUAS listas de extratores**

`tests/test_fixtures_kind_coverage.py` e `tests/test_rules_catalog_reachability.py` mantêm listas manuais e duplicadas de extratores. Extrator novo entra nas duas — e o próprio arquivo avisa que esquecer uma não quebra nada, o que é exatamente por que ela é esquecida. Acrescente `workload` a ambas, com comentário curto dizendo de onde ele vem.

- [ ] **Step 2: Criar os cenários**

Leia `fixtures/consumers/malformed_inventory/` para a forma de `meta.yaml`. Cada cenário tem `input/` (com `facts.json` e, quando fizer sentido, `workload.yaml`), `meta.yaml` e `expected/fingerprint.json`.

| Cenário | Prova |
|---|---|
| `small_batch_extreme_scan` | o caso que motivou o documento de origem: entrada pequena, scan no p99 |
| `no_history` | eixos de volume `unknown`, com o comando; skew e arquivos preenchidos |
| `history_too_short` | `n=2`: recusa de p99 com o `n` declarado |
| `declared_only` | `workload.yaml` presente e nenhum fact de medição |
| `declared_source_not_observed` | declaração que não bate com o medido |
| `shuffle_heavy_small_scan` | o eixo novo separando dois workloads que o scan não separa |

- [ ] **Step 3: Escrever o módulo golden**

`tests/test_fixtures_golden_workload.py`, no molde de `tests/test_fixtures_golden_s3.py`, com `FIXTURES = ROOT / "fixtures" / "workload"` — é o que `test_every_fixture_domain_has_a_golden_module` cobra.

Além dos goldens byte-exatos, as duas garantias sobre o corpus inteiro:

```python
class TestOQueOCorpusInteiroGarante:
    def test_no_measured_axis_without_evidence(self):
        """Eixo `measured` sem evidencia e classe sem lastro.

        Sobre o corpus INTEIRO, e nao por cenario: um default que preenchesse a
        classe sem evidencia passaria em cada cenario isolado e quebraria aqui.
        """
        for directory in fixture_dirs():
            fingerprint = run_fixture(directory)
            for nome, eixo in fingerprint["axes"].items():
                if eixo["confidence"] == "measured":
                    assert eixo["evidence"], (directory.name, nome)
                    assert eixo["basis"], (directory.name, nome)

    def test_no_declared_axis_is_ever_promoted_to_measured(self):
        """A fronteira entre o que alguem escreveu e o que a maquina mediu.

        E dela que depende o subprojeto D, que vai escolher capacidade em cima
        deste perfil e precisa saber em que esta pisando.
        """
        declarados = {"sla_class", "primary_input_class"}
        for directory in fixture_dirs():
            fingerprint = run_fixture(directory)
            for nome in declarados:
                assert fingerprint["axes"][nome]["confidence"] != "measured", (
                    directory.name,
                    nome,
                )
```

- [ ] **Step 4: Rodar**

```bash
rtk pytest tests/test_fixtures_golden_workload.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -v
```

Esperado: PASS. Grave os goldens com a saída real e **leia** cada um antes de commitar — golden gravado sem leitura trava o defeito junto com o comportamento.

- [ ] **Step 5: Commit**

```bash
rtk git add fixtures/workload tests/test_fixtures_golden_workload.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `test(fixtures): seis cenarios sinteticos de perfil de workload`

---

## Task 7: Documentação, suíte completa e os gates

**Files:**
- Modify: `README.md`, `docs/superpowers/STATUS.md`, possivelmente `docs/harness/*.md` e `docs/claims.lock.json`

- [ ] **Step 1: Rodar a suíte inteira**

```bash
rtk pytest -q
```

Cerca de 17 minutos. Qualquer falha é regressão desta entrega.

- [ ] **Step 2: README**

Acrescente o verbo à seção onde `benchmark` e `fuse` aparecem (é verbo de topo, não entra na tabela de `analyze`). Atualize os números de extratores e kinds, **medidos**:

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

- [ ] **Step 3: STATUS**

Registre a fase no formato das existentes: o verbo, a tool, os kinds novos (`spark.stage.shuffle` e os três de `workload.*`), o pacote `sparkforge/workload/`, o número de testes acrescentados (meça), a faixa de commits, a referência à spec, e:

- as três decisões (escala do histórico, `declared` nunca vira `measured`, shuffle medido antes de classificado);
- o que ficou de fora: `cpu_pressure` e `metadata_pressure` (evidência parcial hoje), recomendação de capacidade (é D), custo (é E), grafo de joins (terceiro recorte de C), e nenhuma regra nova.

- [ ] **Step 4: Gate de números**

```bash
rtk python scripts/check_vnext_claims.py
```

Um pacote novo e uma tool nova deslocam contagens em `docs/harness/`. Para cada divergência o gate imprime `esperado X, obtido Y`: corrija o texto para **Y** e ajuste `docs/claims.lock.json`. Itere até `0 divergencia(s).`

```bash
rtk pytest tests/test_docs_coverage.py -q
```

- [ ] **Step 5: Commit e prova final**

```bash
rtk git add README.md docs/superpowers/STATUS.md docs/claims.lock.json docs/harness docs/vnext
rtk git commit -F <arquivo com a mensagem>
rtk pytest -q
```

Mensagem: `docs: o verbo workload, a fase e o que ficou de fora`

Esperado: 0 failed.

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §2 `spark.stage.shuffle` | 1 |
| §2 extrator do inventário declarado | 2 |
| §2 `sparkforge/workload/` | 3, 4 |
| §3.1 mecanismo próprio, não extrator | 3 |
| §3.2 escala do histórico do job | 4 |
| §3.3 `declared` nunca vira `measured` | 3, 4, 6 |
| §3.4 shuffle medido antes de classificado | 1 |
| §3.5 `unknown` em vez de default | 3, 4 |
| §4.1 `spark.stage.shuffle` | 1 |
| §4.2 `workload.declared` | 2 |
| §4.3 `Axis` e `WorkloadFingerprint` | 3, 4 |
| §5 verbo de topo e tool | 5 |
| §6 erros, cada um com o seu nome | 2, 4 |
| §7.1 domínio de fixture e módulo golden | 6 |
| §7.2 as duas garantias sobre o corpus | 6 |
| §8 documentação | 7 |
| §9 critérios de aceite 1–6 | 1, 2, 4, 6 |
| §9 critério de aceite 7 (os cinco gates) | 5, 6, 7 |
