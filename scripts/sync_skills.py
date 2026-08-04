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
"""
from __future__ import annotations

import argparse
import filecmp
import re
import shutil
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

# --------------------------------------------------------------------------
# Renderizacao por plataforma
# --------------------------------------------------------------------------
# Fundamento medido: knowledge/devin/agents-and-subagents.md (retrieved
# 2026-08-04). Desenho: D-1, D-2 e D-3 de
# docs/superpowers/specs/2026-08-04-sparkforge-devin-subagentes-design.md.

# `claude` e `github` recebem o arquivo INALTERADO. Nao ha round-trip de YAML
# em caminho nenhum: parsear e re-serializar reordenaria as chaves e produziria
# diff onde nao houve mudanca, e o gate viraria ruido.
PASSTHROUGH_PLATFORMS = frozenset({"claude", "github"})
PLATFORMS = PASSTHROUGH_PLATFORMS | {"devin"}

# Campos que o espelho do Devin NAO leva.
#
# `tools:` -- o Devin aceita o campo ("Claude Code agent files use `tools`
# instead of `allowed-tools`[...] Both formats are supported automatically"),
# mas o MAPEAMENTO DE VALORES nao esta documentado em lugar nenhum: `Bash` ->
# `exec`? `Write` -> `write`? Os nomes de tool do Devin sao `read`, `edit`,
# `grep`, `glob`, `exec` (cli/reference/permissions.md). Chute em campo de
# PERMISSAO concede ou nega errado, e nos dois sentidos o erro e caro. Omitido,
# o subagente herda o que o harness da -- que e o comportamento que a propria
# documentacao descreve como default ("all tools"). Veto V-DV-8.
DEVIN_DROPPED_KEYS = frozenset({"tools"})

# NENHUM caminho aqui ACRESCENTA `model:`, e isso e deliberado (D-3):
#   1. o default do subagente "is not a fixed model name -- it resolves through
#      a router at spawn time";
#   2. o admin da organizacao sobrescreve pela setting "Default subagent
#      model", inclusive com a opcao *None*, que desliga o despacho por
#      completo;
#   3. o identificador literal e `swe-1-7`, com HIFEN -- a doc interna que
#      motivou esta fase errava com ponto, e nenhuma pagina do CLI documenta
#      esse literal como valor aceito de frontmatter (vetos V-DV-2 e V-DV-3).
# Escrever `model:` seria fingir controle sobre o que o harness decide. Quem
# vier depois vai querer "completar" o frontmatter: nao complete sem medir.

_FRONTMATTER_FENCE = "---"
_TOP_LEVEL_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:")


def _split_frontmatter(text: str) -> tuple[list[str], list[str], list[str]] | None:
    """Fatia o texto em (abertura, corpo do frontmatter, resto).

    Trabalha em linhas com o fim de linha preservado (`keepends=True`): o gate
    compara byte a byte, entao normalizar CRLF para LF produziria DIVERGENTE em
    toda regeneracao numa arvore com `autocrlf`.

    Devolve `None` quando nao ha frontmatter delimitado -- ai o arquivo sai
    inalterado, em vez de o renderizador adivinhar onde o cabecalho termina.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != _FRONTMATTER_FENCE:
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == _FRONTMATTER_FENCE:
            return lines[:1], lines[1:index], lines[index:]
    return None


def _drop_frontmatter_keys(front: list[str], keys: frozenset[str]) -> list[str]:
    """Remove chaves de topo do frontmatter, com as continuacoes delas.

    A continuacao importa porque o campo tem duas formas possiveis:

        tools: Read, Grep, Glob        # inline -- e a forma dos treze perfis hoje
        tools:                         # bloco
          - Read
          - Grep

    Apagar so a linha `tools:` na forma de bloco deixaria `  - Read` orfao e
    quebraria o YAML do espelho. A remocao para na proxima linha nao indentada,
    para nao engolir a chave seguinte -- `skills:` vem logo depois e tambem e
    lista indentada.
    """
    kept: list[str] = []
    dropping = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if not dropping:
                kept.append(line)
            continue
        match = _TOP_LEVEL_KEY.match(content)
        dropping = bool(match) and match.group(1) in keys
        if not dropping:
            kept.append(line)
    return kept


