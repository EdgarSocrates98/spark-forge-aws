"""Plano de escrita no HOME, manifesto, dry-run e idempotencia (D5).

Toda escrita fora do repositorio passa por aqui e fica registrada em
`~/.sparkforge/integrations.json` (formato 2): em `files`, cada arquivo gravado
(caminho relativo a uma raiz declarada, HOME ou APPDATA, em POSIX) com UM sha256
e o conjunto de hosts donos; em `hosts`, por host, a versao do pacote que o
gravou e as entradas de config inseridas. O manifesto e o que torna `detach`
seguro -- sem ele, apagar pelo nome levaria junto arquivo do usuario com o mesmo
nome.

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

import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from sparkforge.integrate import render, sources
from sparkforge.integrate.hosts import Host, default_appdata

MANIFEST_RELATIVE = Path(".sparkforge") / "integrations.json"
SCHEMA = 2


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest_path(home: Path) -> Path:
    return Path(home) / MANIFEST_RELATIVE


class ManifestoRecusado(Exception):
    """O manifesto nao pode guiar escrita nem remocao: nada e tocado."""

    def __init__(self, reason: str, path: Path, action: str, key: str | None = None):
        super().__init__(f"{reason}: {path}")
        self.reason = reason
        self.path = Path(path)
        self.action = action
        self.key = key

    def as_dict(self) -> dict[str, str]:
        recusa = {"reason": self.reason, "path": self.path.as_posix(), "action": self.action}
        if self.key is not None:
            recusa["key"] = self.key
        return recusa


def gravar_atomico(caminho: Path, dados: bytes) -> None:
    """Grava num temporario do MESMO diretorio e troca por `os.replace`: quem le o
    arquivo ve o conteudo velho ou o novo, nunca a metade, mesmo se o processo
    cair no meio. Sem `fsync`: ele protege de queda de energia, nao de processo
    interrompido, e custa um flush de disco por arquivo em centenas de arquivos."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(
        dir=caminho.parent, prefix=f".{caminho.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as saida:
            saida.write(dados)
        os.replace(temporario, caminho)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporario)
        raise


# --------------------------------------------------------------------------
# As duas raizes declaradas: HOME e APPDATA (D4)
# --------------------------------------------------------------------------
# O manifesto nunca guarda caminho absoluto. Cada chave e relativa a uma raiz
# declarada: ao HOME, em POSIX, ou ao APPDATA, com o prefixo `%APPDATA%/` -- o
# Devin no Windows grava em `%APPDATA%\devin`, que pode estar em outro disco.

APPDATA_PREFIX = "%APPDATA%/"


def chave_segura(chave: str) -> bool:
    """Relativa, POSIX, sem `..`, sem unidade e sem barra invertida: so assim a
    chave fica dentro da raiz declarada."""
    if chave.startswith(APPDATA_PREFIX):
        chave = chave[len(APPDATA_PREFIX):]
    if not chave or "\\" in chave or ":" in chave or "%" in chave:
        return False
    partes = PurePosixPath(chave)
    return not partes.is_absolute() and ".." not in partes.parts


def _dentro(caminho: Path, raiz: Path) -> bool:
    return caminho == raiz or raiz in caminho.parents


def _podar(caminho: Path, raiz: Path) -> None:
    """Apaga os diretorios que ficaram vazios, subindo ate a raiz, sem ela."""
    pai = caminho.parent
    raiz = Path(raiz)
    while pai != raiz and raiz in pai.parents and pai.is_dir() and not any(pai.iterdir()):
        pai.rmdir()
        pai = pai.parent


class Disco:
    """Onde a integracao le e grava: as raizes declaradas e o modo (dry-run).

    `appdata=None` e `home/AppData/Roaming`: com `home` injetado, o APPDATA do
    ambiente nunca e lido aqui -- quem quer o real (o CLI) o passa explicito.

    No dry-run nada vai ao disco: gravar e apagar vao para uma sombra em memoria,
    e ler consulta a sombra antes do disco. Assim o segundo host de `all` ve o que
    o primeiro "gravou", e o relatorio do ensaio e o da execucao real.
    """

    def __init__(self, home: Path, appdata: Path | None = None, *, dry_run: bool = False):
        self.home = Path(home)
        self.appdata = default_appdata(self.home) if appdata is None else Path(appdata)
        self.dry_run = dry_run
        self._sombra: dict[Path, bytes | None] = {}

    def _raiz(self, caminho: Path) -> tuple[Path, str]:
        caminho = Path(caminho)
        if _dentro(caminho, self.home):
            return self.home, ""
        if _dentro(caminho, self.appdata):
            return self.appdata, APPDATA_PREFIX
        raise ValueError(f"fora do HOME e do APPDATA declarados: {caminho}")

    def chave(self, caminho: Path) -> str:
        """A chave do manifesto para `caminho`."""
        raiz, prefixo = self._raiz(caminho)
        return prefixo + Path(caminho).relative_to(raiz).as_posix()

    def local(self, chave: str) -> Path:
        """O caminho em disco de uma chave ja conferida por `chave_segura`."""
        if chave.startswith(APPDATA_PREFIX):
            return self.appdata / chave[len(APPDATA_PREFIX):]
        return self.home / chave

    def ler(self, caminho: Path) -> bytes | None:
        caminho = Path(caminho)
        if caminho in self._sombra:
            return self._sombra[caminho]
        return caminho.read_bytes() if caminho.is_file() else None

    def gravar(self, caminho: Path, dados: bytes) -> None:
        if self.dry_run:
            self._sombra[Path(caminho)] = dados
            return
        gravar_atomico(caminho, dados)

    def apagar(self, caminho: Path) -> None:
        caminho = Path(caminho)
        if self.dry_run:
            self._sombra[caminho] = None
            return
        caminho.unlink()
        _podar(caminho, self._raiz(caminho)[0])


