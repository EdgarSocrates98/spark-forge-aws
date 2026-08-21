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