def render_agent(text: str, platform: str) -> str:
    """Devolve o conteudo do perfil no formato que `platform` le.

    `claude` e `github` recebem o texto identico -- o espelho deles nao mudou
    nesta fase, e um renderizador que mexesse em todos os alvos quebraria o
    Copilot sem ninguem pedir.
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; conhecidas: {sorted(PLATFORMS)}"
        )
    if platform in PASSTHROUGH_PLATFORMS:
        return text

    parsed = _split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed

    kept = _drop_frontmatter_keys(front, DEVIN_DROPPED_KEYS)
    if kept == front:
        return text
    return "".join(opening + kept + rest)


def iter_skill_files() -> list[Path]:
    return sorted(p for p in CANONICAL.rglob("*") if p.is_file())


def iter_agent_files() -> list[Path]:
    return sorted(p for p in AGENTS_SRC.glob("*.md") if p.is_file())


def iter_executor_files() -> list[Path]:
    return sorted(p for p in EXECUTORS_SRC.glob("*.md") if p.is_file())


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
            elif not filecmp.cmp(src, dst, shallow=False):
                problems.append(f"DIVERGENTE {dst}")

        for rel in sorted(mirror_rel - canonical_rel):
            problems.append(f"ORFAO {mirror / rel}")

    return problems


def check_agents() -> list[str]:
    problems: list[str] = []
    agent_files = iter_agent_files()

    for mirror_dir, name_pattern in AGENT_MIRRORS:
        expected_names = {name_pattern.format(stem=p.stem) for p in agent_files}
        mirror_names = (
            {p.name for p in mirror_dir.glob("*.md") if p.is_file()}
            if mirror_dir.exists()
            else set()
        )

        for src in agent_files:
            dst = mirror_dir / name_pattern.format(stem=src.stem)
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not filecmp.cmp(src, dst, shallow=False):
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
        mirror_names = (
            {p.name for p in mirror_dir.glob("*.md") if p.is_file()}
            if mirror_dir.exists()
            else set()
        )

        for src in executor_files:
            dst = mirror_dir / src.name
            if not dst.exists():
                problems.append(f"AUSENTE {dst}")
            elif not filecmp.cmp(src, dst, shallow=False):
                problems.append(f"DIVERGENTE {dst}")

        for orphan_name in sorted(mirror_names - expected_names):
            problems.append(f"ORFAO {mirror_dir / orphan_name}")

    return problems


def check() -> int:
    problems = check_skills() + check_agents() + check_executors()

    if problems:
        print(
            "Espelhos fora de sincronia com skills/ e agents/ "
            "(rode: python scripts/sync_skills.py):"
        )
        for line in problems:
            print(f"  {line}")
        return 1

    print("OK: .claude, .agents e .github idênticos a skills/ e agents/.")
    return 0


def sync_skills() -> int:
    canonical_rel = {p.relative_to(CANONICAL) for p in iter_skill_files()}
    changed = 0

    for mirror in MIRRORS:
        # Copia/atualiza arquivos canônicos.
        for rel in sorted(canonical_rel):
            src = CANONICAL / rel
            dst = mirror / rel
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPY {dst}")
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
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPY {dst}")
            changed += 1

        if mirror_dir.exists():
            for path in sorted(
                (p for p in mirror_dir.glob("*.md") if p.is_file()), reverse=True
            ):
                if path.name not in expected_names:
                    path.unlink()
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
            if dst.exists() and filecmp.cmp(src, dst, shallow=False):
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"COPY {dst}")
            changed += 1

        if mirror_dir.exists():
            for path in sorted(
                (p for p in mirror_dir.glob("*.md") if p.is_file()), reverse=True
            ):
                if path.name not in expected_names:
                    path.unlink()
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
