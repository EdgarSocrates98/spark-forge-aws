"""Plano de escrita no HOME, manifesto, dry-run e idempotencia (D5).

Toda escrita fora do repositorio passa por aqui e fica registrada em
`~/.sparkforge/integrations.json`: por host, cada arquivo gravado (caminho
relativo ao HOME, em POSIX, e sha256), a versao do pacote que o gravou e as
entradas de config inseridas. O manifesto e o que torna `detach` seguro -- sem
ele, apagar pelo nome levaria junto arquivo do usuario com o mesmo nome.

Tres regras para arquivo que ja existe no destino:

- nenhum host o registrou: e do usuario, sai recusa `arquivo_do_usuario` e ele
  fica como esta;
- algum host o registrou e o sha256 em disco ainda e o registrado: e nosso, e
  pode ser regravado;
- algum host o registrou e o sha256 mudou: o usuario editou depois, sai recusa
  `editado_pelo_usuario` e ele fica.

Um arquivo de `~/.agents/skills` pode ser de mais de um host; os donos sao os
hosts que o listam no manifesto, e so o ultimo a sair o apaga.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sparkforge.integrate import render, sources
from sparkforge.integrate.hosts import Host

MANIFEST_RELATIVE = Path(".sparkforge") / "integrations.json"
SCHEMA = 1


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_path(home: Path) -> Path:
    return Path(home) / MANIFEST_RELATIVE


def load_manifest(home: Path) -> dict[str, Any]:
    caminho = manifest_path(home)
    if not caminho.is_file():
        return {"schema": SCHEMA, "hosts": {}}
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    dados.setdefault("schema", SCHEMA)
    dados.setdefault("hosts", {})
    return dados


def _texto_do_manifesto(manifesto: dict[str, Any]) -> str:
    return json.dumps(manifesto, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def save_manifest(home: Path, manifesto: dict[str, Any]) -> bool:
    """Grava so se mudou: a segunda execucao identica nao toca nem o mtime."""
    caminho = manifest_path(home)
    texto = _texto_do_manifesto(manifesto)
    if caminho.is_file() and caminho.read_text(encoding="utf-8") == texto:
        return False
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(texto.encode("utf-8"))
    return True


def rel(home: Path, caminho: Path) -> str:
    """Relativo ao HOME, em POSIX; fora dele (um `APPDATA` em outro disco), absoluto.
    `Path(home) / rel(...)` devolve o caminho certo nos dois casos."""
    caminho, home = Path(caminho), Path(home)
    if caminho == home or home in caminho.parents:
        return caminho.relative_to(home).as_posix()
    return caminho.as_posix()


def owners(manifesto: dict[str, Any], relativo: str) -> list[str]:
    return sorted(
        nome
        for nome, entrada in manifesto.get("hosts", {}).items()
        if relativo in (entrada.get("files") or {})
    )


def recorded_sha(manifesto: dict[str, Any], relativo: str) -> str | None:
    for nome in owners(manifesto, relativo):
        return manifesto["hosts"][nome]["files"][relativo]
    return None


def plan_files(h: Host, root: Path) -> list[tuple[Path, bytes]]:
    """Os arquivos que o host `h` recebe, ja renderizados para a plataforma dele."""
    agents_src = sources.agents_dir(root)
    skills_root = sources.skills_dir(root)
    plano: list[tuple[Path, bytes]] = []
    for src in sources.agent_files(root):
        destino = h.agents_dir / h.agent_pattern.format(stem=src.stem)
        plano.append((destino, render.render_agent_file(src, h.agent_platform)))
    if h.executors:
        for src in sources.executor_files(root):
            destino = h.agents_dir / "executors" / src.name
            plano.append((destino, render.render_agent_file(src, h.agent_platform)))
    for src in sources.skill_files(root):
        destino = h.skills_dir / src.relative_to(skills_root)
        dados = render.render_skill_file(
            src, skills_root, h.skill_platform, agents_src=agents_src
        )
        plano.append((destino, dados))
    return plano


def _podar(caminho: Path, home: Path) -> None:
    """Apaga os diretorios que ficaram vazios, subindo ate o HOME, sem ele."""
    pai = caminho.parent
    home = Path(home)
    while pai != home and home in pai.parents and pai.is_dir() and not any(pai.iterdir()):
        pai.rmdir()
        pai = pai.parent


def remove_owned(
    home: Path,
    manifesto: dict[str, Any],
    nome: str,
    relativos: list[str],
    *,
    dry_run: bool,
) -> dict[str, list]:
    """Tira de `nome` os arquivos `relativos`, apagando so o que e so dele e ainda
    tem o sha256 gravado. O manifesto e alterado em memoria; quem chama o salva."""
    removidos: list[str] = []
    mantidos: list[str] = []
    recusas: list[dict[str, str]] = []
    arquivos = manifesto["hosts"][nome].setdefault("files", {})
    for relativo in sorted(relativos):
        gravado = arquivos.get(relativo)
        outros = [o for o in owners(manifesto, relativo) if o != nome]
        caminho = Path(home) / relativo
        if outros:
            mantidos.append(relativo)
        elif caminho.is_file() and sha256_bytes(caminho.read_bytes()) != gravado:
            recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
        else:
            removidos.append(relativo)
            if not dry_run and caminho.is_file():
                caminho.unlink()
                _podar(caminho, home)
        if not dry_run:
            arquivos.pop(relativo, None)
    return {"removed": removidos, "kept_shared": mantidos, "refused": recusas}


def apply_files(
    nome: str,
    plano: list[tuple[Path, bytes]],
    *,
    home: Path,
    manifesto: dict[str, Any],
    version: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Grava o plano de `nome` e atualiza o manifesto em memoria."""
    home = Path(home)
    escritos: list[str] = []
    iguais: list[str] = []
    recusas: list[dict[str, str]] = []
    novos: dict[str, str] = {}
    for destino, dados in plano:
        relativo = rel(home, destino)
        sha = sha256_bytes(dados)
        if destino.is_file():
            atual = sha256_bytes(destino.read_bytes())
            registrado = recorded_sha(manifesto, relativo)
            if registrado is None and atual != sha:
                recusas.append({"reason": "arquivo_do_usuario", "path": relativo})
                continue
            if registrado is not None and atual != registrado and atual != sha:
                recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
                continue
            if atual == sha:
                iguais.append(relativo)
                novos[relativo] = sha
                continue
        escritos.append(relativo)
        novos[relativo] = sha
        if not dry_run:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
    entrada = manifesto["hosts"].get(nome) or {}
    anteriores = sorted(set(entrada.get("files") or {}) - set(novos))
    orfaos: dict[str, list] = {"removed": [], "kept_shared": [], "refused": []}
    if anteriores:
        manifesto["hosts"].setdefault(nome, entrada)
        orfaos = remove_owned(home, manifesto, nome, anteriores, dry_run=dry_run)
    if not dry_run:
        entrada = manifesto["hosts"].setdefault(nome, {})
        entrada["package_version"] = version
        entrada["files"] = dict(sorted(novos.items()))
        entrada.setdefault("config", [])
    return {
        "host": nome,
        "dry_run": dry_run,
        "written": escritos,
        "unchanged": iguais,
        "removed": orfaos["removed"],
        "refused": recusas + orfaos["refused"],
    }
