"""Qual timeout: relogio do Glue, broadcast, rede ou heartbeat.

FORMA, E O PRECEDENTE QUE A JUSTIFICA. Isto e fact, e nao mecanismo, porque nao
ha limiar e nao ha juizo -- e leitura da frase que o runtime escreveu. O
precedente e `heap_oom_in_log`, que ja e atributo de `spark.executor.lost`: ler
o texto do artefato e nomear o que ele diz e leitura, nao opiniao. O julgamento
-- "nao suba o timeout, olhe o spill primeiro" -- fica onde julgamento mora, no
catalogo de regras.

DERIVA DE FACT, NAO DE CAMINHO, como `run_cost.py`: a entrada e um pool de
facts ja extraidos, porque a evidencia vem de tres fontes diferentes que
nenhum extrator ve juntas -- o estado do run Glue (`glue.job_run`), a razao com
que o executor foi removido (`spark.executor.lost`) e a razao da stage que
falhou (`spark.stage.failure`).

O QUE ESTE MODULO RECUSA:
  - Recomendar um valor novo de timeout. Derivar valor de configuracao e o
    criterio 17 do documento de origem, e entra com a procedencia por
    propriedade que o 36 pede -- ou nao entra.
  - Categoria default. Sem evidencia sai `spark.timeout.unresolved` com razao
    nomeada, nunca uma categoria escolhida por ser a mais comum.
  - Escolher em silencio entre dois sinais. A precedencia e declarada, e o que
    ela preteriu continua legivel em `also_seen`.

Puro e deterministico: nunca aplica limiar, nunca atribui severidade, nunca
toca a rede.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "timeout_diagnosis@0.1.0"

EMITTED_KINDS = frozenset(
    {"spark.timeout.diagnosis", "spark.timeout.relation", "spark.timeout.unresolved"}
)

_HEARTBEAT_KEY = "spark.executor.heartbeatInterval"
_NETWORK_KEY = "spark.network.timeout"

# Sufixos que o Spark aceita nestas duas chaves. Valor sem sufixo e lido como
# SEGUNDOS -- e o default documentado das duas, e nao um palpite.
_SUFIXOS_EM_SEGUNDOS = (
    ("ms", 0.001),
    ("s", 1.0),
    ("m", 60.0),
    ("min", 60.0),
    ("h", 3600.0),
)

# Do mais especifico para o mais generico. O generico e CONSEQUENCIA do
# especifico sempre que os dois aparecem: o run estourou o relogio do Glue
# PORQUE o executor morreu, e nao ao contrario. Inverter esta ordem faria todo
# run em TIMEOUT responder "wall_clock" e enterrar a causa.
_PRECEDENCIA = ("heartbeat", "network", "broadcast", "wall_clock")

# A frase de referencia fica ao lado de cada padrao de proposito: quem for
# mexer aqui precisa ver o texto que o Spark escreve, e nao so o regex.
_PADROES_DE_FRASE: tuple[tuple[str, re.Pattern[str]], ...] = (
    # "Executor heartbeat timed out after 130000 ms"
    ("heartbeat", re.compile(r"heartbeat\s+timed\s+out", re.IGNORECASE)),
    # "Futures timed out after [120 seconds]" -- o timeout de RPC/shuffle.
    ("network", re.compile(r"futures\s+timed\s+out|rpc.{0,20}timed\s+out", re.IGNORECASE)),
    # "Could not execute broadcast in 300 secs."
    ("broadcast", re.compile(r"could\s+not\s+execute\s+broadcast", re.IGNORECASE)),
)

_BASIS_POR_KIND = {
    "spark.executor.lost": "executor_removed_reason",
    "spark.stage.failure": "stage_failure_reason",
}

_COMO_COLETAR_LOG = (
    "sparkforge collect event-log seguido de sparkforge analyze event-log traz "
    "as frases que separam broadcast, rede e heartbeat do relogio de parede."
)


def _sinal(categoria: str, basis: str, texto: str, subject: dict[str, Any]) -> dict[str, Any]:
    return {"category": categoria, "basis": basis, "evidence_text": texto, "subject": subject}


def _sinais_de_frase(facts: Sequence[Fact]) -> list[dict[str, Any]]:
    """Le a razao literal de cada fonte de texto e nomeia o que ela diz."""
    achados: list[dict[str, Any]] = []
    for fact in facts:
        basis = _BASIS_POR_KIND.get(fact.kind)
        if basis is None:
            continue
        texto = str(fact.attrs.get("reason") or "")
        if not texto:
            continue
        for categoria, padrao in _PADROES_DE_FRASE:
            if padrao.search(texto):
                achados.append(_sinal(categoria, basis, texto, dict(fact.subject)))
                break
    return achados


def _runs_em_timeout(facts: Sequence[Fact]) -> list[Fact]:
    return [
        f
        for f in facts
        if f.kind == "glue.job_run" and str(f.attrs.get("state") or "").upper() == "TIMEOUT"
    ]


def _subject_do_run(run: Fact | None) -> dict[str, Any]:
    if run is None:
        return {"type": "job_run", "symbol": ""}
    return {
        "type": "job_run",
        "symbol": str(run.subject.get("job_run_id") or run.subject.get("symbol") or ""),
        "job_name": str(run.subject.get("job_name") or ""),
        "job_run_id": str(run.subject.get("job_run_id") or ""),
    }


def _segundos(valor: str) -> float | None:
    """Converte `10s`, `1min`, `500ms` ou `10` para segundos. `None` se nao der.

    Comparar as duas propriedades como STRING seria comparar texto: `"10s"` e
    maior que `"120s"` em ordem lexicografica, e a conclusao sairia invertida.
    """
    texto = str(valor or "").strip().lower()
    if not texto:
        return None
    for sufixo, fator in sorted(_SUFIXOS_EM_SEGUNDOS, key=lambda par: -len(par[0])):
        if texto.endswith(sufixo):
            numero = texto[: -len(sufixo)].strip()
            try:
                return float(numero) * fator
            except ValueError:
                return None
    try:
        return float(texto)
    except ValueError:
        return None


def _sintomas(facts: Sequence[Fact]) -> dict[str, float]:
    """Os sintomas MEDIDOS que viajam com o diagnostico, sem limiar nenhum.

    O limiar e da regra, e por isso nao esta aqui: `SF-TIMEOUT-001` decide o
    que e sintoma bastante para recusar "aumente o timeout", e decide com o
    `threshold` dela, versionado no catalogo junto do resto.

    Sintoma sem fonte fica AUSENTE, nunca zero: zero diria que foi medido e deu
    zero. A unica excecao e `executor_lost_count`, que e contagem de ocorrencia
    -- ali zero e a medida, e nao a ausencia dela.
    """
    por_kind: dict[str, list[Fact]] = {}
    for fact in facts:
        por_kind.setdefault(fact.kind, []).append(fact)

    medidas: dict[str, float] = {}

    razoes = [
        f.measures["p95_ms"] / f.measures["p50_ms"]
        for f in por_kind.get("spark.stage.task_duration") or []
        if f.measures.get("p50_ms")
    ]
    if razoes:
        medidas["skew_p95_over_p50"] = round(max(razoes), 2)

    spills = [
        (f.measures.get("memory_spill_bytes", 0.0) + f.measures.get("disk_spill_bytes", 0.0))
        / f.measures["input_bytes"]
        for f in por_kind.get("spark.stage.spill") or []
        if f.measures.get("input_bytes")
    ]
    if spills:
        medidas["spill_over_input"] = round(max(spills), 3)

    gcs = [
        f.measures["gc_time_ms"] / f.measures["task_time_ms"]
        for f in por_kind.get("spark.stage.gc") or []
        if f.measures.get("task_time_ms")
    ]
    if gcs:
        medidas["gc_ratio"] = round(max(gcs), 3)

    medidas["executor_lost_count"] = float(len(por_kind.get("spark.executor.lost") or []))
    return medidas


def _relacao(facts: Sequence[Fact], subject: dict[str, Any], path: str) -> list[Fact]:
    """`heartbeatInterval` contra `network.timeout`, quando as duas foram vistas."""
    valores: dict[str, str] = {}
    for fact in facts:
        if fact.kind != "spark.conf_effective":
            continue
        chave = str(fact.attrs.get("key") or "")
        if chave in (_HEARTBEAT_KEY, _NETWORK_KEY):
            valores[chave] = str(fact.attrs.get("value") or "")

    if not valores:
        # Sem configuracao nenhuma a ausencia ja e a resposta do log, e uma
        # lacuna aqui repetiria o que `state_without_log` ja diz.
        return []

    heartbeat = _segundos(valores.get(_HEARTBEAT_KEY, ""))
    rede = _segundos(valores.get(_NETWORK_KEY, ""))
    if heartbeat is None or rede is None:
        faltando = [
            chave
            for chave, lido in ((_HEARTBEAT_KEY, heartbeat), (_NETWORK_KEY, rede))
            if lido is None
        ]
        return [
            _unresolved(
                "conf_not_observed",
                "A relacao entre as duas propriedades so e conferivel com as duas "
                f"lidas em segundos. Sem valor utilizavel para: {', '.join(faltando)}. "
                "Valor isolado nao e certo nem errado; a relacao e.",
                subject,
                path,
            )
        ]

    return [
        Fact(
            kind="spark.timeout.relation",
            subject=subject,
            measures={"heartbeat_s": heartbeat, "network_timeout_s": rede},
            attrs={
                "heartbeat_raw": valores[_HEARTBEAT_KEY],
                "network_timeout_raw": valores[_NETWORK_KEY],
            },
            provenance={"extractor": EXTRACTOR_ID, "artifact": path},
        )
    ]


def _unresolved(reason: str, detail: str, subject: dict[str, Any], path: str) -> Fact:
    return Fact(
        kind="spark.timeout.unresolved",
        subject=subject,
        attrs={"reason": reason, "detail": detail},
        provenance={"extractor": EXTRACTOR_ID, "artifact": path},
    )


def extract_timeout_diagnosis(facts: Sequence[Fact], path: str) -> list[Fact]:
    """Uma categoria de timeout por run, com o que ela preteriu ao lado."""
    if not facts:
        # Pool vazio nao e lacuna: nada foi lido, e nada foi lido nao e o
        # mesmo que lido e sem sinal.
        return []

    runs = _runs_em_timeout(facts)
    sinais = _sinais_de_frase(facts)
    if runs:
        sinais.append(
            _sinal(
                "wall_clock",
                "glue_job_run_state",
                f"glue.job_run.state = TIMEOUT (timeout_min="
                f"{runs[0].measures.get('timeout_min')})",
                _subject_do_run(runs[0]),
            )
        )

    subject = _subject_do_run(runs[0] if runs else None)
    relacao = _relacao(facts, subject, path)

    if not sinais:
        return sort_facts(
            [
                _unresolved(
                    "no_timeout_evidence",
                    "Nenhuma fonte trouxe sinal de timeout: o run nao esta em TIMEOUT, "
                    "nenhum executor foi removido por heartbeat, e nenhuma stage falhou "
                    "com frase de broadcast ou de RPC.",
                    subject,
                    path,
                ),
                *relacao,
            ]
        )

    por_categoria = {s["category"]: s for s in sinais}
    ordenadas = [c for c in _PRECEDENCIA if c in por_categoria]
    escolhida = por_categoria[ordenadas[0]]

    saida: list[Fact] = [
        Fact(
            kind="spark.timeout.diagnosis",
            subject=escolhida["subject"] if not runs else subject,
            measures=_sintomas(facts),
            attrs={
                "category": escolhida["category"],
                "basis": escolhida["basis"],
                "evidence_text": escolhida["evidence_text"],
                "also_seen": ordenadas[1:],
            },
            provenance={"extractor": EXTRACTOR_ID, "artifact": path},
        ),
        *relacao,
    ]

    # Um run em TIMEOUT sem event log tem `wall_clock` como resposta honesta, e
    # nada mais: a lacuna registra que a categoria nao pode ser refinada, em vez
    # de deixar o leitor achar que broadcast e rede foram descartados.
    leu_log = any(f.kind in _BASIS_POR_KIND for f in facts)
    if runs and not leu_log:
        saida.append(
            _unresolved(
                "state_without_log",
                "O run esta em TIMEOUT e nao ha event log: o relogio de parede e a "
                f"unica categoria observavel. {_COMO_COLETAR_LOG}",
                subject,
                path,
            )
        )

    return sort_facts(saida)
