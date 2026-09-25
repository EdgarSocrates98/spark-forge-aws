#!/usr/bin/env python3
"""Sincroniza skills e agents canônicos para os adaptadores de plataforma.

Fontes da verdade: skills/ e agents/ (incluindo agents/executors/)
Espelhos gerados:
    - skills/           -> .claude/skills/ e .agents/skills/
    - agents/*.md       -> .claude/agents/, .agents/agents/ e .github/agents/ (sufixo .agent.md)
    - agents/executors/ -> .claude/agents/executors/, .agents/agents/executors/ e
                            .github/agents/executors/ (nome preservado, sem sufixo)

Uso:
    python scripts/sync_skills.py          # regenera os espelhos a partir de skills/ e agents/
    python scripts/sync_skills.py --check   # falha (exit 1) se algum espelho divergir

O modo --check é usado pelos testes e pode ser plugado em CI para impedir drift.

Nada aqui é copiado: perfis e skills são RENDERIZADOS por plataforma
(`render_agent`, `render_skill`), e o gate compara o espelho contra o que o
renderizador produz — não contra a fonte. O invariante é "o espelho é
exatamente o que o tradutor produz", que é estritamente mais forte que
byte-identidade.

Na prática, `.claude/` e `.github/` recebem passthrough byte a byte; só o
espelho do Devin transforma — perfil perde `tools:`, e skill despachável ganha
`subagent:`/`agent:`.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "skills"
MIRRORS = (ROOT / ".claude" / "skills", ROOT / ".agents" / "skills")

AGENTS_SRC = ROOT / "agents"
EXECUTORS_SRC = AGENTS_SRC / "executors"
AGENT_MIRRORS = (
    (ROOT / ".claude" / "agents", "{stem}.md"),
    (ROOT / ".agents" / "agents", "{stem}.md"),
    (ROOT / ".github" / "agents", "{stem}.agent.md"),
)
# Executores nao levam sufixo de plataforma: nenhum adaptador os trata como
# agente de topo, entao preservam o nome e o subdiretorio `executors/`.
EXECUTOR_MIRRORS = (
    ROOT / ".claude" / "agents" / "executors",
    ROOT / ".agents" / "agents" / "executors",
    ROOT / ".github" / "agents" / "executors",
)
STALE_AGENTS = (ROOT / ".github" / "agents" / "spark-performance-engineer.agent.md",)

# Subdiretorios do espelho de agentes que tem DONO PROPRIO. `executors/` mora
# dentro de `.claude/agents/`, `.agents/agents/` e `.github/agents/`, e quem o
# confere e `check_executors`; sem esta exclusao a varredura recursiva acusaria
# os cinco executores como orfaos dos agentes, e o `sync` os apagaria.
AGENT_MIRROR_SUBTREES_WITH_OWNER = frozenset({"executors"})

# A plataforma sai do PROPRIO ALVO, nao de uma quarta lista mantida a mao ao
# lado de `AGENT_MIRRORS` e `EXECUTOR_MIRRORS`. Duas listas paralelas que
# precisam concordar sao a familia de defeito que a Fase 5c achou nos dois
# `EXTRACTORS`: uma cresce, a outra nao, e o desacordo e mudo. Aqui o desacordo
# nem chega a ser possivel -- o diretorio-raiz do espelho E o dado.
PLATFORM_BY_MIRROR_ROOT = {
    ".claude": "claude",
    ".agents": "devin",
    ".github": "github",
}

# --------------------------------------------------------------------------
# Renderizacao por plataforma: mora em sparkforge/integrate/render.py
# --------------------------------------------------------------------------
# Um renderizador so para os espelhos deste repositorio e para a integracao por
# usuario (`sparkforge integrate`), feature INTEGRACAO_USUARIO, D1. Este arquivo e
# a fachada: reexporta os nomes que os testes e o `--check` usam e passa o proprio
# `AGENTS_SRC` as funcoes que leem perfis.
#
# O modulo e carregado PELO CAMINHO, a partir de `ROOT`, e nao por
# `import sparkforge...`. `tests/test_arvore_versionada.py` roda este script sobre
# uma copia de `git archive HEAD`; um import pelo pacote acharia o `render.py` do
# disco (instalacao editavel), e o gate deixaria de conferir o renderizador
# commitado. `render.py` so importa a biblioteca padrao, e por isso carrega sozinho.
_RENDER_PATH = ROOT / "sparkforge" / "integrate" / "render.py"
_RENDER_SPEC = importlib.util.spec_from_file_location("_sparkforge_render", _RENDER_PATH)
if _RENDER_SPEC is None or _RENDER_SPEC.loader is None:
    raise ImportError(f"renderizador nao encontrado: {_RENDER_PATH}")
_render = importlib.util.module_from_spec(_RENDER_SPEC)
sys.modules[_RENDER_SPEC.name] = _render
_RENDER_SPEC.loader.exec_module(_render)

PASSTHROUGH_PLATFORMS = _render.PASSTHROUGH_PLATFORMS
PLATFORMS = _render.PLATFORMS
DEVIN_DROPPED_KEYS = _render.DEVIN_DROPPED_KEYS
DEVIN_BUILTIN_PROFILE_NAMES = _render.DEVIN_BUILTIN_PROFILE_NAMES
DEVIN_SKILL_DISPATCH_KEYS = _render.DEVIN_SKILL_DISPATCH_KEYS
DISPATCHABLE_SKILLS = _render.DISPATCHABLE_SKILLS
NON_DISPATCHABLE_SKILLS = _render.NON_DISPATCHABLE_SKILLS
SKILL_DISPATCH_REASON = _render.SKILL_DISPATCH_REASON
SKILL_FILENAME = _render.SKILL_FILENAME
render_agent = _render.render_agent
_split_frontmatter = _render._split_frontmatter
_drop_frontmatter_keys = _render._drop_frontmatter_keys
_frontmatter_list = _render._frontmatter_list
_frontmatter_scalar = _render._frontmatter_scalar


def coordinators_by_skill() -> dict[str, tuple[str, ...]]:
    return _render.coordinators_by_skill(AGENTS_SRC)


def orchestrator_profiles() -> frozenset[str]:
    return _render.orchestrator_profiles(AGENTS_SRC)


def agent_for_skill(name: str) -> str | None:
    return _render.agent_for_skill(name, AGENTS_SRC)


def render_skill(text: str, platform: str, *, name: str) -> str:
    return _render.render_skill(text, platform, name=name, agents_src=AGENTS_SRC)


def profile_name_problem(path: Path) -> str | None:
    """O identificador que `path` publica colide com um built-in do Devin?

    Confere as **duas** fontes de identidade, porque elas podem discordar: o nome
    do arquivo, que a fonte declara ser o default do campo, e o `name:` do
    frontmatter, que vence quando existe. Um gate que so olhasse o caminho
    deixaria passar `revisor.md` com `name: subagent_general`.
    """
    parsed = _split_frontmatter(path.read_bytes().decode("utf-8"))
    declared = _frontmatter_scalar(parsed[1], "name") if parsed else None
    for identifier in (path.stem, declared):
        if identifier in DEVIN_BUILTIN_PROFILE_NAMES:
            return (
                f"NOME RESERVADO {path}: `{identifier}` e perfil embutido do Devin "
                "(knowledge/devin/agents-and-subagents.md, secao 1). A fonte proibe "
                "a colisao e nao diz o que acontece nela -- escolha outro nome"
            )
    return None


def check_profile_names() -> list[str]:
    """Confere as FONTES, nunca os espelhos.

    O espelho e derivado: um nome reservado que chegasse ao `.agents/agents/`
    teria vindo de `agents/`, e acusar nos dois lugares so multiplicaria a mesma
    linha por tres.
    """
    return [
        problem
        for path in iter_agent_files() + iter_executor_files()
        if (problem := profile_name_problem(path)) is not None
    ]


def skill_name_for(src: Path) -> str:
    """O identificador da skill e o NOME DO DIRETORIO, nao o `name:` do arquivo.

    E o mesmo identificador que o Devin usa (`.agents/skills/<name>/SKILL.md`) e
    o que os coordenadores escrevem em `skills:`. `test_skill_content` ja exige
    que o `name:` do frontmatter case com a pasta; derivar do caminho evita
    depender de um campo que o proprio renderizador poderia ter mexido.
    """
    return src.relative_to(CANONICAL).parts[0]


def rendered_skill_bytes(src: Path, dst: Path) -> bytes:
    """O que o espelho de skill `dst` DEVERIA conter.

    Arquivo que nao e `SKILL.md` sai como esta, sem passar por `decode` -- um
    anexo binario numa skill futura quebraria a leitura, e ele nao tem
    frontmatter para renderizar de todo jeito.
    """
    data = src.read_bytes()
    if src.name != SKILL_FILENAME:
        return data
    rendered = render_skill(
        data.decode("utf-8"), platform_for(dst), name=skill_name_for(src)
    )
    return rendered.encode("utf-8")


def platform_for(mirror_path: Path) -> str:
    """Deriva a plataforma do diretorio-raiz do espelho.

    `.agents/` e `devin`, `.claude/` e `claude`, `.github/` e `github`. Alvo
    fora dos tres levanta -- caminho novo tem que declarar como se traduz para
    ele, em vez de cair num default que publicaria o arquivo cru.
    """
    parts = mirror_path.resolve().relative_to(ROOT).parts
    if not parts or parts[0] not in PLATFORM_BY_MIRROR_ROOT:
        raise ValueError(f"espelho sem plataforma conhecida: {mirror_path}")
    return PLATFORM_BY_MIRROR_ROOT[parts[0]]


def rendered_bytes(src: Path, dst: Path) -> bytes:
    """O que o espelho `dst` DEVERIA conter, a partir da fonte `src`.

    Le e escreve em bytes de proposito. `Path.read_text()` aplica newline
    universal e devolveria CRLF como LF: um espelho gravado com CRLF passaria
    a comparar igual a uma fonte LF, e o gate deixaria de ser byte a byte sem
    ninguem notar.
    """
    text = src.read_bytes().decode("utf-8")
    return render_agent(text, platform_for(dst)).encode("utf-8")


def mirror_is_current(src: Path, dst: Path) -> bool:
    """O invariante da Task 2.

    Nao e mais "os arquivos sao identicos" -- e "o espelho e exatamente o que o
    tradutor produz". A forma antiga (`filecmp.cmp`) nunca poderia pegar um
    campo que a plataforma exige e a fonte nao tem, nem um campo que a fonte
    tem e a plataforma nao deve receber; a nova pega os dois.
    """
    return dst.read_bytes() == rendered_bytes(src, dst)


def write_mirror(src: Path, dst: Path) -> None:
    """Grava o espelho JA RENDERIZADO.

    A escrita passa pelo mesmo tradutor que o `--check` usa. Copiar aqui e
    comparar contra renderizacao la faria o gate acusar na execucao seguinte a
    cada regeneracao -- o script brigaria consigo mesmo.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(rendered_bytes(src, dst))


