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

So colide o que o host integrado CARREGA: `integrate devin` nao ve `.claude/agents`.
Um diretorio lido por mais de um host (`.agents/skills`: devin, codex e copilot) so
sai do repositorio quando TODOS eles estao integrados por usuario; antes disso a
entrada fica, como `mantido_host_nao_integrado`.

Toda remocao passa por tres travas: nenhum componente do caminho, a partir de
`.claude`/`.agents`/`.github`, e link ou juncao; o caminho resolvido e o caminho
logico; e ele fica dentro do repositorio resolvido. A entrada que falha qualquer
uma sai `copia_fora_do_repositorio` e nada dela e apagado -- um link para fora do
repositorio nunca leva o arquivo de la junto.

No proprio repositorio fonte do SparkForge (tem `scripts/sync_skills.py`) os
espelhos `.claude/`, `.agents/` e `.github/` sao gerados e versionados: sai a
recusa `repositorio_fonte` e nada e tocado.

O repositorio e a RAIZ GIT acima do diretorio de onde o comando foi chamado (o
primeiro com `.git`, pasta ou arquivo); sem `.git` acima sai `sem_repositorio` e o
conflito nao e avaliado. Com o cwd no HOME, `repo/.agents/skills` E o
`~/.agents/skills` da propria integracao: a raiz que e o HOME, o APPDATA ou o
CODEX_HOME, que contem algum deles, ou que mora dentro de um destino da integracao
(`~/.agents`, `~/.claude`, `~/.codex`, `~/.copilot`, `~/.config/devin`,
`%APPDATA%/devin`, `$CODEX_HOME`, `~/.sparkforge`) sai `repositorio_e_o_home`, e
`detect` e `resolve` nao tocam em nada.
"""
from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from typing import Any

from sparkforge.integrate import render, sources
from sparkforge.integrate.hosts import default_appdata, default_codex_home

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


def git_root(inicio: Path) -> Path | None:
    """O primeiro diretorio com `.git` (pasta, ou arquivo de worktree), subindo
    de `inicio`; `None` quando nao ha."""
    atual = Path(os.path.abspath(inicio))
    for pasta in (atual, *atual.parents):
        if os.path.lexists(pasta / ".git"):
            return pasta
    return None


def _real(caminho: Path) -> str:
    return os.path.normcase(os.path.realpath(caminho))


def _contem(pai: str, filho: str) -> bool:
    """`filho` e `pai` ou mora dentro dele (caminhos ja normalizados)."""
    return filho == pai or filho.startswith(pai.rstrip(os.sep) + os.sep)


def home_guard(
    repo: Path,
    *,
    home: Path | None = None,
    appdata: Path | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any] | None:
    """A recusa `repositorio_e_o_home`, ou `None` quando `repo` pode ser tocado.

    `home=None` e o HOME do processo: a trava vale mesmo para quem chama sem
    dizer o HOME."""
    casa = Path.home() if home is None else Path(home)
    dados = default_appdata(casa) if appdata is None else Path(appdata)
    codex = default_codex_home(casa) if codex_home is None else Path(codex_home)
    alvo = _real(repo)
    raizes = [casa, dados, codex]
    destinos = [casa / ".agents", casa / ".claude", casa / ".codex", casa / ".copilot",
                casa / ".config" / "devin", dados / "devin", codex, casa / ".sparkforge"]
    if any(_contem(alvo, _real(r)) for r in raizes) or any(
        _contem(_real(d), alvo) for d in destinos
    ):
        return {
            "reason": "repositorio_e_o_home",
            "path": Path(os.path.abspath(repo)).as_posix(),
            "detail": (
                "o repositorio e o HOME (ou o contem, ou mora num destino da "
                "integracao): a copia dele e a propria integracao de usuario, e "
                "nada e tocado"
            ),
        }
    return None


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


def detect(
    repo: Path,
    *,
    root: Path | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    """As colisoes entre a copia do repositorio e o que o wheel integra.

    `repo` e de onde o comando foi chamado; `repo` do resultado e a raiz git
    acima dele, a que `resolve` recebe (`None` quando nao ha)."""
    raiz_git = git_root(Path(repo))
    if raiz_git is None:
        return {"repo": None, "collisions": [], "refused": [{
            "reason": "sem_repositorio",
            "path": Path(os.path.abspath(repo)).as_posix(),
            "detail": "nenhum .git acima do diretorio atual: o conflito nao e avaliado",
        }]}
    repo = raiz_git
    guarda = home_guard(repo, home=home, appdata=appdata, codex_home=codex_home)
    if guarda is not None:
        return {"repo": repo, "collisions": [], "refused": [guarda]}
    if is_source_repo(repo):
        return {"repo": repo, "collisions": [], "refused": [{
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
    return {"repo": repo, "collisions": colisoes, "refused": []}


def relevant(colisoes: list[dict[str, Any]], alvos: Iterable[str]) -> list[dict[str, Any]]:
    """So as colisoes que algum dos hosts `alvos` carrega."""
    alvos = set(alvos)
    return [c for c in colisoes if alvos & set(c["hosts"])]


def missing_hosts(colisao: dict[str, Any], integrados: Iterable[str]) -> list[str]:
    return sorted(set(colisao["hosts"]) - set(integrados))


def _pergunta(colisoes: list[dict[str, Any]]) -> str:
    linhas = [
        f"  [{'identico' if c['identical'] else 'customizado'}] {arquivo}"
        for c in sorted(colisoes, key=lambda c: (c["location"], c["name"]))
        for arquivo in c["files"]
    ]
    return (
        "Copia vendorizada em dobro no repositorio, arquivo por arquivo:\n"
        + "\n".join(linhas)
        + "\n[s] sobrescrever (apaga do repo os dois)  [m] mesclar (apaga so o [identico])  "
        "[i] ignorar (nao toca no repo): "
    )


TENTATIVAS = 3


def choose(
    colisoes: list[dict[str, Any]],
    *,
    on_conflict: str | None,
    interactive: bool,
    prompt: Callable[[str], str] | None,
) -> tuple[str, str | None]:
    """A escolha e o motivo, quando ela nao veio do operador.

    A flag vence; sem flag e com terminal, pergunta (ate `TENTATIVAS` vezes para
    resposta que nao se entende); senao, `ignore`. Terminal fechado (EOF) ou
    interrompido e `ignore` com `prompt_sem_resposta`, nunca um traceback."""
    if on_conflict is not None:
        if on_conflict not in ESCOLHAS:
            raise ValueError(f"--on-conflict invalido: {on_conflict!r}; use {list(ESCOLHAS)}")
        return on_conflict, None
    if not colisoes:
        return "ignore", None
    if not interactive or prompt is None:
        return "ignore", "sem_terminal_e_sem_flag"
    texto = _pergunta(colisoes)
    for _ in range(TENTATIVAS):
        try:
            resposta = prompt(texto)
        except (EOFError, KeyboardInterrupt):
            return "ignore", "prompt_sem_resposta"
        escolha = _RESPOSTAS.get(resposta.strip().lower())
        if escolha is not None:
            return escolha, None
    return "ignore", "resposta_invalida"


_REPARSE_DE_LINK = {
    getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003),
    getattr(stat, "IO_REPARSE_TAG_SYMLINK", 0xA000000C),
}


def _e_link(caminho: Path) -> bool:
    """Symlink ou juncao. No Windows antes do 3.12 a juncao nao e `islink`: o
    `st_reparse_tag` do `lstat` a denuncia."""
    if os.path.islink(caminho):
        return True
    e_juncao = getattr(caminho, "is_junction", None)
    if e_juncao is not None and e_juncao():
        return True
    try:
        marca = getattr(os.lstat(caminho), "st_reparse_tag", 0)
    except OSError:
        return False
    return marca in _REPARSE_DE_LINK


def _norm(caminho: Path) -> str:
    return os.path.normcase(str(caminho))


def inside_repo(repo: Path, relativo: str) -> bool:
    """`relativo` (POSIX, relativo a `repo`) pode ser apagado: nenhum componente e
    link ou juncao, o caminho resolvido e o logico e fica dentro do repositorio."""
    partes = PurePosixPath(relativo).parts
    if not partes or ".." in partes or PurePosixPath(relativo).is_absolute():
        return False
    atual = Path(repo)
    for parte in partes:
        atual = atual / parte
        if _e_link(atual):
            return False
    try:
        raiz = Path(repo).resolve()
        resolvido = (Path(repo) / relativo).resolve()
    except (OSError, RuntimeError):
        return False
    return _norm(resolvido) == _norm(raiz.joinpath(*partes)) and _norm(raiz) in {
        _norm(p) for p in resolvido.parents
    }


def _podar(caminho: Path, base: Path) -> None:
    pai = caminho.parent
    while (
        pai != base
        and base in pai.parents
        and not _e_link(pai)
        and pai.is_dir()
        and not any(pai.iterdir())
    ):
        pai.rmdir()
        pai = pai.parent


def _chave(colisao: dict[str, Any]) -> str:
    return f"{colisao['location']}/{colisao['name']}"


def resolve(
    repo: Path,
    colisoes: list[dict[str, Any]],
    escolha: str,
    *,
    dry_run: bool,
    integrados: Iterable[str] | None = None,
    announce: Callable[[list[str]], None] | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    """Aplica a escolha. A lista do que sai, arquivo por arquivo, vem no relatorio
    (`planned_removals`) e chega a `announce` ANTES da primeira remocao.

    `integrados=None` trata todo host como integrado; com a lista, a entrada que
    um host ainda nao integrado le fica, como `mantido_host_nao_integrado`.
    `repo` que e o HOME (ou o contem, ou mora num destino) sai
    `repositorio_e_o_home`, sem remocao nenhuma, qualquer que seja a escolha."""
    repo = Path(repo)
    guarda = home_guard(repo, home=home, appdata=appdata, codex_home=codex_home)
    if guarda is not None:
        return {
            "choice": escolha,
            "dry_run": dry_run,
            "planned_removals": [],
            "removed": [],
            "still_duplicated": sorted(_chave(c) for c in colisoes),
            "kept": [],
            "refused": [guarda],
        }
    mantidos = []
    if integrados is not None:
        integrados = list(integrados)
        for c in colisoes:
            faltam = missing_hosts(c, integrados)
            if faltam:
                mantidos.append({"path": _chave(c), "reason": "mantido_host_nao_integrado",
                                 "missing_hosts": faltam})
    bloqueadas = {m["path"] for m in mantidos}
    candidatas = [c for c in colisoes if _chave(c) not in bloqueadas]
    if escolha == "overwrite":
        saem = candidatas
    elif escolha == "merge":
        saem = [c for c in candidatas if c["identical"]]
    else:
        saem = []
    recusas = [
        {"reason": "copia_fora_do_repositorio", "path": _chave(c)}
        for c in saem
        if not all(inside_repo(repo, arquivo) for arquivo in c["files"])
    ]
    fora = {r["path"] for r in recusas}
    saem = [c for c in saem if _chave(c) not in fora]
    ficam = [c for c in colisoes if c not in saem]
    planejados = sorted(arquivo for c in saem for arquivo in c["files"])
    removidos: list[str] = []
    if not dry_run and planejados:
        if announce is not None:
            announce(list(planejados))
        for relativo in planejados:
            caminho = repo / relativo
            # Rechecado na hora de apagar: o que mudou desde a deteccao nao passa.
            if caminho.is_file() and inside_repo(repo, relativo):
                caminho.unlink()
                removidos.append(relativo)
                _podar(caminho, repo / relativo.split("/")[0])
    return {
        "choice": escolha,
        "dry_run": dry_run,
        "planned_removals": planejados,
        "removed": planejados if dry_run else removidos,
        "still_duplicated": sorted(_chave(c) for c in ficam),
        "kept": mantidos,
        "refused": recusas,
    }


__all__ = [
    "ESCOLHAS",
    "VENDOR_LOCATIONS",
    "choose",
    "detect",
    "git_root",
    "home_guard",
    "inside_repo",
    "is_source_repo",
    "missing_hosts",
    "relevant",
    "resolve",
]
