"""Gera `docs/agentic-catalog.md` — o catálogo didático §11.

Cada coordenador, executor e skill vira uma ficha com os campos do §11 do
prompt de produto (purpose, when_to_use, when_not_to_use, triggers, hosts,
skills, tools, dependências MCP, inputs, saída esperada, verificação,
exemplo e limitações), derivada dos canônicos (`agents/`, `skills/`,
`integrate/render.py`, `AGENTS.md`) — nunca escrita à mão.

Uso: `python scripts/gen_agentic_catalog.py` (reescreve o arquivo).
`tests/test_agentic_catalog.py` reprova o documento velho.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs" / "agentic-catalog.md"

GERADO = (
    "<!-- Gerado por scripts/gen_agentic_catalog.py a partir dos canonicos. "
    "Nao edite a mao: rode `python scripts/gen_agentic_catalog.py`. -->"
)

_TOOL_RE = re.compile(r"sparkforge_aws_[a-z0-9_]+")
_QUOTE_RE = re.compile(r"[\"“]([^\"”]{10,160}?)[\"”]")


def _frontmatter(texto: str) -> tuple[dict, str]:
    if not texto.startswith("---"):
        return {}, texto
    fim = texto.find("---", 3)
    try:
        return yaml.safe_load(texto[3:fim]) or {}, texto[fim + 3 :]
    except yaml.YAMLError:
        return {}, texto[fim + 3 :]


def _secao(corpo: str, titulo: str) -> str:
    """O texto de um `## <titulo>` ate o proximo `## ` (ou fim)."""
    achado = re.search(rf"(?ms)^## {re.escape(titulo)}\s*$(.*?)(?=^## |\Z)", corpo)
    return achado.group(1).strip() if achado else ""


def _bullets(texto: str, teto: int = 3) -> list[str]:
    itens = []
    for linha in texto.splitlines():
        linha = linha.strip()
        if linha.startswith(("- ", "* ")):
            itens.append(re.sub(r"\s+", " ", linha[2:]).strip())
        if len(itens) >= teto:
            break
    return itens


def _primeira_frase(texto: str, teto: int = 200) -> str:
    texto = re.sub(r"\s+", " ", texto).strip()
    fim = re.search(r"(?<=[.!?])\s", texto)
    corte = fim.start() if fim and fim.start() <= teto else teto
    return texto[:corte].rstrip(" .") + ("…" if len(texto) > corte else "")


def _use_quando() -> dict[str, str]:
    """A coluna 'Use quando…' da tabela de coordenadores do AGENTS.md."""
    texto = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    tabela = re.search(r"\| Coordinator \|.*?\n((?:\|.*\|\n)+)", texto)
    out: dict[str, str] = {}
    if tabela:
        for linha in tabela.group(1).strip().splitlines():
            celulas = [c.strip() for c in linha.strip("|").split("|")]
            if len(celulas) >= 2 and celulas[0].startswith("`"):
                out[celulas[0].strip("`")] = celulas[1]
    return out


EXEMPLOS_COORDENADOR: dict[str, str] = {
    "spark-performance-architect": (
        "Investigue este job Glue de ponta a ponta com o perfil "
        "spark-performance-architect: encontre o gargalo dominante e diga o "
        "próximo passo com evidência."
    ),
    "glue-incremental-performance-architect": (
        "Meu job incremental está tão lento quanto o full. Use "
        "glue-incremental-performance-architect para mapear os dois fluxos "
        "antes de qualquer tuning."
    ),
    "glue-infra-reviewer": (
        "Revise a definição Terraform deste job Glue com o perfil "
        "glue-infra-reviewer: workers, bookmark, retries, observabilidade."
    ),
    "athena-query-optimizer": (
        "A consulta Athena ficou cara. Use athena-query-optimizer para medir "
        "bytes escaneados, pruning de partição e workgroup."
    ),
    "pyspark-code-reviewer": (
        "Revise jobs/etl.py com o perfil pyspark-code-reviewer: fonte, plano "
        "físico e call graph, com evidência ancora por linha."
    ),
    "iceberg-performance-engineer": (
        "Esta tabela Iceberg está lenta para consultar. Use "
        "iceberg-performance-engineer para medir a dívida de data files, "
        "delete files e snapshots."
    ),
    "emr-infra-reviewer": (
        "Revise a definição deste cluster EMR com emr-infra-reviewer: fleets, "
        "managed scaling, logs, segredo em configuração."
    ),
    "data-quality-reviewer": (
        "Este job valida dado — a validação está no lugar certo e custa "
        "quanto? Use data-quality-reviewer."
    ),
    "streaming-realtime-architect": (
        "Avalie esta plataforma streaming (Flink + Kafka + Iceberg) com "
        "streaming-realtime-architect: transporte, checkpoint, backlog."
    ),
    "cdc-contract-reviewer": (
        "Revise estes eventos CDC/Debezium com cdc-contract-reviewer: chaves, "
        "seam snapshot/CDC, deletes e tombstones."
    ),
    "sf-lake-formation-specialist": (
        "Diagnostique por que este job lê e não escreve na tabela governada: "
        "use sf-lake-formation-specialist."
    ),
    "sf-runtime-specialist": (
        "Confira a compatibilidade de versão deste job com "
        "sf-runtime-specialist: Glue, Spark, Python e Iceberg observados."
    ),
    "sf-security-reviewer": (
        "Faça a revisão de segurança deste job com sf-security-reviewer: "
        "segredos, permissões e superfície exposta."
    ),
    "sf-terraform-specialist": (
        "Revise este módulo Terraform de plataforma de dados com "
        "sf-terraform-specialist."
    ),
}

HOSTS_TXT = (
    "subagente em **Claude Code** e **Devin** (espelhos `.claude/`, "
    "`.agents/`); **`playbook`** em Codex e Copilot CI — único caminho lá, "
    "e piso nas demais quando o despacho está desligado"
)

_CLAUDE_COMO = (
    "cole a tarefa na sessão; a skill `sparkforge-aws-diagnose` ativa pela "
    'descrição. Para despachar o coordenador: *"Use the '
    "spark-performance-architect profile as a subagent for this "
    'investigation."*'
)
_DEVIN_COMO = (
    'cole a tarefa; para o coordenador como subagente: *"Use the '
    "spark-performance-architect profile as a subagent…\"* — ou comece a "
    "sessão com `Read PROMPT_INICIAL_MESTRE.md and use the "
    "spark-performance-architect skill.`"
)
_CODEX_COMO = (
    "cole a tarefa; a orquestração é o `playbook` (sem despacho de "
    "subagente): `sparkforge-aws playbook spark-performance-architect "
    "--repo .` — cada passo do plano devolvido é executado na sessão."
)
_OUTROS_COMO = (
    "cole a tarefa e aponte o `playbook` como procedimento; as skills "
    "ficam em `.agents/skills/`."
)

COOKBOOK = f"""\
## §11.1 — Agentic Invocation Cookbook

