# Capacity optimizer — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Escolher, entre as capacidades que o job realmente rodou, a mais barata que cumpre o SLA — contando só os runs comparáveis ao de hoje, e recusando quando a evidência não sustenta a afirmação.

**Architecture:** Mecanismo próprio em `sparkforge/capacity/`, no molde do `WorkloadFingerprint`: escolher capacidade é juízo, e fact não julga. Consome facts já extraídos — `glue.job_run` (duração, capacidade e DPU por run), `spark.sql.scan` (volume por run) e `workload.declared` (SLA e alvo). Verbo de topo `sparkforge capacity`, pela mesma regra de `benchmark`, `fuse` e `workload`.

**Tech Stack:** Python 3, `pytest`, `PyYAML`. Spec: [`../specs/2026-08-28-capacity-sla-optimizer-design.md`](../specs/2026-08-28-capacity-sla-optimizer-design.md).

**Convenções do repositório que valem em toda tarefa:**

- O `CapacityPlan` **não é fact** — é onde o limiar mora. Nada aqui entra em `sparkforge/facts/`.
- Nenhum caminho do código aplica a mudança. §34 do documento de origem classifica troca de worker como `REVIEW`.
- Lint ruff `E,F,I,UP,B,S`, linha máxima 100.
- Todo comando com prefixo `rtk`. Commit em português, Conventional Commits, via `rtk git commit -F <arquivo>`. **Escreva a mensagem com heredoc para um arquivo** (`cat > /tmp/msg.txt <<'EOF' … EOF`), nunca com `printf` de string longa — `printf` com escapes produziu byte NUL e o commit foi recusado.
- Não rode a suíte inteira sem alvo (17 minutos), exceto onde a tarefa pedir.
- Não faça `git add` dos untracked pré-existentes na raiz. Cuidado com `git add .claude` — ele varre um `.bak`.

**Formato real dos facts que D consome** (medido em 2026-08-28, confira antes de usar):

```
glue.job_run
  subject   {type: job_run, job_name, job_run_id, symbol}
  attrs     {state, worker_type, glue_version, execution_class, autoscaling,
             started_on, completed_on, dpu_source}
  measures  {execution_time_s, number_of_workers, timeout_min, dpu_seconds}
            -- `dpu_seconds` AUSENTE quando B recusou derivar (autoscaling sem DPUSeconds)

spark.sql.scan
  measures  {bytes_read, files_read, ...}   -- so o que a execucao publicou

workload.declared
  subject   {type: job_run, symbol: <nome do job>}
  measures  {sla_minutes}
  attrs     {primary_source}
```

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/capacity/__init__.py` | Export de `Candidate`, `CapacityPlan`, `build_capacity_plan` |
| `sparkforge/capacity/plan.py` | O modelo e a escolha |
| `tests/test_capacity_plan.py` | Testes do modelo e da escolha |
| `tests/test_fixtures_golden_capacity.py` | Módulo golden do domínio novo |
| `fixtures/capacity/` | Seis cenários sintéticos |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/facts/workload.py` | `reliability_target` e `volume_tolerance` no inventário |
| `tests/test_facts_workload.py` | Casos dos dois campos novos |
| `sparkforge/adapters/_core.py` | `capacity_plan` |
| `sparkforge/adapters/cli.py` | Verbo de topo `capacity` |
| `sparkforge/adapters/tools.py` | `sparkforge_capacity` |
| `manifest.json`, `parity.yaml` | A tool nova |
| `agents/` | Citar a tool, senão o gate de órfão reprova |
| `README.md`, `docs/superpowers/STATUS.md` | O verbo, a fase, e os números medidos |

---

## Task 1: O inventário ganha o alvo e a tolerância

**Files:**
- Modify: `sparkforge/facts/workload.py`
- Test: `tests/test_facts_workload.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_facts_workload.py`:

```python
class TestAlvoETolerancia:
    def test_declares_reliability_target_and_volume_tolerance(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {
                "jobs": [
                    {
                        "name": "etl-pedidos",
                        "sla_minutes": 45,
                        "reliability_target": 0.95,
                        "volume_tolerance": 0.25,
                    }
                ]
            },
        )

        declarado = [
            f for f in extract_workload_path(alvo) if f.kind == "workload.declared"
        ][0]

        assert declarado.measures["reliability_target"] == 0.95
        assert declarado.measures["volume_tolerance"] == 0.25

    def test_absent_fields_are_absent_not_defaulted(self, tmp_path):
        alvo = _inventario(tmp_path, {"jobs": [{"name": "etl", "sla_minutes": 45}]})

        declarado = [
            f for f in extract_workload_path(alvo) if f.kind == "workload.declared"
        ][0]

        # O default e decisao de quem CONSOME a declaracao, nao do extrator.
        # Um fact que inventa 0.95 nao distingue "o operador escolheu 95%" de
        # "ninguem escolheu nada".
        assert "reliability_target" not in declarado.measures
        assert "volume_tolerance" not in declarado.measures

    def test_target_outside_zero_to_one_is_unresolved(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {"jobs": [{"name": "etl", "sla_minutes": 45, "reliability_target": 95}]},
        )
        facts = extract_workload_path(alvo)

        lacunas = [
            f
            for f in facts
            if f.kind == "workload.unresolved"
            and f.attrs["reason"] == "reliability_target_out_of_range"
        ]
        declarado = [f for f in facts if f.kind == "workload.declared"][0]

        # 95 quase certamente quis dizer 0,95. Aceitar produziria um alvo que
        # nenhuma capacidade cumpre, e a recusa nomeia o engano.
        assert len(lacunas) == 1
        assert "reliability_target" not in declarado.measures

    def test_negative_tolerance_is_unresolved(self, tmp_path):
        alvo = _inventario(
            tmp_path,
            {"jobs": [{"name": "etl", "sla_minutes": 45, "volume_tolerance": -0.1}]},
        )
        facts = extract_workload_path(alvo)

        assert [
            f.attrs["reason"]
            for f in facts
            if f.kind == "workload.unresolved"
        ] == ["volume_tolerance_out_of_range"]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_workload.py::TestAlvoETolerancia -v
```