def iter_skill_files() -> list[Path]:
    return sorted(p for p in CANONICAL.rglob("*") if p.is_file())


def iter_agent_files() -> list[Path]:
    return sorted(p for p in AGENTS_SRC.glob("*.md") if p.is_file())


def iter_executor_files() -> list[Path]:
    return sorted(p for p in EXECUTORS_SRC.glob("*.md") if p.is_file())


def iter_mirror_files(mirror_dir: Path, *, skip: frozenset[str] = frozenset()) -> list[Path]:
    """Todo arquivo do espelho, em qualquer profundidade e qualquer extensao.

    Era `mirror_dir.glob("*.md")` -- **raso, e so `.md`**. Duas coisas passavam:

    1. `.agents/agents/<nome>/AGENT.md`. Isso nao e arquivo perdido: e **layout
       de descoberta documentado do Devin** (secao 1.1 da pesquisa -- "Directory
       -- `agents/<name>/AGENT.md`. The directory name becomes the profile's
       identifier", com precedencia `AGENT.md > AGENTS.md > agent.md >
       agents.md`). Um perfil publicado por ali tem `tools:` arbitrario, nao tem
       `## Nao faz`, e nao aparece nem no gate nem no teste de fronteira -- que
       deriva das pastas-fonte, nunca do espelho.
    2. Arquivo de outra extensao, que o gate simplesmente nao via.

    `skip` nomeia os subdiretorios com dono proprio; o resto da arvore e do
    chamador. Devolve os caminhos absolutos, e o chamador relativiza -- a
    comparacao com o esperado e por caminho relativo em POSIX, para que
    `rogue/AGENT.md` e `rogue\\AGENT.md` sejam a mesma coisa nos dois SOs.
    """
    if not mirror_dir.exists():
        return []
    return sorted(
        path
        for path in mirror_dir.rglob("*")
        if path.is_file() and path.relative_to(mirror_dir).parts[0] not in skip
    )


