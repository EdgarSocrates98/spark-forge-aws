"""Gera a referencia de `docs/guia/referencia/` a partir do codigo.

Uma pagina por comando de topo da CLI (`build_parser`), por tool MCP (`TOOLS`),
por agent (`agents/**/*.md`) e por skill (`skills/*/SKILL.md`), mais um indice
por familia. Os guias escritos a mao ficam em `docs/guia/` e apontam para ca.

Referencia escrita a mao envelhece a cada tool nova sem que nada acuse. Esta e
gerada, e `tests/test_reference_docs.py` falha quando o que esta em disco nao e
o que o codigo produz hoje.

Uso:
    python scripts/gen_reference_docs.py          # regrava a referencia
    python scripts/gen_reference_docs.py --check  # sai 1 se estiver velha
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEST = ROOT / "docs" / "guia" / "referencia"
AVISO = (
    "<!-- Gerado por scripts/gen_reference_docs.py a partir do codigo. Nao edite a mao: "
    "rode `python scripts/gen_reference_docs.py`. -->\n\n"
)

CLASSES = {
    (True, False, True): "Só leitura: não grava nada e não acessa a rede.",
    (False, False, True): "Grava em disco local (repetir a chamada dá o mesmo resultado).",
    (False, True, True): "Acessa a AWS (lê a conta) e grava o artefato em disco local.",
    (False, False, False): (
        "Grava em disco local e muda o estado a cada chamada "
        "(repetir não é igual a chamar uma vez)."
    ),
}
CLASSE_CURTA = {
    (True, False, True): "só leitura",
    (False, False, True): "grava local",
    (False, True, True): "acessa a AWS",
    (False, False, False): "muda estado local",
}


# --------------------------------------------------------------------------- #
# utilitarios
# --------------------------------------------------------------------------- #


def _cel(valor: Any) -> str:
    """Texto seguro para uma celula de tabela Markdown."""
    texto = "" if valor is None else str(valor)
    return " ".join(texto.split()).replace("|", "\\|")


def _primeira_frase(texto: str, teto: int = 180) -> str:
    plano = " ".join((texto or "").split())
    corte = plano.find(". ")
    frase = plano if corte == -1 else plano[: corte + 1]
    return frase if len(frase) <= teto else frase[: teto - 3].rstrip() + "..."


def _frontmatter(texto: str) -> tuple[dict[str, Any], str]:
    if not texto.startswith("---"):
        return {}, texto
    fim = texto.find("\n---", 3)
    if fim == -1:
        return {}, texto
    bruto = texto[3:fim]
    corpo = texto[fim + 4 :].lstrip("\n")
    try:
        meta = yaml.safe_load(bruto) or {}
    except yaml.YAMLError:
        # Ha frontmatter com `: ` dentro de valor sem aspas (a descricao de
        # skill cita `plan.file_scan: ...`), que YAML estrito recusa. Os hosts
        # leem chave por linha; aqui tambem.
        meta = {}
        for linha in bruto.splitlines():
            if ":" in linha and not linha.startswith((" ", "-")):
                chave, _, valor = linha.partition(":")
                meta[chave.strip()] = valor.strip()
    return (meta if isinstance(meta, dict) else {}), corpo


def _rebaixar_titulos(corpo: str, niveis: int = 1) -> str:
    """Desce um nivel os titulos do corpo, fora de bloco de codigo, para que a
    pagina tenha um so titulo de primeiro nivel."""
    saida: list[str] = []
    em_codigo = False
    for linha in corpo.splitlines():
        if linha.lstrip().startswith("```"):
            em_codigo = not em_codigo
        if not em_codigo and linha.startswith("#"):
            linha = "#" * niveis + linha
        saida.append(linha)
    return "\n".join(saida).strip() + "\n"


_LINK = re.compile(r"(\]\()([^)\s]+)(\))")


def _reancorar_links(corpo: str, origem: Path, pagina: Path) -> str:
    """Links relativos do texto integral apontam a partir do arquivo de origem;
    na pagina gerada eles passam a apontar a partir da pagina."""

    def trocar(achado: re.Match[str]) -> str:
        alvo = achado.group(2)
        if alvo.startswith(("http://", "https://", "#", "mailto:", "/")):
            return achado.group(0)
        caminho, _, ancora = alvo.partition("#")
        absoluto = (origem.parent / caminho).resolve()
        novo = Path(os.path.relpath(absoluto, pagina.parent)).as_posix()
        return f"{achado.group(1)}{novo}{'#' + ancora if ancora else ''}{achado.group(3)}"

    return _LINK.sub(trocar, corpo)


def _lista_links(nomes: list[str], pasta: str, existentes: set[str]) -> str:
    itens = []
    for nome in nomes:
        itens.append(f"[`{nome}`](../{pasta}/{nome}.md)" if nome in existentes else f"`{nome}`")
    return ", ".join(itens)


def _paridade() -> list[dict[str, Any]]:
    dados = yaml.safe_load((ROOT / "parity.yaml").read_text(encoding="utf-8")) or {}
    return list(dados.get("capabilities") or [])


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    return next(
        (a for a in parser._actions if isinstance(a, argparse._SubParsersAction)),  # noqa: SLF001
        None,
    )


def _ajudas(sub: argparse._SubParsersAction) -> dict[str, str]:
    return {a.dest: (a.help or "") for a in sub._choices_actions}  # noqa: SLF001


def _texto_de_ajuda(acao: argparse.Action) -> str:
    texto = acao.help or ""
    if texto == argparse.SUPPRESS:
        return ""
    return texto.replace("%(default)s", str(acao.default)).replace("%%", "%")


def _tabela_de_flags(parser: argparse.ArgumentParser) -> list[str]:
    linhas = [
        "| Opção | Obrigatória | Valor | Repetível | Padrão | O que faz |",
        "|---|---|---|---|---|---|",
    ]
    for acao in parser._actions:  # noqa: SLF001
        if isinstance(acao, (argparse._HelpAction, argparse._SubParsersAction)):  # noqa: SLF001
            continue
        nome = ", ".join(f"`{o}`" for o in acao.option_strings) or f"`{acao.dest}` (posicional)"
        obrigatoria = "sim" if (acao.required or not acao.option_strings) else "não"
        if isinstance(acao, (argparse._StoreTrueAction, argparse._StoreFalseAction)):  # noqa: SLF001
            valor = "liga/desliga"
        elif acao.choices:
            valor = ", ".join(f"`{c}`" for c in acao.choices)
        else:
            valor = f"`{acao.metavar}`" if isinstance(acao.metavar, str) else "texto"
        acumula = (argparse._AppendAction, argparse._ExtendAction)  # noqa: SLF001
        repetivel = "sim" if isinstance(acao, acumula) else ""
        padrao = acao.default
        if padrao in (None, False, argparse.SUPPRESS) or padrao == []:
            padrao_txt = ""
        else:
            padrao_txt = f"`{padrao}`"
        linhas.append(
            f"| {nome} | {obrigatoria} | {valor} | {repetivel} | {_cel(padrao_txt)} | "
            f"{_cel(_texto_de_ajuda(acao))} |"
        )
    if len(linhas) == 2:
        return ["Este comando não recebe opções."]
    return linhas


def _pagina_cli(
    nome: str, ajuda: str, parser: argparse.ArgumentParser, cli_para_tools: dict[str, set[str]]
) -> str:
    partes = [AVISO + f"# `sparkforge {nome}`\n", _cel(ajuda) or _cel(parser.description) or ""]
    partes.append("")
    aninhado = _subparsers(parser)
    folhas: list[tuple[str, str, argparse.ArgumentParser]]
    if aninhado:
        ajudas = _ajudas(aninhado)
        folhas = [
            (f"{nome} {sub}", ajudas.get(sub, ""), aninhado.choices[sub])
            for sub in sorted(aninhado.choices)
        ]
        partes.append("## Subcomandos\n")
        partes.append("| Subcomando | O que faz |")
        partes.append("|---|---|")
        for verbo, texto, _ in folhas:
            ancora = verbo.replace(" ", "-")
            partes.append(f"| [`sparkforge {verbo}`](#sparkforge-{ancora}) | {_cel(texto)} |")
        partes.append("")
    else:
        folhas = [(nome, ajuda, parser)]
    for verbo, texto, sub_parser in folhas:
        if aninhado:
            partes.append(f"## `sparkforge {verbo}`\n")
            if texto:
                partes.append(_cel(texto) + "\n")
        partes.append("```bash")
        partes.append(f"sparkforge {verbo} --help")
        partes.append("```\n")
        partes.append("### Opções\n" if aninhado else "## Opções\n")
        partes.extend(_tabela_de_flags(sub_parser))
        partes.append("")
        tools = sorted(cli_para_tools.get(verbo, set()))
        titulo = "### Tool MCP equivalente\n" if aninhado else "## Tool MCP equivalente\n"
        partes.append(titulo)
        if tools:
            partes.append(", ".join(f"[`{t}`](../tools/{t}.md)" for t in tools))
        else:
            partes.append("Nenhuma: este verbo existe só na CLI.")
        partes.append("")
    return "\n".join(partes).rstrip() + "\n"


def _render_cli(cli_para_tools: dict[str, set[str]]) -> dict[Path, str]:
    from sparkforge.adapters.cli import build_parser

    parser = build_parser()
    sub = _subparsers(parser)
    assert sub is not None
    ajudas = _ajudas(sub)
    paginas: dict[Path, str] = {}
    indice = [
        AVISO + "# Referência da CLI\n",
        "Um comando de topo por página, com todos os subcomandos e opções. "
        "Todo comando imprime JSON na saída padrão; `--help` mostra o mesmo texto no terminal.\n",
        "| Comando | O que faz |",
        "|---|---|",
    ]
    for nome in sorted(sub.choices):
        paginas[DEST / "cli" / f"{nome}.md"] = _pagina_cli(
            nome, ajudas.get(nome, ""), sub.choices[nome], cli_para_tools
        )
        resumo = _cel(_primeira_frase(ajudas.get(nome, "")))
        indice.append(f"| [`sparkforge {nome}`]({nome}.md) | {resumo} |")
    paginas[DEST / "cli" / "README.md"] = "\n".join(indice) + "\n"
    return paginas


# --------------------------------------------------------------------------- #
# tools
# --------------------------------------------------------------------------- #


def _classe(anotacoes: dict[str, Any]) -> tuple[bool, bool, bool]:
    return (
        bool(anotacoes.get("readOnlyHint")),
        bool(anotacoes.get("openWorldHint")),
        bool(anotacoes.get("idempotentHint")),
    )


def _tipo(propriedade: dict[str, Any]) -> str:
    tipo = propriedade.get("type", "")
    texto = " ou ".join(tipo) if isinstance(tipo, list) else str(tipo or "qualquer")
    itens = propriedade.get("items")
    if isinstance(itens, dict) and itens.get("type"):
        texto += f" de {itens['type']}"
    if propriedade.get("enum"):
        texto += ": " + ", ".join(f"`{v}`" for v in propriedade["enum"])
    return texto


def _pagina_tool(nome: str, tool: dict[str, Any], tool_para_cli: dict[str, set[str]],
                 tool_para_capacidade: dict[str, set[str]]) -> str:
    esquema = tool.get("inputSchema") or {}
    obrigatorios = set(esquema.get("required") or [])
    propriedades = esquema.get("properties") or {}
    partes = [AVISO + f"# `{nome}`\n"]
    efeito = CLASSES.get(_classe(tool.get("annotations") or {}), "ver anotações")
    partes.append(f"**Efeito:** {efeito}\n")
    partes.append("## O que faz\n")
    partes.append(" ".join((tool.get("description") or "").split()) + "\n")
    partes.append("## Parâmetros\n")
    if propriedades:
        partes.append("| Parâmetro | Tipo | Obrigatório | Descrição |")
        partes.append("|---|---|---|---|")
        for chave in sorted(propriedades, key=lambda k: (k not in obrigatorios, k)):
            prop = propriedades[chave] or {}
            partes.append(
                f"| `{chave}` | {_cel(_tipo(prop))} | "
                f"{'sim' if chave in obrigatorios else 'não'} | "
                f"{_cel(prop.get('description', ''))} |"
            )
    else:
        partes.append("Esta tool não recebe parâmetros.")
    partes.append("")
    verbos = sorted(tool_para_cli.get(nome, set()))
    partes.append("## Na CLI\n")
    if verbos:
        partes.append(", ".join(
            f"[`sparkforge {v}`](../cli/{v.split()[0]}.md)" for v in verbos
        ))
    else:
        partes.append("Sem verbo de CLI declarado para esta tool.")
    partes.append("")
    capacidades = sorted(tool_para_capacidade.get(nome, set()))
    if capacidades:
        partes.append("## Capacidade\n")
        partes.append("; ".join(capacidades))
        partes.append("")
    anotacoes = tool.get("annotations") or {}
    partes.append("## Anotações MCP\n")
    partes.append("| Anotação | Valor |")
    partes.append("|---|---|")
    for chave in sorted(anotacoes):
        partes.append(f"| `{chave}` | `{str(anotacoes[chave]).lower()}` |")
    return "\n".join(partes).rstrip() + "\n"


def _render_tools(tool_para_cli: dict[str, set[str]],
                  tool_para_capacidade: dict[str, set[str]]) -> dict[Path, str]:
    from sparkforge.adapters.tools import TOOLS

    paginas: dict[Path, str] = {}
    familias: dict[str, list[str]] = {}
    for nome in sorted(TOOLS):
        paginas[DEST / "tools" / f"{nome}.md"] = _pagina_tool(
            nome, TOOLS[nome], tool_para_cli, tool_para_capacidade
        )
        familia = nome.removeprefix("sparkforge_").split("_")[0]
        familias.setdefault(familia, []).append(nome)
    indice = [
        AVISO + "# Referência das tools MCP\n",
        "Uma página por tool, agrupadas pela primeira palavra do nome. O efeito diz se a tool "
        "só lê, grava em disco local ou acessa a AWS.\n",
    ]
    for familia in sorted(familias):
        indice.append(f"## {familia}\n")
        indice.append("| Tool | Efeito | O que faz |")
        indice.append("|---|---|---|")
        for nome in familias[familia]:
            efeito = CLASSE_CURTA.get(_classe(TOOLS[nome].get("annotations") or {}), "")
            indice.append(
                f"| [`{nome}`]({nome}.md) | {efeito} | "
                f"{_cel(_primeira_frase(TOOLS[nome].get('description', '')))} |"
            )
        indice.append("")
    paginas[DEST / "tools" / "README.md"] = "\n".join(indice).rstrip() + "\n"
    return paginas


# --------------------------------------------------------------------------- #
# agents e skills
# --------------------------------------------------------------------------- #


def _arquivos_de_agent() -> list[Path]:
    return sorted(
        p for p in (ROOT / "agents").rglob("*.md") if p.name != "README.md"
    )


def _nomes_de_skill() -> list[str]:
    return sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))


def _papel(caminho: Path, meta: dict[str, Any]) -> str:
    if caminho.parent.name == "executors" or meta.get("role") == "executor":
        return "executor"
    if meta.get("executors"):
        return "coordenador"
    return "especialista"


def _render_agents(skills: set[str]) -> dict[Path, str]:
    paginas: dict[Path, str] = {}
    linhas = []
    arquivos = _arquivos_de_agent()
    nomes = {
        _frontmatter(p.read_text(encoding="utf-8"))[0].get("name") or p.stem for p in arquivos
    }
    for caminho in arquivos:
        meta, corpo = _frontmatter(caminho.read_text(encoding="utf-8"))
        nome = str(meta.get("name") or caminho.stem)
        papel = _papel(caminho, meta)
        relativo = caminho.relative_to(ROOT).as_posix()
        partes = [AVISO + f"# Agent `{nome}`\n"]
        if meta.get("description"):
            partes.append(" ".join(str(meta["description"]).split()) + "\n")
        partes.append("| Campo | Valor |")
        partes.append("|---|---|")
        partes.append(f"| Papel | {papel} |")
        partes.append(f"| Arquivo de origem | `{relativo}` |")
        if meta.get("tools"):
            partes.append(f"| Ferramentas do host | {_cel(meta['tools'])} |")
        if meta.get("function"):
            partes.append(f"| Função no loop | {_cel(meta['function'])} |")
        if meta.get("rule_areas"):
            partes.append(f"| Áreas de regra | {_cel(', '.join(map(str, meta['rule_areas'])))} |")
        partes.append("")
        if meta.get("skills"):
            partes.append("## Skills que ele usa\n")
            partes.append(_lista_links([str(s) for s in meta["skills"]], "skills", skills))
            partes.append("")
        if meta.get("executors"):
            partes.append("## Executores que ele despacha\n")
            partes.append(_lista_links([str(e) for e in meta["executors"]], "agents", nomes))
            partes.append("")
        partes.append("## Instruções do agent (texto integral)\n")
        pagina = DEST / "agents" / f"{nome}.md"
        partes.append(_reancorar_links(_rebaixar_titulos(corpo, 2), caminho, pagina))
        paginas[pagina] = "\n".join(partes).rstrip() + "\n"
        linhas.append((papel, nome, _primeira_frase(str(meta.get("description") or ""))))
    indice = [
        AVISO + "# Referência dos agents\n",
        "Coordenadores despacham executores em ordem; especialistas respondem uma área; "
        "executores fazem uma função do loop de fase (ver `AGENT_PROTOCOL.md`).\n",
    ]
    for papel in ("coordenador", "especialista", "executor"):
        grupo = [(n, d) for p, n, d in linhas if p == papel]
        if not grupo:
            continue
        plural = "es" if papel == "coordenador" else "s"
        indice.append(f"## {papel.capitalize()}{plural}\n")
        indice.append("| Agent | O que faz |")
        indice.append("|---|---|")
        for nome, descricao in sorted(grupo):
            indice.append(f"| [`{nome}`]({nome}.md) | {_cel(descricao)} |")
        indice.append("")
    paginas[DEST / "agents" / "README.md"] = "\n".join(indice).rstrip() + "\n"
    return paginas


def _render_skills() -> dict[Path, str]:
    paginas: dict[Path, str] = {}
    indice = [
        AVISO + "# Referência das skills\n",
        "Uma skill é um procedimento escrito que o agente segue para uma tarefa focada. "
        "O texto integral de cada uma está na página dela.\n",
        "| Skill | Quando usar |",
        "|---|---|",
    ]
    for nome in _nomes_de_skill():
        caminho = ROOT / "skills" / nome / "SKILL.md"
        meta, corpo = _frontmatter(caminho.read_text(encoding="utf-8"))
        partes = [AVISO + f"# Skill `{nome}`\n"]
        if meta.get("description"):
            partes.append(" ".join(str(meta["description"]).split()) + "\n")
        partes.append("| Campo | Valor |")
        partes.append("|---|---|")
        partes.append(f"| Arquivo de origem | `skills/{nome}/SKILL.md` |")
        for chave in sorted(meta):
            if chave in {"name", "description"}:
                continue
            valor = meta[chave]
            if isinstance(valor, list):
                valor = ", ".join(map(str, valor))
            partes.append(f"| `{chave}` | {_cel(valor)} |")
        partes.append("")
        partes.append("## Procedimento (texto integral)\n")
        pagina = DEST / "skills" / f"{nome}.md"
        partes.append(_reancorar_links(_rebaixar_titulos(corpo, 1), caminho, pagina))
        paginas[pagina] = "\n".join(partes).rstrip() + "\n"
        resumo = _cel(_primeira_frase(str(meta.get("description") or "")))
        indice.append(f"| [`{nome}`]({nome}.md) | {resumo} |")
    paginas[DEST / "skills" / "README.md"] = "\n".join(indice) + "\n"
    return paginas


# --------------------------------------------------------------------------- #
# montagem
# --------------------------------------------------------------------------- #


def render_all() -> dict[Path, str]:
    """Todas as paginas da referencia, por caminho absoluto."""
    cli_para_tools: dict[str, set[str]] = {}
    tool_para_cli: dict[str, set[str]] = {}
    tool_para_capacidade: dict[str, set[str]] = {}
    for capacidade in _paridade():
        tools = set(capacidade.get("tools") or [])
        verbos = list(capacidade.get("cli") or [])
        for verbo in verbos:
            cli_para_tools.setdefault(verbo, set()).update(tools)
        for tool in tools:
            tool_para_cli.setdefault(tool, set()).update(verbos)
            tool_para_capacidade.setdefault(tool, set()).add(str(capacidade.get("name")))
    skills = set(_nomes_de_skill())
    paginas: dict[Path, str] = {}
    paginas.update(_render_cli(cli_para_tools))
    paginas.update(_render_tools(tool_para_cli, tool_para_capacidade))
    paginas.update(_render_agents(skills))
    paginas.update(_render_skills())
    contagem = {
        pasta: sum(1 for p in paginas if p.parent.name == pasta and p.name != "README.md")
        for pasta in ("cli", "tools", "agents", "skills")
    }
    paginas[DEST / "README.md"] = (
        AVISO
        + "# Referência gerada\n\n"
        + "Gerada do código a cada mudança; os guias em `docs/guia/` explicam como usar.\n\n"
        + "| Seção | Páginas |\n|---|---|\n"
        + f"| [Comandos da CLI](cli/README.md) | {contagem['cli']} comandos de topo |\n"
        + f"| [Tools MCP](tools/README.md) | {contagem['tools']} tools |\n"
        + f"| [Agents](agents/README.md) | {contagem['agents']} agents |\n"
        + f"| [Skills](skills/README.md) | {contagem['skills']} skills |\n"
    )
    return paginas


def divergencias(paginas: dict[Path, str]) -> tuple[list[str], list[str]]:
    """(paginas ausentes ou diferentes, paginas em disco que o codigo nao gera)."""
    diferentes = [
        p.relative_to(ROOT).as_posix()
        for p, texto in sorted(paginas.items())
        if not p.is_file() or p.read_text(encoding="utf-8").replace("\r\n", "\n") != texto
    ]
    sobrando = sorted(
        p.relative_to(ROOT).as_posix()
        for p in DEST.rglob("*.md")
        if p not in paginas
    ) if DEST.is_dir() else []
    return diferentes, sobrando


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="So confere; sai 1 se estiver velha.")
    args = parser.parse_args(argv)
    paginas = render_all()
    diferentes, sobrando = divergencias(paginas)
    if args.check:
        for caminho in diferentes:
            print(f"velha ou ausente: {caminho}")
        for caminho in sobrando:
            print(f"sem origem no codigo: {caminho}")
        return 1 if (diferentes or sobrando) else 0
    for caminho in sobrando:
        (ROOT / caminho).unlink()
    for caminho, texto in paginas.items():
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8", newline="\n")
    print(f"{len(paginas)} paginas em {DEST.relative_to(ROOT).as_posix()}; "
          f"{len(diferentes)} regravadas, {len(sobrando)} removidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
