"""Mutacao dos limiares do catalogo, e propriedades metamorficas do `judge`.

O diferencial deste projeto e o julgamento deterministico, e golden por fixture
prova que o julgamento de HOJE bate com o esperado -- nao que o teste perceberia se
o julgamento mudasse. Mutacao responde a segunda pergunta: muda-se um limiar ou um
operador da regra, julga-se de novo cada fixture com `expected/facts.json`, e o
mutante "morre" se algum golden mudar. Mutante que sobrevive e mudanca que a suite
inteira deixaria passar calada.

Medido em 2026-09-15, sobre 348 fixtures:

- **41 valores numericos** em blocos `threshold:` de 30 regras. Perturbar cada um em
  10% para cima ou para baixo muda algum golden em **41 de 41** -- todo limiar tem um
  golden a menos de 10% da fronteira. Isso vira invariante: regra nova com limiar
  precisa de golden perto dele.
- **57 trocas de operador** (`<=`/`<`, `>=`/`>`) nas expressoes das regras, e **39
  sobrevivem**: nenhum golden fica EXATAMENTE no limiar daquelas comparacoes, entao
  trocar `>=` por `>` nao muda nada. Isso NAO vira falha, vira divida DECLARADA em
  `FRONTEIRA_SEM_GOLDEN`, com igualdade exata: um golden novo que mate uma delas
  obriga a tira-la da lista, e uma sobrevivente nova precisa ser declarada a vista.

As propriedades metamorficas cobram o que golden individual nao alcanca: a ordem
dos facts nao muda o julgamento, julgar duas vezes da o mesmo, e um fact de kind que
nenhuma regra le nao muda nada. O `judge` ja ordena os facts por dentro
(`sort_facts`); a primeira propriedade trava isso contra uma mudanca futura.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import re
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from sparkforge.adapters._core import _facts_from_dicts
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FATORES = (0.9, 1.1)
TROCAS = (("<=", "<"), (">=", ">"), ("<", "<="), (">", ">="))
KIND_QUE_NENHUMA_REGRA_LE = "synthetic.metamorphic_noise"

FRONTEIRA_SEM_GOLDEN = frozenset(
    {
        ("SF-ATH-003", "measures.partition_count >= threshold.count", ">= -> >"),
        (
            "SF-BENCH-001",
            "measures.total_input_bytes_delta_pct > threshold.input_divergence_pct or "
            "measures.total_input_bytes_delta_pct < -threshold.input_divergence_pct",
            "< -> <=",
        ),
        ("SF-BENCH-002", "measures.total_task_ms_delta_pct > threshold.regression_pct", "> -> >="),
        (
            "SF-BENCH-003",
            "measures.total_task_ms_delta_pct < -threshold.improvement_pct and "
            "(measures.total_spill_bytes_after > measures.total_spill_bytes_before * "
            "threshold.growth_factor or measures.total_gc_ms_after > "
            "measures.total_gc_ms_before * threshold.growth_factor)",
            "< -> <=",
        ),
        (
            "SF-BENCH-004",
            "measures.unmatched_stage_count / (measures.matched_stage_count + "
            "measures.unmatched_stage_count) > threshold.unmatched_ratio",
            "> -> >=",
        ),
        ("SF-EMRS-001", "measures.initial_capacity_worker_count >= 1", ">= -> >"),
        ("SF-ENV-004", "attrs.spark_minor < 3.2", "< -> <="),
        ("SF-ERR-001", "attrs.scala_minor < 13", "< -> <="),
        ("SF-FVAL-004", "measures.relative_delta > threshold.relative_tolerance", "> -> >="),
        ("SF-GLUE-003", "measures.value > 1", "> -> >="),
        ("SF-GLUE-004", "measures.value > 0", "> -> >="),
        ("SF-ICE-001", "measures.avg_file_bytes < threshold.min_avg_bytes", "< -> <="),
        (
            "SF-ICE-002",
            "measures.delete_file_count / measures.data_file_count >= threshold.ratio",
            ">= -> >",
        ),
        ("SF-ICE-003", "measures.snapshot_count >= threshold.count", ">= -> >"),
        (
            "SF-PQ-001",
            "measures.avg_file_bytes < threshold.min_avg_bytes and "
            "measures.file_count >= threshold.min_count",
            ">= -> >",
        ),
        ("SF-PQ-003", "measures.max_file_bytes >= threshold.min_bytes", ">= -> >"),
        (
            "SF-PQ-004",
            "measures.read_schema_columns / measures.referenced_columns >= threshold.ratio",
            ">= -> >",
        ),
        ("SF-PQ-005", "measures.distinct_values <= threshold.min_cardinality", "<= -> <"),
        (
            "SF-PQ-005",
            "measures.avg_bytes_per_partition < threshold.min_partition_bytes",
            "< -> <=",
        ),
        ("SF-PQ-006", "measures.total_byte_size < threshold.piso_bytes", "< -> <="),
        ("SF-PQ-006", "measures.total_byte_size > threshold.teto_bytes", "> -> >="),
        ("SF-PQ-008", "measures.avg_range_coverage > threshold.cobertura_maxima", "> -> >="),
        ("SF-PY-003", "measures.join_index < measures.first_reduction_index", "< -> <="),
        ("SF-PY-007", "measures.run_length >= threshold.run_length", ">= -> >"),
        ("SF-SPARK4-003", "attrs.major < 15", "< -> <="),
        ("SF-SPARK4-004", "attrs.scala_minor < 13", "< -> <="),
        ("SF-TIMEOUT-001", "measures.skew_p95_over_p50 >= threshold.skew_ratio", ">= -> >"),
        ("SF-TIMEOUT-001", "measures.spill_over_input >= threshold.spill_ratio", ">= -> >"),
        ("SF-TIMEOUT-001", "measures.gc_ratio >= threshold.gc_ratio", ">= -> >"),
        ("SF-TIMEOUT-002", "measures.heartbeat_s >= measures.network_timeout_s", ">= -> >"),
        ("SF-UI-002", "measures.max_bytes / measures.p50_bytes >= threshold.ratio", ">= -> >"),
        (
            "SF-UI-003",
            "measures.disk_spill_bytes / measures.input_bytes >= threshold.ratio",
            ">= -> >",
        ),
        (
            "SF-UI-006",
            "measures.task_count < measures.available_cores * threshold.factor",
            "< -> <=",
        ),
        ("SF-WASTE-001", "measures.worker_utilization_p50 <= threshold.utilization", "<= -> <"),
        ("SF-WASTE-001", "measures.memory_used_pct_p95 <= threshold.memory_pct", "<= -> <"),
        ("SF-WASTE-001", "measures.disk_used_pct_p95 <= threshold.disk_pct", "<= -> <"),
        ("SF-WASTE-001", "measures.skew_p95_over_p50 < threshold.skew_ratio", "< -> <="),
        ("SF-WASTE-002", "measures.worker_utilization_p50 <= threshold.utilization", "<= -> <"),
        ("SF-WASTE-002", "measures.skew_p95_over_p50 >= threshold.skew_ratio", ">= -> >"),
    }
)


@lru_cache(maxsize=1)
def _catalogo() -> tuple[dict[str, Any], ...]:
    return tuple(load_catalog())


@lru_cache(maxsize=1)
def _casos() -> tuple[tuple[str, tuple[Fact, ...], dict[str, Any]], ...]:
    casos = []
    for arquivo in sorted(ROOT.glob("fixtures/**/expected/facts.json")):
        diretorio = arquivo.parent.parent
        meta_path = diretorio / "meta.yaml"
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        facts = tuple(_facts_from_dicts(json.loads(arquivo.read_text(encoding="utf-8"))))
        runtime = (meta or {}).get("runtime") or {}
        casos.append((diretorio.relative_to(ROOT).as_posix(), facts, runtime))
    return tuple(casos)


def _assinatura(facts, regras, runtime) -> list[str]:
    return sorted(json.dumps(f.to_dict(), sort_keys=True) for f in judge(facts, regras, runtime))


def _base(regra: dict[str, Any]) -> dict[str, list[str]]:
    return {nome: _assinatura(facts, [regra], rt) for nome, facts, rt in _casos()}


def _mata(mutante: dict[str, Any], base: dict[str, list[str]]) -> bool:
    return any(_assinatura(facts, [mutante], rt) != base[nome] for nome, facts, rt in _casos())


def _exprs(no: Any, caminho: tuple[Any, ...] = ()) -> Iterator[tuple[tuple[Any, ...], str]]:
    if isinstance(no, dict):
        for chave, valor in no.items():
            if chave == "expr" and isinstance(valor, str):
                yield caminho + (chave,), valor
            else:
                yield from _exprs(valor, caminho + (chave,))
    elif isinstance(no, list):
        for indice, valor in enumerate(no):
            yield from _exprs(valor, caminho + (indice,))


def _atribuir(no: Any, caminho: tuple[Any, ...], valor: str) -> None:
    for passo in caminho[:-1]:
        no = no[passo]
    no[caminho[-1]] = valor


def _perturbado(valor: int | float, fator: float) -> int | float:
    novo = valor * fator
    if isinstance(valor, int) and round(novo) != valor:
        return int(round(novo))
    return novo


def test_todo_limiar_numerico_e_percebido_por_algum_golden_a_10_por_cento() -> None:
    frouxos = []
    for regra in _catalogo():
        limiares = regra.get("threshold")
        if not isinstance(limiares, dict):
            continue
        base = _base(regra)
        for chave, valor in limiares.items():
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor == 0:
                continue
            morto = False
            for fator in FATORES:
                mutante = copy.deepcopy(regra)
                mutante["threshold"][chave] = _perturbado(valor, fator)
                if _mata(mutante, base):
                    morto = True
                    break
            if not morto:
                frouxos.append((regra["id"], chave, valor))
    assert not frouxos, (
        f"limiar que nenhum golden percebe com 10% de perturbacao: {frouxos}. "
        "Acrescente uma fixture com a medida perto da fronteira da regra."
    )


def test_fronteira_exata_sem_golden_e_a_divida_declarada() -> None:
    sobreviventes = set()
    for regra in _catalogo():
        base = None
        for caminho, expr in _exprs(regra.get("when")):
            for velho, novo in TROCAS:
                padrao = (
                    re.compile(re.escape(velho) + r"(?![=])")
                    if velho in ("<", ">")
                    else re.compile(re.escape(velho))
                )
                if not padrao.search(expr):
                    continue
                if base is None:
                    base = _base(regra)
                mutante = copy.deepcopy(regra)
                _atribuir(mutante["when"], caminho, padrao.sub(novo, expr, count=1))
                if not _mata(mutante, base):
                    sobreviventes.add((regra["id"], expr, f"{velho} -> {novo}"))
                break
    novas = sorted(sobreviventes - FRONTEIRA_SEM_GOLDEN)
    mortas = sorted(FRONTEIRA_SEM_GOLDEN - sobreviventes)
    assert not novas and not mortas, (
        f"fronteira sem golden que nao esta declarada: {novas}; declarada que algum "
        f"golden ja percebe (tire da lista): {mortas}"
    )


def _julgado(facts, runtime) -> list[str]:
    return _assinatura(facts, _catalogo(), runtime)


def test_a_ordem_dos_facts_nao_muda_o_julgamento() -> None:
    divergentes = [
        nome
        for nome, facts, rt in _casos()
        if _julgado(tuple(reversed(facts)), rt) != _julgado(facts, rt)
    ]
    assert not divergentes, divergentes


def test_julgar_duas_vezes_da_o_mesmo() -> None:
    divergentes = [
        nome for nome, facts, rt in _casos() if _julgado(facts, rt) != _julgado(facts, rt)
    ]
    assert not divergentes, divergentes


def test_fact_de_kind_que_nenhuma_regra_le_nao_muda_o_julgamento() -> None:
    divergentes = []
    for nome, facts, rt in _casos():
        if not facts:
            continue
        ruido = dataclasses.replace(facts[0], kind=KIND_QUE_NENHUMA_REGRA_LE)
        if _julgado(facts + (ruido,), rt) != _julgado(facts, rt):
            divergentes.append(nome)
    assert not divergentes, divergentes
