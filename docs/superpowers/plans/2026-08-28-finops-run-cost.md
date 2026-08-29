# FinOps — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reunir tudo o que é financeiro num lugar só — quanto custou, se mais recurso por menos tempo sai mais barato, quanto custa por desfecho que serve, e onde a alavanca está: capacidade ou código.

**Architecture:** Um fact novo (`glue.run_cost`, no precedente do DPU derivado que B estabeleceu) e um verbo de topo `sparkforge finops` que compõe: a fronteira custo-versus-tempo entre capacidades observadas, o custo por desfecho de SLA, os sintomas ao lado, e a separação das alavancas. Nada aqui atribui custo a causa.

**Tech Stack:** Python 3, `pytest`. Spec: [`../specs/2026-08-28-finops-run-cost-design.md`](../specs/2026-08-28-finops-run-cost-design.md).

**Convenções do repositório que valem em toda tarefa:**

- Lint ruff `E,F,I,UP,B,S`, linha máxima 100 (config do `pyproject.toml`).
- Todo comando com prefixo `rtk`. Commit em português, Conventional Commits, via `rtk git commit -F <arquivo>`. **Mensagem via heredoc para um arquivo** (`cat > /tmp/msg.txt <<'EOF' … EOF`), nunca `printf` de string longa — já produziu byte NUL e o commit foi recusado.
- Não rode a suíte inteira sem alvo (17 minutos), exceto onde a tarefa pedir.
- Não faça `git add` dos untracked pré-existentes na raiz. Cuidado com `git add .claude` — ele varre um `.bak`.
- Módulo golden novo **tem** que chamar `validate_fact`. Foi a ausência disso que deixou oito kinds inválidos passarem numa entrega anterior.

**APIs reais que este plano consome** (medidas em 2026-08-28):

```
sparkforge.facts.pricing.prices(runtime_version=None) -> list[dict]
  cada entrada: {value: "0.44" (STRING), currency, region, runtime_version,
                 source, source_type, retrieved, note}
  `region` e `runtime_version` valem "UNQUALIFIED" hoje.

glue.job_run   measures {execution_time_s, number_of_workers, timeout_min, dpu_seconds}
               attrs    {state, worker_type, glue_version, autoscaling, dpu_source, ...}
               `dpu_seconds` AUSENTE quando o coletor recusou derivar.

Finding        campos: rule_id, title, severity, confidence, status, subject,
                       evidence, measured, threshold, runtime_scope, explanation,
                       proposed_change, expected_effect, benchmark_ref, risks,
                       tradeoffs, validation, rollback, sources, catalog_version,
                       schema_version

sparkforge.capacity.plan.resolution_supports(resolution, target) -> bool
sparkforge.adapters._core._load_facts_file / _load_facts_dir
```

---

## Estrutura de arquivos

**Criar:**

| Arquivo | Responsabilidade |
|---|---|
| `sparkforge/facts/run_cost.py` | O fact `glue.run_cost` e o `glue.run_cost.unresolved` |
| `sparkforge/finops/__init__.py` | Export de `build_finops_report` |
| `sparkforge/finops/report.py` | Fronteira, custo por desfecho, sintomas e alavancas |
| `tests/test_facts_run_cost.py` | Testes do fact |
| `tests/test_finops_report.py` | Testes do relatório |
| `tests/test_fixtures_golden_finops.py` | Módulo golden do domínio novo |
| `fixtures/finops/` | Nove cenários |

**Modificar:**

| Arquivo | Mudança |
|---|---|
| `sparkforge/adapters/_core.py`, `cli.py`, `tools.py` | Verbo de topo `finops` e a tool |
| `manifest.json`, `parity.yaml`, `agents/` | A tool nova |
| `tests/test_fixtures_kind_coverage.py`, `tests/test_rules_catalog_reachability.py` | Registrar `run_cost` nas DUAS listas |
| `README.md`, `docs/superpowers/STATUS.md` | O verbo, a fase, e os números medidos |

---

## Task 1: O fact de custo

**Files:**
- Create: `sparkforge/facts/run_cost.py`
- Test: `tests/test_facts_run_cost.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_facts_run_cost.py`:

