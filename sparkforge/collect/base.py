"""Interface de coletores e o manifesto de artefatos.

`ArtifactEntry` e o manifesto (`manifest.json`) sao a Fase 0 da coleta:
descrevem *o que* um artefato e e *como* recolete-lo, sem implementar nenhum
coletor real. Os coletores completos (event log via CloudWatch/S3, Terraform
state, `explain()`, metadados Iceberg) sao Fase 1.

Artefatos brutos nunca sao committados -- podem carregar dados de negocio e
chegar a centenas de MB. O que e committado e este manifesto: sha256, origem
e o comando exato de recoleta, para que uma sessao que retome em outra
ferramenta (Devin -> Claude Code, ou vice-versa) saiba exatamente o que
falta e como obter de novo, sem depender de memoria de contexto.

Este modulo nao importa boto3 no topo do arquivo. O nucleo determinístico
roda num sandbox Devin e em CI sem boto3 instalado; so `require_boto3()`
toca o import, e so quando um coletor real (Fase 1) precisar dele.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MANIFEST_RELATIVE = Path(".sparkforge") / "artifacts" / "manifest.json"

ARTIFACT_KINDS = (
    "event_log",
    "terraform",
    "explain",
    "cloudwatch",
    "iceberg_metadata",
    "athena_workgroup",
    "source",
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class CollectorUnavailable(RuntimeError):
    """boto3 ausente, ou credenciais AWS indisponiveis para um coletor real."""


@dataclass(frozen=True)
class ArtifactEntry:
    """Uma linha do manifesto: identidade, integridade e como recolete-la.

    `collect_command` nunca pode ser vazio -- um artefato sem comando de
    recoleta deixa `resume()` cego: o case sabe que falta algo, mas nao sabe
    como resolver. Isso derrota o proposito do manifesto.
    """

    kind: str
    path: str
    sha256: str
    source: str
    collect_command: str
    collected_at: str

    def __post_init__(self) -> None:
        if self.kind not in ARTIFACT_KINDS:
            raise ValueError(
                f"kind desconhecido: {self.kind!r} "
                f"(esperado uma de: {', '.join(ARTIFACT_KINDS)})"
            )
        if not _SHA256_RE.match(self.sha256 or ""):
            raise ValueError(
                f"sha256 malformado: {self.sha256!r} (esperado 64 caracteres hex minusculos)"
            )
        if not self.collect_command:
            raise ValueError(
                "collect_command vazio: um artefato sem comando de recoleta deixa "
                "o resume cego, o que derrota o proposito do manifesto."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.path,
            "sha256": self.sha256,
            "source": self.source,
            "collect_command": self.collect_command,
            "collected_at": self.collected_at,
        }


def manifest_path(root: Path | str) -> Path:
    return Path(root) / MANIFEST_RELATIVE


def load_manifest(root: Path | str) -> list[dict[str, Any]]:
    """Le o manifesto. Ausente, ilegivel ou malformado: lista vazia, nunca excecao.

    `resume()` consome isto para decidir o que falta; um manifesto que nao
    pode ser lido deve degradar para "nada registrado", nao travar a
    rehidratacao do case.
    """
    path = manifest_path(root)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


def register_artifact(entry: ArtifactEntry, root: Path | str) -> list[dict[str, Any]]:
    """Adiciona `entry` ao manifesto, substituindo qualquer entrada com o
    mesmo `path`. Escreve JSON ordenado e deterministico: o mesmo conjunto
    logico de entradas sempre produz o mesmo texto, condicao necessaria para
    o manifesto ser diffavel e revisavel como qualquer outro artefato de
    codigo committado.
    """
    entries = [e for e in load_manifest(root) if e.get("path") != entry.path]
    entries.append(entry.to_dict())
    entries.sort(key=lambda e: e["path"])

    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(entries, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return entries


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(entry_dict: dict[str, Any], root: Path | str) -> dict[str, Any]:
    """Confere presenca e integridade de um artefato do manifesto no disco.

    `hash_matches` so pode ser True quando o arquivo esta presente e o
    sha256 recalculado bate com o registrado -- um artefato ausente nunca
    "combina" por vacuidade.
    """
    rel_path = entry_dict.get("path", "")
    file_path = Path(root) / rel_path
    present = file_path.is_file()
    hash_matches = False
    if present:
        try:
            hash_matches = _sha256_of(file_path) == entry_dict.get("sha256")
        except OSError:
            hash_matches = False
    return {
        "kind": entry_dict.get("kind"),
        "path": rel_path,
        "present": present,
        "hash_matches": hash_matches,
        "collect_command": entry_dict.get("collect_command"),
        "source": entry_dict.get("source"),
    }


def verify_all(root: Path | str) -> list[dict[str, Any]]:
    """Verifica todas as entradas do manifesto de `root` de uma vez."""
    return [verify_artifact(entry, root) for entry in load_manifest(root)]


def require_boto3() -> Any:
    """Importa boto3 sob demanda. Nunca importado no topo deste modulo: o
    nucleo determinístico roda num sandbox Devin e em CI sem boto3
    instalado, e nenhum deles deveria falhar por causa de um coletor Fase 1
    que ninguem chamou.
    """
    try:
        import boto3
    except ImportError as exc:
        raise CollectorUnavailable(
            "boto3 nao disponivel. Instale com `pip install 'sparkforge-aws[aws]'` "
            "para usar coletores AWS, ou colete o artefato manualmente (AWS CLI ou "
            "console) e registre-o com `sparkforge.collect.register_artifact`."
        ) from exc
    return boto3
