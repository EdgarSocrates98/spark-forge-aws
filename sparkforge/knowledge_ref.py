# sparkforge/knowledge_ref.py
"""Localizacao dos arquivos de `knowledge/` a partir do pacote.

Existe porque `knowledge/` passou a ser embarcado no artefato (Fase 3a) e
nenhum codigo sabia encontra-lo: as referencias no pacote eram todas comentario
e docstring. Empacotar 19 arquivos que ninguem consegue localizar seria peso sem
consumidor.

Espelha `sparkforge/rules/loader.py` na ordem de precedencia e na contencao de
caminho. Duas resolucoes com regras diferentes no mesmo pacote seriam a origem
do proximo bug de path.
"""
from __future__ import annotations

import os
from pathlib import Path


class KnowledgeError(ValueError):
    """Raiz de knowledge inexistente, ou caminho que escapa dela."""


def knowledge_dir() -> Path:
    """Raiz de knowledge: env var -> raiz do repo -> pacote.

    A mesma ordem de `catalog_dir()`. No repositorio a raiz vence, e o
    comportamento e identico ao de sempre; instalado por pip, so o fallback
    existe.
    """
    override = os.environ.get("SPARKFORGE_KNOWLEDGE")
    if override:
        resolved = Path(override).expanduser().resolve()
        if not resolved.is_dir():
            raise KnowledgeError(
                f"SPARKFORGE_KNOWLEDGE aponta para {resolved}, que nao e um diretorio existente"
            )
        return resolved

    repo_root = Path(__file__).resolve().parents[1]
    candidate = repo_root / "knowledge"
    if candidate.is_dir():
        return candidate

    # Fallback deliberadamente sem checagem de is_dir(), espelhando catalog_dir().
    # Quem consumir precisa validar (is_dir() ou o exists() de safe_knowledge_file);
    # catalog_dir() delega essa rede de seguranca para load_catalog(), que ainda
    # nao tem equivalente aqui (chega nas Tasks 4 e 5).
    return Path(__file__).resolve().parent / "knowledge"


def safe_knowledge_file(base: Path, name: str) -> Path:
    """Resolve `name` dentro de `base` e recusa o que escapar dele."""
    root = Path(base).expanduser().resolve()
    target = (root / name).resolve()
    if root != target and root not in target.parents:
        raise KnowledgeError(f"caminho fora do diretorio de knowledge: {target}")
    if not target.exists():
        raise KnowledgeError(
            f"{name} nao existe em {root}. "
            f"Liste o que ha com: sparkforge knowledge path"
        )
    return target
