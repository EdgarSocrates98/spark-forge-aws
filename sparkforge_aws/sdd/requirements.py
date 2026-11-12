"""O modelo de requisitos do define: `requirements` no frontmatter.

Cada requisito tem id estavel (`REQ-`/`NFR-`/`US-` + numero), texto, kind,
aceite, fonte, referencias a decisoes e flag `critical`. Os validadores aqui
sao heuristicas honestas: o que e deterministico (duplicado, referencia
desconhecida, metrica sem fonte) vira recusa no gate; o que depende de
julgamento (testabilidade duvidosa, contradicao por negacao, bloqueio por
desconhecido) vira lacuna -- o codigo diz o que achou, o operador decide.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import Any

_ID_RE = re.compile(r"^(REQ|NFR|US)-[0-9]+$")
_METRICA_RE = re.compile(r"\d|>=|<=|==|!=|%|::")

# verbos observaveis: o aceite precisa dizer o que se ve, nao o que se pensa
_VERBOS_OBSERVAVEIS = (
    "retorna", "return", "falha", "fail", "rejeita", "reject", "grava", "write",
    "emite", "emit", "lista", "list", "exibe", "show", "cria", "creat", "remov",
    "delet", "registra", "record", "valida", "valid", "nega", "deny", "aceita",
    "accept", "conta", "count", "mede", "measur", "detecta", "detect", "expo",
    "gera", "generat", "compara", "compar", "bloqueia", "block", "permite",
    "allow", "imprime", "print", "salva", "save", "le ", "read",
)
_NEGACOES = frozenset({"nao", "não", "not", "never", "nunca", "sem", "without", "no"})
# palavras que nao carregam o sujeito da frase; fora delas, poucas em comum e
# a "contradicao" e so duas frases sobre assuntos diferentes
_STOPWORDS = frozenset({
    "a", "o", "as", "os", "de", "do", "da", "dos", "das", "em", "no", "na",
    "e", "ou", "the", "of", "to", "in", "and", "or", "for", "um", "uma",
    "que", "com", "por", "para", "ao", "se", "its", "it", "is", "be",
})
_PONTUACAO = str.maketrans("", "", string.punctuation)


@dataclass(frozen=True)
class Finding:
    """Um problema de requisito; `kind` vira o codigo do contrato no gate."""

    kind: str  # duplicate | untestable | metric_no_source | contradicts |
    #          decision_unknown | decision_open | blocked
    item: str | None
    detail: str


def _normaliza(texto: str) -> str:
    return " ".join(texto.lower().translate(_PONTUACAO).split())


def _tokens(texto: str) -> set[str]:
    return {t for t in _normaliza(texto).split() if t not in _STOPWORDS and len(t) > 2}


def _tem_metrica(texto: str) -> bool:
    return bool(_METRICA_RE.search(texto) or " <" in texto or " >" in texto)


def _testavel(aceite: str) -> bool:
    """Aceite testavel: metrica, referencia de teste ou verbo observavel.

    Heuristica de superficie, declarada: um aceite sem nenhum dos tracos pode
    ser perfeitamente testavel (o gate emite lacuna, nao recusa); um aceite
    com verbo da lista pode ser vago mesmo assim.
    """
    if _tem_metrica(aceite) or ".py" in aceite:
        return True
    baixo = aceite.lower()
    return any(verbo in baixo for verbo in _VERBOS_OBSERVAVEIS)


def _contradiz(outro: str, texto: str) -> bool:
    """Mesma base de tokens, uma so com negacao: contradicao por negacao.

    Precisa de pelo menos 3 tokens significativos em comum -- abaixo disso a
    interseccao e acaso, nao premissa compartilhada.
    """
    a, b = _tokens(outro), _tokens(texto)
    comuns = (a & b) - _NEGACOES
    if len(comuns) < 3:
        return False
    return (a & _NEGACOES) != (b & _NEGACOES)


def validate_requirements(
    requirements: list[dict[str, Any]],
    unknowns: list[dict[str, Any]],
    out_of_scope: list[str],
    decisions: dict[str, Any] | None,
) -> list[Finding]:
    """Os problemas dos requisitos, deterministicos primeiro.

    `decisions` e a arvore `forge/DecisionTree/v1` da feature (ou `None` quando
    nao existe -- nesse caso todo `decision_refs` e desconhecido).
    """
    achados: list[Finding] = []
    ids_vistos: set[str] = set()
    textos: dict[str, str] = {}
    for req in requirements:
        ident = req["id"]
        if ident in ids_vistos:
            achados.append(Finding("duplicate", ident, f"id {ident} repetido em requirements"))
        ids_vistos.add(ident)
        normal = _normaliza(req["text"])
        if normal in textos:
            achados.append(Finding(
                "duplicate", ident,
                f"{ident} repete o texto de {textos[normal]}; funda ou diferencie",
            ))
        else:
            textos[normal] = ident
    for req in requirements:
        ident = req["id"]
        aceite = str(req["acceptance"])
        if not _testavel(aceite):
            achados.append(Finding(
                "untestable", ident,
                f"{ident}: o aceite nao tem metrica, referencia de teste nem verbo "
                "observavel; reescreva com o que se mede (exit, contagem, saida)",
            ))
        if _tem_metrica(aceite) and not str(req.get("source") or "").strip():
            achados.append(Finding(
                "metric_no_source", ident,
                f"{ident}: o aceite traz metrica e o requisito nao declara source; "
                "diga de onde vem o numero",
            ))
        for dep in req.get("decision_refs") or []:
            if decisions is None or dep not in {
                d.get("id") for d in decisions.get("decisions") or [] if isinstance(d, dict)
            }:
                achados.append(Finding(
                    "decision_unknown", ident,
                    f"{ident} cita a decisao {dep}, que nao esta na arvore da feature",
                ))
            else:
                [dec] = [d for d in decisions["decisions"] if d.get("id") == dep]
                if dec.get("status") != "decided":
                    achados.append(Finding(
                        "decision_open", ident,
                        f"{ident} depende de {dep}, que esta {dec.get('status')}; "
                        "quem aprova e o operador",
                    ))
    for req in requirements:
        if not req.get("critical"):
            continue
        for desconhecido in unknowns:
            if not isinstance(desconhecido, dict):
                continue
            if req["id"] in (desconhecido.get("blocks") or []):
                achados.append(Finding(
                    "blocked", req["id"],
                    f"{req['id']} e critical e segue bloqueado por {desconhecido.get('id')}; "
                    "a premissa nao foi confirmada",
                ))
    for i, req in enumerate(requirements):
        for outro in requirements[i + 1:]:
            if _contradiz(req["text"], outro["text"]):
                achados.append(Finding(
                    "contradicts", req["id"],
                    f"{req['id']} e {outro['id']} divergem por negacao sobre a mesma "
                    "base; o operador decide qual fica",
                ))
        escopo = _tokens(req["text"])
        for fora in out_of_scope:
            alvo = _tokens(fora)
            if not alvo or not escopo:
                continue
            # requisito quase inteiro dentro do fora-de-escopo (ou o contrario)
            if len(escopo & alvo) >= 3 and (
                len(escopo & alvo) / len(escopo) >= 0.6
                or len(escopo & alvo) / len(alvo) >= 0.6
            ):
                achados.append(Finding(
                    "contradicts", req["id"],
                    f"{req['id']} cobre quase o mesmo que o fora-de-escopo "
                    f"'{fora}'; escopo inconsistente",
                ))
    return achados
