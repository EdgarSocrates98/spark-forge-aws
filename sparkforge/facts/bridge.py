"""A ponte entre o codigo lido e a execucao medida, pelo callsite do stage.

## A lacuna que este modulo fecha, medida

O motor tem 146 regras. Medido em 2026-09-02, por `requires_facts`:

    20  usam so fato ESTATICO   (`callgraph.*`, `graph.*`, `pyspark.*`, `sql.*`)
    35  usam so fato de RUNTIME (`spark.*`, `glue.*`, `emr*`)
     0  cruzam os dois

Zero. O motor le codigo e le execucao, e nunca os poe lado a lado.

## A ancora sempre esteve no artefato

O Spark escreve o nome do stage no formato de CALLSITE -- `collect at job.py:42`
--, e `event_log.py` guarda esse nome verbatim desde sempre. `spark.stage.callsite`
(extrator) faz o parse; este modulo faz o CRUZAMENTO.

## Por que aqui, e nao no motor de regras

`engine._same_subject` agrupa por `subject.symbol` quando ha um, e por
`file:line` quando nao ha. Os dois lados desta ponte tem formas DIFERENTES:
`spark.stage.callsite` tem `symbol` (o nome do stage) e `pyspark.driver_collect`
tem `file`/`line`. Eles nunca cairiam no mesmo grupo, e forcar isso mudaria o
agrupamento de todas as outras regras.

Entao o cruzamento e DERIVACAO sobre a uniao dos facts -- funcao pura, no molde
exato de `build_call_graph`: nunca reparseia artefato, so le o que os extratores
ja resolveram.

## O que a corroboracao acrescenta, e o que ela NAO afirma

`SF-PY-002` diz *"este codigo pode puxar tudo para o driver"* -- leitura
estatica, `status: structural`. O fato derivado aqui diz *"este codigo puxou N
bytes para o driver, e aqui esta o stage"*.

**Nao ha atribuicao de custo.** O callsite diz onde o RDD NASCEU, nao quanto
aquela linha custou -- a regra 13 do `CLAUDE.md` proibe a segunda leitura, e o
`measures` deste fato traz o volume do STAGE, nomeado como tal.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EMITTED_KINDS = frozenset(
    {
        "bridge.driver_collect_confirmed",
        "bridge.unresolved",
        "bridge.analyzed",
    }
)

# O lado estatico que esta ponte atravessa hoje. UM so, e de proposito: cada
# kind acrescentado aqui precisa de fixture com os DOIS artefatos, e uma lista
# que cresce sem golden e superficie que envelhece sem que nada acuse.
_ESTATICO = "pyspark.driver_collect"
_CALLSITE = "spark.stage.callsite"

# Os kinds de volume do stage, na ordem em que se prefere um sobre o outro. O
# primeiro que existir manda: `task_input` mede o que ENTROU no stage, que e o
# numero que corrobora um `collect`; `shuffle` mede movimentacao, que e outra
# coisa e so serve quando o primeiro falta.
_VOLUME = ("spark.stage.task_input", "spark.stage.shuffle")


def _subject_do_artefato(nome: str) -> dict[str, Any]:
    """O subject das entradas que falam do ARTEFATO inteiro, e nao de um ponto.

    `subject.type` e enum FECHADO no schema de `Fact`, e `artifact` nao esta
    nele. A convencao que as outras sentinelas ja usam -- `pyspark.module_analyzed`,
    `callgraph.summary`, `graph.module_analyzed` -- e `source_location` ancorada
    em `line: 0`, que `engine._same_subject` le como grupo proprio: ela prova que
    a varredura aconteceu, sem afirmar nada sobre uma localizacao especifica.
    """
    return {
        "type": "source_location",
        "file": nome,
        "line": 0,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _chave(arquivo: str, linha: Any) -> str:
    """`basename:linha`, que e a unica forma em que os dois lados coincidem.

    O lado estatico ancora em caminho relativo ao artefato (`job.py`); o event
    log escreve o caminho que o executor viu (`/opt/src/job.py`). Casar o
    caminho inteiro exigiria que as duas convencoes coincidissem por acidente.

    A LINHA entra na chave, e nao so o arquivo: dois `collect` no mesmo arquivo
    sao dois callsites, e casar por arquivo os confundiria -- exatamente o falso
    positivo que `_same_subject` do motor evita agrupando por localizacao.
    """
    base = str(arquivo).replace("\\", "/").rsplit("/", 1)[-1]
    return f"{base}:{linha}"


def _volume_do_stage(facts: Sequence[Fact], stage_symbol: str) -> tuple[str, dict]:
    """As medidas do stage que corroboram, e de qual kind elas vieram.

    Devolve `("", {})` quando nenhum kind de volume existe para aquele stage --
    e isso NAO e erro: um stage pode aparecer no log sem metrica de entrada, e
    inventar zero seria afirmar que nada entrou.
    """
    for kind in _VOLUME:
        for fato in facts:
            if fato.kind == kind and (fato.subject or {}).get("symbol") == stage_symbol:
                return kind, dict(fato.measures or {})
    return "", {}


def build_bridge(facts: Sequence[Fact], path_hint: str = "") -> list[Fact]:
    """Cruza o lado estatico com o callsite do stage, e devolve os derivados.

    Funcao PURA sobre Facts: nunca reparseia fonte nem event log.

    Sem um dos dois lados, devolve `bridge.unresolved` NOMEADO em vez de lista
    vazia. Lista vazia se le como "nada a corroborar"; o que ha e "faltou o
    artefato do outro lado", e as duas coisas mandam o operador a lugares
    diferentes.
    """
    estaticos = [f for f in facts if f.kind == _ESTATICO]
    callsites = [
        f
        for f in facts
        if f.kind == _CALLSITE and (f.attrs or {}).get("resolved") is True
    ]

    provenance = {
        "artifact": path_hint or "facts",
        "artifact_sha256": "",
        "extractor": "bridge@0.1.0",
    }
    saida: list[Fact] = []

    if not estaticos or not callsites:
        razao = (
            "sem_fato_estatico"
            if not estaticos
            else "sem_callsite_resolvido"
        )
        destrava = (
            "extraia o codigo-fonte com `analyze pyspark`"
            if not estaticos
            else (
                "extraia o event log com `analyze event-log`; se ja extraiu, os "
                "nomes de stage nao tem a forma `<metodo> at <arquivo>.py:<linha>` "
                "-- veja `spark.stage.callsite.attrs.reason`"
            )
        )
        saida.append(
            Fact(
                kind="bridge.unresolved",
                subject=_subject_do_artefato(path_hint or "facts"),
                measures={
                    "static_facts": len(estaticos),
                    "resolved_callsites": len(callsites),
                },
                attrs={"reason": razao, "unblocked_by": destrava},
                provenance=provenance,
            )
        )
        saida.append(_analisado(provenance, 0, len(estaticos), len(callsites)))
        return sort_facts(saida)

    por_chave: dict[str, Fact] = {}
    for callsite in callsites:
        attrs = callsite.attrs or {}
        chave = _chave(attrs.get("file", ""), (callsite.measures or {}).get("line"))
        # O PRIMEIRO callsite de cada chave vence. Dois stages no mesmo callsite
        # sao a mesma linha executada duas vezes -- corroboram o mesmo fato
        # estatico, e emitir dois achados para uma linha duplicaria o relatorio.
        por_chave.setdefault(chave, callsite)

    corroborados = 0
    for estatico in estaticos:
        subject = estatico.subject or {}
        chave = _chave(subject.get("file", ""), subject.get("line"))
        callsite = por_chave.get(chave)
        if callsite is None:
            continue
        stage_symbol = str((callsite.subject or {}).get("symbol", ""))
        kind_volume, medidas = _volume_do_stage(facts, stage_symbol)
        corroborados += 1
        saida.append(
            Fact(
                kind="bridge.driver_collect_confirmed",
                # O subject e o do lado ESTATICO: o achado fala de uma linha de
                # codigo, e e para la que o operador vai. O stage viaja em
                # `attrs`, como evidencia de que a linha executou.
                subject=dict(subject),
                measures={
                    # Medidas do STAGE, nomeadas como tal. Nao sao "o custo desta
                    # linha" -- a regra 13 do CLAUDE.md proibe essa leitura, e o
                    # prefixo `stage_` existe para que ela nao seja possivel.
                    f"stage_{nome}": valor
                    for nome, valor in medidas.items()
                    if isinstance(valor, (int, float))
                },
                attrs={
                    "stage_name": stage_symbol,
                    "stage_id": (callsite.subject or {}).get("stage_id"),
                    "stage_method": (callsite.attrs or {}).get("method", ""),
                    "volume_kind": kind_volume or "nenhum",
                    "bounded": (estatico.attrs or {}).get("bounded"),
                },
                provenance=provenance,
            )
        )

    saida.append(
        _analisado(provenance, corroborados, len(estaticos), len(callsites))
    )
    return sort_facts(saida)


def _analisado(
    provenance: dict[str, Any],
    corroborados: int,
    estaticos: int,
    callsites: int,
) -> Fact:
    """A sentinela: a ponte RODOU, e estes sao os denominadores.

    Sem ela, zero corroboracoes e indistinguivel de "a ponte nao foi chamada" --
    e as duas coisas se leem igual num relatorio, que e o defeito que toda
    sentinela `*.analyzed` deste repositorio existe para fechar.
    """
    return Fact(
        kind="bridge.analyzed",
        subject=_subject_do_artefato(provenance["artifact"]),
        measures={
            "confirmed": corroborados,
            "static_facts": estaticos,
            "resolved_callsites": callsites,
        },
        attrs={},
        provenance=provenance,
    )


__all__ = ["EMITTED_KINDS", "build_bridge"]
