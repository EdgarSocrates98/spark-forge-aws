"""Testes de qualidade e integridade do conteúdo das skills.

Complementam test_package_structure/test_v020_structure (que checam existência)
validando frontmatter, seções padronizadas, referências e paridade das 3 cópias.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "skills"
MIRRORS = (ROOT / ".claude" / "skills", ROOT / ".agents" / "skills")

SKILL_DIRS = sorted(p for p in CANONICAL.iterdir() if p.is_dir())
SKILL_IDS = [p.name for p in SKILL_DIRS]

# Diretórios de suporte referenciáveis por caminho relativo à raiz do repo.
REF_ROOTS = ("templates", "checklists", "knowledge", "examples")
REF_PATTERN = re.compile(r"`((?:templates|checklists|knowledge|examples)/[\w./-]+)`")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        raise AssertionError("SKILL.md deve começar com frontmatter YAML (---).")
    end = text.index("\n---", 3)
    body = text[3:end]
    data: dict[str, str] = {}
    for line in body.splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            data[key.strip()] = value.strip()
    return data


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_frontmatter_valido(skill_dir: Path) -> None:
    fm = parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    assert fm.get("name") == skill_dir.name, "name do frontmatter deve casar com a pasta"
    desc = fm.get("description", "")
    assert desc, "description obrigatória"
    assert len(desc) <= 1024, "frontmatter deve caber em 1024 chars"
    # SDO: descrição orientada ao gatilho, não ao que a skill faz.
    assert desc.lower().startswith("use quando"), (
        f"{skill_dir.name}: description deve começar com 'Use quando' (gatilho), "
        f"não com o que a skill faz."
    )


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_secoes_padronizadas(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    for heading in ("## Quando NÃO usar", "## Referência rápida", "## Red flags"):
        assert heading in text, f"{skill_dir.name}: seção obrigatória ausente: {heading}"


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_referencias_resolvem(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    for ref in REF_PATTERN.findall(text):
        assert (ROOT / ref).exists(), f"{skill_dir.name}: referência inexistente: {ref}"


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_copias_identicas(skill_dir: Path) -> None:
    canonical = (skill_dir / "SKILL.md").read_bytes()
    for mirror in MIRRORS:
        dst = mirror / skill_dir.name / "SKILL.md"
        assert dst.exists(), f"espelho ausente: {dst}"
        assert dst.read_bytes() == canonical, (
            f"{dst} divergente. Rode: python scripts/sync_skills.py"
        )


# `runtime_scope` so sobra em 8 regras do catalogo, todas sobre Glue -- a Fase 5a
# esvaziou os guardas de versao que nao guardavam versao nenhuma. Essas 8 falham
# fechado quando o runtime nao e conhecido, e `judge` sem `--glue` pulava o eixo
# de infraestrutura Glue inteiro.
#
# Desde a Fase 5a.2 isso deixou de depender SO da flag: `build_runtime_context`
# deriva fontes dos proprios facts (`tf.attribute` glue_version,
# `spark.runtime_version`), entao um `judge --facts <terraform>` ja resolve o
# runtime sozinho. A exigencia de flag continua travada aqui de proposito
# ate as skills serem reescritas para o fluxo novo: uma skill que hoje instrui o
# operador a digitar a versao nao esta errada, so esta pedindo mais do que
# precisa. Relaxar esta regra e mudanca de texto de skill, nao de motor -- ver o
# plano da Fase 5a.2.
JUDGE_INVOCATION = re.compile(r"^\s*(?:\d+\.\s*)?`?sparkforge judge\b")
RUNTIME_FLAGS = ("--glue", "--spark", "--iceberg", "--athena")


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_toda_invocacao_de_judge_passa_runtime(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not JUDGE_INVOCATION.match(line):
            continue
        # Comando pode continuar em linhas seguintes via `\` no fim.
        bloco, j = line, i
        while bloco.rstrip().endswith("\\") and j + 1 < len(lines):
            j += 1
            bloco += lines[j]
        assert any(flag in bloco for flag in RUNTIME_FLAGS), (
            f"{skill_dir.name}:{i + 1} chama `sparkforge judge` sem passar runtime. "
            f"Sem isso, as 8 regras com `runtime_scope` sobre Glue sao puladas -- "
            f"o eixo de infraestrutura Glue nao e coberto. Acrescente `--glue <versao>` "
            f"ou a flag que a skill investiga.\n  {line.strip()}"
        )