Esperado: FAIL — os dois campos não são lidos.

- [ ] **Step 3: Implementar**

Em `extract_workload`, junto de onde `sla_minutes` é lido, acrescente os dois campos com validação de faixa. **Cuidado com `bool`**: ele é subclasse de `int` em Python, e a leitura de `sla_minutes` já trata isso — repita o cuidado.

```python
        alvo = entrada.get("reliability_target")
        if alvo is not None:
            if isinstance(alvo, bool) or not isinstance(alvo, int | float):
                facts.append(
                    _unresolved(
                        path,
                        "reliability_target_out_of_range",
                        f"`reliability_target` precisa ser numero entre 0 e 1; veio {alvo!r}.",
                        job_name=nome,
                    )
                )
            elif not 0 < alvo <= 1:
                facts.append(
                    _unresolved(
                        path,
                        "reliability_target_out_of_range",
                        f"`reliability_target` veio {alvo}. E fracao entre 0 e 1 -- 95 quase "
                        f"certamente quis dizer 0.95, e aceitar produziria um alvo que "
                        f"capacidade nenhuma cumpre.",
                        job_name=nome,
                    )
                )
            else:
                measures["reliability_target"] = alvo

        tolerancia = entrada.get("volume_tolerance")
        if tolerancia is not None:
            if (
                isinstance(tolerancia, bool)
                or not isinstance(tolerancia, int | float)
                or tolerancia < 0
            ):
                facts.append(
                    _unresolved(
                        path,
                        "volume_tolerance_out_of_range",
                        f"`volume_tolerance` precisa ser fracao nao negativa; veio "
                        f"{tolerancia!r}.",
                        job_name=nome,
                    )
                )
            else:
                measures["volume_tolerance"] = tolerancia
```

Ausência continua sendo ausência: o default é decisão de quem consome.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_workload.py -v
```

Esperado: PASS. Reporte a contagem real.

- [ ] **Step 5: Conferir o golden de workload**

```bash
rtk pytest tests/test_fixtures_golden_workload.py -v
```

Se algum `workload.yaml` de fixture ganhar campo, o golden muda — mas esta tarefa não muda fixture nenhuma, então o esperado é PASS sem mudança. Se mudar, investigue antes de regravar.

- [ ] **Step 6: Commit**

```bash
rtk git add sparkforge/facts/workload.py tests/test_facts_workload.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): alvo de confiabilidade e tolerancia de volume no inventario`

---

## Task 2: O candidato e a escolha

**Files:**
- Create: `sparkforge/capacity/__init__.py`, `sparkforge/capacity/plan.py`
- Test: `tests/test_capacity_plan.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_capacity_plan.py`:

```python
"""Testes da escolha de capacidade sob restricao de SLA."""
from __future__ import annotations

from sparkforge.capacity import build_capacity_plan
from sparkforge.findings.models import Fact


def _run(run_id, segundos, worker="G.2X", workers=10, dpu=1000.0, autoscaling=False):
    measures = {"execution_time_s": segundos, "number_of_workers": workers}
    if dpu is not None:
        measures["dpu_seconds"] = dpu
    return Fact(
        kind="glue.job_run",
        subject={
            "type": "job_run",
            "job_name": "etl",
            "job_run_id": run_id,
            "symbol": run_id,
        },
        measures=measures,
        attrs={
            "state": "SUCCEEDED",
            "worker_type": worker,
            "glue_version": "5.0",
            "autoscaling": autoscaling,
            "dpu_source": "derived",
        },
    )


def _scan(bytes_read):
    return Fact(
        kind="spark.sql.scan",
        subject={
            "type": "plan_node",
            "node_id": 1,
            "operator": "Scan parquet",
            "relation": "db.pedidos",
            "symbol": "0:1",
            "execution_id": 0,
        },
        measures={"bytes_read": bytes_read},
        attrs={"format": "parquet", "scan_api": "v1", "node_name": "Scan parquet"},
    )


def _declarado(sla=10, alvo=0.9, tolerancia=0.25):
    measures = {"sla_minutes": sla}
    if alvo is not None:
        measures["reliability_target"] = alvo
    if tolerancia is not None:
        measures["volume_tolerance"] = tolerancia
    return Fact(
        kind="workload.declared",
        subject={"type": "job_run", "symbol": "etl"},
        measures=measures,
    )


