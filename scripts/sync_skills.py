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
import re
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


# --------------------------------------------------------------------------
# Skills que despacham
# --------------------------------------------------------------------------
# `.agents/skills/<name>/SKILL.md` e caminho de descoberta NATIVO do Devin, nao
# convencao deste repositorio, e o frontmatter de skill aceita `subagent`
# (boolean, default `false`) e `agent` (string, default nenhum) -- tabela de
# knowledge/devin/agents-and-subagents.md secao 8. Desenho: D-5 e D-6.
#
# So o espelho do Devin recebe os campos. `.claude/skills/` continua passthrough
# byte a byte: o Claude Code nao le `subagent:`, e escrever la seria publicar
# campo que ninguem consome.

SKILL_FILENAME = "SKILL.md"

# Campos que a renderizacao do Devin CONTROLA numa skill. Sao removidos antes de
# reinseridos, e nao so acrescentados: assim uma skill que deixou de despachar
# perde o campo no espelho, e um `subagent: true` posto a mao num espelho volta
# a divergir do que o tradutor produz. Acrescentar sem remover deixaria os dois
# casos passarem calados.
DEVIN_SKILL_DISPATCH_KEYS = frozenset({"subagent", "agent"})

# D-6: despacha quem e investigacao fechada -- o subagente le artefato, julga
# contra o catalogo, e devolve texto que o pai resume. Nao despacha quem dirige
# o loop, quem orquestra outras skills, ou quem precisa de uma decisao que so
# uma pessoa tem.
#
# A assimetria que decide os casos duvidosos: uma skill despachavel a mais que
# precisasse perguntar falha MUDA -- `ask_user_question` e sempre negado a
# subagente (veto V-DV-10), entao ela inventa a resposta ou para sem dizer por
# que. Uma skill despachavel a menos custa contexto do pai, e mais nada. Na
# duvida, nao despacha.
DISPATCHABLE_SKILLS = {
    "analyze-batch-loop": "extrai o loop do codigo e julga; a saida e relatorio",
    "analyze-library-call-graph": "varre a biblioteca e devolve o grafo; leitura fechada",
    "analyze-spark-plan": "interpreta um plano fisico ja salvo; nao pede nada a ninguem",
    "analyze-spark-ui": "coleta e julga o event log de um run identificado no pedido",
    "diagnose-data-skew": "cruza SF-UI-001 com SF-UI-002 sobre o event log que ela mesma coleta",
    "diagnose-oom": "classifica o OOM por `heap_oom_in_log`; discriminador esta no artefato",
    "optimize-parquet-layout": "junta listagem, plano e catalogo, todos coletaveis so lendo",
    "optimize-pyspark-code": "mesma forma de `review-pyspark-pr`: extrai, julga, propoe diff",
    "review-data-validation": "revisa a validacao declarada no codigo e devolve achados",
    "review-emr-cluster": "revisa a definicao do cluster que ja esta em disco",
    "review-glue-terraform": "revisa o .tf que ja esta em disco",
    "review-pyspark-pr": "revisa um diff fechado e classifica risco",
}

NON_DISPATCHABLE_SKILLS = {
    # As duas que dirigem o loop. Um subagente nao herda o historico do pai e,
    # por default, nao gera subagente proprio (`max-nesting`): despachar quem
    # orquestra e perder justamente a orquestracao.
    "sparkforge-diagnose": (
        "abre o case e roteia. Despachar joga o ciclo de vida do case para um "
        "contexto que nao volta -- e o case e o que faz a investigacao atravessar "
        "sessoes e ferramentas"
    ),
    "glue-incremental-performance-architect": (
        "orquestra as skills especializadas por `next-step` e le "
        "PROMPT_INICIAL_MESTRE.md; subagente nao gera subagente por default"
    ),
    # As que precisam de uma decisao que nao esta no repositorio.
    "optimize-iceberg-table": (
        "`expire_snapshots` e `remove_orphan_files` nao tem desfazer, e a propria "
        "skill exige que a retencao venha do dono dos dados. Dentro de subagente "
        "essa confirmacao e inalcancavel"
    ),
    "optimize-latest-per-key": (
        "a secao `Perguntas que o extrator nao faz por voce` sao quatro perguntas "
        "de semantica de negocio -- desempate, timezone, correcao retroativa"
    ),
    "design-incremental-processing": (
        "o contrato de saida tem dezesseis campos de desenho que nenhum extrator "
        "preenche; a propria skill os chama de perguntas"
    ),
    # As que dependem de evidencia que o pai ja acumulou, ou de uma execucao nova.
    "benchmark-pyspark-job": (
        "o passo 2 e `aplique a mudanca` entre as duas coletas: exige um run novo "
        "e o id dele, que so aparece depois de alguem publicar a mudanca"
    ),
    "optimize-variable-volume-job": (
        "classificar execucoes por perfil parte do volume observado no workload, "
        "e compara N runs que o operador escolhe"
    ),
    "tune-glue-job": (
        "o passo 1 exige baseline ja provado por `analyze-spark-ui`, `diagnose-oom` "
        "e `diagnose-data-skew`; subagente nao herda o historico do pai e teria de "
        "reconstruir a evidencia que motivou a chamada"
    ),
}

SKILL_DISPATCH_REASON = {**DISPATCHABLE_SKILLS, **NON_DISPATCHABLE_SKILLS}

_LIST_ITEM = re.compile(r"^\s*-\s+(.*)$")