Prompts de intenção associados ao mecanismo real de cada host. A tarefa é a
mesma; o que muda é o mecanismo que a executa.

### Tarefa canônica

> "Analise os jobs Glue deste repositório utilizando as skills relevantes do
> Spark Forge AWS. Investigue performance, dependências e possíveis riscos,
> separe fatos de hipóteses e produza evidências verificáveis."

| Host | Como invocar |
|---|---|
| **Claude Code** | {_CLAUDE_COMO} |
| **Devin** | {_DEVIN_COMO} |
| **Codex** | {_CODEX_COMO} |
| **Copilot / outros leitores de `AGENTS.md`** | {_OUTROS_COMO} |
"""


def _tools_de(corpo: str) -> list[str]:
    return sorted(set(_TOOL_RE.findall(corpo)))


def _ficha_coordenador(caminho: Path, use_quando: dict[str, str]) -> str:
    meta, corpo = _frontmatter(caminho.read_text(encoding="utf-8"))
    nome = meta.get("name", caminho.stem)
    nao_faz = _bullets(_secao(corpo, "Não faz"))
    skills = list(meta.get("skills") or [])
    executores = list(meta.get("executores") or [])
    tools = _tools_de(corpo)
    purpose = _primeira_frase(str(meta.get("description", "")))
    quando = use_quando.get(nome, purpose)
    linhas = [
        f"### `{nome}`\n",
        "| Campo | Valor |",
        "|---|---|",
        f"| NAME | `{nome}` |",
        f"| PURPOSE | {purpose} |",
        f"| DOMAIN | {', '.join(meta.get('rule_areas') or ['orquestração'])} |",
        f"| WHEN_TO_USE | {quando} |",
        "| WHEN_NOT_TO_USE | "
        + ("; ".join(nao_faz) if nao_faz else "ver `## Não faz` na fonte")
        + " |",
        "| TRIGGERS | skills: "
        + (", ".join(f"`{s}`" for s in skills) or "nenhuma declarada")
        + " |",
        f"| SUPPORTED_HOSTS | {HOSTS_TXT} |",
        "| REQUIRED_SKILLS | "
        + (", ".join(f"`{s}`" for s in skills) or "—")
        + " |",
        f"| AVAILABLE_TOOLS | {meta.get('tools', '—')} |",
        "| MCP_DEPENDENCIES | "
        + (", ".join(f"`{t}`" for t in tools) or "—")
        + " |",
        "| INPUTS | case aberto, artifacts coletados, findings do `judge` |",
        "| EXPECTED_OUTPUT | direção: próximo executor, evidência, case |",
        "| VERIFICATION | `next-step` concorda com a rota; `playbook` decompõe |",
        "| EXAMPLE_PROMPT | “"
        + EXEMPLOS_COORDENADOR.get(
            nome, f"Use o perfil {nome} nesta investigação."
        )
        + "” |",
        "| LIMITATIONS | subagente não despacha executores; `playbook` é o piso em Codex/Copilot |",
        "",
    ]
    if executores:
        linhas.append(
            "Despacha: " + ", ".join(f"`{e}`" for e in executores) + ".\n"
        )
    return "\n".join(linhas)


def _ficha_executor(caminho: Path) -> str:
    meta, corpo = _frontmatter(caminho.read_text(encoding="utf-8"))
    nome = meta.get("name", caminho.stem)
    faz = _bullets(_secao(corpo, "Faz"))
    pressupoe = _bullets(_secao(corpo, "Pressupõe"))
    entrega = _bullets(_secao(corpo, "Entrega"))
    nao_faz = _bullets(_secao(corpo, "Não faz"))
    tools = _tools_de(corpo)
    funcao = str(meta.get("function", "?"))
    linhas = [
        f"### `{nome}`\n",
        "| Campo | Valor |",
        "|---|---|",
        f"| NAME | `{nome}` |",
        f"| PURPOSE | executor `{funcao}` — "
        + ("; ".join(faz[:2]) if faz else "ver fonte")
        + " |",
        f"| DOMAIN | pipeline determinístico (`{funcao}`) |",
        "| WHEN_TO_USE | quando o coordenador o despacha — nunca direto |",
        "| WHEN_NOT_TO_USE | "
        + ("; ".join(nao_faz) if nao_faz else "ver `## Não faz` na fonte")
        + " |",
        "| TRIGGERS | despacho do coordenador (ou passo de `playbook`) |",
        "| SUPPORTED_HOSTS | todos via `playbook`; inline em Claude/Devin |",
        "| REQUIRED_SKILLS | — |",
        f"| AVAILABLE_TOOLS | {meta.get('tools', '—')} |",
        "| MCP_DEPENDENCIES | "
        + (", ".join(f"`{t}`" for t in tools) or "—")
        + " |",
        "| INPUTS | "
        + ("; ".join(pressupoe) if pressupoe else "ver `## Pressupõe` na fonte")
        + " |",
        "| EXPECTED_OUTPUT | "
        + ("; ".join(entrega) if entrega else "ver `## Entrega` na fonte")
        + " |",
        "| VERIFICATION | contrato `## Pressupõe`/`## Entrega` na fonte |",
        f"| EXAMPLE_PROMPT | via coordenador — o `{nome}` roda como passo |",
        "| LIMITATIONS | não são perfis despacháveis (não viram `.toml` no Codex) |",
        "",
    ]
    return "\n".join(linhas)


def _limpar(texto: str) -> str:
    """Yaml guarda `\\"` escapado; o catalogo mostra o texto, nao o escape."""
    return texto.replace('\\"', '"').replace("\\'", "'")


def _ficha_skill(
    caminho: Path,
    razoes: dict[str, str],
    despachaveis: set[str],
    agentes_da_skill: dict[str, list[str]],
) -> str:
    meta, corpo = _frontmatter(caminho.read_text(encoding="utf-8"))
    nome = meta.get("name", caminho.parent.name)
    descricao = _limpar(str(meta.get("description", "")))
    despachavel = nome in despachaveis
    hosts = (
        "subagente despachável em Claude/Devin; `playbook` em Codex/Copilot"
        if despachavel
        else "host pai apenas — não-despachável"
    )
    citacao = _QUOTE_RE.search(descricao)
    exemplo = (
        _limpar(citacao.group(1)).strip()
        if citacao
        else f"pedido que case a descrição de `{nome}`"
    )
    tools = _tools_de(corpo)
    agentes = agentes_da_skill.get(nome, [])
    linhas = [
        f"### `{nome}`\n",
        "| Campo | Valor |",
        "|---|---|",
        f"| NAME | `{nome}` |",
        f"| PURPOSE | {_primeira_frase(descricao)} |",
        f"| TRIGGERS | {descricao.strip()} |",
        "| SUPPORTED_HOSTS | "
        + hosts
        + " — "
        + razoes.get(nome, "razão em `integrate/render.py`")
        + " |",
        "| ACTIVATION_METHOD | descrição do frontmatter — ativa por linguagem natural |",
        "| RELATED_AGENTS | " + (", ".join(f"`{a}`" for a in agentes) or "—") + " |",
        "| RELATED_MCP_TOOLS | " + (", ".join(f"`{t}`" for t in tools) or "—") + " |",
        f"| EXAMPLE | “{exemplo}” |",
        "| VERIFICATION | saída ancora em `rule_id`/`fact_id` ou recusa nomeada |",
        "",
    ]
    return "\n".join(linhas)


def render_all() -> dict[Path, str]:
    from sparkforge_aws.integrate.render import (
        DISPATCHABLE_SKILLS,
        SKILL_DISPATCH_REASON,
    )

    use_quando = _use_quando()
    coordenadores = sorted(
        p for p in (ROOT / "agents").glob("*.md")
    )
    executores = sorted((ROOT / "agents" / "executors").glob("*.md"))
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))

    agentes_da_skill: dict[str, list[str]] = {}
    for caminho in coordenadores:
        meta, _ = _frontmatter(caminho.read_text(encoding="utf-8"))
        for s in meta.get("skills") or []:
            agentes_da_skill.setdefault(s, []).append(meta.get("name", caminho.stem))

    partes = [
        GERADO,
        "",
        "# Catálogo agentic — Spark Forge AWS",
        "",
        "Ficha §11 de cada coordenador, executor e skill, gerada dos canônicos.",
        "O valor de cada recurso está no campo — este arquivo não é uma lista",
        "de nomes.",
        "",
        f"Superfície: **{len(coordenadores)} coordenadores**, "
        f"**{len(executores)} executores**, **{len(skills)} skills**.",
        "",
        "## Coordenadores",
        "",
    ]
    partes += [_ficha_coordenador(p, use_quando) for p in coordenadores]
    partes += ["## Executores", ""]
    partes += [_ficha_executor(p) for p in executores]
    partes += ["## Skills", ""]
    partes += [
        _ficha_skill(
            p, SKILL_DISPATCH_REASON, set(DISPATCHABLE_SKILLS), agentes_da_skill
        )
        for p in skills
    ]
    partes.append(COOKBOOK)
    return {DEST: "\n".join(partes)}


def divergencias(paginas: dict[Path, str]) -> tuple[list[str], list[str]]:
    diferentes = [str(p) for p, texto in paginas.items()
                  if not p.is_file() or p.read_text(encoding="utf-8") != texto]
    return diferentes, []


def main() -> int:
    paginas = render_all()
    for caminho, texto in paginas.items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        anterior = caminho.read_text(encoding="utf-8") if caminho.is_file() else None
        if anterior != texto:
            caminho.write_text(texto, encoding="utf-8")
            print(f"regravado: {caminho.relative_to(ROOT)}")
    print(f"{len(paginas)} pagina(s) conferidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