```python
"""Testes do fact de custo por run."""
from __future__ import annotations

import pytest

from sparkforge.facts.run_cost import extract_run_cost
from sparkforge.findings.models import Fact


def _run(run_id="jr_1", dpu=3600.0, dpu_source="derived"):
    measures = {"execution_time_s": 600, "number_of_workers": 10}
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
            "worker_type": "G.2X",
            "glue_version": "5.0",
            "autoscaling": False,
            "dpu_source": dpu_source,
        },
    )


class TestCusto:
    def test_cost_is_dpu_hours_times_the_published_price(self):
        # 3600 DPU-s = 1 DPU-hora. Ao preco publicado de 0.44, custo 0.44.
        facts = extract_run_cost([_run(dpu=3600.0)], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        assert custo.measures["dpu_hours"] == 1.0
        assert custo.measures["cost"] == pytest.approx(0.44)
        assert custo.measures["dpu_seconds"] == 3600.0

    def test_the_formula_is_the_one_aws_publishes(self):
        # A propria pagina de preco traz: 6 DPU * 0.25 h * 0.44 = 0.66.
        facts = extract_run_cost([_run(dpu=6 * 0.25 * 3600)], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        assert custo.measures["cost"] == pytest.approx(0.66)

    def test_both_caveats_travel_inside_the_fact(self):
        facts = extract_run_cost([_run()], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        # Regiao E versao de runtime. Uma ressalva que fica so no relatorio
        # se perde no primeiro salto.
        assert custo.attrs["region"] == "UNQUALIFIED"
        assert custo.attrs["runtime_version"] == "UNQUALIFIED"
        assert custo.attrs["price_source"].startswith("http")
        assert custo.attrs["price_retrieved"]
        assert custo.attrs["currency"] == "USD"

    def test_dpu_source_is_carried_from_the_run(self):
        derivado = extract_run_cost([_run(dpu_source="derived")], "facts.json")
        observado = extract_run_cost([_run(dpu_source="observed")], "facts.json")

        # Custo sobre DPU derivado e uma derivacao sobre outra, e o leitor
        # precisa saber sem ir atras do fact de origem.
        assert [f for f in derivado if f.kind == "glue.run_cost"][0].attrs[
            "dpu_source"
        ] == "derived"
        assert [f for f in observado if f.kind == "glue.run_cost"][0].attrs[
            "dpu_source"
        ] == "observed"

    def test_the_formula_is_in_the_provenance(self):
        facts = extract_run_cost([_run()], "facts.json")
        custo = [f for f in facts if f.kind == "glue.run_cost"][0]

        assert "dpu_hours" in custo.provenance["formula"]


class TestRecusas:
    def test_a_run_without_dpu_produces_a_gap_never_a_zero(self):
        facts = extract_run_cost([_run(dpu=None)], "facts.json")

        assert not [f for f in facts if f.kind == "glue.run_cost"]
        lacunas = [f for f in facts if f.kind == "glue.run_cost.unresolved"]
        assert len(lacunas) == 1
        assert lacunas[0].attrs["reason"] == "dpu_seconds_unavailable"

    def test_a_price_table_that_does_not_load_is_a_gap(self, monkeypatch):
        from sparkforge.facts import run_cost

        def boom(*_args, **_kwargs):
            from sparkforge.facts.pricing import PricingError

            raise PricingError("tabela ausente")

        monkeypatch.setattr(run_cost, "prices", boom)
        facts = extract_run_cost([_run()], "facts.json")

        assert [f.attrs["reason"] for f in facts] == ["price_unavailable"]

    def test_two_prices_without_an_axis_is_ambiguous_not_a_guess(self, monkeypatch):
        from sparkforge.facts import run_cost

        entrada = {
            "value": "0.44",
            "currency": "USD",
            "region": "UNQUALIFIED",
            "runtime_version": "UNQUALIFIED",
            "source": "https://aws.amazon.com/glue/pricing/",
            "retrieved": "2026-08-23",
        }
        monkeypatch.setattr(
            run_cost, "prices", lambda *a, **k: [entrada, {**entrada, "value": "0.51"}]
        )
        facts = extract_run_cost([_run()], "facts.json")
        lacuna = [f for f in facts if f.kind == "glue.run_cost.unresolved"][0]

        # Escolher um dos dois seria escolher pelo operador.
        assert lacuna.attrs["reason"] == "price_ambiguous"
        assert "0.44" in lacuna.attrs["detail"]
        assert "0.51" in lacuna.attrs["detail"]


class TestSchema:
    def test_every_emitted_fact_validates(self):
        from sparkforge.findings.validate import validate_fact

        facts = extract_run_cost([_run(), _run("jr_2", dpu=None)], "facts.json")

        assert facts
        for fact in facts:
            validate_fact(fact.to_dict())
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_facts_run_cost.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.facts.run_cost'`.

- [ ] **Step 3: Implementar**

`sparkforge/facts/run_cost.py`:

