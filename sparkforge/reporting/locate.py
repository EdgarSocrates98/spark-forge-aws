"""Onde, no repositorio, um finding pode ser mostrado -- ou por que nao pode.

O GitHub Code Scanning descarta resultado sem localizacao, e interpreta `uri`
relativo a partir da raiz do repositorio (documentacao de SARIF do GitHub).
Medido nos goldens de `fixtures/` em 2026-09-11: dos 222 findings, cerca de 77
tem linha em arquivo de codigo; os 116 de `job_run`, `stage` e `table` vem de
execucao e nao tem linha nenhuma. Ancora-los numa linha qualquer seria precisao
falsa, entao o que nao se localiza sai como recusa com nome (regra 20).

Duas coisas nao sao obvias, e as duas sao decisao:

* `subject.file` e relativo ao DIRETORIO ANALISADO, e nao a raiz do git:
  `analyze pyspark --path jobs` chama `extract_tree(target, repo_root=target)`.
  Por isso quem chama declara as raizes (`--source-root`), na ordem em que rodou
  os `analyze`. Um arquivo que existe em duas raizes e `caminho_ambiguo`: chutar
  poria o alerta no arquivo errado.
* A evidencia so empresta localizacao quando o fact dela e de CODIGO
  (`source_location`, `tf_resource`). Um fact com linha num dump ou num
  `plan.txt` apontaria o revisor para algo que nao esta no diff.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Any

from sparkforge.facts.runtime_detect import EMITTED_KINDS as _KINDS_DA_DETECCAO
from sparkforge.facts.runtime_detect import SUBJECT_SYMBOLS as _SIMBOLOS_DA_DETECCAO

SUBJECTS_COM_CODIGO = frozenset({"source_location", "tf_resource"})
SUBJECTS_LOCALIZAVEIS = SUBJECTS_COM_CODIGO | {"plan_node"}
SUBJECTS_DE_RUNTIME = frozenset({"job_run", "stage", "table"})

MOTIVOS = (
    "evidencia_ausente",
    "runtime",
    "sem_linha",
    "arquivo_fora_do_repo",
    "caminho_ambiguo",
    "limite_do_github",
    "callsite_ausente",
    "callsite_sem_forma",
    "callsite_nao_python",
    "callsite_ambiguo",
)

CALLSITE_KIND = "spark.stage.callsite"
# Nome de stage da JVM: `save at Etl.scala:120`. O extrator do event log so
# resolve callsite Python e grava `resolved: false` com o nome base para o
# resto; a linha do Scala esta no nome do stage, e e lida aqui -- na
# apresentacao --, para que nenhum golden de extrator mude.
_SIMBOLO_JVM = re.compile(r"^(?P<metodo>\w+) at (?P<arquivo>[^:\s]+):(?P<linha>\d+)$")

Callsites = Mapping[tuple[Any, str], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class Localizado:
    uri: str
    line: int
    col: int | None
    nota: str | None = None


@dataclass(frozen=True)
class Recusa:
    motivo: str


def _uri(file: str, raizes: Sequence[str], existe: Callable[[str], bool]) -> str | Recusa:
    candidatos = []
    for raiz in raizes:
        caminho = PurePosixPath(file) if raiz in (".", "") else PurePosixPath(raiz) / file
        candidatos.append(caminho.as_posix())
    achados = sorted({c for c in candidatos if existe(c)})
    if not achados:
        return Recusa("arquivo_fora_do_repo")
    if len(achados) > 1:
        return Recusa("caminho_ambiguo")
    return achados[0]


def _linha(valor: Any) -> int | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int) and valor >= 1:
        return valor
    return None


def _de_subject(
    subject: Mapping[str, Any], tipos: frozenset[str]
) -> tuple[str, int, int | None] | None:
    if subject.get("type") not in tipos or not subject.get("file"):
        return None
    line = _linha(subject.get("line"))
    if line is None:
        return None
    return str(subject["file"]).replace("\\", "/"), line, _linha(subject.get("col"))


@lru_cache(maxsize=1)
def _regras_que_leem_a_deteccao() -> frozenset[str]:
    """`rule_id` das regras cujo `requires_facts` intersecta `_KINDS_DA_DETECCAO`.

    Cacheado porque o catalogo nao muda durante a vida do processo -- mesmo
    padrao de `diagnosis.root_cause._governanca_declarada` -- e porque
    `localizar` roda uma vez por finding dentro do laco de `projetar`, que
    recarregaria o catalogo do disco a cada achado sem o cache. Catalogo
    indisponivel devolve conjunto vazio em vez de derrubar a chamada (regra 27).
    """
    try:
        from sparkforge.rules.loader import load_catalog

        regras = load_catalog()
    except Exception:  # noqa: BLE001 - medicao nunca derruba a chamada
        return frozenset()
    return frozenset(
        str(regra["id"])
        for regra in regras
        if set(regra.get("requires_facts") or []) & _KINDS_DA_DETECCAO
    )


def _subject_da_deteccao(finding: Mapping[str, Any], subject: Mapping[str, Any]) -> bool:
    """O subject que a deteccao de runtime escreve (`env.*`, `databricks.photon`)
    -- e SO quando a REGRA do achado de fato le um kind dela.

    A forma sozinha (`type: job_run`, so `type` e `symbol`, `symbol` em
    `runtime_detect.SUBJECT_SYMBOLS`) NAO basta, e tratá-la como suficiente e
    um risco real de mascarar evidencia ausente de verdade: outros extratores
    emitem subject `job_run` de duas chaves com symbol ARBITRARIO --
    `athena_workgroup` (nome do workgroup), `emr_cluster` (cluster_id),
    `emr_serverless` (application_id), `benchmark` (path_hint). Um workgroup
    chamado `athena`, um cluster_id `platform` ou um path_hint `spark` colide
    com `SUBJECT_SYMBOLS` por acaso, sem ligacao nenhuma com a deteccao de
    runtime. Por isso a segunda condicao, obrigatoria: o `requires_facts` da
    regra do achado (achada por `rule_id`, via `_regras_que_leem_a_deteccao`)
    precisa intersectar `runtime_detect.EMITTED_KINDS` -- so uma regra que LE
    um kind da deteccao pode ter sido silenciada por ele faltar.

    Com as duas condicoes: um facts.json gravado antes de o scan gravar os
    facts da deteccao nao os traz, e o achado SF-ENV-00x que os cita ficaria em
    `evidencia_ausente`. O fact faltante e de runtime, sem linha em arquivo
    nenhum: o motivo certo e `runtime`.
    """
    forma = (
        subject.get("type") == "job_run"
        and set(subject) == {"type", "symbol"}
        and subject.get("symbol") in _SIMBOLOS_DA_DETECCAO
    )
    if not forma:
        return False
    return str(finding.get("rule_id") or "") in _regras_que_leem_a_deteccao()


def indice_de_callsites(facts_por_id: Mapping[str, Mapping[str, Any]]) -> Callsites:
    """Os `spark.stage.callsite` da uniao, por (`stage_id`, artefato de origem).

    O `stage_id` recomeca em 0 em cada aplicacao Spark: na uniao de dois event
    logs, o stage 0 de um nao e o do outro. Medido em 2026-09-11: nos 34 pares
    (fact de stage, callsite) do corpus, o artefato e o mesmo.
    """
    indice: dict[tuple[Any, str], list[Mapping[str, Any]]] = {}
    for fact in facts_por_id.values():
        if fact.get("kind") != CALLSITE_KIND:
            continue
        chave = (
            (fact.get("subject") or {}).get("stage_id"),
            str((fact.get("provenance") or {}).get("artifact") or ""),
        )
        indice.setdefault(chave, []).append(fact)
    return indice


def _candidato(raiz: str, sufixo: str) -> str:
    if raiz in (".", ""):
        return PurePosixPath(sufixo).as_posix()
    return (PurePosixPath(raiz) / sufixo).as_posix()


def _por_sufixo(
    partes: Sequence[str], raizes: Sequence[str], existe: Callable[[str], bool]
) -> str | Recusa:
    """Do sufixo mais longo ao mais curto; para no primeiro nivel que casa.

    Um nivel com mais de um arquivo e `caminho_ambiguo`, e a busca para ali:
    cair para o nome base depois de um empate trocaria ambiguidade por chute.
    """
    for inicio in range(len(partes)):
        sufixo = "/".join(partes[inicio:])
        achados = sorted({c for c in (_candidato(r, sufixo) for r in raizes) if existe(c)})
        if len(achados) == 1:
            return achados[0]
        if len(achados) > 1:
            return Recusa("caminho_ambiguo")
    return Recusa("arquivo_fora_do_repo")


def _stage_da_evidencia(
    finding: Mapping[str, Any], facts_por_id: Mapping[str, Mapping[str, Any]]
) -> tuple[Any, str] | None:
    """(`stage_id`, artefato) do primeiro fact de stage da evidencia.

    Para um finding de stage, so conta o fact do MESMO `stage_id` do subject.
    """
    subject_finding = finding.get("subject") or {}
    do_stage = subject_finding.get("type") == "stage"
    for fact_id in finding.get("evidence") or []:
        fact = facts_por_id.get(fact_id) or {}
        subject = fact.get("subject") or {}
        if subject.get("type") != "stage":
            continue
        if do_stage and subject.get("stage_id") != subject_finding.get("stage_id"):
            continue
        artefato = str((fact.get("provenance") or {}).get("artifact") or "")
        return subject.get("stage_id"), artefato
    return None


def _candidatos_de_callsite(
    finding: Mapping[str, Any],
    facts_por_id: Mapping[str, Mapping[str, Any]],
    callsites: Callsites,
) -> list[Mapping[str, Any]] | Recusa | None:
    chave = _stage_da_evidencia(finding, facts_por_id)
    if chave is not None:
        return list(callsites.get(chave, ()))
    subject = finding.get("subject") or {}
    if subject.get("type") != "stage":
        return None
    # Sem fact de stage na evidencia nao ha artefato: o callsite so vale se o
    # `stage_id` for de uma aplicacao so na uniao.
    por_artefato = {
        artefato: lista
        for (stage_id, artefato), lista in callsites.items()
        if stage_id == subject.get("stage_id")
    }
    if len(por_artefato) > 1:
        return Recusa("callsite_ambiguo")
    return [c for lista in por_artefato.values() for c in lista]


def _caminho_de_stage(
    finding: Mapping[str, Any],
    facts_por_id: Mapping[str, Mapping[str, Any]],
    raizes: Sequence[str],
    existe: Callable[[str], bool],
    callsites: Callsites,
) -> Localizado | Recusa | None:
    """Linha da ACAO que originou o stage, ou a recusa precisa. `None` sem stage."""
    candidatos = _candidatos_de_callsite(finding, facts_por_id, callsites)
    if candidatos is None or isinstance(candidatos, Recusa):
        return candidatos
    if not candidatos:
        return Recusa("callsite_ausente")
    callsite = candidatos[0]
    subject = callsite.get("subject") or {}
    attrs = callsite.get("attrs") or {}
    if attrs.get("resolved"):
        linha = _linha((callsite.get("measures") or {}).get("line"))
        caminho = str(attrs.get("path") or attrs.get("file") or "").replace("\\", "/")
        partes = [p for p in caminho.split("/") if p]
        if linha is None or not partes:
            return Recusa("callsite_sem_forma")
        metodo = str(attrs.get("method") or "acao")
        onde = _por_sufixo(partes, raizes, existe)
    else:
        casado = _SIMBOLO_JVM.match(str(subject.get("symbol") or ""))
        linha = _linha(int(casado["linha"])) if casado else None
        if casado is None or linha is None:
            return Recusa("callsite_sem_forma")
        metodo = casado["metodo"]
        onde = _por_sufixo([casado["arquivo"]], raizes, existe)
        if isinstance(onde, Recusa) and onde.motivo == "arquivo_fora_do_repo":
            return Recusa("callsite_nao_python")
    if isinstance(onde, Recusa):
        return onde
    nota = (
        f"linha da acao `{metodo}` que originou o stage {subject.get('stage_id')} "
        "(nao e a causa)"
    )
    return Localizado(uri=onde, line=linha, col=None, nota=nota)


def localizar(
    finding: Mapping[str, Any],
    facts_por_id: Mapping[str, Mapping[str, Any]],
    raizes: Sequence[str],
    existe: Callable[[str], bool],
    callsites: Callsites | None = None,
) -> Localizado | Recusa:
    """`Localizado` quando o finding tem linha num arquivo do repositorio.

    Ordem: o `subject` do proprio finding; senao, o primeiro fact de `evidence`
    (na ordem do finding) que esteja na uniao e seja de codigo; e so entao a
    resolucao do arquivo pelas raizes. Os motivos de recusa sao testados na
    ordem de `MOTIVOS`.
    """
    subject = finding.get("subject") or {}
    alvo = _de_subject(subject, SUBJECTS_LOCALIZAVEIS)
    faltou_evidencia = False
    if alvo is None:
        for fact_id in finding.get("evidence") or []:
            fact = facts_por_id.get(fact_id)
            if fact is None:
                faltou_evidencia = True
                continue
            alvo = _de_subject(fact.get("subject") or {}, SUBJECTS_COM_CODIGO)
            if alvo is not None:
                break
    if alvo is None:
        # Sem linha propria nem evidencia de codigo: o stage, se houver, diz
        # onde a ACAO foi chamada -- e, quando nao diz, a recusa diz por que.
        indice = indice_de_callsites(facts_por_id) if callsites is None else callsites
        de_stage = _caminho_de_stage(finding, facts_por_id, raizes, existe, indice)
        if de_stage is not None:
            return de_stage
        if faltou_evidencia:
            return Recusa(
                "runtime" if _subject_da_deteccao(finding, subject) else "evidencia_ausente"
            )
        if subject.get("type") in SUBJECTS_DE_RUNTIME:
            return Recusa("runtime")
        return Recusa("sem_linha")
    file, line, col = alvo
    uri = _uri(file, raizes, existe)
    if isinstance(uri, Recusa):
        return uri
    return Localizado(uri=uri, line=line, col=col)
