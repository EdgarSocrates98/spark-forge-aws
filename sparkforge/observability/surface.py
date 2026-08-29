"""Quanto pesa a superficie do SparkForge ANTES de qualquer chamada.

Tres superficies, e todas sao bytes de disco ou de serializacao -- nada aqui
executa tool, roda suite ou chama modelo. E por isso que esta medida cabe num CI
que hoje nao consegue rodar a suite inteira.

  tools     -- o que `tools/list` devolve, por tool
  skills    -- cada `SKILL.md`
  knowledge -- cada documento de `knowledge/`

O numero de cada uma e o que `docs/surface.lock.json` trava: crescer a superficie
passa a exigir declarar o crescimento, que e o que este repositorio ja faz com
toda alegacao publicada.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SERIALIZATION_BASIS = 'len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))'


def _bytes_of(obj: Any) -> int:
    """Sem `default=str`: mascarar objeto nao serializavel com `str()` mediria
    a conversao em vez do payload, e o `TypeError` e o sinal certo de que um
    schema tem coisa que nao deveria ter."""
    return len(json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def measure_directory(root: Path, pattern: str) -> dict[str, Any]:
    """Bytes de cada arquivo que casa `pattern`, e o que nao deu para ler.

    Chave e o caminho RELATIVO a `root` (com `/`), nao so o nome do arquivo:
    `knowledge/` repete nome de arquivo em subdiretorio diferente (por exemplo
    `runtime-matrix.md` em `emr/`, `emr-serverless/` e `glue/`), e indexar por
    nome faria um pisar no outro -- a medida ficaria menor que a superficie real,
    exatamente o erro que esta funcao existe para nao cometer.

    Arquivo ilegivel entra em `unresolved` com o caminho: pular em silencio
    teria o mesmo efeito de encolher a superficie sem avisar.
    """
    por_caminho: dict[str, int] = {}
    nao_resolvidos: list[str] = []
    for caminho in sorted(root.rglob(pattern)):
        if not caminho.is_file():
            continue
        chave = caminho.relative_to(root).as_posix()
        try:
            por_caminho[chave] = len(caminho.read_text(encoding="utf-8").encode("utf-8"))
        except (UnicodeDecodeError, OSError):
            nao_resolvidos.append(chave)
    return {
        "by_name": por_caminho,
        "total_bytes": sum(por_caminho.values()),
        "document_count": len(por_caminho),
        "unresolved": nao_resolvidos,
    }


def measure_tool_catalogue() -> dict[str, Any]:
    """Bytes do que `tools/list` devolve, por tool.

    Le `TOOLS` direto -- e o mesmo objeto que o servidor serializa, e medir a
    partir dele nao exige subir servidor nenhum.
    """
    from sparkforge.adapters.tools import TOOLS

    por_nome = {nome: _bytes_of(declaracao) for nome, declaracao in TOOLS.items()}
    return {
        "by_name": por_nome,
        "total_bytes": sum(por_nome.values()),
        "tool_count": len(por_nome),
        "basis": SERIALIZATION_BASIS,
    }


def measure_skills(root: Path) -> dict[str, Any]:
    """Bytes de cada `SKILL.md`, indexados pelo nome do DIRETORIO.

    `measure_directory` indexaria todos por `SKILL.md` mesmo com a chave sendo o
    caminho relativo -- e um dicionario com dezenas de entradas iguais a
    `<skill>/SKILL.md` ainda assim fica menos legivel do que o nome da skill.
    Aqui a chave e sempre unica por construcao: cada skill tem um diretorio so.
    """
    por_nome: dict[str, int] = {}
    nao_resolvidos: list[str] = []
    for caminho in sorted(root.rglob("SKILL.md")):
        try:
            por_nome[caminho.parent.name] = len(
                caminho.read_text(encoding="utf-8").encode("utf-8")
            )
        except (UnicodeDecodeError, OSError):
            nao_resolvidos.append(caminho.parent.name)
    return {
        "by_name": por_nome,
        "total_bytes": sum(por_nome.values()),
        "document_count": len(por_nome),
        "unresolved": nao_resolvidos,
    }


def measure_surface(root: Path | None = None) -> dict[str, Any]:
    """As tres superficies, medidas sem executar nada."""
    raiz = root or ROOT
    return {
        "tools": measure_tool_catalogue(),
        "skills": measure_skills(raiz / "skills"),
        "knowledge": measure_directory(raiz / "knowledge", "*.md"),
    }