```python
"""Custo em moeda por run, a partir do DPU medido e do preco publicado.

FORMA, E O PRECEDENTE QUE A JUSTIFICA. Isto e fact, e nao mecanismo, porque nao
ha limiar e nao ha juizo -- e aritmetica sobre um numero medido e uma constante
com fonte. `glue.job_run` ja carrega `dpu_seconds` derivado de um fator
documentado, com `dpu_source` nos attrs e a formula na proveniencia; custo tem
exatamente essa forma. Sendo fact, entra no motor de regras.

SOBRE `facts/pricing.py` NAO CALCULAR NADA. Aquele docstring proibe uma
combinacao especifica: preco publicado vezes o anuncio de reducao do Glue 6.0,
cujo produto seria um preco por versao que fonte nenhuma publica. Este modulo
NAO toca em `announcements`. Ele aplica o preco tal como publicado a uma
medicao, e carrega as duas ressalvas da fonte junto do numero.

AS DUAS RESSALVAS VIAJAM DENTRO DO FACT. `region` e `runtime_version` valem
`UNQUALIFIED` porque a fonte foi lida e nao qualificou nenhum dos dois eixos --
diferente de campo ausente, que diria que ninguem leu. Deixa-las no relatorio
em vez de no fact seria perde-las no primeiro salto: o fact vai para `--out`,
para a tool MCP, para o contexto de um agente.

Puro e deterministico: nunca aplica limiar, nunca atribui severidade, nunca
toca a rede.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.facts.pricing import PricingError, prices
from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "run_cost@0.1.0"

EMITTED_KINDS = frozenset({"glue.run_cost", "glue.run_cost.unresolved"})

_SEGUNDOS_POR_HORA = 3600.0
_FORMULA = "dpu_hours * price_per_dpu_hour, dpu_hours = dpu_seconds / 3600"


def _run_subject(run: Fact) -> dict[str, Any]:
    return {
        "type": "job_run",
        "symbol": str(run.subject.get("job_run_id") or run.subject.get("symbol") or ""),
        "job_name": str(run.subject.get("job_name") or ""),
        "job_run_id": str(run.subject.get("job_run_id") or ""),
    }


def _unresolved(run: Fact, reason: str, detail: str, path: str) -> Fact:
    return Fact(
        kind="glue.run_cost.unresolved",
        subject=_run_subject(run),
        attrs={"reason": reason, "detail": detail},
        provenance={"extractor": EXTRACTOR_ID, "artifact": path},
    )


def _preco() -> tuple[dict[str, Any] | None, str, str]:
    """Devolve `(entrada, reason, detail)`. Entrada `None` quando nao da."""
    try:
        candidatos = prices()
    except PricingError as exc:
        return None, "price_unavailable", str(exc)
    if not candidatos:
        return None, "price_unavailable", "A tabela de preco nao tem entrada de DPU-hora."
    if len(candidatos) > 1:
        valores = ", ".join(str(c.get("value")) for c in candidatos)
        return (
            None,
            "price_ambiguous",
            f"A tabela publica mais de um preco por DPU-hora sem eixo que os separe "
            f"({valores}). Escolher um seria escolher pelo operador.",
        )
    return candidatos[0], "", ""


def extract_run_cost(facts: Sequence[Fact], path: str) -> list[Fact]:
    """Emite um `glue.run_cost` por run que tem `dpu_seconds` medido."""
    runs = [f for f in facts if f.kind == "glue.job_run"]
    if not runs:
        return []

    entrada, reason, detail = _preco()
    saida: list[Fact] = []

    for run in sorted(runs, key=lambda f: str(f.subject.get("job_run_id") or "")):
        dpu_seconds = run.measures.get("dpu_seconds")
        if dpu_seconds is None:
            saida.append(
                _unresolved(
                    run,
                    "dpu_seconds_unavailable",
                    "O run nao tem `dpu_seconds`. Sob Auto Scaling sem DPUSeconds o "
                    "coletor recusou derivar, porque `number_of_workers` e teto e nao "
                    "uso -- e sem DPU nao ha custo. Custo zero seria a mentira mais "
                    "confortavel possivel aqui.",
                    path,
                )
            )
            continue
        if entrada is None:
            saida.append(_unresolved(run, reason, detail, path))
            continue

        dpu_hours = float(dpu_seconds) / _SEGUNDOS_POR_HORA
        preco = float(entrada["value"])
        saida.append(
            Fact(
                kind="glue.run_cost",
                subject=_run_subject(run),
                measures={
                    "dpu_seconds": float(dpu_seconds),
                    "dpu_hours": dpu_hours,
                    "price_per_dpu_hour": preco,
                    "cost": dpu_hours * preco,
                },
                attrs={
                    "region": str(entrada.get("region") or ""),
                    "runtime_version": str(entrada.get("runtime_version") or ""),
                    "currency": str(entrada.get("currency") or ""),
                    "price_source": str(entrada.get("source") or ""),
                    "price_retrieved": str(entrada.get("retrieved") or ""),
                    "dpu_source": str(run.attrs.get("dpu_source") or ""),
                },
                provenance={
                    "extractor": EXTRACTOR_ID,
                    "artifact": path,
                    "formula": _FORMULA,
                },
            )
        )
    return sort_facts(saida)
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_facts_run_cost.py -v
```

Esperado: PASS, 9 testes.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/facts/run_cost.py tests/test_facts_run_cost.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(facts): custo por run, com as duas ressalvas da fonte dentro do fact`

---

## Task 2: A fronteira custo-versus-tempo

**Files:**
- Create: `sparkforge/finops/__init__.py`, `sparkforge/finops/report.py`
- Test: `tests/test_finops_report.py`

- [ ] **Step 1: Escrever o teste que falha**

`tests/test_finops_report.py`:

```python
"""Testes do relatorio financeiro."""
from __future__ import annotations

from sparkforge.finops import build_finops_report
from sparkforge.findings.models import Fact


def _run(run_id, segundos, workers, dpu, worker="G.2X", state="SUCCEEDED"):
    return Fact(
        kind="glue.job_run",
        subject={
            "type": "job_run",
            "job_name": "etl",
            "job_run_id": run_id,
            "symbol": run_id,
        },
        measures={
            "execution_time_s": segundos,
            "number_of_workers": workers,
            "dpu_seconds": dpu,
        },
        attrs={
            "state": state,
            "worker_type": worker,
            "glue_version": "5.0",
            "autoscaling": False,
            "dpu_source": "derived",
        },
    )