def _remove_orphan(path: Path, mirror_dir: Path) -> None:
    """Apaga o orfao e os diretorios que ficaram vazios por causa dele.

    Sem a segunda parte, apagar `rogue/AGENT.md` deixaria `rogue/` em disco --
    diretorio vazio nao publica perfil, mas confunde quem olha, e o proximo
    arquivo posto ali dentro voltaria a ser o mesmo caso. A subida para na raiz
    do espelho e em qualquer diretorio que ainda tenha conteudo.
    """
    path.unlink()
    parent = path.parent
    while parent != mirror_dir and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent


def check_skills() -> list[str]:
    problems: list[str] = []
    canonical_rel = {p.relative_to(CANONICAL) for p in iter_skill_files()}

    for mirror in MIRRORS:
        mirror_rel = {
            p.relative_to(mirror) for p in mirror.rglob("*") if p.is_file()
        } if mirror.exists() else set()

        for rel in sorted(canonical_rel):
            src = CANONICAL / rel
            dst = mirror / rel
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif dst.read_bytes() != rendered_skill_bytes(src, dst):
                problems.append(f"DIVERGENTE {dst}")

        for rel in sorted(mirror_rel - canonical_rel):
            problems.append(f"ORFAO {mirror / rel}")

    return problems


def check_agents() -> list[str]:
    problems: list[str] = []
    agent_files = iter_agent_files()

    for mirror_dir, name_pattern in AGENT_MIRRORS:
        expected_names = {name_pattern.format(stem=p.stem) for p in agent_files}
        mirror_names = {
            p.relative_to(mirror_dir).as_posix()
            for p in iter_mirror_files(
                mirror_dir, skip=AGENT_MIRROR_SUBTREES_WITH_OWNER
            )
        }

        for src in agent_files:
            dst = mirror_dir / name_pattern.format(stem=src.stem)
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not mirror_is_current(src, dst):
                problems.append(f"DIVERGENTE {dst}")

        for orphan_name in sorted(mirror_names - expected_names):
            problems.append(f"ORFAO {mirror_dir / orphan_name}")

    for stale in STALE_AGENTS:
        if stale.exists():
            problems.append(f"OBSOLETO {stale}")

    return problems


