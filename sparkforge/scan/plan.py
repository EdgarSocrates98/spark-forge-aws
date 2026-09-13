"""Plano do `sparkforge scan` (§22): o que roda em cada arquivo, sem executar nada.

Duas portas decidem, e so elas:

- **artefato coletado** entra pelo `kind` que o proprio coletor gravou em
  `.sparkforge/artifacts/manifest.json`, e so depois de o sha256 conferir;
- **codigo do repositorio** entra pela extensao (`.py`, `.sql`, `.tf`,
  `.jsonl`), pela mesma varredura que os extratores usam
  (`varrer_source_files`), que ja pula `.sparkforge`, dependencias e cofres de
  credencial com a razao escrita.

JSON solto fora do manifesto NAO e classificado pelo conteudo: dez extratores
leem `.json`, e farejar chaves mandaria um dump ambiguo ao extrator errado. Ele
sai recusado por nome (`sem_manifesto`), como toda recusa daqui (regra 20).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from sparkforge.collect.base import MANIFEST_RELATIVE, verify_artifact
from sparkforge.facts.scan import varrer_source_files

# `kind` gravado pelos `collect_*` -> analyze que o le. `None` e kind conhecido
# sem extrator: `collect glue-job` grava a definicao IMPLANTADA do job em JSON
# com `kind="terraform"`, e o `analyze terraform` le HCL.
KIND_PARA_ANALYZE: dict[str, str | None] = {
    "event_log": "event-log",
    "glue_job_run": "glue-job-runs",
    "cloudwatch": "cloudwatch",
    "cloudwatch_logs": "cloudwatch-logs",
    "iceberg_metadata": "iceberg",
    "athena_workgroup": "athena-workgroup",
    "emr_cluster": "emr-cluster",
    "emr_serverless": "emr-serverless",
    "emr_eks": "emr-eks",
    "parquet_footer": "parquet-footer",
    "iam_access": "iam-access",
    "lakeformation": "lakeformation-grants",
    "glue_resource_link": "glue-resource-link",
    "terraform": None,
}
SEM_EXTRATOR = {
    "terraform": (
        "definicao implantada do job (collect glue-job) em JSON; o analyze terraform "
        "le HCL e nenhum extrator le este artefato"
    ),
}
EXTENSAO_PARA_ANALYZE: dict[str, tuple[str, ...]] = {
    ".py": ("pyspark", "sql"),
    ".sql": ("sql",),
    ".tf": ("terraform",),
    ".jsonl": ("event-log",),
}
PADROES = ("*.py", "*.sql", "*.tf", "*.jsonl", "*.json")
RECUSAS = (
    "sem_manifesto",
    "sha256_divergente",
    "kind_sem_analyze",
    "exige_job_name",
    "fora_da_raiz",
    "analyze_falhou",
)
_JOB_DO_SOURCE = re.compile(r"^glue:get_job_runs:(?P<job>[^/]+)/")


class ScanError(ValueError):
    """Entrada que impede montar o plano (manifesto ilegivel)."""


@dataclass(frozen=True)
class Entrada:
    analyze: str
    path: str
    origem: str
    job_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        saida: dict[str, Any] = {"analyze": self.analyze, "path": self.path, "origin": self.origem}
        if self.job_name is not None:
            saida["job_name"] = self.job_name
        return saida


@dataclass(frozen=True)
class Recusa:
    path: str
    reason: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "reason": self.reason, "detail": self.detail}


@dataclass(frozen=True)
class Plano:
    entradas: tuple[Entrada, ...]
    recusas: tuple[Recusa, ...]
    pulos: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entradas],
            "refused": [r.to_dict() for r in self.recusas],
            "skipped": [dict(p) for p in self.pulos],
        }


def _manifesto(raiz: Path) -> list[dict[str, Any]]:
    caminho = raiz / MANIFEST_RELATIVE
    if not caminho.is_file():
        return []
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScanError(f"{MANIFEST_RELATIVE.as_posix()}: manifesto ilegivel: {exc}") from exc
    if not isinstance(dados, list):
        raise ScanError(f"{MANIFEST_RELATIVE.as_posix()}: o manifesto precisa ser uma lista.")
    return [e for e in dados if isinstance(e, dict)]


def _dentro_da_raiz(raiz: Path, relativo: str) -> bool:
    if not relativo or PurePosixPath(relativo).is_absolute() or Path(relativo).is_absolute():
        return False
    try:
        (raiz / relativo).resolve().relative_to(raiz.resolve())
    except ValueError:
        return False
    return True


def _do_manifesto(raiz: Path) -> tuple[list[Entrada], list[Recusa]]:
    entradas: list[Entrada] = []
    recusas: list[Recusa] = []
    jobs: set[tuple[str, str]] = set()
    for item in _manifesto(raiz):
        relativo = str(item.get("path") or "")
        kind = str(item.get("kind") or "")
        if not _dentro_da_raiz(raiz, relativo):
            recusas.append(Recusa(relativo, "fora_da_raiz", "caminho do manifesto fora da raiz"))
            continue
        conferido = verify_artifact(item, raiz)
        if not conferido["present"]:
            recusas.append(Recusa(relativo, "sha256_divergente", "artefato ausente"))
            continue
        if not conferido["hash_matches"]:
            recusas.append(Recusa(relativo, "sha256_divergente", "sha256 nao bate com o manifesto"))
            continue
        if kind not in KIND_PARA_ANALYZE:
            recusas.append(Recusa(relativo, "kind_sem_analyze", f"kind {kind!r} desconhecido"))
            continue
        analyze = KIND_PARA_ANALYZE[kind]
        if analyze is None:
            recusas.append(Recusa(relativo, "kind_sem_analyze", SEM_EXTRATOR.get(kind, "")))
            continue
        if analyze == "glue-job-runs":
            achado = _JOB_DO_SOURCE.match(str(item.get("source") or ""))
            if achado is None:
                recusas.append(Recusa(
                    relativo, "exige_job_name", "source fora da forma glue:get_job_runs:<job>/<run>"
                ))
                continue
            pasta = PurePosixPath(relativo).parent.as_posix()
            chave = (pasta, achado["job"])
            if chave not in jobs:
                jobs.add(chave)
                entradas.append(Entrada(analyze, pasta, "manifesto", achado["job"]))
            continue
        entradas.append(Entrada(analyze, relativo, "manifesto"))
    return entradas, recusas


def plan(raiz: Path | str) -> Plano:
    """O plano do scan sobre `raiz`. Puro: le o disco e nao grava nada."""
    raiz = Path(raiz)
    entradas, recusas = _do_manifesto(raiz)
    pulos: dict[str, str] = {}
    for padrao in PADROES:
        varredura = varrer_source_files(raiz, padrao)
        for pulo in varredura.pulos:
            pulos.setdefault(pulo.relativo, pulo.razao)
        for arquivo in varredura.arquivos:
            relativo = arquivo.relative_to(raiz).as_posix()
            sufixo = arquivo.suffix.lower()
            if sufixo == ".json":
                recusas.append(Recusa(
                    relativo, "sem_manifesto",
                    "JSON fora do manifesto nao e classificado pelo conteudo",
                ))
                continue
            for analyze in EXTENSAO_PARA_ANALYZE.get(sufixo, ()):
                entradas.append(Entrada(analyze, relativo, "extensao"))
    entradas.sort(key=lambda e: (e.analyze, e.path, e.job_name or ""))
    recusas.sort(key=lambda r: (r.reason, r.path))
    return Plano(
        tuple(entradas),
        tuple(recusas),
        tuple({"path": p, "reason": r} for p, r in sorted(pulos.items())),
    )
