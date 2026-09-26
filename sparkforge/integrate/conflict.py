"""Copia vendorizada em dobro no repositorio atual (D9).

`scripts/install_skills.py` copia skills e agents para dentro do repositorio. Com
a integracao de usuario, o mesmo nome aparece duas vezes nos hosts que nao
separam por namespace. Aqui a copia e achada por NOME e classificada por
CONTEUDO: `identico` quando e byte a byte o que o wheel renderiza para aquele
diretorio, `customizado` quando difere.

Tres escolhas, e nenhuma e tomada sem o operador:

- `overwrite` (SOBRESCREVER): apaga do repositorio as duas classes;
- `merge` (MESCLAR): apaga so os identicos e lista os customizados, que continuam
  em dobro;
- `ignore` (IGNORAR): nao toca no repositorio. E o padrao sem terminal e sem
  `--on-conflict`.

No proprio repositorio fonte do SparkForge (tem `scripts/sync_skills.py`) os
espelhos `.claude/`, `.agents/` e `.github/` sao gerados e versionados: sai a
recusa `repositorio_fonte` e nada e tocado.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from sparkforge.integrate import render, sources

ESCOLHAS = ("overwrite", "merge", "ignore")

# (diretorio no repo, tipo, plataforma do renderizador, hosts que o leem)
VENDOR_LOCATIONS = (
    (".claude/skills", "skill", "claude", ("claude",)),
    (".agents/skills", "skill", "devin", ("devin", "codex", "copilot")),
    (".claude/agents", "agent", "claude", ("claude",)),
    (".agents/agents", "agent", "devin", ("devin",)),
    (".github/agents", "agent", "github", ("copilot",)),
)

_RESPOSTAS = {
    "s": "overwrite", "sobrescrever": "overwrite", "overwrite": "overwrite",
    "m": "merge", "mesclar": "merge", "merge": "merge",
    "i": "ignore", "ignorar": "ignore", "ignore": "ignore", "": "ignore",
}


def is_source_repo(repo: Path) -> bool:
    return (Path(repo) / "scripts" / "sync_skills.py").is_file()


def _arquivos(base: Path) -> dict[str, bytes]:
    return {
        p.relative_to(base).as_posix(): p.read_bytes()
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }


def _colisoes_de_skill(
    repo: Path, local: str, plataforma: str, hosts: tuple[str, ...], root: Path
) -> list[dict[str, Any]]:
    skills_root = sources.skills_dir(root)
    agents_src = sources.agents_dir(root)
    achadas = []
    for nome in sources.skill_names(root):
        pasta = repo / local / nome
        if not pasta.is_dir():
            continue
        esperado = {
            src.relative_to(skills_root / nome).as_posix(): render.render_skill_file(
                src, skills_root, plataforma, agents_src=agents_src
            )
            for src in sources.skill_files(root)
            if src.relative_to(skills_root).parts[0] == nome
        }
        encontrado = _arquivos(pasta)
        achadas.append({
            "name": nome,
            "kind": "skill",
            "location": local,
            "hosts": list(hosts),
            "identical": encontrado == esperado,
            "files": [f"{local}/{nome}/{r}" for r in sorted(encontrado)],
        })
    return achadas


def _colisoes_de_agent(
    repo: Path, local: str, plataforma: str, hosts: tuple[str, ...], root: Path
) -> list[dict[str, Any]]:
    sufixo = ".agent.md" if plataforma == "github" else ".md"
    candidatos = [(src, f"{src.stem}{sufixo}") for src in sources.agent_files(root)]
    candidatos += [(src, f"executors/{src.name}") for src in sources.executor_files(root)]
    achadas = []
    for src, relativo in candidatos:
        arquivo = repo / local / relativo
        if not arquivo.is_file():
            continue
        achadas.append({
            "name": src.stem,
            "kind": "agent",
            "location": local,
            "hosts": list(hosts),
            "identical": arquivo.read_bytes() == render.render_agent_file(src, plataforma),
            "files": [f"{local}/{relativo}"],
        })
    return achadas


def detect(repo: Path, *, root: Path | None = None) -> dict[str, Any]:
    """As colisoes entre a copia do repositorio e o que o wheel integra."""
    repo = Path(repo)
    if is_source_repo(repo):
        return {"collisions": [], "refused": [{
            "reason": "repositorio_fonte",
            "detail": "os espelhos deste repositorio sao gerados por scripts/sync_skills.py",
        }]}
    raiz = sources.content_root() if root is None else Path(root)
    colisoes: list[dict[str, Any]] = []
    for local, tipo, plataforma, hosts in VENDOR_LOCATIONS:
        if not (repo / local).is_dir():
            continue
        busca = _colisoes_de_skill if tipo == "skill" else _colisoes_de_agent
        colisoes.extend(busca(repo, local, plataforma, hosts, raiz))
    return {"collisions": colisoes, "refused": []}


def _pergunta(colisoes: list[dict[str, Any]]) -> str:
    nomes = ", ".join(sorted({f"{c['location']}/{c['name']}" for c in colisoes}))
    return (
        f"Copia vendorizada em dobro no repositorio: {nomes}.\n"
        "[s] sobrescrever (apaga do repo)  [m] mesclar (apaga so o identico)  "
        "[i] ignorar (nao toca no repo): "
    )


def choose(
    colisoes: list[dict[str, Any]],
    *,
    on_conflict: str | None,
    interactive: bool,
    prompt: Callable[[str], str] | None,
) -> str:
    """A escolha: a flag vence; sem flag e com terminal, pergunta; senao, `ignore`."""
    if on_conflict is not None:
        if on_conflict not in ESCOLHAS:
            raise ValueError(f"--on-conflict invalido: {on_conflict!r}; use {list(ESCOLHAS)}")
        return on_conflict
    if not colisoes or not interactive or prompt is None:
        return "ignore"
    return _RESPOSTAS.get(prompt(_pergunta(colisoes)).strip().lower(), "ignore")


def _podar(caminho: Path, base: Path) -> None:
    pai = caminho.parent
    while pai != base and base in pai.parents and pai.is_dir() and not any(pai.iterdir()):
        pai.rmdir()
        pai = pai.parent


def resolve(
    repo: Path, colisoes: list[dict[str, Any]], escolha: str, *, dry_run: bool
) -> dict[str, Any]:
    """Aplica a escolha. A lista do que sai vem no relatorio, com ou sem dry-run."""
    repo = Path(repo)
    if escolha == "overwrite":
        saem = colisoes
    elif escolha == "merge":
        saem = [c for c in colisoes if c["identical"]]
    else:
        saem = []
    ficam = [c for c in colisoes if c not in saem]
    removidos = sorted(arquivo for c in saem for arquivo in c["files"])
    if not dry_run:
        for relativo in removidos:
            caminho = repo / relativo
            if caminho.is_file():
                caminho.unlink()
                _podar(caminho, repo / relativo.split("/")[0])
    return {
        "choice": escolha,
        "dry_run": dry_run,
        "removed": removidos,
        "still_duplicated": sorted(f"{c['location']}/{c['name']}" for c in ficam),
    }


__all__ = ["ESCOLHAS", "VENDOR_LOCATIONS", "choose", "detect", "is_source_repo", "resolve"]
