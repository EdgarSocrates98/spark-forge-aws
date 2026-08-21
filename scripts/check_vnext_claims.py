#!/usr/bin/env python3
"""Gate de lastro das alegações publicadas em `docs/vnext/`.

Fonte da verdade: `docs/vnext/claims.lock.json`. Toda alegação dos documentos
precisa existir no manifesto, e toda entrada do manifesto precisa existir nos
documentos -- fail-closed nos dois sentidos, pela mesma razão registrada em
`tests/test_docs_coverage.py`: lista copiada envelhece sem que nada acuse.

Uso:
    python scripts/check_vnext_claims.py           # audita; sai 1 se divergir
    python scripts/check_vnext_claims.py --full    # inclui provas `tier: slow`
    python scripts/check_vnext_claims.py --seed    # gera manifesto semente
    python scripts/check_vnext_claims.py --report  # tabela de lastro em Markdown
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VNEXT = ROOT / "docs" / "vnext"
MANIFEST = VNEXT / "claims.lock.json"
SOURCES_LOCK = ROOT / "knowledge" / "sources.lock.json"

SCHEMA_VERSION = 1
STATES = frozenset({"PROVADA", "SEM_LASTRO", "REMOVIDA"})
TYPES = frozenset({"number", "capability", "external_fact"})
TIERS = frozenset({"fast", "slow"})
PROOF_KINDS = frozenset({"command", "artifact", "source"})


def rel(path: Path) -> str:
    """Caminho relativo à raiz, sempre com `/`, para o manifesto não mudar
    conforme o sistema operacional de quem rodou o `--seed`."""
    return path.resolve().relative_to(ROOT).as_posix()


def audited_docs(root: Path = VNEXT) -> list[Path]:
    # Fail-open deliberado: `adrs/` ausente ou renomeado devolve glob vazio,
    # nao erro -- um gate que degrada em silencio para de vigiar sem avisar.
    return sorted(root.glob("*.md")) + sorted((root / "adrs").glob("*.md"))


# Qualquer numero, com sinal de percentual opcional. O grupo so pode terminar
# em digito ou em `%` -- pontuacao de frase (`,` de enumeracao, `.` final)
# nunca entra no token, entao "3.5," na prosa vira "3.5", nao "3.5,". Contagem
# de um ou dois digitos (`8 coordenadores`, `38 agentes`) e a forma dominante
# de alegacao nestes documentos, e por isso nao tem piso de tamanho aqui --
# um numero que o extrator nao ve e uma alegacao que escapa da auditoria para
# sempre, o que pesa mais que o ruido de sobra-capturar. O lookbehind e o
# lookahead descartam sozinhos qualquer numero colado a `-` ou a letra, o que
# mata data ISO (`2026-08-21`) e identificador (`ADR-003`) sem precisar de regra.
NUMBER_RE = re.compile(r"(?<![\w.-])(\d(?:[\d.,]*\d)?\s*%?)(?![\w-])")

# Cada padrao ignorado carrega a razao. Allowlist sem razao registrada vira
# deposito de excecao conveniente, e ninguem consegue auditar depois por que
# um numero deixou de ser alegacao.
IGNORED_TOKENS = (
    (
        re.compile(r"^\d+\.\d+\.\d+$"),
        "versao semantica e fato de release, nao alegacao de resultado",
    ),
    (
        re.compile(r"^(19|20)\d{2}$"),
        "ano de quatro digitos e datacao; o custo conhecido e mascarar uma "
        "contagem que caia em 1900-2099, aceito por ser improvavel nestes documentos",
    ),
)


def _display_path(path: Path) -> str:
    """Caminho para registrar no achado ou citar num erro. Documento real
    vive sob ROOT e usa o caminho relativo de `rel()` (estavel entre sistemas
    operacionais). Fora de ROOT -- caso pratico so em teste, que escreve o
    documento sintetico em `tmp_path` -- `rel()` explode, e cair para o
    caminho absoluto mantem a funcao utilizavel sem afrouxar o contrato de
    `rel()`, que continua exigindo caminho dentro do repositorio."""
    try:
        return rel(path)
    except ValueError:
        return path.resolve().as_posix()


def _strip_code_blocks(text: str, path: Path) -> str:
    """Zera o conteudo de bloco cercado. Numero dentro de exemplo de codigo e
    ilustracao; audita-lo produziria ruido sem nenhuma alegacao por tras."""
    out: list[str] = []
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    if fenced:
        # Cerca sem fechamento apagaria o resto do documento em silencio --
        # exatamente a falha de miss silencioso que este gate existe para
        # impedir. Estourar alto aqui, com o nome do arquivo, deixa alguem
        # achar e corrigir o Markdown quebrado em vez de o gate so parar de
        # ver alegacoes sem avisar ninguem.
        raise ValueError(f"bloco de codigo cercado nao fechado em {_display_path(path)}")
    return "\n".join(out)


def extract_numbers(path: Path) -> list[dict]:
    doc = _display_path(path)
    text = _strip_code_blocks(path.read_text(encoding="utf-8"), path)
    found: list[dict] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if "http" in line:
            # Citacao de fonte: o numero pertence ao endereco, nao ao
            # produto. Descarta a linha inteira -- se algum dia uma alegacao
            # real dividir linha com um link, ela some junto. Nenhum
            # documento atual faz isso; aceito ate acontecer de verdade.
            continue
        for match in NUMBER_RE.finditer(line):
            token = match.group(1).strip()
            if any(rx.match(token) for rx, _ in IGNORED_TOKENS):
                continue
            found.append(
                {
                    "doc": doc,
                    "line": lineno,
                    "text": token,
                    "context": line.strip()[:120],
                    "type": "number",
                }
            )
    return found


# Alegacao de capacidade sai de ESTRUTURA, nunca de prosa. Varrer prosa livre
# atras de "o sistema faz X" produz falso positivo demais para ser gate.
CAPABILITY_TABLES = ("CAPABILITY-MATRIX.md", "AGENT-CATALOG.md")


def _is_table_separator(stripped: str) -> bool:
    # Exige o "|" inicial explicitamente: sem isso, string vazia (linha em
    # branco) tambem bateria (conjunto vazio e subconjunto de qualquer
    # conjunto), e uma linha em branco depois de uma linha de tabela seria
    # lida como separador por acidente.
    return stripped.startswith("|") and set(stripped) <= set("|-: ")


def extract_capabilities(root: Path = VNEXT) -> list[dict]:
    found: list[dict] = []
    for name in CAPABILITY_TABLES:
        path = root / name
        if not path.exists():
            continue
        # Mesma cerca de `extract_numbers`: linha dentro de bloco cercado e
        # exemplo, nao alegacao. Sem isto, uma tabela ou lista ilustrativa
        # dentro de um bloco de codigo em AGENT-CATALOG.md ou FINAL-REPORT.md
        # (ambos ja tem blocos cercados hoje) vira alegacao real por acidente.
        lines = _strip_code_blocks(path.read_text(encoding="utf-8"), path).split("\n")
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped.startswith("|") or _is_table_separator(stripped):
                continue
            # Cabecalho de tabela GFM e definido por POSICAO, nao por
            # vocabulario: e a linha imediatamente seguida pela linha
            # separadora ("|---|---|"). Deteccao por posicao e exata e nao
            # envelhece; a lista de palavras-chave anterior ("Capacidade",
            # "Agent"...) vazava toda vez que uma tabela nova usava um
            # cabecalho diferente ("Servico AWS", "Coordinator"), como o
            # sanity check da Task 3 provou.
            # Tabela sem linha separadora (Markdown malformado) nao tem
            # ancora nenhuma linha nunca sera seguida por um separador, entao
            # nenhuma linha e descartada como cabecalho, nem mesmo a que
            # visualmente seria o cabecalho. Decisao deliberada: sem a linha
            # separadora nao ha como distinguir cabecalho de dado por
            # posicao, e tratar tudo como dado (falso positivo eventual) e
            # preferivel a inventar uma heuristica de vocabulario -- que e
            # exatamente o problema que esta reescrita elimina.
            proxima = lines[lineno].strip() if lineno < len(lines) else ""
            if _is_table_separator(proxima):
                continue
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if not cells or not cells[0]:
                continue
            found.append(
                {
                    "doc": _display_path(path),
                    "line": lineno,
                    "text": cells[0],
                    "context": stripped[:120],
                    "type": "capability",
                }
            )
    found.extend(_final_report_inventory(root))
    return found


def _final_report_inventory(root: Path = VNEXT) -> list[dict]:
    """Item de lista dentro da secao "## 4." do FINAL-REPORT (inventario de
    pacotes, modulos e documentos entregues) tambem e alegacao de capacidade:
    cada linha afirma que algo especifico foi criado. A deteccao usa o
    prefixo "4." do titulo, nao o texto inteiro do titulo -- sobrevive a
    renomeacao da secao ("Inventario..." virar outra coisa) desde que a
    numeracao continue "## 4.".

    Documento ausente (`FINAL-REPORT.md` nao existe) e tratado como lista
    vazia sem erro -- e o caso pratico de qualquer fixture sintetica em
    `tmp_path`, e ausencia do documento inteiro nao e a mesma falha que
    ancora perdida dentro dele. Mas se o arquivo existe e a ancora "## 4."
    NAO e encontrada -- secao renumerada, prefixo mudado -- isso e estourado
    como ValueError, nao devolvido como lista vazia: um gate que perde o
    proprio ponto de entrada e degrada em silencio nao vale nada, e este gate
    existe exatamente para impedir que uma alegacao suma sem barulho. Pela
    mesma razao, ancora encontrada mas ZERO itens coletados tambem estoura:
    a lista so reconhece marcador "- ", entao uma secao 4 reescrita com lista
    numerada ("1. ", "2. ") passa pela deteccao de ancora sem erro e devolve
    lista vazia -- exatamente o miss silencioso que este gate existe para
    impedir.

    `text` guarda a linha do item inteira (sem o marcador "- "), com path e
    descricao juntos: e a chave que o manifesto casa, e qualquer
    reformatacao do inventario (novo caminho, nova descricao) precisa
    re-registrar a alegacao -- aceitar so o path deixaria a descricao mudar
    sem o gate perceber.
    """
    path = root / "FINAL-REPORT.md"
    if not path.exists():
        return []
    found: list[dict] = []
    in_section = False
    anchor_found = False
    text = _strip_code_blocks(path.read_text(encoding="utf-8"), path)
    for lineno, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped[3:].lstrip().startswith("4.")
            anchor_found = anchor_found or in_section
            continue
        if not in_section:
            continue
        if stripped.startswith("- "):
            item_text = stripped[2:].strip()
            if not item_text:
                continue
            found.append(
                {
                    "doc": _display_path(path),
                    "line": lineno,
                    "text": item_text,
                    "context": stripped[:120],
                    "type": "capability",
                }
            )
    if not anchor_found:
        raise ValueError(
            f"ancora de inventario '## 4.' nao encontrada em {_display_path(path)}"
        )
    if not found:
        raise ValueError(
            f"secao '## 4.' encontrada em {_display_path(path)} mas nenhum item de "
            "lista foi coletado -- ou os marcadores de lista mudaram de forma (o "
            "extrator so reconhece '- ') e precisa aprender o novo formato, ou a "
            "secao foi esvaziada de proposito e a expectativa de ancora neste "
            "script precisa ser atualizada deliberadamente"
        )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Inclui provas tier slow.")
    parser.add_argument("--seed", action="store_true", help="Gera manifesto semente.")
    parser.add_argument("--report", action="store_true", help="Tabela de lastro.")
    args = parser.parse_args()
    # `seed`/`report`/`audit` chegam nas Tasks 6 e 7 -- nenhum teste desta
    # task chama `main()`, e o noqa e temporario ate essas funcoes existirem.
    if args.seed:
        return seed()  # noqa: F821
    if args.report:
        return report()  # noqa: F821
    return audit(include_slow=args.full)  # noqa: F821


if __name__ == "__main__":
    raise SystemExit(main())