def check_executors() -> list[str]:
    problems: list[str] = []
    executor_files = iter_executor_files()
    expected_names = {p.name for p in executor_files}

    for mirror_dir in EXECUTOR_MIRRORS:
        mirror_names = {
            p.relative_to(mirror_dir).as_posix() for p in iter_mirror_files(mirror_dir)
        }

        for src in executor_files:
            dst = mirror_dir / src.name
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not mirror_is_current(src, dst):
                problems.append(f"DIVERGENTE {dst}")

        for orphan_name in sorted(mirror_names - expected_names):
            problems.append(f"ORFAO {mirror_dir / orphan_name}")

    return problems


def check() -> int:
    problems = (
        check_skills() + check_agents() + check_executors() + check_profile_names()
    )

    if problems:
        print(
            "Espelhos fora de sincronia com skills/ e agents/ "
            "(rode: python scripts/sync_skills.py):"
        )
        for line in problems:
            print(f"  {line}")
        return 1

    print(
        "OK: .claude, .agents e .github em dia com skills/ e agents/ "
        "(perfis conferidos contra a renderização de cada plataforma)."
    )
    return 0


def sync_skills() -> int:
    canonical_rel = {p.relative_to(CANONICAL) for p in iter_skill_files()}
    changed = 0

    for mirror in MIRRORS:
        # Renderiza/atualiza arquivos canônicos.
        for rel in sorted(canonical_rel):
            src = CANONICAL / rel
            dst = mirror / rel
            data = rendered_skill_bytes(src, dst)
            if dst.exists() and dst.read_bytes() == data:
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            print(f"{'REND' if data != src.read_bytes() else 'COPY'} {dst}")
            changed += 1

        # Remove órfãos que não existem mais no canônico.
        if mirror.exists():
            for path in sorted(
                (p for p in mirror.rglob("*") if p.is_file()), reverse=True
            ):
                if path.relative_to(mirror) not in canonical_rel:
                    path.unlink()
                    print(f"DEL  {path}")
                    changed += 1

    return changed


