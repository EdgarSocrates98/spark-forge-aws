"""Testes de qualidade e integridade do conteúdo das skills.

Complementam test_package_structure/test_v020_structure (que checam existência)
validando frontmatter, seções padronizadas, referências e paridade das 3 cópias.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from scripts import sync_skills
from sparkforge.adapters.cli import build_parser
from sparkforge.findings.models import RuntimeContext
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

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
def test_copias_conferem_com_a_renderizacao(skill_dir: Path) -> None:
    """Este teste afirmava byte-identidade com a fonte nos DOIS espelhos.

    Isso deixou de ser o invariante: `.agents/skills/` recebe `subagent:` e
    `agent:` nas skills despacháveis, então o espelho do Devin byte-idêntico à
    fonte passou a ser justamente o defeito — é o que sai sem declarar despacho.
    `.claude/` segue passthrough e continua comparado byte a byte com a fonte,
    porque lá a identidade é o contrato.

    A comparação é em bytes, e não em texto, pela mesma razão da Task 2:
    `read_text()` aplica newline universal e um espelho gravado com CRLF
    passaria a comparar igual a uma fonte LF.
    """
    src = skill_dir / "SKILL.md"
    for mirror in MIRRORS:
        dst = mirror / skill_dir.name / "SKILL.md"
        assert dst.exists(), f"espelho ausente: {dst}"
        assert dst.read_bytes() == sync_skills.rendered_skill_bytes(src, dst), (
            f"{dst} divergente. Rode: python scripts/sync_skills.py"
        )
    claude = MIRRORS[0] / skill_dir.name / "SKILL.md"
    assert claude.read_bytes() == src.read_bytes(), f"{claude} deixou de ser cópia"


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


# --------------------------------------------------------------------------- #
# a documentacao nao pode negar capacidade que o motor ja tem
# --------------------------------------------------------------------------- #
#
# Defeito de origem: os commits `081a570` e `bb72f9f` desbloquearam o catalogo
# inteiro e acrescentaram extratores (`analyze plan`, `analyze s3-listing`,
# `analyze terraform-diff`), e as skills continuaram afirmando o contrario --
# "nao existe parser de plano no toolkit", "nao invente esses comandos",
# "`SF-ICE-004` esta `blocked_on`, nunca dispara hoje". DUAS dessas afirmacoes
# estavam na `description` do frontmatter, que e o gatilho de SELECAO: um agente
# le as descricoes para escolher a skill, e uma que diz "nao existe parser de
# plano" faz ele descartar a ferramenta certa antes de abrir o arquivo. E a mesma
# familia de defeito que `pyspark.unresolved` existe para evitar do outro lado --
# la, ponto cego lido como ausencia de problema; aqui, capacidade existente
# declarada inexistente.
#
# POR QUE NAO E BUSCA POR FRASE MAGICA: os tres invariantes abaixo perguntam ao
# motor QUAIS verbos e QUAIS regras existem -- os subparsers saem de
# `build_parser()` por introspecao do argparse, e o conjunto bloqueado sai de
# `load_catalog()`. Nada aqui enumera `plan`, `s3-listing` ou `SF-ICE-004` a mao.
# Consequencia pratica: no dia em que alguem acrescentar `analyze foo` ou marcar
# uma regra com `blocked_on`, a cobertura acompanha sozinha; e no dia em que
# alguem REMOVER um verbo, o terceiro teste cobra a documentacao que ainda o
# anuncia. So a lista de marcadores de negacao e vocabulario, e ela e
# deliberadamente ampla e casada por SENTENCA, nao por frase inteira -- foi a
# literalidade de um teste guardando string exata que deixou `{athena: "*"}`
# passar na Fase 5a.

DOC_FILES = sorted(
    [p / "SKILL.md" for p in SKILL_DIRS]
    + list((ROOT / "agents").glob("*.md"))
    + list((ROOT / "agents" / "executors").glob("*.md"))
    + [
        ROOT / name
        for name in (
            "README.md",
            "AGENTS.md",
            "AGENT_PROTOCOL.md",
            "PROMPT_INICIAL_MESTRE.md",
            "GUIA_DE_USO.md",
        )
        if (ROOT / name).exists()
    ]
)
DOC_IDS = [str(p.relative_to(ROOT)).replace("\\", "/") for p in DOC_FILES]


def _cli_subcommands() -> dict[str, frozenset[str]]:
    """`{verbo_de_topo: {subcomandos}}`, por introspecao do parser real.

    Perguntar ao argparse em vez de escrever a lista e o que amarra este arquivo
    ao motor: `sparkforge analyze plan` passou a existir sem ninguem tocar aqui.
    """

    def choices(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                return dict(action.choices)
        return {}

    top = choices(build_parser())
    return {name: frozenset(choices(sub)) for name, sub in top.items()}


CLI_SUBCOMMANDS = _cli_subcommands()

# Todo par `<topo> <sub>` que o motor aceita hoje, na forma como a documentacao o
# escreve. So os verbos que TEM subcomando: `sparkforge judge` sozinho nao admite
# negacao de existencia interessante.
EXISTING_COMMANDS = tuple(
    sorted(f"{top} {sub}" for top, subs in CLI_SUBCOMMANDS.items() for sub in subs)
)

# Marcadores de negacao de existencia. Amplo de proposito, e casado por SENTENCA
# para que reformular a frase nao contorne o invariante.
NEGATION_MARKERS = (
    "nao existe",
    "não existe",
    "nao ha",
    "não há",
    "nao tem",
    "não tem",
    "inexistente",
    "nao invente",
    "não invente",
    "sem extrator",
    "nenhum extrator",
    "nao le",
    "não lê",
    "ainda nao",
    "ainda não",
    "nunca dispara",
    "nao vai disparar",
    "não vai disparar",
    "inerte",
    "bloqueada",
    "blocked_on",
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.;:!?])\s+|\n")

# Um marcador em qualquer lugar da sentenca nao prova que ele nega O COMANDO --
# "`sparkforge analyze terraform` (...) quando voce nao tem o `.tf` a mao" nega o
# arquivo, nao o verbo. Exige-se entao que a negacao venha ANTES do comando, perto
# dele, e sem ponto final no meio: e a forma que o defeito real tinha ("nao ha
# `sparkforge analyze plan`", "Nao existe `sparkforge analyze s3` nem
# `sparkforge analyze plan`"). Menos abrangente e mais confiavel -- um teste que
# grita em prosa correta e desligado no primeiro incomodo, e ai nao guarda nada.
NEGATION_WINDOW = 60

# IDs de regra REAIS, perguntados ao catalogo: uma regra removida some daqui
# sozinha, e uma nova entra sozinha.
CATALOG = load_catalog()
RULE_IDS = frozenset(str(r["id"]) for r in CATALOG)
BLOCKED_RULE_IDS = frozenset(str(r["id"]) for r in CATALOG if r.get("blocked_on"))
RULE_ID_PATTERN = re.compile(r"\bSF-[A-Z]+-\d+\b")


def _sentences(text: str) -> list[tuple[int, str]]:
    """Sentencas com o numero da linha em que comecam."""
    out: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for part in _SENTENCE_SPLIT.split(line):
            if part.strip():
                out.append((lineno, part))
    return out


def test_ha_comandos_e_regras_para_cobrir() -> None:
    """Guarda dos parametrize e dos conjuntos derivados.

    Se `EXISTING_COMMANDS`, `RULE_IDS` ou `DOC_FILES` esvaziarem -- refatoracao no
    parser, no loader, ou um `glob` que parou de casar --, os testes abaixo
    passariam por vacuidade em vez de falhar. Denuncia aqui.
    """
    assert EXISTING_COMMANDS, "nenhum subcomando derivado do parser -- introspecao quebrou"
    assert "analyze plan" in EXISTING_COMMANDS, (
        "`analyze plan` sumiu do parser; se foi removido de proposito, o terceiro "
        "teste passa a cobrar a documentacao que ainda o anuncia -- ajuste os dois juntos"
    )
    assert RULE_IDS, "catalogo vazio -- load_catalog() quebrou"
    assert DOC_FILES, "nenhum documento coletado -- os globs de DOC_FILES quebraram"


def _negation_of(text: str, target: str) -> str | None:
    """Marcador que nega `target` em `text`, ou `None`.

    "Nega" = o marcador aparece ANTES do alvo, a menos de `NEGATION_WINDOW`
    caracteres, sem ponto final separando os dois.
    """
    low = text.lower()
    start = 0
    while (hit := low.find(target, start)) != -1:
        window = low[max(0, hit - NEGATION_WINDOW) : hit]
        window = window.rsplit(".", 1)[-1]
        for marker in NEGATION_MARKERS:
            if marker in window:
                return marker
        start = hit + 1
    return None


@pytest.mark.parametrize("doc", DOC_FILES, ids=DOC_IDS)
def test_doc_nao_nega_comando_que_existe(doc: Path) -> None:
    """Nenhum documento pode declarar inexistente um verbo que o CLI tem."""
    rel = str(doc.relative_to(ROOT)).replace("\\", "/")
    for lineno, sentence in _sentences(doc.read_text(encoding="utf-8")):
        for command in EXISTING_COMMANDS:
            marker = _negation_of(sentence, command)
            assert marker is None, (
                f"{rel}:{lineno} nega um comando que EXISTE.\n"
                f"  comando: `sparkforge {command}` (esta em `build_parser()` agora)\n"
                f"  negacao: {marker!r}\n"
                f"  sentenca: {sentence.strip()!r}\n"
                f"  Uma skill que declara inexistente uma capacidade que o motor tem "
                f"instrui o agente a NAO usar a ferramenta certa. Rode "
                f"`sparkforge {command} --help`, confirme o que o verbo faz, e "
                f"reescreva com o limite VERDADEIRO, que costuma ser de coleta (o "
                f"artefato que ninguem coletou ainda), nao com a negacao da existencia."
            )


@pytest.mark.parametrize("skill_dir", SKILL_DIRS, ids=SKILL_IDS)
def test_description_nao_nega_o_proprio_toolkit(skill_dir: Path) -> None:
    """A `description` e o gatilho de SELECAO -- e o pior lugar para uma negacao.

    Duas das cinco afirmacoes falsas que originaram estes testes estavam aqui, e
    e o unico lugar onde o dano acontece ANTES da leitura: o agente le so as
    descricoes para escolher a skill, entao "nao existe parser de plano no
    toolkit" faz ele descartar a ferramenta certa sem nunca abrir o arquivo.
    Nessa forma a negacao nem precisou nomear o verbo, e por isso o teste acima
    (que casa `<topo> <sub>`) nao a pegaria: aqui a ancora e a propria palavra
    `sparkforge`. Escopo estreito -- 1 linha por skill -- para que a exigencia
    seja severa sem virar ruido.
    """
    fm = parse_frontmatter((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    marker = _negation_of(fm.get("description", ""), "sparkforge")
    assert marker is None, (
        f"{skill_dir.name}: a `description` nega o proprio toolkit ({marker!r}).\n"
        f"  {fm.get('description', '')}\n"
        f"  A description e lida para ESCOLHER a skill. Uma negacao aqui desqualifica "
        f"a ferramenta antes de o agente abrir o arquivo -- e se a capacidade existe, "
        f"ele deixa de usar o que resolveria o problema. Descreva o gatilho e o que "
        f"rodar; limite de coleta e assunto do corpo, nao do gatilho."
    )


@pytest.mark.parametrize("doc", DOC_FILES, ids=DOC_IDS)
def test_doc_nao_cita_blocked_on_de_regra_desbloqueada(doc: Path) -> None:
    """`blocked_on` so pode ser citado como estado corrente de quem o tem.

    O projeto distingue deliberadamente os dois motivos de skip em
    `judge --show-skipped`: `blocked_on` e inercia por desenho do catalogo,
    `requires_facts` e coleta que faltou. Trocar um pelo outro na documentacao
    ensina o agente a nao coletar justamente o que resolveria o skip.
    """
    rel = str(doc.relative_to(ROOT)).replace("\\", "/")
    for lineno, sentence in _sentences(doc.read_text(encoding="utf-8")):
        if "blocked_on" not in sentence.lower():
            continue
        for rule_id in RULE_ID_PATTERN.findall(sentence):
            if rule_id not in RULE_IDS:
                continue
            assert rule_id in BLOCKED_RULE_IDS, (
                f"{rel}:{lineno} cita `blocked_on` para {rule_id}, que NAO esta "
                f"bloqueada no catalogo.\n"
                f"  regras com `blocked_on` hoje: {sorted(BLOCKED_RULE_IDS) or 'nenhuma'}\n"
                f"  sentenca: {sentence.strip()!r}\n"
                f"  Se ela ainda nao dispara na sua analise, o motivo e outro e tem nome "
                f"proprio: `requires_facts`, um fact que ninguem coletou. Diga QUAL "
                f"artefato falta e como coleta-lo -- isso e acionavel; `blocked_on` e o "
                f"contrario, ensina a desistir."
            )


@pytest.mark.parametrize("doc", DOC_FILES, ids=DOC_IDS)
def test_doc_nao_anuncia_comando_que_nao_existe(doc: Path) -> None:
    """O inverso: prometer um verbo que o CLI nao tem.

    Puramente derivado -- nao ha vocabulario nenhum aqui. Todo
    `sparkforge <topo> <sub>` escrito na documentacao e conferido contra os
    subparsers reais.
    """
    rel = str(doc.relative_to(ROOT)).replace("\\", "/")
    pattern = re.compile(
        r"sparkforge\s+(" + "|".join(sorted(CLI_SUBCOMMANDS)) + r")\s+([a-z][a-z0-9-]*)"
    )
    # Um token so e cobrado quando parece subcomando de ALGUM verbo; senao a
    # proxima palavra da frase depois de `sparkforge judge` viraria falso positivo.
    known_anywhere = {sub for subs in CLI_SUBCOMMANDS.values() for sub in subs}
    for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
        for top, sub in pattern.findall(line):
            if sub not in known_anywhere:
                continue
            # Dizer que um comando NAO existe nao e anuncia-lo -- e o oposto, e e
            # informacao util ("nao existe `collect s3-listing`, a coleta e sua").
            # Nao ha risco de isso virar escape: se a negacao for de um comando que
            # EXISTE, `test_doc_nao_nega_comando_que_existe` cobra. Os dois testes
            # se completam, cada um guardando um lado.
            if _negation_of(line, f"{top} {sub}") is not None:
                continue
            assert sub in CLI_SUBCOMMANDS[top], (
                f"{rel}:{lineno} anuncia `sparkforge {top} {sub}`, que o parser NAO "
                f"aceita.\n"
                f"  subcomandos validos de `{top}`: {sorted(CLI_SUBCOMMANDS[top])}\n"
                f"  Um comando inventado falha de forma confusa na mao do agente, em vez "
                f"de simplesmente nao ajudar."
            )