class TestFronteira:
    def _duas_capacidades(self):
        """x10 em 500 s custa 10.000 DPU-s; x20 em 200 s custa 8.000."""
        facts = []
        for i in range(6):
            facts.append(_run(f"a{i}", 500, 10, 10000.0))
        for i in range(6):
            facts.append(_run(f"b{i}", 200, 20, 8000.0))
        return facts

    def test_more_resource_can_cost_less_and_the_report_shows_it(self):
        relatorio = build_finops_report(self._duas_capacidades(), job_name="etl")
        linhas = {
            (c["worker_type"], c["number_of_workers"]): c
            for c in relatorio["frontier"]
        }

        vinte = linhas[("G.2X", 20)]
        dez = linhas[("G.2X", 10)]

        # O DOBRO do recurso, e mais barato -- porque o tempo caiu para 40%.
        assert vinte["number_of_workers"] > dez["number_of_workers"]
        assert vinte["cost_per_run_p95"] < dez["cost_per_run_p95"]
        assert vinte["runtime_p95_s"] < dez["runtime_p95_s"]

    def test_the_frontier_is_ordered_by_cost(self):
        relatorio = build_finops_report(self._duas_capacidades(), job_name="etl")
        custos = [c["cost_per_run_p95"] for c in relatorio["frontier"]]

        assert custos == sorted(custos)

    def test_relative_cost_is_against_the_cheapest(self):
        relatorio = build_finops_report(self._duas_capacidades(), job_name="etl")

        assert relatorio["frontier"][0]["cost_relative"] == 1.0
        assert relatorio["frontier"][1]["cost_relative"] > 1.0

    def test_a_capacity_without_cost_is_named_not_dropped(self):
        facts = self._duas_capacidades()
        facts.append(
            Fact(
                kind="glue.job_run",
                subject={
                    "type": "job_run",
                    "job_name": "etl",
                    "job_run_id": "s1",
                    "symbol": "s1",
                },
                measures={"execution_time_s": 300, "number_of_workers": 10},
                attrs={
                    "state": "SUCCEEDED",
                    "worker_type": "G.4X",
                    "glue_version": "5.0",
                    "autoscaling": True,
                    "dpu_source": "",
                },
            )
        )
        relatorio = build_finops_report(facts, job_name="etl")

        assert any(
            r["reason"] == "cost_unobservable" for r in relatorio["refused"]
        )
        assert not [
            c for c in relatorio["frontier"] if c["worker_type"] == "G.4X"
        ]
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_finops_report.py -v
```

Esperado: FAIL com `ModuleNotFoundError: No module named 'sparkforge.finops'`.

- [ ] **Step 3: Implementar**

`sparkforge/finops/report.py`, primeira parte — a fronteira:

```python
"""O relatorio financeiro: custo, a troca recurso-tempo, e onde a alavanca esta.

NAO e extrator, e nada aqui vira Fact. O fact de custo e
`sparkforge/facts/run_cost.py`; este modulo COMPOE -- e composicao e leitura,
nao medicao.

A FRONTEIRA E O NUCLEO. DPU-segundos nao e invariante na troca entre mais
recurso e mais tempo: dobrar workers raramente divide o tempo por dois, e as
vezes divide por mais. Duas capacidades medidas lado a lado respondem o que
nenhum modelo responderia sem inventar um fator de eficiencia que fonte
nenhuma publica.

O QUE ESTE MODULO RECUSA:
  - Atribuir custo a causa. "Voce desperdicou X com spill" exige o custo do run
    que NAO aconteceu.
  - Interpolar entre capacidades observadas. A curva seria bonita e mentiria
    exatamente entre os pontos, que e onde alguem olharia.
  - Ordenar achado por economia estimada. Cada numero desses e um
    contrafactual disfarcado de prioridade.
  - Limiar de "caro". Fonte nenhuma diz que 2,32 USD por run e muito.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.facts.run_cost import extract_run_cost
from sparkforge.findings.models import Fact


def _nearest_rank(ordenados: list[float], pct: int) -> float:
    n = len(ordenados)
    rank = -(-(pct * n) // 100)
    rank = min(max(rank, 1), n)
    return ordenados[rank - 1]


def _capacidade(run: Fact) -> tuple[str, str, int, bool]:
    return (
        str(run.attrs.get("glue_version") or ""),
        str(run.attrs.get("worker_type") or ""),
        int(run.measures.get("number_of_workers") or 0),
        bool(run.attrs.get("autoscaling")),
    )


def _frontier(
    runs: Sequence[Fact], custo_por_run: dict[str, float]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grupos: dict[tuple[str, str, int, bool], list[Fact]] = {}
    for run in runs:
        grupos.setdefault(_capacidade(run), []).append(run)

    linhas: list[dict[str, Any]] = []
    recusas: list[dict[str, Any]] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        custos = sorted(
            custo_por_run[str(m.subject.get("job_run_id"))]
            for m in membros
            if str(m.subject.get("job_run_id")) in custo_por_run
        )
        if not custos:
            recusas.append(
                {
                    "reason": "cost_unobservable",
                    "capacity": f"{worker_type} x{workers}",
                    "runs": len(membros),
                    "detail": (
                        "Nenhum run desta capacidade tem custo: sem `dpu_seconds` nao ha "
                        "o que converter. Sob Auto Scaling sem DPUSeconds o coletor "
                        "recusou derivar, e a recusa se propaga ate aqui."
                    ),
                }
            )
            continue
        duracoes = sorted(
            float(m.measures["execution_time_s"])
            for m in membros
            if m.measures.get("execution_time_s") is not None
        )
        linhas.append(
            {
                "glue_version": glue_version,
                "worker_type": worker_type,
                "number_of_workers": workers,
                "autoscaling": autoscaling,
                "runs": len(membros),
                "runtime_p50_s": _nearest_rank(duracoes, 50) if duracoes else None,
                "runtime_p95_s": _nearest_rank(duracoes, 95) if duracoes else None,
                "cost_per_run_p95": _nearest_rank(custos, 95),
            }
        )

    linhas.sort(key=lambda linha: linha["cost_per_run_p95"])
    if linhas:
        barato = linhas[0]["cost_per_run_p95"]
        for linha in linhas:
            linha["cost_relative"] = (
                linha["cost_per_run_p95"] / barato if barato else None
            )
    return linhas, recusas


def build_finops_report(
    facts: Sequence[Fact],
    *,
    job_name: str,
    findings: Sequence[Any] = (),
) -> dict[str, Any]:
    """Compoe o relatorio financeiro a partir de facts ja extraidos."""
    runs = [
        f
        for f in facts
        if f.kind == "glue.job_run" and f.subject.get("job_name") == job_name
    ]
    custos = extract_run_cost(runs, "<facts>")
    custo_por_run = {
        str(c.subject.get("job_run_id")): float(c.measures["cost"])
        for c in custos
        if c.kind == "glue.run_cost"
    }

    frontier, recusas = _frontier(runs, custo_por_run)
    return {
        "job_name": job_name,
        "currency": next(
            (c.attrs["currency"] for c in custos if c.kind == "glue.run_cost"), ""
        ),
        "region": next(
            (c.attrs["region"] for c in custos if c.kind == "glue.run_cost"), ""
        ),
        "runtime_version": next(
            (c.attrs["runtime_version"] for c in custos if c.kind == "glue.run_cost"),
            "",
        ),
        "frontier": frontier,
        "refused": recusas,
    }
```

`sparkforge/finops/__init__.py`:

```python
"""Leitura financeira: custo, a troca recurso-tempo, e onde a alavanca esta.