def _historico(*runs):
    """Cada elemento e o conjunto de facts de UM run anterior."""
    return list(runs)


class TestEscolha:
    def _tres_capacidades(self, volume=1000):
        """G.1X x10 estoura o SLA; G.2X x10 e G.2X x20 cabem."""
        historico = []
        for i in range(10):
            historico.append(
                [_run(f"a{i}", 900, worker="G.1X", workers=10, dpu=900.0), _scan(volume)]
            )
        for i in range(10):
            historico.append(
                [_run(f"b{i}", 500, worker="G.2X", workers=10, dpu=1000.0), _scan(volume)]
            )
        for i in range(10):
            historico.append(
                [_run(f"c{i}", 200, worker="G.2X", workers=20, dpu=2000.0), _scan(volume)]
            )
        return historico

    def test_chooses_the_cheapest_that_fits_not_the_fastest(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )

        # G.2X x20 e o mais rapido e o mais caro. A escolha certa e o do meio.
        assert plano.chosen is not None
        assert plano.chosen.worker_type == "G.2X"
        assert plano.chosen.number_of_workers == 10

    def test_candidates_are_ordered_by_cost(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )
        custos = [c.dpu_seconds_p95 for c in plano.candidates]

        assert custos == sorted(custos)

    def test_the_capacity_that_misses_the_sla_is_never_chosen(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )
        estourou = [c for c in plano.candidates if c.worker_type == "G.1X"][0]

        assert estourou.meets_sla is False
        assert plano.chosen is not estourou

    def test_when_nothing_fits_it_refuses_instead_of_picking_the_least_bad(self):
        plano = build_capacity_plan(
            [_declarado(sla=1), _scan(1000)],
            history=self._tres_capacidades(),
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.chosen is None
        assert len(plano.candidates) == 3
        assert all(c.meets_sla is False for c in plano.candidates)


class TestResolucao:
    def test_a_target_finer_than_the_evidence_is_refused(self):
        historico = [
            [_run(f"b{i}", 500, dpu=1000.0), _scan(1000)] for i in range(28)
        ]
        plano = build_capacity_plan(
            [_declarado(alvo=0.99), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )
        candidato = plano.candidates[0]

        # 1/28 = 3,6%. Afirmar 99% exigiria distinguir 1%.
        assert candidato.meets_sla is False
        assert plano.chosen is None
        recusa = [r for r in plano.refused if r["reason"] == "resolution_too_coarse"][0]
        assert recusa["runs_comparable"] == 28
        assert recusa["runs_needed"] >= 100

    def test_the_same_history_fits_a_coarser_target(self):
        historico = [
            [_run(f"b{i}", 500, dpu=1000.0), _scan(1000)] for i in range(28)
        ]
        plano = build_capacity_plan(
            [_declarado(alvo=0.9), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.chosen is not None


class TestComparabilidade:
    def test_only_runs_within_the_volume_tolerance_are_counted(self):
        # 20 runs de dia pequeno, todos rapidos; 5 de dia grande, todos lentos.
        historico = [[_run(f"p{i}", 100, dpu=1000.0), _scan(100)] for i in range(20)]
        historico += [[_run(f"g{i}", 900, dpu=1000.0), _scan(1000)] for i in range(5)]

        plano = build_capacity_plan(
            [_declarado(sla=10, alvo=0.8), _scan(1000)],  # hoje e dia GRANDE
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )
        candidato = plano.candidates[0]

        # Os 20 dias pequenos estao fora da faixa de 1000 +/- 25%.
        assert candidato.runs_total == 25
        assert candidato.runs_comparable == 5

    def test_the_volume_filter_can_flip_the_answer(self):
        historico = [[_run(f"p{i}", 100, dpu=1000.0), _scan(100)] for i in range(20)]
        historico += [[_run(f"g{i}", 900, dpu=1000.0), _scan(1000)] for i in range(5)]

        # SLA de 5 min: os dias pequenos cabem, os grandes nao.
        grande = build_capacity_plan(
            [_declarado(sla=5, alvo=0.8), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )
        pequeno = build_capacity_plan(
            [_declarado(sla=5, alvo=0.8), _scan(100)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert pequeno.chosen is not None
        assert grande.chosen is None

    def test_a_run_without_measured_volume_is_discarded_and_counted(self):
        historico = [[_run(f"b{i}", 500, dpu=1000.0), _scan(1000)] for i in range(10)]
        historico += [[_run("sem_scan", 500, dpu=1000.0)] for _ in range(1)]

        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.discarded_runs["volume_unknown"] == 1


class TestCusto:
    def test_capacity_without_measured_dpu_is_refused_not_ranked(self):
        historico = [
            [_run(f"a{i}", 100, worker="G.2X", workers=10, dpu=1000.0), _scan(1000)]
            for i in range(10)
        ]
        historico += [
            [
                _run(f"s{i}", 100, worker="G.2X", workers=10, dpu=None, autoscaling=True),
                _scan(1000),
            ]
            for i in range(10)
        ]

        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert [r["reason"] for r in plano.refused] == ["cost_unobservable"]
        assert all(c.autoscaling is False for c in plano.candidates)


class TestSemLastro:
    def test_without_a_declaration_the_plan_is_unknown(self):
        plano = build_capacity_plan(
            [_scan(1000)],
            history=[[_run("a", 100), _scan(1000)]],
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert plano.chosen is None
        assert plano.sla_minutes is None
        assert any(r["reason"] == "sla_not_declared" for r in plano.refused)

    def test_a_single_observed_capacity_says_there_is_nothing_to_compare(self):
        historico = [[_run(f"b{i}", 100, dpu=1000.0), _scan(1000)] for i in range(10)]
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=historico,
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert len(plano.candidates) == 1
        assert plano.chosen is not None
        assert plano.only_one_capacity_observed is True


class TestSeguranca:
    def test_every_candidate_is_review_and_nothing_applies(self):
        plano = build_capacity_plan(
            [_declarado(), _scan(1000)],
            history=[[_run(f"b{i}", 100, dpu=1000.0), _scan(1000)] for i in range(10)],
            job_name="etl",
            job_run_id="jr_hoje",
        )

        assert all(c.safety == "REVIEW" for c in plano.candidates)
        assert not hasattr(plano, "apply")
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_capacity_plan.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.capacity'`.

- [ ] **Step 3: Implementar**

`sparkforge/capacity/plan.py`:

```python
"""Escolha de capacidade sob restricao de SLA.

MINIMIZE dpu_seconds  sujeito a  P(runtime <= SLA) >= reliability_target.

Entre as capacidades que cumprem o SLA, escolhe a mais BARATA -- nao a mais
rapida. Uma capacidade que corre em 3 minutos quando o SLA e 15 nao esta
ganhando nada; esta gastando.

TRES RECUSAS SUSTENTAM TUDO O QUE ESTE MODULO AFIRMA:

  1. So capacidade OBSERVADA entra. Extrapolar para uma nunca rodada exigiria
     uma lei de escala que fonte nenhuma publica, e o numero inventado
     escolheria quanto alguem gasta.
  2. So run COMPARAVEL conta. O historico mistura dias grandes e pequenos, e
     uma capacidade pode ter cumprido o SLA porque a maioria dos runs foi de
     dia pequeno.
  3. A RESOLUCAO e declarada. Com n runs a estimativa nao distingue nada mais
     fino que 1/n; alvo mais fino que isso e recusa, nao aprovacao.

NAO e um extrator, e nada aqui vira Fact: escolher capacidade e juizo, e fact
nao julga. Mesmo molde do `WorkloadFingerprint`.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sparkforge.findings.models import Fact

# `worker change` e REVIEW na secao 34 do documento de origem, que diz para
# nunca aplicar REVIEW automaticamente em producao. Nao ha caminho neste
# modulo que aplique coisa alguma.
_SAFETY = "REVIEW"

_TOLERANCIA_PADRAO = 0.25
_ALVO_PADRAO = 0.95


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    """Percentil por nearest-rank, sem interpolacao: rank = ceil(pct/100 * n)."""
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


@dataclass(frozen=True)
class Candidate:
    glue_version: str
    worker_type: str
    number_of_workers: int
    autoscaling: bool
    runs_total: int
    runs_comparable: int
    runs_within_sla: int
    reliability: float
    resolution: float
    dpu_seconds_p95: float
    meets_sla: bool
    safety: str = _SAFETY

    def to_dict(self) -> dict[str, Any]:
        return {
            "glue_version": self.glue_version,
            "worker_type": self.worker_type,
            "number_of_workers": self.number_of_workers,
            "autoscaling": self.autoscaling,
            "runs_total": self.runs_total,
            "runs_comparable": self.runs_comparable,
            "runs_within_sla": self.runs_within_sla,
            "reliability": self.reliability,
            "resolution": self.resolution,
            "dpu_seconds_p95": self.dpu_seconds_p95,
            "meets_sla": self.meets_sla,
            "safety": self.safety,
        }


@dataclass(frozen=True)
class CapacityPlan:
    job_name: str
    job_run_id: str
    sla_minutes: float | None
    reliability_target: float | None
    volume_tolerance: float | None
    current_volume_bytes: int | None
    candidates: list[Candidate] = field(default_factory=list)
    chosen: Candidate | None = None
    refused: list[dict[str, Any]] = field(default_factory=list)
    discarded_runs: dict[str, int] = field(default_factory=dict)
    only_one_capacity_observed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "job_run_id": self.job_run_id,
            "sla_minutes": self.sla_minutes,
            "reliability_target": self.reliability_target,
            "volume_tolerance": self.volume_tolerance,
            "current_volume_bytes": self.current_volume_bytes,
            "candidates": [c.to_dict() for c in self.candidates],
            "chosen": self.chosen.to_dict() if self.chosen else None,
            "refused": self.refused,
            "discarded_runs": self.discarded_runs,
            "only_one_capacity_observed": self.only_one_capacity_observed,
        }


def _volume_de(facts: Sequence[Fact]) -> int | None:
    """Bytes varridos, somando os scans. `None` quando nenhum scan os publicou."""
    total = 0
    visto = False
    for fact in facts:
        if fact.kind != "spark.sql.scan":
            continue
        bytes_read = fact.measures.get("bytes_read")
        if bytes_read is None:
            continue
        visto = True
        total += int(bytes_read)
    return total if visto else None


def _capacidade_de(run: Fact) -> tuple[str, str, int, bool]:
    return (
        str(run.attrs.get("glue_version") or ""),
        str(run.attrs.get("worker_type") or ""),
        int(run.measures.get("number_of_workers") or 0),
        bool(run.attrs.get("autoscaling")),
    )


def build_capacity_plan(
    facts: Sequence[Fact],
    *,
    job_name: str,
    job_run_id: str,
    history: Sequence[Sequence[Fact]] = (),
) -> CapacityPlan:
    """Monta o plano. `history` e uma sequencia de conjuntos, UM POR RUN anterior."""
    declarados = [
        f
        for f in facts
        if f.kind == "workload.declared" and f.subject.get("symbol") == job_name
    ]
    declarado = declarados[0] if declarados else None

    sla_minutes = declarado.measures.get("sla_minutes") if declarado else None
    alvo = declarado.measures.get("reliability_target") if declarado else None
    tolerancia = declarado.measures.get("volume_tolerance") if declarado else None
    if alvo is None:
        alvo = _ALVO_PADRAO if declarado else None
    if tolerancia is None:
        tolerancia = _TOLERANCIA_PADRAO if declarado else None

    volume_atual = _volume_de(facts)
    descartados: dict[str, int] = {}
    recusas: list[dict[str, Any]] = []

    if sla_minutes is None:
        recusas.append(
            {
                "reason": "sla_not_declared",
                "detail": (
                    "Sem `sla_minutes` em workload.yaml para este job nao ha restricao a "
                    "satisfazer, e sem restricao a escolha e apenas a mais barata -- que "
                    "seria a recomendacao errada."
                ),
            }
        )
        return CapacityPlan(
            job_name=job_name,
            job_run_id=job_run_id,
            sla_minutes=None,
            reliability_target=alvo,
            volume_tolerance=tolerancia,
            current_volume_bytes=volume_atual,
            refused=recusas,
        )

    sla_segundos = float(sla_minutes) * 60.0

    # Agrupa os runs por capacidade, guardando duracao, dpu e volume de cada um.
    grupos: dict[tuple[str, str, int, bool], list[dict[str, Any]]] = {}
    for conjunto in history:
        runs = [f for f in conjunto if f.kind == "glue.job_run"]
        if len(runs) != 1:
            descartados["history_file_not_one_run"] = (
                descartados.get("history_file_not_one_run", 0) + 1
            )
            continue
        run = runs[0]
        duracao = run.measures.get("execution_time_s")
        if duracao is None:
            descartados["runtime_unknown"] = descartados.get("runtime_unknown", 0) + 1
            continue
        volume = _volume_de(conjunto)
        grupos.setdefault(_capacidade_de(run), []).append(
            {
                "duracao": float(duracao),
                "dpu": run.measures.get("dpu_seconds"),
                "volume": volume,
            }
        )

    candidatos: list[Candidate] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave

        comparaveis = []
        for membro in membros:
            if membro["volume"] is None:
                descartados["volume_unknown"] = descartados.get("volume_unknown", 0) + 1
                continue
            if volume_atual is None:
                comparaveis.append(membro)
                continue
            limite = volume_atual * float(tolerancia)
            if abs(membro["volume"] - volume_atual) <= limite:
                comparaveis.append(membro)

        if not comparaveis:
            recusas.append(
                {
                    "reason": "no_comparable_runs",
                    "capacity": f"{worker_type} x{workers}",
                    "runs_total": len(membros),
                    "detail": (
                        "Nenhum run desta capacidade tem volume dentro da tolerancia do run "
                        "corrente. A evidencia existe, mas nao se aplica a hoje."
                    ),
                }
            )
            continue

        custos = sorted(m["dpu"] for m in comparaveis if m["dpu"] is not None)
        if not custos:
            recusas.append(
                {
                    "reason": "cost_unobservable",
                    "capacity": f"{worker_type} x{workers}",
                    "runs_comparable": len(comparaveis),
                    "detail": (
                        "Nenhum run comparavel tem `dpu_seconds` medido. Sob Auto Scaling "
                        "sem DPUSeconds, `number_of_workers` e teto e nao uso, e o coletor "
                        "recusou derivar -- sem custo nao ha o que minimizar."
                    ),
                }
            )
            continue

        n = len(comparaveis)
        dentro = sum(1 for m in comparaveis if m["duracao"] <= sla_segundos)
        confiabilidade = dentro / n
        resolucao = 1.0 / n

        cabe = confiabilidade >= float(alvo)
        if cabe and resolucao > 1.0 - float(alvo):
            # A contagem diz que cabe, e a contagem nao tem resolucao para
            # sustentar a afirmacao. Recusa, nao aprovacao.
            cabe = False
            necessarios = math.ceil(1.0 / (1.0 - float(alvo))) if alvo < 1 else 0
            recusas.append(
                {
                    "reason": "resolution_too_coarse",
                    "capacity": f"{worker_type} x{workers}",
                    "runs_comparable": n,
                    "runs_needed": necessarios,
                    "detail": (
                        f"Com {n} runs comparaveis a menor diferenca observavel e "
                        f"{resolucao:.1%}, e o alvo de {float(alvo):.1%} exige distinguir "
                        f"{1 - float(alvo):.1%}. Sao precisos ao menos {necessarios} runs."
                    ),
                }
            )

        candidatos.append(
            Candidate(
                glue_version=glue_version,
                worker_type=worker_type,
                number_of_workers=workers,
                autoscaling=autoscaling,
                runs_total=len(membros),
                runs_comparable=n,
                runs_within_sla=dentro,
                reliability=confiabilidade,
                resolution=resolucao,
                dpu_seconds_p95=_nearest_rank(custos, 95),
                meets_sla=cabe,
            )
        )

    candidatos.sort(key=lambda c: (c.dpu_seconds_p95, c.worker_type, c.number_of_workers))
    escolhido = next((c for c in candidatos if c.meets_sla), None)

    return CapacityPlan(
        job_name=job_name,
        job_run_id=job_run_id,
        sla_minutes=float(sla_minutes),
        reliability_target=float(alvo),
        volume_tolerance=float(tolerancia),
        current_volume_bytes=volume_atual,
        candidates=candidatos,
        chosen=escolhido,
        refused=recusas,
        discarded_runs=descartados,
        only_one_capacity_observed=len(grupos) == 1,
    )
```

`sparkforge/capacity/__init__.py`:

```python
"""Escolha de capacidade sob restricao de SLA.

NAO e um extrator. Escolher capacidade e juizo, e fact nao julga -- mesmo
molde de `sparkforge/workload/`. Toda recomendacao nasce `REVIEW`, e nada
neste pacote aplica mudanca nenhuma.
"""
from sparkforge.capacity.plan import Candidate, CapacityPlan, build_capacity_plan

__all__ = ["Candidate", "CapacityPlan", "build_capacity_plan"]
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_capacity_plan.py -v
```

Esperado: PASS. Reporte a contagem real.

**Se `test_a_target_finer_than_the_evidence_is_refused` falhar na conta de `runs_needed`:** a fórmula é o menor `n` tal que `1/n <= 1 − alvo`, ou seja `ceil(1 / (1 − alvo))`. Para alvo 0,99 isso é 100. Ajuste até a asserção passar; ela é o contrato.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/capacity tests/test_capacity_plan.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(capacity): a mais barata que cabe, entre as capacidades observadas`

---

## Task 3: Superfície — verbo de topo e tool

**Files:**
- Modify: `sparkforge/adapters/_core.py`, `cli.py`, `tools.py`, `manifest.json`, `parity.yaml`, um arquivo de `agents/`
- Test: `tests/test_adapters_cli.py`, `tests/test_adapters_tools.py`

- [ ] **Step 1: Escrever o teste que falha**

Acrescente a `tests/test_adapters_cli.py`:

```python
class TestCapacityCommand:
    def _fact(self, kind, subject, measures=None, attrs=None):
        return {
            "id": "0" * 16,
            "schema_version": 1,
            "kind": kind,
            "subject": subject,
            "measures": measures or {},
            "attrs": attrs or {},
            "provenance": {},
        }

    def _scan(self, bytes_read):
        return self._fact(
            "spark.sql.scan",
            {
                "type": "plan_node",
                "node_id": 1,
                "operator": "Scan parquet",
                "relation": "db.pedidos",
                "symbol": "0:1",
                "execution_id": 0,
            },
            {"bytes_read": bytes_read},
            {"format": "parquet", "scan_api": "v1", "node_name": "Scan parquet"},
        )

    def _run(self, run_id, segundos, workers, dpu):
        return self._fact(
            "glue.job_run",
            {
                "type": "job_run",
                "job_name": "etl",
                "job_run_id": run_id,
                "symbol": run_id,
            },
            {
                "execution_time_s": segundos,
                "number_of_workers": workers,
                "dpu_seconds": dpu,
            },
            {
                "state": "SUCCEEDED",
                "worker_type": "G.2X",
                "glue_version": "5.0",
                "autoscaling": False,
                "dpu_source": "derived",
            },
        )

    def _monta(self, tmp_path):
        facts = tmp_path / "facts.json"
        facts.write_text(
            json.dumps(
                [
                    self._fact(
                        "workload.declared",
                        {"type": "job_run", "symbol": "etl"},
                        {"sla_minutes": 10, "reliability_target": 0.8},
                    ),
                    self._scan(1000),
                ]
            ),
            encoding="utf-8",
        )
        historico = tmp_path / "history"
        historico.mkdir()
        for i in range(6):
            (historico / f"barato{i}.json").write_text(
                json.dumps([self._run(f"b{i}", 500, 10, 1000.0), self._scan(1000)]),
                encoding="utf-8",
            )
        for i in range(6):
            (historico / f"caro{i}.json").write_text(
                json.dumps([self._run(f"c{i}", 200, 20, 2000.0), self._scan(1000)]),
                encoding="utf-8",
            )
        return facts, historico

    def test_capacity_is_a_top_level_verb(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        facts, historico = self._monta(tmp_path)
        code = main(
            [
                "capacity",
                "--facts",
                str(facts),
                "--job-name",
                "etl",
                "--job-run",
                "jr_hoje",
                "--history",
                str(historico),
            ]
        )

        assert code == 0
        payload = json.loads(capsys.readouterr().out)
        assert len(payload["candidates"]) == 2
        # As duas cabem no SLA de 10 min; a escolha e a mais barata.
        assert payload["chosen"]["number_of_workers"] == 10
        assert payload["chosen"]["safety"] == "REVIEW"

    def test_out_file_carries_the_whole_plan(self, tmp_path, capsys):
        from sparkforge.adapters.cli import main

        facts, historico = self._monta(tmp_path)
        out = tmp_path / "plan.json"
        code = main(
            [
                "capacity",
                "--facts",
                str(facts),
                "--job-name",
                "etl",
                "--job-run",
                "jr_hoje",
                "--history",
                str(historico),
                "--out",
                str(out),
            ]
        )

        assert code == 0
        plano = json.loads(out.read_text(encoding="utf-8"))
        assert plano["job_run_id"] == "jr_hoje"
        assert plano["reliability_target"] == 0.8
```

E a `tests/test_adapters_tools.py`:

```python
class TestCapacityTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_capacity" in tools.TOOLS
        assert "sparkforge_capacity" in tools._HANDLERS
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_cli.py::TestCapacityCommand tests/test_adapters_tools.py::TestCapacityTool -v
```

Esperado: FAIL — `SystemExit: 2` e `AssertionError`.

- [ ] **Step 3: Implementar**

Leia `_core.workload_fingerprint` — ele é o molde exato, inclusive no carregamento do diretório de histórico (um `_load_facts_file` por arquivo `*.json`, cada arquivo virando um elemento de `history`).

```python
from sparkforge.capacity import build_capacity_plan

_FACTS_FROM_RUN_AND_SCAN = (
    "por run anterior: sparkforge analyze glue-job-runs --path <dir> --job-name <job> "
    "--out {path}\n"
    "    e sparkforge analyze sql-metrics --path <event-log-do-run>.jsonl --out {path}"
)


def capacity_plan(
    facts_path: str,
    job_name: str,
    job_run_id: str,
    history_path: str = "",
) -> dict[str, Any]:
    """Escolhe a capacidade mais barata que cumpre o SLA, entre as observadas.

    Verbo de TOPO, e nao `analyze capacity`, pela mesma razao de `benchmark`,
    `fuse` e `workload`: nao extrai nada de artefato -- decide sobre o que
    outros verbos ja extrairam.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_RUN_AND_SCAN, "--facts")
    historico = _load_facts_dir(history_path, _FACTS_FROM_RUN_AND_SCAN, "--history")
    plano = build_capacity_plan(
        facts, job_name=job_name, job_run_id=job_run_id, history=historico
    )
    return plano.to_dict()
```

Se `_load_facts_dir` ainda não existir, o `workload_fingerprint` já faz esse carregamento inline — extraia-o para um helper compartilhado e faça os dois usarem, ou replique a forma. Diga no relatório qual escolheu.

Parser, handler e despacho em `cli.py`, e a tool em `tools.py`, no molde de `workload`. Os parâmetros de caminho da tool terminam em `_path`, como o resto do catálogo, senão `test_harness_authorization` acusa.

- [ ] **Step 4: Manifesto, paridade e o gate de órfão**

- `manifest.json`, lista `tools`: `sparkforge_capacity`, em ordem alfabética.
- `parity.yaml`: a capability que lista `workload` ganha `sparkforge_capacity` e `capacity`.
- `agents/`: cite a tool onde `sparkforge_workload` já aparece, dizendo **por que** ela existe — o perfil descreve, esta escolhe, e a escolha é `REVIEW`.

```bash
rtk python scripts/sync_skills.py
rtk pytest tests/test_adapters_cli.py tests/test_adapters_tools.py tests/test_adapters_mcp.py tests/test_capability_parity.py tests/test_canonical_registry.py tests/test_agent_coverage.py tests/test_arvore_versionada.py tests/test_harness_authorization.py -q
```

A contagem fixa de tools com caminho sobe em um. Atualize e relate.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/adapters manifest.json parity.yaml tests agents .claude .agents .github
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(cli): verbo capacity e a tool da escolha sob SLA`

---

## Task 4: Fixtures golden

**Files:**
- Create: `fixtures/capacity/` (seis cenários), `tests/test_fixtures_golden_capacity.py`
- Modify: `tests/test_fixtures_kind_coverage.py` se ele cobrar o domínio novo

- [ ] **Step 1: Criar os cenários**

Leia `fixtures/workload/` para a forma — é o domínio mais parecido, porque também consome facts em vez de artefato bruto. Cada cenário tem `input/facts.json`, `input/history/<run>.json` (um por run), `meta.yaml` e `expected/plan.json`.

| Cenário | Prova |
|---|---|
| `cheapest_that_fits` | o exemplo do §18: três capacidades, duas cabem, escolhe a mais barata |
| `none_fits` | `chosen: None`, com o quanto cada uma erra |
| `resolution_too_coarse` | alvo de 99% com poucos runs: recusa, não aprovação frágil |
| `volume_filter_changes_the_answer` | a capacidade que ganharia com o histórico inteiro perde ao comparar só o comparável |
| `autoscaling_without_cost` | capacidade sem custo observável sai da comparação |
| `single_capacity_observed` | sem alternativa, e o plano diz isso |

Nada de nome, número ou particularidade de ambiente real.

- [ ] **Step 2: O módulo golden e as três garantias**

`tests/test_fixtures_golden_capacity.py`, com `FIXTURES = ROOT / "fixtures" / "capacity"`, no molde de `tests/test_fixtures_golden_workload.py`. Além dos goldens byte-exatos:

```python
class TestOQueOCorpusInteiroGarante:
    def test_never_chooses_a_costlier_candidate_that_also_fits(self):
        """O objetivo do paragrafo 18: a mais barata que cabe.

        Um erro de ordenacao passaria em cada cenario isolado.
        """
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            if plano["chosen"] is None:
                continue
            cabem = [c for c in plano["candidates"] if c["meets_sla"]]
            assert plano["chosen"]["dpu_seconds_p95"] == min(
                c["dpu_seconds_p95"] for c in cabem
            ), directory.name

    def test_never_chooses_a_candidate_that_misses_the_sla(self):
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            if plano["chosen"] is not None:
                assert plano["chosen"]["meets_sla"] is True, directory.name

    def test_every_approved_candidate_has_the_resolution_to_say_so(self):
        """A garantia que separa "medimos que cabe" de "nao temos como saber"."""
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            alvo = plano["reliability_target"]
            if alvo is None:
                continue
            for candidato in plano["candidates"]:
                if candidato["meets_sla"]:
                    assert candidato["resolution"] <= 1 - alvo, (
                        directory.name,
                        candidato,
                    )

    def test_no_candidate_is_ever_anything_but_review(self):
        for directory in fixture_dirs():
            plano = run_fixture(directory)
            for candidato in plano["candidates"]:
                assert candidato["safety"] == "REVIEW", directory.name
```

- [ ] **Step 3: Rodar**

```bash
rtk pytest tests/test_fixtures_golden_capacity.py tests/test_fixtures_kind_coverage.py -q
```

Grave os goldens com a saída real e **leia** cada um antes de commitar.

- [ ] **Step 4: Commit**

```bash
rtk git add fixtures/capacity tests
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `test(fixtures): seis cenarios de escolha de capacidade sob SLA`

---

## Task 5: Documentação e os gates

**Files:**
- Modify: `README.md`, `docs/superpowers/STATUS.md`, possivelmente `docs/harness/*.md` e `docs/claims.lock.json`

- [ ] **Step 1: Rodar a suíte inteira**

```bash
rtk pytest -q
```

- [ ] **Step 2: README**

O verbo novo junto de `benchmark`, `fuse` e `workload`. Atualize os números de extratores e kinds, **medidos** — e confira os **dois** lugares do README que citam contagem de kinds.

- [ ] **Step 3: STATUS**

A fase, com: o pacote `sparkforge/capacity/`, o verbo e a tool, os dois campos novos do inventário, o número de testes acrescentados (meça), a faixa de commits, a referência à spec, e:

- as quatro decisões (só observadas, DPU-segundos e não moeda, resolução declarada, só runs comparáveis);
- que **nenhum caminho do código aplica a mudança**, e que todo candidato nasce `REVIEW` por §34;
- o que ficou de fora: custo em moeda (é E), capacidade nunca observada, recomendação de conf do Spark, canary.

- [ ] **Step 4: Gate de números**

```bash
rtk python scripts/check_vnext_claims.py
rtk pytest tests/test_docs_coverage.py -q
```

Itere até `0 divergencia(s).`

- [ ] **Step 5: Commit e prova final**

```bash
rtk git add README.md docs/superpowers/STATUS.md docs/claims.lock.json docs/harness docs/vnext
rtk git commit -F <arquivo com a mensagem>
rtk pytest -q
```

Mensagem: `docs: o verbo capacity, a fase e o que ficou de fora`

Esperado: 0 failed.

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §2 `reliability_target` e `volume_tolerance` no inventário | 1 |
| §3.1 só capacidades observadas | 2 |
| §3.2 custo em DPU-segundos, sobre os comparáveis | 2 |
| §3.3 confiabilidade contada, resolução declarada | 2 |
| §3.4 só runs comparáveis | 2 |
| §3.5 contrato de `--history` | 2, 3 |
| §3.6 tudo nasce `REVIEW` | 2, 4 |
| §4 `Candidate` e `CapacityPlan` | 2 |
| §5 verbo de topo e tool | 3 |
| §6 erros, cada um com o seu nome | 1, 2 |
| §7.1 domínio de fixture e módulo golden | 4 |
| §7.2 as três garantias sobre o corpus | 4 |
| §8 documentação | 5 |
| §9 critérios de aceite 1–7 | 2, 4 |
| §9 critério de aceite 8 | 3, 4, 5 |
