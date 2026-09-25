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
import re
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


# --------------------------------------------------------------------------
# Config de usuario em JSON (Devin, Copilot): so `mcpServers.sparkforge` (D6)
# --------------------------------------------------------------------------


def _registro_de_config(
    manifesto: dict[str, Any], nome: str, relativo: str
) -> dict[str, Any] | None:
    for registro in manifesto["hosts"].get(nome, {}).get("config") or []:
        if registro["path"] == relativo:
            return registro
    return None


def _guardar_registro(
    manifesto: dict[str, Any], nome: str, registro: dict[str, Any]
) -> None:
    registros = manifesto["hosts"].setdefault(nome, {}).setdefault("config", [])
    if registro not in registros:
        registros.append(registro)


def _json_de_config(caminho: Path) -> tuple[str, dict[str, Any] | None]:
    """(texto, dados), com `dados=None` quando o arquivo nao e JSON de objeto."""
    if not caminho.is_file():
        return "", {}
    texto = caminho.read_text(encoding="utf-8")
    try:
        dados = json.loads(texto) if texto.strip() else {}
    except json.JSONDecodeError:
        return texto, None
    if not isinstance(dados, dict) or not isinstance(dados.get("mcpServers", {}), dict):
        return texto, None
    return texto, dados


def apply_json_config(
    nome: str,
    caminho: Path,
    entrada: dict[str, Any],
    *,
    home: Path,
    manifesto: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    """Poe `mcpServers.sparkforge` no JSON de config do host e nada mais."""
    relativo = rel(home, caminho)
    registro = _registro_de_config(manifesto, nome, relativo)
    texto, dados = _json_de_config(caminho)
    if dados is None:
        return {"path": relativo, "status": "refused", "reason": "config_invalida"}
    servidores = dados.get("mcpServers")
    if isinstance(servidores, dict) and "sparkforge" in servidores and registro is None:
        return {"path": relativo, "status": "refused", "reason": "sparkforge_ja_configurado"}
    novo = dict(dados)
    novo["mcpServers"] = {**(servidores or {}), "sparkforge": entrada}
    novo_texto = json.dumps(novo, indent=2, ensure_ascii=False) + "\n"
    status = "unchanged" if novo_texto == texto else "written"
    if registro is None:
        registro = {
            "path": relativo,
            "format": "json",
            "created": not caminho.is_file(),
            "had_mcp_servers": servidores is not None,
        }
    if not dry_run:
        if status == "written":
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(novo_texto.encode("utf-8"))
        _guardar_registro(manifesto, nome, registro)
    return {"path": relativo, "status": status}


# --------------------------------------------------------------------------
# Config de usuario em TOML (Codex): um bloco marcado (D6)
# --------------------------------------------------------------------------
# O Python 3.10 que o projeto suporta nao le TOML e o projeto nao tem dependencia
# para isso; por isso o SparkForge nao reescreve o arquivo -- so poe, troca ou tira
# o bloco entre os dois marcadores. `[mcp_servers.sparkforge]` fora do bloco foi
# escrito por outra pessoa e sai recusa. Marcador sem par sai recusa tambem: nao
# da para saber onde o bloco termina.

INICIO_TOML = "# >>> sparkforge (gerenciado)"
FIM_TOML = "# <<< sparkforge"
_TABELA_SPARKFORGE = re.compile(r"^\s*\[mcp_servers\.sparkforge\]", re.MULTILINE)


def toml_block(comando: str, args: list[str]) -> str:
    """O bloco com `[mcp_servers.sparkforge]`. `json.dumps` produz string e array
    validos de TOML (o escape do JSON e subconjunto do escape de string basica)."""
    return (
        f"{INICIO_TOML}\n"
        "[mcp_servers.sparkforge]\n"
        f"command = {json.dumps(comando, ensure_ascii=False)}\n"
        f"args = {json.dumps(args, ensure_ascii=False)}\n"
        f"{FIM_TOML}\n"
    )


def _limites_do_bloco(texto: str) -> tuple[int, int] | None | str:
    """(inicio, fim) do bloco, `None` sem bloco, ou `"quebrado"`."""
    inicio, fim = texto.find(INICIO_TOML), texto.find(FIM_TOML)
    if inicio == -1 and fim == -1:
        return None
    if inicio == -1 or fim == -1 or fim < inicio:
        return "quebrado"
    return inicio, fim + len(FIM_TOML)


def apply_toml_config(
    nome: str,
    caminho: Path,
    bloco: str,
    *,
    home: Path,
    manifesto: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    """Poe (ou troca) o bloco marcado no TOML de config; o resto nao e tocado."""
    relativo = rel(home, caminho)
    existia = caminho.is_file()
    texto = caminho.read_text(encoding="utf-8") if existia else ""
    limites = _limites_do_bloco(texto)
    if limites == "quebrado":
        return {"path": relativo, "status": "refused", "reason": "bloco_toml_quebrado"}
    fora = texto if limites is None else texto[: limites[0]] + texto[limites[1]:]
    if _TABELA_SPARKFORGE.search(fora):
        return {"path": relativo, "status": "refused", "reason": "sparkforge_ja_configurado"}
    if limites is None:
        base = texto.rstrip("\n")
        novo = (base + "\n\n" if base else "") + bloco
    else:
        novo = texto[: limites[0]] + bloco.rstrip("\n") + texto[limites[1]:]
    status = "unchanged" if novo == texto else "written"
    registro = _registro_de_config(manifesto, nome, relativo) or {
        "path": relativo,
        "format": "toml",
        "created": not existia,
    }
    if not dry_run:
        if status == "written":
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(novo.encode("utf-8"))
        _guardar_registro(manifesto, nome, registro)
    return {"path": relativo, "status": status}
