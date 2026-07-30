"""Interface de coleta de artefatos (Fase 0) e o manifesto que a sustenta.

Apenas a interface e o manifesto pertencem a Fase 0 -- os coletores AWS
completos (event log via CloudWatch/S3, Terraform state, `explain()`,
metadados Iceberg) sao Fase 1, porque dependem de boto3 e de credenciais
que o nucleo determinístico nao deve exigir.

O manifesto e o que faz o resume funcionar entre ferramentas: ele registra
sha256, origem e o comando de recoleta para artefatos que, deliberadamente,
nao sao committados -- podem carregar dados de negocio e centenas de MB. Uma
sessao que retoma em outra ferramenta le o manifesto e sabe exatamente o que
falta e como coletar de novo.
"""
from __future__ import annotations

from sparkforge.collect.base import (
    ARTIFACT_KINDS,
    MANIFEST_RELATIVE,
    ArtifactEntry,
    CollectorUnavailable,
    load_manifest,
    manifest_path,
    register_artifact,
    require_boto3,
    verify_all,
    verify_artifact,
)

__all__ = [
    "ARTIFACT_KINDS",
    "MANIFEST_RELATIVE",
    "ArtifactEntry",
    "CollectorUnavailable",
    "load_manifest",
    "manifest_path",
    "register_artifact",
    "require_boto3",
    "verify_all",
    "verify_artifact",
]
