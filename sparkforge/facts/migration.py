"""Observacoes de migracao entre versoes de Glue.

Uma fase em andamento adiciona analise de compatibilidade para migrar um job
Glue entre um par arbitrario de versoes. Este extrator OBSERVA sinais de
migracao no codigo-fonte e nunca julga: um import `com.amazonaws.*` (SDK v1
da AWS) e uma OBSERVACAO. Que ele seja bloqueante para uma versao-alvo
especifica e JUIZO, e pertence a uma regra com `runtime_scope` declarado no
catalogo (Task 7 desta fase). Essa divisao e o que permite julgar facts
antigos com um catalogo de regras novo sem reparsear o artefato -- o mesmo
contrato descrito em `sparkforge/findings/models.py` para `Fact`.

`EMITTED_KINDS` declara apenas `mig.sdk_import` por enquanto, embora a area de
migracao preveja mais kinds (`mig.emrfs_config`, `mig.ansi_risk`, etc.). Cada
um deles entra no vocabulario no MESMO commit em que ganha extrator e fixture
golden -- convencao ja em uso em `graph.py` e `emr_serverless.py`, cujos
comentarios de Task explicam por que: `tests/test_fixtures_kind_coverage.py`
exige golden para todo kind de `EMITTED_KINDS` assim que o modulo entra no
registro `EXTRACTORS` daquele teste (e do `tests/test_rules_catalog_reachability.py`).
Declarar kinds aspiracionais aqui nao quebra nada HOJE porque `migration`
ainda nao esta em nenhum dos dois registros -- mas quebraria assim que
alguem o registrasse antes de todos os kinds terem golden, entao o vocabulario
fica restrito ao que o modulo de fato emite.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "migration@0.1.0"

EMITTED_KINDS = frozenset({"mig.sdk_import"})

# SDK v1 da AWS para Java/Scala: `com.amazonaws.*`. Aparece em jobs Glue que
# chamam a API do SDK diretamente (fora do que `awsglue`/`boto3` cobrem), tipo
# comum em UDF ou bootstrap escrito antes da migracao para o SDK v2.
_SDK_V1_RE = re.compile(r"\bcom\.amazonaws\b")

# SDK v2, sucessor do v1. Observar os dois lado a lado deixa explicito qual
# geracao um job ja usa, sem precisar de uma segunda passada.
_SDK_V2_RE = re.compile(r"\bsoftware\.amazon\.awssdk\b")

_SDK_GENERATIONS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (_SDK_V1_RE, "v1", "com.amazonaws"),
    (_SDK_V2_RE, "v2", "software.amazon.awssdk"),
)


def _source_subject(file: str, line: int) -> dict[str, Any]:
    return {
        "type": "source_location",
        "file": file,
        "line": line,
        "col": 0,
        "symbol": "",
        "snippet": "",
    }


def _sdk_imports(text: str, anchor: str, provenance: dict[str, Any]) -> list[Fact]:
    facts: list[Fact] = []
    for lineno, linha in enumerate(text.split("\n"), start=1):
        for regex, geracao, pacote in _SDK_GENERATIONS:
            if regex.search(linha):
                facts.append(
                    Fact(
                        kind="mig.sdk_import",
                        subject=_source_subject(anchor, lineno),
                        attrs={"package": pacote, "generation": geracao},
                        provenance=provenance,
                    )
                )
    return facts


def extract_migration_path(path: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de um `.py`, ancorando o path relativo a `repo_root`."""
    rel = str(path.relative_to(repo_root)) if repo_root else str(path)
    anchor = rel.replace("\\", "/")

    text = path.read_text(encoding="utf-8-sig")
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"artifact": anchor, "artifact_sha256": sha, "extractor": EXTRACTOR_ID}

    facts = _sdk_imports(text, anchor, provenance)

    unknown = {f.kind for f in facts} - EMITTED_KINDS
    if unknown:
        raise AssertionError(f"kind fora do namespace declarado: {sorted(unknown)}")

    return sort_facts(facts)


def extract_migration_tree(root: Path, repo_root: Path | None = None) -> list[Fact]:
    """Extrai de todos os `.py` sob `root`, em ordem deterministica de path."""
    facts: list[Fact] = []
    for py in sorted(root.rglob("*.py")):
        if "__pycache__" in py.parts:
            continue
        facts.extend(extract_migration_path(py, repo_root or root))
    return sort_facts(facts)
