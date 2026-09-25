"""Plano de escrita no HOME, manifesto, dry-run e idempotencia (D5).

Toda escrita fora do repositorio passa por aqui e fica registrada em
`~/.sparkforge/integrations.json` (formato 2): em `files`, cada arquivo gravado
(caminho relativo ao HOME, em POSIX) com UM sha256 e o conjunto de hosts donos;
em `hosts`, por host, a versao do pacote que o gravou e as entradas de config
inseridas. O manifesto e o que torna `detach` seguro -- sem
ele, apagar pelo nome levaria junto arquivo do usuario com o mesmo nome.

Tres regras para arquivo que ja existe no destino:

- nenhum host o registrou: e do usuario, sai recusa `arquivo_do_usuario` e ele
  fica como esta;
- algum host o registrou e o sha256 em disco ainda e o registrado: e nosso, e
  pode ser regravado;
- algum host o registrou e o sha256 mudou: o usuario editou depois, sai recusa
  `editado_pelo_usuario` e ele fica.

Um arquivo de `~/.agents/skills` pode ser de mais de um host. O sha256 e do
ARQUIVO, nao do dono: com um sha por host, o host que nao regravou ficava com o
sha velho e acusava edicao do usuario que nao houve. So o ultimo dono a sair
apaga o arquivo.

Arquivo que ja estava no HOME com o conteudo identico ao que gravariamos e
adotado com `preexistente: true`: fica registrado (a proxima execucao nao o trata
como alheio), mas nenhum detach o apaga -- ele nao nasceu daqui.

O formato 1 (um mapa `files` por host) e migrado ao carregar.
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
SCHEMA = 2


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_path(home: Path) -> Path:
    return Path(home) / MANIFEST_RELATIVE


def _manifesto_vazio() -> dict[str, Any]:
    return {"schema": SCHEMA, "files": {}, "hosts": {}}


def _migrar_v1(dados: dict[str, Any], home: Path) -> dict[str, Any]:
    """Formato 1 -> 2: um sha por arquivo, com os donos. Donos com sha divergente
    ficam com o que esta em disco; sem nenhum igual ao disco, o do primeiro."""
    shas: dict[str, list[str]] = {}
    donos: dict[str, list[str]] = {}
    hosts: dict[str, Any] = {}
    for nome, entrada in sorted((dados.get("hosts") or {}).items()):
        entrada = dict(entrada)
        for relativo, sha in sorted((entrada.pop("files", None) or {}).items()):
            shas.setdefault(relativo, []).append(sha)
            donos.setdefault(relativo, []).append(nome)
        hosts[nome] = entrada
    arquivos: dict[str, Any] = {}
    for relativo, candidatos in sorted(shas.items()):
        caminho = Path(home) / relativo
        em_disco = sha256_bytes(caminho.read_bytes()) if caminho.is_file() else None
        sha = em_disco if em_disco in candidatos else candidatos[0]
        arquivos[relativo] = {"sha256": sha, "owners": sorted(donos[relativo])}
    return {"schema": SCHEMA, "files": arquivos, "hosts": hosts}


def load_manifest(home: Path) -> dict[str, Any]:
    caminho = manifest_path(home)
    if not caminho.is_file():
        return _manifesto_vazio()
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    if dados.get("schema", 1) < 2:
        dados = _migrar_v1(dados, home)
    dados.setdefault("schema", SCHEMA)
    dados.setdefault("files", {})
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
    return list((manifesto["files"].get(relativo) or {}).get("owners") or [])


def recorded_sha(manifesto: dict[str, Any], relativo: str) -> str | None:
    return (manifesto["files"].get(relativo) or {}).get("sha256")


def host_files(manifesto: dict[str, Any], nome: str) -> list[str]:
    """Os arquivos de que `nome` e dono."""
    return sorted(
        relativo
        for relativo, registro in manifesto["files"].items()
        if nome in (registro.get("owners") or [])
    )


def _adotar(
    manifesto: dict[str, Any], relativo: str, nome: str, sha: str, *, preexistente: bool
) -> None:
    """`nome` passa a ser dono de `relativo`, cujo conteudo e `sha`."""
    registro = manifesto["files"].setdefault(relativo, {"sha256": sha, "owners": []})
    registro["sha256"] = sha
    registro["owners"] = sorted({*registro.get("owners", []), nome})
    if preexistente:
        registro["preexistente"] = True


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
    """Tira `nome` dos donos de `relativos`. O arquivo so sai do disco quando `nome`
    era o ultimo dono, o sha256 em disco ainda e o gravado e ele nao e
    `preexistente`. O manifesto e alterado em memoria; quem chama o salva."""
    removidos: list[str] = []
    mantidos: list[str] = []
    preexistentes: list[str] = []
    recusas: list[dict[str, str]] = []
    arquivos = manifesto["files"]
    for relativo in sorted(relativos):
        registro = arquivos.get(relativo)
        if registro is None:
            continue
        outros = [o for o in registro.get("owners") or [] if o != nome]
        caminho = Path(home) / relativo
        if outros:
            mantidos.append(relativo)
            if not dry_run:
                registro["owners"] = outros
            continue
        if registro.get("preexistente"):
            preexistentes.append(relativo)
        elif caminho.is_file() and sha256_bytes(caminho.read_bytes()) != registro["sha256"]:
            recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
        else:
            removidos.append(relativo)
            if not dry_run and caminho.is_file():
                caminho.unlink()
                _podar(caminho, home)
        if not dry_run:
            del arquivos[relativo]
    return {
        "removed": removidos,
        "kept_shared": mantidos,
        "kept_preexisting": preexistentes,
        "refused": recusas,
    }


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
    vistos: set[str] = set()
    for destino, dados in plano:
        relativo = rel(home, destino)
        sha = sha256_bytes(dados)
        registrado = recorded_sha(manifesto, relativo)
        if destino.is_file():
            atual = sha256_bytes(destino.read_bytes())
            if registrado is None and atual != sha:
                recusas.append({"reason": "arquivo_do_usuario", "path": relativo})
                continue
            if registrado is not None and atual not in (registrado, sha):
                recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
                if nome in owners(manifesto, relativo):
                    vistos.add(relativo)
                continue
            if atual == sha:
                iguais.append(relativo)
                vistos.add(relativo)
                if not dry_run:
                    _adotar(manifesto, relativo, nome, sha, preexistente=registrado is None)
                continue
        escritos.append(relativo)
        vistos.add(relativo)
        if not dry_run:
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
            _adotar(manifesto, relativo, nome, sha, preexistente=False)
    anteriores = [r for r in host_files(manifesto, nome) if r not in vistos]
    orfaos = remove_owned(home, manifesto, nome, anteriores, dry_run=dry_run)
    if not dry_run:
        entrada = manifesto["hosts"].setdefault(nome, {})
        entrada["package_version"] = version
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


# --------------------------------------------------------------------------
# detach: devolver a config de usuario ao que era (D7)
# --------------------------------------------------------------------------


def _gravar_ou_apagar(caminho: Path, texto: str, *, apagar: bool, home: Path) -> None:
    if apagar:
        caminho.unlink()
        _podar(caminho, home)
    else:
        caminho.write_bytes(texto.encode("utf-8"))


def revert_json_config(
    registro: dict[str, Any], *, home: Path, dry_run: bool
) -> dict[str, Any]:
    """Tira `mcpServers.sparkforge`; o resto do JSON fica. Se o integrate criou o
    arquivo e ele ficou vazio, o arquivo sai."""
    relativo = registro["path"]
    caminho = Path(home) / relativo
    if not caminho.is_file():
        return {"path": relativo, "status": "absent"}
    _, dados = _json_de_config(caminho)
    if dados is None:
        return {"path": relativo, "status": "refused", "reason": "config_invalida"}
    servidores = dict(dados.get("mcpServers") or {})
    if "sparkforge" not in servidores:
        return {"path": relativo, "status": "absent"}
    del servidores["sparkforge"]
    novo = dict(dados)
    if servidores or registro.get("had_mcp_servers"):
        novo["mcpServers"] = servidores
    else:
        novo.pop("mcpServers", None)
    apagar = bool(registro.get("created")) and not novo
    if not dry_run:
        texto = json.dumps(novo, indent=2, ensure_ascii=False) + "\n"
        _gravar_ou_apagar(caminho, texto, apagar=apagar, home=home)
    return {"path": relativo, "status": "deleted" if apagar else "reverted"}


def revert_toml_config(
    registro: dict[str, Any], *, home: Path, dry_run: bool
) -> dict[str, Any]:
    """Tira o bloco marcado e a linha em branco que o integrate pos antes dele."""
    relativo = registro["path"]
    caminho = Path(home) / relativo
    if not caminho.is_file():
        return {"path": relativo, "status": "absent"}
    texto = caminho.read_text(encoding="utf-8")
    limites = _limites_do_bloco(texto)
    if limites == "quebrado":
        return {"path": relativo, "status": "refused", "reason": "bloco_toml_quebrado"}
    if limites is None:
        return {"path": relativo, "status": "absent"}
    partes = [
        parte
        for parte in (texto[: limites[0]].rstrip("\n"), texto[limites[1]:].lstrip("\n"))
        if parte
    ]
    novo = "\n\n".join(partes) + ("\n" if partes else "")
    apagar = bool(registro.get("created")) and not novo.strip()
    if not dry_run:
        _gravar_ou_apagar(caminho, novo, apagar=apagar, home=home)
    return {"path": relativo, "status": "deleted" if apagar else "reverted"}


def revert_config(registro: dict[str, Any], *, home: Path, dry_run: bool) -> dict[str, Any]:
    if registro.get("format") == "toml":
        return revert_toml_config(registro, home=home, dry_run=dry_run)
    return revert_json_config(registro, home=home, dry_run=dry_run)


def drop_manifest_if_empty(home: Path, manifesto: dict[str, Any]) -> None:
    """Sem host integrado, o manifesto sai do HOME; senao, e regravado."""
    if manifesto.get("hosts") or manifesto.get("files"):
        save_manifest(home, manifesto)
        return
    caminho = manifest_path(home)
    if caminho.is_file():
        caminho.unlink()
        _podar(caminho, home)