def sync_agents() -> int:
    agent_files = iter_agent_files()
    changed = 0

    for mirror_dir, name_pattern in AGENT_MIRRORS:
        expected_names = {name_pattern.format(stem=p.stem) for p in agent_files}

        for src in agent_files:
            dst = mirror_dir / name_pattern.format(stem=src.stem)
            if dst.exists() and mirror_is_current(src, dst):
                continue
            write_mirror(src, dst)
            print(f"REND {dst}")
            changed += 1

        for path in sorted(
            iter_mirror_files(mirror_dir, skip=AGENT_MIRROR_SUBTREES_WITH_OWNER),
            reverse=True,
        ):
            if path.relative_to(mirror_dir).as_posix() not in expected_names:
                _remove_orphan(path, mirror_dir)
                print(f"DEL  {path}")
                changed += 1

    for stale in STALE_AGENTS:
        if stale.exists():
            stale.unlink()
            print(f"DEL  {stale}")
            changed += 1

    return changed


def sync_executors() -> int:
    executor_files = iter_executor_files()
    expected_names = {p.name for p in executor_files}
    changed = 0

    for mirror_dir in EXECUTOR_MIRRORS:
        for src in executor_files:
            dst = mirror_dir / src.name
            if dst.exists() and mirror_is_current(src, dst):
                continue
            write_mirror(src, dst)
            print(f"REND {dst}")
            changed += 1

        for path in sorted(iter_mirror_files(mirror_dir), reverse=True):
            if path.relative_to(mirror_dir).as_posix() not in expected_names:
                _remove_orphan(path, mirror_dir)
                print(f"DEL  {path}")
                changed += 1

    return changed


def sync() -> int:
    changed = sync_skills() + sync_agents() + sync_executors()
    print(f"Sync concluído ({changed} alteração(ões)).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Apenas verifica sincronia; não escreve nada.",
    )
    args = parser.parse_args()
    return check() if args.check else sync()


if __name__ == "__main__":
    raise SystemExit(main())
