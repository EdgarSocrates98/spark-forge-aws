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

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

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
)


@dataclass(frozen=True)
class Localizado:
    uri: str
    line: int
    col: int | None


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


def localizar(
    finding: Mapping[str, Any],
    facts_por_id: Mapping[str, Mapping[str, Any]],
    raizes: Sequence[str],
    existe: Callable[[str], bool],
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
        if faltou_evidencia:
            return Recusa("evidencia_ausente")
        if subject.get("type") in SUBJECTS_DE_RUNTIME:
            return Recusa("runtime")
        return Recusa("sem_linha")
    file, line, col = alvo
    uri = _uri(file, raizes, existe)
    if isinstance(uri, Recusa):
        return uri
    return Localizado(uri=uri, line=line, col=col)