Pacote proprio, e nao `sparkforge/economy/`: aquele e sobre economia de
chamadas e tokens de LLM, com perfis ECO/QUALITY/STRICT, e o nome colidiria
com o assunto errado. A separacao esta na seccao 22 do documento de origem.
"""
from sparkforge.finops.report import build_finops_report

__all__ = ["build_finops_report"]
```

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_finops_report.py tests/test_facts_run_cost.py -v
```

Esperado: PASS. Reporte a contagem real.

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/finops tests/test_finops_report.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(finops): a fronteira custo-versus-tempo entre capacidades observadas`

---

## Task 3: Custo por desfecho de SLA, e os sintomas

**Files:**
- Modify: `sparkforge/finops/report.py`
- Test: `tests/test_finops_report.py`

- [ ] **Step 1: Escrever o teste que falha**

```python
class TestCustoPorDesfecho:
    def _declarado(self, sla=10, alvo=0.8):
        return Fact(
            kind="workload.declared",
            subject={"type": "job_run", "symbol": "etl"},
            measures={"sla_minutes": sla, "reliability_target": alvo},
        )

    def _misto(self):
        """x10 e barata por run e estoura o SLA em 4 de 10.

        x20 custa mais por run e cumpre sempre.
        """
        facts = [self._declarado()]
        for i in range(6):
            facts.append(_run(f"a{i}", 300, 10, 6000.0))
        for i in range(4):
            facts.append(_run(f"b{i}", 900, 10, 9000.0))  # estoura 10 min
        for i in range(10):
            facts.append(_run(f"c{i}", 400, 20, 16000.0))
        return facts

    def test_cheaper_per_run_can_be_costlier_per_outcome(self):
        relatorio = build_finops_report(self._misto(), job_name="etl")
        por_desfecho = {
            (c["worker_type"], c["number_of_workers"]): c
            for c in relatorio["per_sla_outcome"]
        }

        dez = por_desfecho[("G.2X", 10)]
        vinte = por_desfecho[("G.2X", 20)]

        assert dez["reliability"] < vinte["reliability"]
        assert dez["cost_per_sla_success"] > vinte["cost_per_sla_success"]

    def test_short_term_and_long_term_can_disagree(self):
        relatorio = build_finops_report(self._misto(), job_name="etl")

        mais_barata_por_run = relatorio["frontier"][0]
        mais_barata_por_desfecho = relatorio["per_sla_outcome"][0]

        assert (
            mais_barata_por_run["number_of_workers"]
            != mais_barata_por_desfecho["number_of_workers"]
        )

    def test_a_capacity_without_resolution_leaves_the_long_term_view(self):
        facts = [self._declarado(alvo=0.99)]
        for i in range(10):
            facts.append(_run(f"a{i}", 300, 10, 6000.0))
        relatorio = build_finops_report(facts, job_name="etl")

        # 1/10 nao sustenta afirmacao de 99%.
        assert relatorio["per_sla_outcome"] == []
        assert any(
            r["reason"] == "resolution_too_coarse" for r in relatorio["refused"]
        )
        # E continua na visao de curto prazo.
        assert relatorio["frontier"]

    def test_without_a_declared_sla_there_is_no_long_term_view(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(facts, job_name="etl")

        assert relatorio["per_sla_outcome"] == []
        assert any(r["reason"] == "sla_not_declared" for r in relatorio["refused"])


class TestSintomas:
    def test_symptoms_sit_beside_the_cost_without_being_subtracted(self):
        facts = [_run("a1", 300, 10, 6000.0)]
        facts.append(
            Fact(
                kind="spark.stage.task_duration",
                subject={"type": "stage", "symbol": "s1", "stage_id": 1},
                measures={"p50_ms": 100, "p95_ms": 1140, "task_count": 20},
            )
        )
        relatorio = build_finops_report(facts, job_name="etl")

        assert relatorio["symptoms"]["skew_p95_over_p50"] == 11.4
        blob = str(relatorio).lower()
        assert "desperd" not in blob
        assert "waste" not in blob
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_finops_report.py::TestCustoPorDesfecho tests/test_finops_report.py::TestSintomas -v
```

- [ ] **Step 3: Implementar**

Acrescente a `report.py` o import de `resolution_supports` e a composição:

```python
from sparkforge.capacity.plan import resolution_supports
```

```python
def _per_sla_outcome(
    runs: Sequence[Fact],
    custo_por_run: dict[str, float],
    sla_segundos: float | None,
    alvo: float | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Custo por run que ficou DENTRO do SLA.

    Curto prazo e o custo de um run; longo prazo e o custo por desfecho util.
    Uma capacidade mais barata por run que estoura o SLA com frequencia custa
    mais por resultado que serve -- e o run que estourou custou dinheiro sem
    entregar o que precisava.
    """
    if sla_segundos is None or alvo is None:
        return [], [
            {
                "reason": "sla_not_declared",
                "detail": (
                    "Sem `sla_minutes` e `reliability_target` em workload.yaml nao ha "
                    "desfecho util a contar, e custo por desfecho vira divisao por uma "
                    "definicao que ninguem deu."
                ),
            }
        ]

    grupos: dict[tuple[str, str, int, bool], list[Fact]] = {}
    for run in runs:
        grupos.setdefault(_capacidade(run), []).append(run)

    linhas: list[dict[str, Any]] = []
    recusas: list[dict[str, Any]] = []
    for chave, membros in sorted(grupos.items(), key=lambda item: str(item[0])):
        glue_version, worker_type, workers, autoscaling = chave
        com_custo = [
            m for m in membros if str(m.subject.get("job_run_id")) in custo_por_run
        ]
        if not com_custo:
            continue
        n = len(com_custo)
        dentro = [
            m
            for m in com_custo
            if float(m.measures.get("execution_time_s") or 0) <= sla_segundos
        ]
        confiabilidade = len(dentro) / n
        resolucao = 1.0 / n
        if not resolution_supports(resolucao, float(alvo)):
            recusas.append(
                {
                    "reason": "resolution_too_coarse",
                    "capacity": f"{worker_type} x{workers}",
                    "runs": n,
                    "detail": (
                        f"Com {n} runs a menor diferenca observavel e {resolucao:.1%}, e o "
                        f"alvo de {float(alvo):.1%} exige distinguir {1 - float(alvo):.1%}. "
                        f"A visao de curto prazo continua valendo; a de longo nao."
                    ),
                }
            )
            continue
        custo_total = sum(
            custo_por_run[str(m.subject.get("job_run_id"))] for m in com_custo
        )
        linhas.append(
            {
                "glue_version": glue_version,
                "worker_type": worker_type,
                "number_of_workers": workers,
                "autoscaling": autoscaling,
                "runs": n,
                "runs_within_sla": len(dentro),
                "reliability": confiabilidade,
                # O denominador e o numero de runs que SERVIRAM. O run que
                # estourou entra no numerador -- ele custou.
                "cost_per_sla_success": (
                    custo_total / len(dentro) if dentro else None
                ),
            }
        )

    linhas.sort(
        key=lambda linha: (
            linha["cost_per_sla_success"] is None,
            linha["cost_per_sla_success"] or 0.0,
        )
    )
    return linhas, recusas