# --------------------------------------------------------------------------
# Manifesto
# --------------------------------------------------------------------------


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
        legivel = chave_segura(relativo) and caminho.is_file()
        em_disco = sha256_bytes(caminho.read_bytes()) if legivel else None
        sha = em_disco if em_disco in candidatos else candidatos[0]
        arquivos[relativo] = {"sha256": sha, "owners": sorted(donos[relativo])}
    return {"schema": SCHEMA, "files": arquivos, "hosts": hosts}


_ACAO_ILEGIVEL = (
    "o manifesto lista o que o SparkForge gravou e nao se deixa ler; nada foi tocado. "
    "Restaure-o (de um backup ou do conteudo que ele tinha) e rode de novo; apagar o "
    "arquivo faz o proximo integrate tratar como do usuario o que ja esta no HOME"
)
_ACAO_FORA = (
    "o manifesto aponta um caminho fora do HOME; nada foi apagado. Confira a entrada "
    "nomeada em `key` e retire-a do manifesto antes de rodar de novo"
)


def _chaves(dados: dict[str, Any]) -> list[str]:
    chaves = list(dados["files"])
    for entrada in dados["hosts"].values():
        chaves += [registro.get("path", "") for registro in entrada.get("config") or []]
    return chaves


def load_manifest(home: Path) -> dict[str, Any]:
    """O manifesto do HOME. Ilegivel, ou com caminho que sai da raiz declarada,
    levanta `ManifestoRecusado` antes de qualquer escrita ou remocao."""
    caminho = manifest_path(home)
    if not caminho.is_file():
        return _manifesto_vazio()
    try:
        dados = json.loads(caminho.read_bytes().decode("utf-8"))
        if not isinstance(dados, dict):
            raise ValueError("o manifesto nao e um objeto JSON")
        if dados.get("schema", 1) < 2:
            dados = _migrar_v1(dados, home)
        dados.setdefault("schema", SCHEMA)
        dados.setdefault("files", {})
        dados.setdefault("hosts", {})
        chaves = _chaves(dados)
    except (ValueError, TypeError, AttributeError) as erro:
        raise ManifestoRecusado("manifesto_ilegivel", caminho, _ACAO_ILEGIVEL) from erro
    for chave in chaves:
        if not isinstance(chave, str) or not chave_segura(chave):
            raise ManifestoRecusado("manifesto_fora_do_home", caminho, _ACAO_FORA, str(chave))
    return dados


def _texto_do_manifesto(manifesto: dict[str, Any]) -> str:
    return json.dumps(manifesto, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def save_manifest(home: Path, manifesto: dict[str, Any]) -> bool:
    """Grava so se mudou: a segunda execucao identica nao toca nem o mtime."""
    caminho = manifest_path(home)
    texto = _texto_do_manifesto(manifesto)
    if caminho.is_file() and caminho.read_text(encoding="utf-8") == texto:
        return False
    gravar_atomico(caminho, texto.encode("utf-8"))
    return True


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


# --------------------------------------------------------------------------
# Arquivos de agents e skills
# --------------------------------------------------------------------------


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


def remove_owned(
    disco: Disco,
    manifesto: dict[str, Any],
    nome: str,
    relativos: list[str],
) -> dict[str, list]:
    """Tira `nome` dos donos de `relativos`. O arquivo so sai do disco quando `nome`
    era o ultimo dono, o sha256 em disco ainda e o gravado e ele nao e
    `preexistente`. O manifesto e alterado em memoria (no dry-run, nunca salvo);
    quem chama o salva."""
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
        caminho = disco.local(relativo)
        if outros:
            mantidos.append(relativo)
            registro["owners"] = outros
            continue
        atual = disco.ler(caminho)
        if registro.get("preexistente"):
            preexistentes.append(relativo)
        elif atual is not None and sha256_bytes(atual) != registro["sha256"]:
            recusas.append({"reason": "editado_pelo_usuario", "path": relativo})
        else:
            removidos.append(relativo)
            if atual is not None:
                disco.apagar(caminho)
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
    disco: Disco,
    manifesto: dict[str, Any],
    version: str,
) -> dict[str, Any]:
    """Grava o plano de `nome` e atualiza o manifesto em memoria."""
    escritos: list[str] = []
    iguais: list[str] = []
    recusas: list[dict[str, str]] = []
    vistos: set[str] = set()
    for destino, dados in plano:
        relativo = disco.chave(destino)
        sha = sha256_bytes(dados)
        registrado = recorded_sha(manifesto, relativo)
        em_disco = disco.ler(destino)
        if em_disco is not None:
            atual = sha256_bytes(em_disco)
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
                _adotar(manifesto, relativo, nome, sha, preexistente=registrado is None)
                continue
        escritos.append(relativo)
        vistos.add(relativo)
        disco.gravar(destino, dados)
        _adotar(manifesto, relativo, nome, sha, preexistente=False)
    anteriores = [r for r in host_files(manifesto, nome) if r not in vistos]
    orfaos = remove_owned(disco, manifesto, nome, anteriores)
    entrada = manifesto["hosts"].setdefault(nome, {})
    entrada["package_version"] = version
    entrada.setdefault("config", [])
    return {
        "host": nome,
        "dry_run": disco.dry_run,
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


def _texto_de(disco: Disco, caminho: Path) -> str | None:
    dados = disco.ler(caminho)
    return None if dados is None else dados.decode("utf-8").replace("\r\n", "\n")


def _json_de_config(texto: str | None) -> dict[str, Any] | None:
    """Os dados do JSON de config, `{}` sem arquivo, ou `None` se nao e JSON de objeto."""
    if texto is None or not texto.strip():
        return {}
    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("mcpServers", {}), dict):
        return None
    return dados


