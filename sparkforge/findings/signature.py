"""Assinatura de CORRESPONDENCIA de um relatorio.

Ela prova que aquele texto foi derivado daquela evidencia com aquele catalogo.
Ela NAO prova autoria: nao ha chave, nao ha segredo, e qualquer pessoa com os
mesmos facts produz exatamente a mesma assinatura. E decisao registrada (D-6 do
spec da Fase 4b), e o limite vai escrito dentro do bloco que o relatorio carrega
-- bloco que sugira autoridade mente por omissao.

O que entra no hash, e o que cada parte pega (D-7 do spec):

| Entra                                  | Pega                                       |
|----------------------------------------|--------------------------------------------|
| `fact_ids` citados, ordenados e unicos | achado que cita evidencia trocada          |
| `rule_ids` que dispararam, idem        | achado acrescentado a mao                  |
| `catalog_version`, `schema_version`    | relatorio julgado por catalogo nao declarado |
| corpo do relatorio, normalizado        | prosa editada depois da emissao            |

Sem o corpo alguem reescreveria o texto inteiro mantendo a assinatura valida, e
ela garantiria menos do que o leitor supoe. Com o corpo, edicao legitima
invalida -- e reassinar e barato.

`SIGNATURE_VERSION` entra DENTRO do hash de proposito: mudar a normalizacao no
futuro sem mudar a versao faria assinaturas antigas parecerem invalidas sem que
nada tivesse sido adulterado, e "invalido" que na verdade significa "mudamos a
regra" e pior que nao assinar.

A serializacao e a canonica do repositorio (`models._canonical`, a mesma base do
`Fact.id`), e nao uma segunda inventada aqui: duas formas de canonizar sao duas
oportunidades de divergir.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

# `_canonical` e privado do modulo vizinho, e o import e deliberado: e a unica
# serializacao canonica do projeto (chaves ordenadas, sem espaco, ASCII escapado)
# e ja e a base do `Fact.id`. Copiar `json.dumps(...)` para ca criaria uma
# segunda definicao de "canonico" que ninguem manteria em sincronia.
from sparkforge.findings.models import _canonical

SIGNATURE_VERSION = 1
SIGNATURE_PREFIX = "sig_"

# sha256 inteiro, 64 hex. O projeto ja separa os dois usos de digest: `Fact.id`
# trunca sha1 em 6 hex porque so precisa de content-addressing (e diz isso na
# propria docstring), e `CollectEntry.sha256` guarda os 64 hex porque e
# integridade. Assinatura e integridade -- ela existe para resistir a uma edicao
# deliberada -- entao ela fica do lado dos 64 hex. Truncar reintroduziria em
# silencio o "forca criptografica e irrelevante aqui" no unico valor desta fase
# em que ela e exatamente o que importa.
SIGNATURE_RE = re.compile(r"^sig_[0-9a-f]{64}$")

_INNER_WS = re.compile(r"[ \t]+")
_BLANK_RUN = re.compile(r"\n{3,}")


def _normalize_line(line: str) -> str:
    stripped = line.rstrip()
    if not stripped:
        return ""
    body = stripped.lstrip(" \t")
    indent = stripped[: len(stripped) - len(body)]
    return indent + _INNER_WS.sub(" ", body)


def normalize_body(body: str) -> str:
    """Absorve reformatacao, e SO ela.

    O que ela absorve, exaustivamente:

    - fim de linha CRLF ou CR vira LF;
    - espaco horizontal repetido DENTRO da linha (depois do primeiro caractere
      nao-branco) colapsa para um espaco;
    - espaco em branco no fim da linha some;
    - mais de uma linha em branco seguida colapsa para uma;
    - linha em branco no inicio e no fim do documento some.

    O que ela NAO absorve: pontuacao, ordem, numero, palavra -- e tambem NAO
    absorve a **indentacao** da linha. Em Markdown o recuo decide se a linha e
    bloco de codigo ou prosa, e em que nivel um item de lista esta: colapsar o
    recuo deixaria passar como "reformatacao" uma mudanca que muda o que o
    leitor le. Cada item desta lista tem teste dos dois lados -- reformatar nao
    invalida, editar conteudo invalida -- porque normalizacao silenciosa e
    superficie para adulteracao que passa.
    """
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(_normalize_line(line) for line in text.split("\n"))
    return _BLANK_RUN.sub("\n\n", text).strip("\n")


def compute_signature(
    body: str,
    fact_ids: Sequence[str],
    rule_ids: Sequence[str],
    catalog_version: int,
    schema_version: int,
) -> str:
    """Assinatura de correspondencia: `sig_` + sha256 do payload canonico.

    `fact_ids` e `rule_ids` entram ordenados e sem repeticao: a ordem em que o
    relatorio cita a evidencia e apresentacao, nao conteudo, e citar o mesmo
    fact duas vezes nao muda o que foi assinado.
    """
    payload = {
        "signature_version": SIGNATURE_VERSION,
        "body": normalize_body(body),
        "fact_ids": sorted(set(fact_ids)),
        "rule_ids": sorted(set(rule_ids)),
        "catalog_version": catalog_version,
        "schema_version": schema_version,
    }
    digest = hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()
    return SIGNATURE_PREFIX + digest