def _symptoms(facts: Sequence[Fact]) -> dict[str, Any]:
    """Os sintomas medidos, AO LADO do custo -- nunca subtraidos dele."""
    saida: dict[str, Any] = {}

    duracoes = [f for f in facts if f.kind == "spark.stage.task_duration"]
    razoes = [
        f.measures["p95_ms"] / f.measures["p50_ms"]
        for f in duracoes
        if f.measures.get("p50_ms")
    ]
    if razoes:
        saida["skew_p95_over_p50"] = round(max(razoes), 2)

    spills = [f for f in facts if f.kind == "spark.stage.spill"]
    razoes_spill = [
        (f.measures.get("memory_spill_bytes", 0) + f.measures.get("disk_spill_bytes", 0))
        / f.measures["input_bytes"]
        for f in spills
        if f.measures.get("input_bytes")
    ]
    if razoes_spill:
        saida["spill_over_input"] = round(max(razoes_spill), 3)

    scans = [f for f in facts if f.kind == "spark.sql.scan"]
    if scans:
        saida["bytes_read"] = sum(f.measures.get("bytes_read", 0) for f in scans)

    util = [
        f
        for f in facts
        if f.kind == "glue.metric"
        and f.attrs.get("name") == "glue.driver.workerUtilization"
    ]
    if util:
        saida["worker_utilization_p50"] = min(f.measures["p50"] for f in util)

    return saida
```

E ligue as duas em `build_finops_report`, lendo o SLA de `workload.declared`:

```python
    declarados = [
        f
        for f in facts
        if f.kind == "workload.declared" and f.subject.get("symbol") == job_name
    ]
    declarado = declarados[0] if declarados else None
    sla_segundos = (
        float(declarado.measures["sla_minutes"]) * 60.0
        if declarado and "sla_minutes" in declarado.measures
        else None
    )
    alvo = declarado.measures.get("reliability_target") if declarado else None

    por_desfecho, recusas_sla = _per_sla_outcome(
        runs, custo_por_run, sla_segundos, alvo
    )