def _frontmatter_list(front: list[str], key: str) -> list[str]:
    """Le uma lista do frontmatter, nas duas formas que o corpus usa.

        skills:          |  rule_areas: [SF-EMR, SF-PY]
          - review-x     |
          - review-y     |

    A forma inline existe hoje em `rule_areas:` e `executors:`; se alguem
    escrever `skills:` assim, um leitor que so entendesse blocos devolveria
    lista vazia -- e lista vazia aqui vira "nenhum coordenador declara esta
    skill", que e silencio, nao erro.
    """
    values: list[str] = []
    collecting = False
    for line in front:
        content = line.rstrip("\r\n")
        if content[:1] in (" ", "\t"):
            if collecting:
                item = _LIST_ITEM.match(content)
                if item:
                    values.append(item.group(1).strip().strip("'\""))
            continue
        match = _TOP_LEVEL_KEY.match(content)
        collecting = False
        if match and match.group(1) == key:
            inline = content.split(":", 1)[1].strip()
            if not inline:
                collecting = True
            elif inline.startswith("[") and inline.endswith("]"):
                values.extend(
                    part.strip().strip("'\"")
                    for part in inline[1:-1].split(",")
                    if part.strip()
                )
            else:
                values.append(inline.strip("'\""))
    return values


def coordinators_by_skill() -> dict[str, tuple[str, ...]]:
    """A relacao skill -> coordenadores, DERIVADA do `skills:` de cada perfil.

    D-5: nao existe segunda lista. Cada coordenador ja declara as skills que
    coordena, e essa declaracao ja e testada por `test_agent_coverage`. Manter
    uma tabela paralela `skill -> agente` seria a familia de defeito que a Fase
    5c achou nos dois `EXTRACTORS` mantidos a mao: uma cresce, a outra nao, e o
    desacordo e mudo.
    """
    relation: dict[str, list[str]] = {}
    for path in iter_agent_files():
        parsed = _split_frontmatter(path.read_bytes().decode("utf-8"))
        if parsed is None:
            continue
        for skill in _frontmatter_list(parsed[1], "skills"):
            relation.setdefault(skill, []).append(path.stem)
    return {skill: tuple(sorted(names)) for skill, names in sorted(relation.items())}


def agent_for_skill(name: str) -> str | None:
    """O perfil que a skill `name` nomeia em `agent:`, ou `None`.

    **Medido antes de decidir** (Step 1 da Task 4): das doze skills despachaveis,
    so tres sao declaradas por UM coordenador. As outras nove aparecem no
    `skills:` de dois a quatro perfis, e para elas `agent:` nao tem resposta
    unica.

    As saidas honestas eram duas, e a escolha esta registrada: a skill ambigua
    **nao** declara `agent:`, e o Devin escolhe o perfil. A alternativa --
    "declara o primeiro em ordem deterministica" -- foi recusada com o numero na
    mao: em ordem alfabetica, `review-pyspark-pr` cairia em
    `data-quality-reviewer` e `analyze-spark-plan` em
    `glue-incremental-performance-architect`, quando o especialista de cada uma e
    `pyspark-code-reviewer`. Ordem alfabetica nao e criterio de competencia, e
    fingir que e publicaria um roteamento errado com cara de decisao.

    `subagent: true` sozinho e forma documentada: `agent` tem default "none" na
    tabela de frontmatter da fonte, e `subagent` sozinho roda a skill como
    subagente no perfil que o harness escolher.
    """
    coordinators = coordinators_by_skill().get(name, ())
    return coordinators[0] if len(coordinators) == 1 else None


def _newline_of(lines: list[str]) -> str:
    """O fim de linha que o arquivo usa, para a linha inserida usar o mesmo.

    Misturar LF e CRLF dentro do mesmo frontmatter faria o espelho divergir a
    cada regeneracao numa arvore com `autocrlf` -- o mesmo cuidado do
    `_split_frontmatter`, agora do lado da insercao.
    """
    for line in reversed(lines):
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def render_skill(text: str, platform: str, *, name: str) -> str:
    """Devolve a skill `name` no formato que `platform` le.

    So o Devin recebe `subagent:`/`agent:`. Os campos entram no FIM do
    frontmatter, imediatamente antes da cerca de fechamento: e a unica posicao
    que nao depende de onde as chaves existentes estao, e a que nao pode cair
    dentro de uma lista indentada. Nao ha round-trip de YAML aqui, pela mesma
    razao do `render_agent` -- reserializar reordenaria as chaves e produziria
    diff onde nao houve mudanca.
    """
    if platform not in PLATFORMS:
        raise ValueError(
            f"plataforma desconhecida: {platform!r}; conhecidas: {sorted(PLATFORMS)}"
        )
    if name not in SKILL_DISPATCH_REASON:
        raise ValueError(
            f"skill sem decisao de despacho registrada: {name!r}. Declare em "
            "DISPATCHABLE_SKILLS ou em NON_DISPATCHABLE_SKILLS, com a razao ao "
            "lado -- o default silencioso seria publicar a skill sem ninguem ter "
            "decidido se ela pode rodar sem poder perguntar."
        )
    if platform in PASSTHROUGH_PLATFORMS:
        return text

    parsed = _split_frontmatter(text)
    if parsed is None:
        return text
    opening, front, rest = parsed

    kept = _drop_frontmatter_keys(front, DEVIN_SKILL_DISPATCH_KEYS)
    added: list[str] = []
    if name in DISPATCHABLE_SKILLS:
        newline = _newline_of(kept or opening)
        added.append(f"subagent: true{newline}")
        agent = agent_for_skill(name)
        if agent is not None:
            added.append(f"agent: {agent}{newline}")

    if kept == front and not added:
        return text
    return "".join(opening + kept + added + rest)


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
    problems = check_skills() + check_agents() + check_executors()

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
