"""Testes de qualidade e integridade do conteúdo das skills.

Complementam test_package_structure/test_v020_structure (que checam existência)
validando frontmatter, seções padronizadas, referências e paridade das 3 cópias.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from sparkforge.findings.models import RuntimeContext
from sparkforge.rules.engine import judge

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


# --------------------------------------------------------------------------- #
# runtime nas skills que chamam `judge`
# --------------------------------------------------------------------------- #
#
# A Fase 5a exigia aqui que toda invocacao de `judge` carregasse ALGUMA flag de
# runtime. Era um teste que nao pegava nada: todas as skills ja passavam, e o que
# passavam era `--glue <versao>` -- um PLACEHOLDER, que pede ao agente um valor
# que ele nao tem de onde tirar. Preencher errado julga contra o limiar errado em
# silencio; omitir pula as 8 regras versionadas. O teste aprovava as duas.
#
# Desde `8a7d506` o motor infere o runtime dos proprios facts (`tf.attribute`
# glue_version, `spark.runtime_version`) e devolve, em `judge`, o campo `runtime`
# com o contexto EFETIVAMENTE usado. A flag virou declaracao opcional de quem
# sabe a versao de fonte confiavel, e o invariante que interessa mudou junto:
# nao e mais "passou flag", e sim **a skill diz ao operador como o runtime chega,
# e o que fazer quando nao chega**. Uma skill que chama `judge` sem mencionar nem
# a inferencia, nem `--show-skipped`, nem o motivo do skip deixa o agente cego --
# e e isso que este teste existe para pegar.
#
# POR QUE NAO E BUSCA POR FRASE MAGICA: o vocabulario exigido nao esta escrito
# aqui, e PERGUNTADO AO MOTOR. Os nomes de campo saem de `RuntimeContext.to_dict`
# e o motivo do skip sai de uma execucao real de `judge` com uma regra-sonda.
# Sao identificadores do contrato de saida, nao prosa: uma skill nova pode
# reescrever cada frase como quiser e continua tendo que nomea-los, porque e por
# eles que o operador le a proveniencia (`detected_from`), a discordancia entre
# fontes (`divergences`) e o motivo de uma regra nao ter sido avaliada. E se
# alguem renomear um campo no motor, este teste passa a cobrar o nome NOVO em vez
# de continuar aprovando skills que documentam um contrato que nao existe mais --
# foi assim que `{athena: "*"}` passou despercebido na Fase 5a, guardando por uma
# string que ninguem mais emitia.
#
# O limite honesto: nenhum teste de texto prova que a explicacao e boa. Ele prova
# que os identificadores acionaveis estao la, o que e o piso -- e o piso e o que
# uma skill nova, copiada do comando alheio, nao alcanca sozinha.

_RUNTIME_FIELDS = RuntimeContext().to_dict()
# `glue`, `spark`, `python`, `iceberg`, `athena` -- que sao tambem os nomes das flags.
RUNTIME_COMPONENTS = tuple(k for k, v in _RUNTIME_FIELDS.items() if isinstance(v, str))
# `detected_from`, `divergences` -- por onde o operador le DE ONDE veio a versao.
PROVENANCE_FIELDS = tuple(k for k, v in _RUNTIME_FIELDS.items() if isinstance(v, list))

# Placeholder nao preenchido colado numa flag de runtime: `--glue <versao>`,
# `--iceberg <version>`, `--spark <>`. E a forma exata do defeito que esta task
# removeu -- pedir ao agente um valor que ele nao tem de onde tirar. Uma versao
# concreta (`--glue 5.1`) e declaracao legitima e passa.
RUNTIME_FLAG_PLACEHOLDER = re.compile(
    r"--(?:" + "|".join(RUNTIME_COMPONENTS) + r")[=\s]+<[^>\n]*>"
)


def _runtime_scope_reason() -> str:
    """O motivo que o motor emite ao pular por versao, perguntado a ele.

    Uma regra-sonda com guarda impossivel e runtime vazio: `in_scope` falha
    fechada e `judge` registra o skip. Ler o `reason` daqui, em vez de escrever
    a string no teste, e o que mantem a exigencia amarrada ao motor.
    """
    _findings, skipped = judge(
        [], [{"id": "PROBE-RUNTIME-SCOPE", "runtime_scope": {"glue": ">=99.0"}}], {},
        return_skipped=True,
    )
    assert skipped, "regra-sonda deveria ter sido pulada por runtime_scope"
    return str(skipped[0]["reason"])


RUNTIME_SCOPE_REASON = _runtime_scope_reason()

# Escopo: a skill INSTRUI a rodar `judge`. Deliberadamente mais largo que uma
# regex de linha de comando -- uma skill que so cita `sparkforge judge` na
# description ja esta mandando o agente rodar, e tem a mesma obrigacao de dizer
# como o runtime chega.
JUDGE_MENTION = "sparkforge judge"

JUDGE_SKILLS = [
    p for p in SKILL_DIRS if JUDGE_MENTION in (p / "SKILL.md").read_text(encoding="utf-8")
]
JUDGE_SKILL_IDS = [p.name for p in JUDGE_SKILLS]


def test_ha_skills_que_chamam_judge() -> None:
    """Guarda do proprio parametrize.

    Com `JUDGE_SKILLS` vazio os testes abaixo nao falhariam -- sumiriam da
    coleta, que e pior. Se uma refatoracao mudar o nome do verbo, este teste
    denuncia em vez de deixar a suite verde por ausencia.
    """
    assert JUDGE_SKILLS, (
        f"nenhuma skill menciona {JUDGE_MENTION!r} -- o escopo do invariante evaporou"
    )


@pytest.mark.parametrize("skill_dir", JUDGE_SKILLS, ids=JUDGE_SKILL_IDS)
def test_skill_que_chama_judge_nao_pede_versao_por_placeholder(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    for i, line in enumerate(text.splitlines(), start=1):
        found = RUNTIME_FLAG_PLACEHOLDER.search(line)
        assert not found, (
            f"{skill_dir.name}:{i} pede a versao por placeholder: {found.group(0)!r}\n"
            f"  O agente nao tem de onde tirar esse valor: se inventar, julga contra o "
            f"limiar errado em silencio; se omitir a flag inteira, some tambem a "
            f"explicacao. Escolha uma das duas saidas reais:\n"
            f"   - omita a flag e diga que o motor infere dos facts (`--facts` e "
            f"repetivel; junte os do Terraform ou do event log);\n"
            f"   - declare uma versao concreta (`--glue 5.1`) quando a skill tiver "
            f"fonte confiavel para ela.\n  {line.strip()}"
        )


@pytest.mark.parametrize("skill_dir", JUDGE_SKILLS, ids=JUDGE_SKILL_IDS)
def test_skill_que_chama_judge_explica_como_o_runtime_chega(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    assert any(field in text for field in PROVENANCE_FIELDS), (
        f"{skill_dir.name} manda rodar `{JUDGE_MENTION}` sem dizer como o runtime chega.\n"
        f"  `judge` devolve o campo `runtime` com o contexto que usou de fato para "
        f"filtrar por versao. Cite ao menos um destes campos, para o operador saber "
        f"ler a proveniencia em vez de supor: {list(PROVENANCE_FIELDS)}.\n"
        f"  `detected_from` diz de qual fonte a versao saiu (`terraform`, `event_log`, "
        f"`cli`); `divergences` denuncia fontes que discordam -- que e achado proprio "
        f"(SF-ENV-001), nao detalhe."
    )


@pytest.mark.parametrize("skill_dir", JUDGE_SKILLS, ids=JUDGE_SKILL_IDS)
def test_skill_que_chama_judge_explica_o_que_nao_foi_avaliado(skill_dir: Path) -> None:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

    assert "--show-skipped" in text, (
        f"{skill_dir.name} manda rodar `{JUDGE_MENTION}` sem `--show-skipped`.\n"
        f"  Sem isso, 'nenhum achado' e 'nao consegui avaliar' ficam indistinguiveis "
        f"na saida -- e a inferencia de runtime nao remove esse risco, so muda quando "
        f"ele aparece."
    )

    assert RUNTIME_SCOPE_REASON in text, (
        f"{skill_dir.name} cita `--show-skipped` mas nunca o motivo "
        f"{RUNTIME_SCOPE_REASON!r}.\n"
        f"  Quando nenhuma fonte declara a versao, o contexto fica vazio, `in_scope` "
        f"falha fechada e as regras versionadas sao puladas com esse `reason`. Esse e "
        f"o comportamento CORRETO, nao um bug -- mas so serve se a skill disser ao "
        f"operador que ele vai ver isso, e o que fazer: dar a fonte ao motor "
        f"(`analyze terraform`/`analyze event-log` + `--facts` repetido) ou declarar "
        f"uma versao concreta que ele conheca."
    )