```

e acrescente ao dicionário de saída `"per_sla_outcome": por_desfecho`, `"symptoms": _symptoms(facts)`, e `recusas + recusas_sla` em `"refused"`.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_finops_report.py -v
```

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/finops tests/test_finops_report.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(finops): custo por desfecho de SLA, e os sintomas ao lado`

---

## Task 4: A alavanca — capacidade ou código

**Files:**
- Modify: `sparkforge/finops/report.py`
- Test: `tests/test_finops_report.py`

Esta é a tarefa que separa E de um relatório de custo.

- [ ] **Step 1: Escrever o teste que falha**

```python
class TestAlavanca:
    def _finding(self, rule_id):
        from sparkforge.findings.models import Finding

        return Finding(
            rule_id=rule_id,
            title=f"achado {rule_id}",
            severity="P1",
            confidence="high",
            status="confirmed",
            subject={"type": "source_location", "file": "etl.py", "line": 10},
        )

    def test_code_findings_are_listed_under_the_code_lever(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts,
            job_name="etl",
            findings=[self._finding("SF-PY-004"), self._finding("SF-PQ-002")],
        )

        codigo = relatorio["levers"]["code"]
        assert sorted(f["rule_id"] for f in codigo["findings"]) == [
            "SF-PQ-002",
            "SF-PY-004",
        ]

    def test_a_code_finding_never_appears_under_the_capacity_lever(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts, job_name="etl", findings=[self._finding("SF-PY-004")]
        )

        capacidade = str(relatorio["levers"]["capacity"])
        assert "SF-PY-004" not in capacidade

    def test_infrastructure_findings_are_not_code(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts, job_name="etl", findings=[self._finding("SF-GLUE-007")]
        )

        assert not relatorio["levers"]["code"]["findings"]

    def test_no_finding_and_sized_capacity_is_an_answer_not_a_gap(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(facts, job_name="etl", findings=[])

        assert relatorio["levers"]["none_found"] is True

    def test_findings_are_never_ranked_by_estimated_saving(self):
        facts = [_run(f"a{i}", 300, 10, 6000.0) for i in range(6)]
        relatorio = build_finops_report(
            facts,
            job_name="etl",
            findings=[self._finding("SF-PY-004"), self._finding("SF-UI-006")],
        )

        blob = str(relatorio).lower()
        for palavra in ("estimated_saving", "economia", "saving"):
            assert palavra not in blob
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_finops_report.py::TestAlavanca -v
```

- [ ] **Step 3: Implementar**

```python
# Areas cujo achado aponta para o CODIGO ou para o layout do dado, e nao para
# a capacidade. Lista explicita, e nao prefixo generico: `SF-GLUE` e `SF-EMR`
# sao infraestrutura, e por-los aqui faria a alavanca de codigo sugerir
# consertar codigo para um problema de Terraform.
#
# A separacao existe porque trocar worker para consertar um destes e comprar
# saida de um defeito: o custo cai um pouco, o defeito fica, e a conta volta
# maior quando o volume crescer.
_AREAS_DE_CODIGO = frozenset(
    {"SF-PY", "SF-PQ", "SF-PLAN", "SF-UI", "SF-SQL", "SF-CG", "SF-GRAPH", "SF-DQ"}
)


def _area_de(rule_id: str) -> str:
    return rule_id.rsplit("-", 1)[0]


def _levers(findings: Sequence[Any]) -> dict[str, Any]:
    """Qual alavanca se aplica -- nunca QUANTO do custo e de cada lado.

    Atribuir o quanto exigiria o custo do run que nao aconteceu, e a spec
    recusa isso por escrito. O que este bloco faz e nomear a evidencia que ja
    existe, agrupada pelo eixo que faltava: o financeiro.

    A ordem e a que o `judge` devolveu. Ordenar por "economia estimada" seria
    um contrafactual disfarcado de prioridade.
    """
    de_codigo = [
        {
            "rule_id": f.rule_id,
            "title": f.title,
            "severity": f.severity,
            "subject": f.subject,
        }
        for f in findings
        if _area_de(f.rule_id) in _AREAS_DE_CODIGO
    ]
    return {
        "code": {
            "findings": de_codigo,
            "detail": (
                "Nenhum destes muda trocando worker. Um job que varre dez vezes o que "
                "precisa e caro em qualquer capacidade."
            )
            if de_codigo
            else "",
        },
        "capacity": {
            "detail": (
                "A pergunta de capacidade tem resposta com evidencia em "
                "`sparkforge capacity`, que compara as capacidades observadas contra o "
                "SLA declarado."
            )
        },
        "none_found": not de_codigo,
    }
```

e acrescente `"levers": _levers(findings)` à saída.

**Atenção ao `none_found`:** ele diz que nenhuma alavanca **de código** foi encontrada. A spec (§3.7) trata isso como resposta — um job pode simplesmente custar o que custa. Se a implementação precisar distinguir "sem achado de código" de "sem achado nenhum e capacidade dimensionada", relate: o teste do plano só cobra o primeiro.

- [ ] **Step 4: Rodar e ver passar**

```bash
rtk pytest tests/test_finops_report.py tests/test_facts_run_cost.py -v
```

- [ ] **Step 5: Commit**

```bash
rtk git add sparkforge/finops tests/test_finops_report.py
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `feat(finops): a alavanca do custo, capacidade ou codigo, sem atribuir quanto`

---

## Task 5: Superfície

**Files:**
- Modify: `sparkforge/adapters/_core.py`, `cli.py`, `tools.py`, `manifest.json`, `parity.yaml`, `agents/`
- Test: `tests/test_adapters_cli.py`, `tests/test_adapters_tools.py`

- [ ] **Step 1: Escrever o teste que falha**

Em `tests/test_adapters_cli.py`, uma classe `TestFinopsCommand` no molde de `TestCapacityCommand` (leia-a): escreve um `facts.json` com seis `glue.job_run` de duas capacidades e um `workload.declared`, chama `main(["finops", "--facts", …, "--job-name", "etl"])`, e afirma código 0, `frontier` com duas linhas e `region` igual a `UNQUALIFIED` no payload.

Em `tests/test_adapters_tools.py`:

```python
class TestFinopsTool:
    def test_the_tool_is_declared_and_dispatchable(self):
        from sparkforge.adapters import tools

        assert "sparkforge_finops" in tools.TOOLS
        assert "sparkforge_finops" in tools._HANDLERS
```

- [ ] **Step 2: Rodar e ver falhar**

```bash
rtk pytest tests/test_adapters_cli.py::TestFinopsCommand tests/test_adapters_tools.py::TestFinopsTool -v
```

- [ ] **Step 3: Implementar**

Em `_core.py`, no molde de `capacity_plan` (leia-o):

```python
def finops_report(
    facts_path: str,
    job_name: str,
    runtime: str = "",
) -> dict[str, Any]:
    """Reune o financeiro: custo, a troca recurso-tempo, e onde a alavanca esta.

    Verbo de TOPO pela mesma razao de `benchmark`, `fuse`, `workload` e
    `capacity`: consome facts ja extraidos e nao le artefato nenhum.

    Os achados vem do `judge` sobre os MESMOS facts -- E nao escreve regra, ele
    agrupa o que o motor ja produz sob o eixo financeiro.
    """
    facts = _load_facts_file(facts_path, _FACTS_FROM_RUN_AND_SCAN, "--facts")
    findings, _ = judge(facts, load_catalog(), _runtime_de(runtime), return_skipped=True)
    return build_finops_report(facts, job_name=job_name, findings=findings)
```

Confira como os outros verbos deste arquivo montam o `runtime` para o `judge` — se houver um helper, use; se o runtime for opcional em algum deles, siga a mesma forma e relate qual escolheu.

Parser, handler e despacho em `cli.py`; a tool em `tools.py` com `facts_path` e o `outputSchema` construído a partir da saída **real** de `build_finops_report`. Se a saída real não validar contra o schema declarado, conserte o schema — não invente schema genérico (uma entrega anterior fez isso e era defeito).

- [ ] **Step 4: Manifesto, paridade e o gate de órfão**

- `manifest.json`: `sparkforge_finops` em ordem alfabética.
- `parity.yaml`: a capability que lista `capacity` ganha `sparkforge_finops` e `finops`.
- `agents/`: cite a tool onde `sparkforge_capacity` já aparece, dizendo por que ela existe — capacidade e código são alavancas diferentes, e a conta não diz qual é sozinha.

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

Mensagem: `feat(cli): verbo finops e a tool da leitura financeira`

---

## Task 6: Fixtures e as garantias do corpus

**Files:**
- Create: `fixtures/finops/` (nove cenários), `tests/test_fixtures_golden_finops.py`
- Modify: `tests/test_fixtures_kind_coverage.py`, `tests/test_rules_catalog_reachability.py`

- [ ] **Step 1: Registrar `run_cost` nas DUAS listas de extratores**

As duas são manuais e duplicadas, e o próprio arquivo avisa que esquecer uma não quebra nada — é por isso que ela é esquecida.

- [ ] **Step 2: Os nove cenários**

| Cenário | Prova |
|---|---|
| `cost_from_derived_dpu` | custo sobre DPU derivado, `dpu_source` propagado |
| `cost_from_observed_dpu` | custo sobre `DPUSeconds` medido |
| `no_dpu_no_cost` | Auto Scaling sem `DPUSeconds`: lacuna, não zero |
| `more_resource_costs_less` | o dobro de workers custando menos |
| `more_resource_costs_more` | o mesmo eixo no sentido oposto |
| `cheap_but_misses_sla` | mais barata por run, mais cara por desfecho |
| `cost_is_in_the_code` | achados de código: a alavanca não é worker |
| `no_lever_found` | sem achado e com capacidade dimensionada |
| `no_cloudwatch` | custo sai, sintoma de utilização ausente |

- [ ] **Step 3: O módulo golden e as quatro garantias**

`tests/test_fixtures_golden_finops.py`, com `FIXTURES = ROOT / "fixtures" / "finops"`, chamando `validate_fact` nos facts de custo. Mais:

```python
class TestOQueOCorpusInteiroGarante:
    def test_every_cost_fact_carries_both_caveats(self):
        """Um fact de custo sem ressalva e um numero que parece preciso."""
        for directory in fixture_dirs():
            for fact in _facts(directory):
                if fact.kind != "glue.run_cost":
                    continue
                assert fact.attrs["region"], directory.name
                assert fact.attrs["runtime_version"], directory.name

    def test_no_cost_fact_exists_without_measured_dpu(self):
        """Custo sobre DPU ausente seria zero disfarcado."""
        for directory in fixture_dirs():
            for fact in _facts(directory):
                if fact.kind == "glue.run_cost":
                    assert fact.measures.get("dpu_seconds"), directory.name

    def test_no_code_finding_under_the_capacity_lever(self):
        """Sugerir troca de worker para um SF-PY e comprar saida de um defeito."""
        for directory in fixture_dirs():
            relatorio = run_fixture(directory)
            capacidade = str(relatorio["levers"]["capacity"])
            for achado in relatorio["levers"]["code"]["findings"]:
                assert achado["rule_id"] not in capacidade, directory.name

    def test_nothing_attributes_cost_to_a_cause(self):
        """A garantia de 3.3, sobre o corpus inteiro.

        Sem ela, a proxima pessoa a mexer aqui vai achar que atribuir e o
        objetivo.
        """
        for directory in fixture_dirs():
            blob = str(run_fixture(directory)).lower()
            for palavra in ("desperd", "waste", "estimated_saving", "economia"):
                assert palavra not in blob, (directory.name, palavra)
```

- [ ] **Step 4: Rodar**

```bash
rtk pytest tests/test_fixtures_golden_finops.py tests/test_fixtures_kind_coverage.py tests/test_rules_catalog_reachability.py -q
```

Grave os goldens com a saída real e **leia** cada um antes de commitar.

- [ ] **Step 5: Commit**

```bash
rtk git add fixtures/finops tests
rtk git commit -F <arquivo com a mensagem>
```

Mensagem: `test(fixtures): nove cenarios da leitura financeira`

---

## Task 7: Documentação e os gates

- [ ] **Step 1: Suíte inteira**

```bash
rtk pytest -q
```

- [ ] **Step 2: README** — o verbo novo junto de `benchmark`, `fuse`, `workload` e `capacity`, e os números de extratores e kinds **medidos**, nos **dois** lugares que os citam.

- [ ] **Step 3: STATUS** — a fase, e o **fechamento do roadmap de cinco subprojetos**: A, B, C1, C2, C3, D e E entregues. Registre as decisões (custo é fact no precedente do DPU derivado; as duas ressalvas viajam dentro do fact; custo ao lado do sintoma sem atribuir; a alavanca separa capacidade de código) e o que ficou de fora (limiar de "caro", atribuição por causa, custo de EMR/Athena/S3, os sete módulos do §22 que já existem em outro lugar).

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

Mensagem: `docs: o verbo finops, a fase, e o roadmap fechado`

---

## Cobertura da spec

| Requisito da spec | Task |
|---|---|
| §3.1 custo é fact | 1 |
| §3.2 as duas ressalvas dentro do fact | 1, 6 |
| §3.3 custo ao lado do sintoma | 3, 6 |
| §3.4 a correlação do §37 | 3 |
| §3.5 a fronteira custo-versus-tempo | 2 |
| §3.6 curto e longo prazo | 3 |
| §3.7 a alavanca | 4, 6 |
| §4.1 `glue.run_cost` | 1 |
| §4.2 `glue.run_cost.unresolved` | 1 |
| §4.3 o relatório | 2, 3, 4 |
| §5 verbo de topo e tool | 5 |
| §6 erros, cada um com o seu nome | 1, 3 |
| §7.1 domínio de fixture | 6 |
| §7.2 as garantias do corpus | 6 |
| §8 documentação | 7 |
| §9 critérios de aceite 1–11 | 1, 2, 3, 4, 6 |
