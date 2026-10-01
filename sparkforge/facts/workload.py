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
        if isinstance(sla, int | float) and not isinstance(sla, bool):
            measures["sla_minutes"] = sla

        alvo_confiabilidade = entrada.get("reliability_target")
        if alvo_confiabilidade is not None:
            if isinstance(alvo_confiabilidade, bool) or not isinstance(
                alvo_confiabilidade, int | float
            ):
                facts.append(
                    _unresolved(
                        path,
                        "reliability_target_out_of_range",
                        "`reliability_target` precisa ser numero entre 0 e 1; veio "
                        f"{alvo_confiabilidade!r}.",
                        job_name=nome,
                    )
                )
            elif not 0 < alvo_confiabilidade <= 1:
                facts.append(
                    _unresolved(
                        path,
                        "reliability_target_out_of_range",
                        f"`reliability_target` veio {alvo_confiabilidade}. E fracao entre 0 e "
                        "1 -- 95 quase certamente quis dizer 0.95, e aceitar produziria um "
                        "alvo que capacidade nenhuma cumpre.",
                        job_name=nome,
                    )
                )
            else:
                measures["reliability_target"] = alvo_confiabilidade

        tolerancia_volume = entrada.get("volume_tolerance")
        if tolerancia_volume is not None:
            if (
                isinstance(tolerancia_volume, bool)
                or not isinstance(tolerancia_volume, int | float)
                or tolerancia_volume < 0
            ):
                facts.append(
                    _unresolved(
                        path,
                        "volume_tolerance_out_of_range",
                        "`volume_tolerance` precisa ser fracao nao negativa; veio "
                        f"{tolerancia_volume!r}.",
                        job_name=nome,
                    )
                )
            else:
                measures["volume_tolerance"] = tolerancia_volume

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

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

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