def apply_json_config(
    nome: str,
    caminho: Path,
    entrada: dict[str, Any],
    *,
    disco: Disco,
    manifesto: dict[str, Any],
) -> dict[str, Any]:
    """Poe `mcpServers.sparkforge` no JSON de config do host e nada mais."""
    relativo = disco.chave(caminho)
    registro = _registro_de_config(manifesto, nome, relativo)
    texto = _texto_de(disco, caminho)
    dados = _json_de_config(texto)
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
            "created": texto is None,
            "had_mcp_servers": servidores is not None,
        }
    if status == "written":
        disco.gravar(caminho, novo_texto.encode("utf-8"))
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
    """O bloco com `[mcp_servers.sparkforge]`, com as strings escritas pelo mesmo
    `_toml_string` do renderizador (string basica de TOML sem dependencia)."""
    lista = ", ".join(render._toml_string(arg) for arg in args)
    return (
        f"{INICIO_TOML}\n"
        "[mcp_servers.sparkforge]\n"
        f"command = {render._toml_string(comando)}\n"
        f"args = [{lista}]\n"
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
    disco: Disco,
    manifesto: dict[str, Any],
) -> dict[str, Any]:
    """Poe (ou troca) o bloco marcado no TOML de config; o resto nao e tocado."""
    relativo = disco.chave(caminho)
    lido = _texto_de(disco, caminho)
    texto = lido or ""
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
        "created": lido is None,
    }
    if status == "written":
        disco.gravar(caminho, novo.encode("utf-8"))
    _guardar_registro(manifesto, nome, registro)
    return {"path": relativo, "status": status}


# --------------------------------------------------------------------------
# detach: devolver a config de usuario ao que era (D7)
# --------------------------------------------------------------------------


def revert_json_config(registro: dict[str, Any], *, disco: Disco) -> dict[str, Any]:
    """Tira `mcpServers.sparkforge`; o resto do JSON fica. Se o integrate criou o
    arquivo e ele ficou vazio, o arquivo sai."""
    relativo = registro["path"]
    caminho = disco.local(relativo)
    texto = _texto_de(disco, caminho)
    if texto is None:
        return {"path": relativo, "status": "absent"}
    dados = _json_de_config(texto)
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
    if apagar:
        disco.apagar(caminho)
    else:
        disco.gravar(caminho, (json.dumps(novo, indent=2, ensure_ascii=False) + "\n").encode())
    return {"path": relativo, "status": "deleted" if apagar else "reverted"}


def revert_toml_config(registro: dict[str, Any], *, disco: Disco) -> dict[str, Any]:
    """Tira o bloco marcado e a linha em branco que o integrate pos antes dele."""
    relativo = registro["path"]
    caminho = disco.local(relativo)
    texto = _texto_de(disco, caminho)
    if texto is None:
        return {"path": relativo, "status": "absent"}
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
    if apagar:
        disco.apagar(caminho)
    else:
        disco.gravar(caminho, novo.encode("utf-8"))
    return {"path": relativo, "status": "deleted" if apagar else "reverted"}


def revert_config(registro: dict[str, Any], *, disco: Disco) -> dict[str, Any]:
    if registro.get("format") == "toml":
        return revert_toml_config(registro, disco=disco)
    return revert_json_config(registro, disco=disco)


def drop_manifest_if_empty(home: Path, manifesto: dict[str, Any]) -> None:
    """Sem host integrado, o manifesto sai do HOME; senao, e regravado."""
    if manifesto.get("hosts") or manifesto.get("files"):
        save_manifest(home, manifesto)
        return
    caminho = manifest_path(home)
    if caminho.is_file():
        caminho.unlink()
        _podar(caminho, home)
