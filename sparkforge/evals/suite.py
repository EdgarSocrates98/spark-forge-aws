"""O gabarito de uma suite de avaliacao de agente.

`suite.yaml` referencia perguntas de `evals/fase0.xml` por indice (1-based) e
acrescenta o que o XML nao tem: as tools que a resposta exige, a ordem parcial
entre elas, e as perguntas cuja resposta certa e recusar. O XML fica intocado
porque `scripts/check_evals.py` o recomputa contra o corpus.

O `sha256` cobre a suite RESOLVIDA -- protocolo de resposta mais cada pergunta
com texto, resposta esperada, tools, ordem e abstencao --, e nao os bytes do
YAML. Mudar uma resposta em `fase0.xml` deixa o YAML byte a byte igual, e dois
scorecards pontuados contra gabaritos diferentes pareceriam comparaveis. E
reformatar o YAML nao muda o que se pontua, entao nao muda o hash.

Todo defeito de schema e `SuiteError` nomeando o campo. Default silencioso aqui
seria gabarito inventado.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

SUITE_FILE = "suite.yaml"
SCHEMA_VERSION = 1
QUESTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

_XML_PROLOGO = re.compile(r"^\s*<\?xml[^>]*\?>")
_ENVELOPE = re.compile(r"<evaluation>(?P<miolo>.*)</evaluation>", re.S)
_QA_PAIR = re.compile(
    r"<qa_pair>\s*<question>(?P<pergunta>.*?)</question>\s*"
    r"<answer>(?P<resposta>.*?)</answer>\s*</qa_pair>",
    re.S,
)


class SuiteError(ValueError):
    """Gabarito invalido. A mensagem nomeia a pergunta e o campo."""


@dataclass(frozen=True)
class Question:
    id: str
    question: str
    expected: str | None
    required_tools: tuple[str | tuple[str, ...], ...]
    order: tuple[tuple[str, str], ...] = ()
    expects_abstention: bool = False
    anchor: dict[str, str] = field(default_factory=dict)

    def canonical(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "expected": self.expected,
            "required_tools": [t if isinstance(t, str) else list(t) for t in self.required_tools],
            "order": [list(par) for par in self.order],
            "expects_abstention": self.expects_abstention,
        }


@dataclass(frozen=True)
class Suite:
    id: str
    answer_protocol: str
    questions: tuple[Question, ...]
    sha256: str

    def by_id(self) -> dict[str, Question]:
        return {q.id: q for q in self.questions}


def _qa_pairs(xml_path: Path) -> list[tuple[str, str]]:
    """Os `qa_pair` de uma fonte no formato de `evals/fase0.xml`, SEM parser XML.

    O formato e fixo e raso -- `<evaluation>` com `<qa_pair>` de `<question>` e
    `<answer>` --, entao ele e lido por expressao estrita, e toda estrutura fora
    dela e recusada por nome. Nenhum parser XML entra aqui: `defusedxml` e
    dependencia so de `dev`, e `xml.etree` resolve entidade conforme a versao do
    expat. Sem parser nao ha entidade externa nem expansao para explorar, e
    DTD ou declaracao de entidade e recusada antes de tudo.
    `tests/test_evals_suite.py` confere o resultado contra `defusedxml`.
    """
    try:
        texto = xml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SuiteError(f"fonte ilegivel: {xml_path.name}: {exc}") from exc
    if "<!DOCTYPE" in texto or "<!ENTITY" in texto:
        raise SuiteError(
            f"fonte {xml_path.name} declara DTD ou entidade -- recusada. O leitor "
            "de fonte nao expande entidade nenhuma."
        )
    corpo = _XML_PROLOGO.sub("", texto).strip()
    envelope = _ENVELOPE.fullmatch(corpo)
    if envelope is None:
        raise SuiteError(f"fonte ilegivel: {xml_path.name}: raiz <evaluation> ausente")
    miolo = envelope.group("miolo")
    pares = []
    posicao = 0
    for casou in _QA_PAIR.finditer(miolo):
        if miolo[posicao : casou.start()].strip():
            raise SuiteError(f"fonte ilegivel: {xml_path.name}: conteudo fora de <qa_pair>")
        pergunta, resposta = casou.group("pergunta"), casou.group("resposta")
        if "<" in pergunta or "<" in resposta:
            raise SuiteError(f"fonte ilegivel: {xml_path.name}: elemento dentro de qa_pair")
        pares.append((html.unescape(pergunta).strip(), html.unescape(resposta).strip()))
        posicao = casou.end()
    if miolo[posicao:].strip():
        raise SuiteError(f"fonte ilegivel: {xml_path.name}: conteudo fora de <qa_pair>")
    return pares


def _resolve_source(suite_dir: Path, qid: str, source: str) -> tuple[str, str]:
    arquivo, separador, indice = source.partition("#")
    if not separador or not indice.isdigit():
        raise SuiteError(f"{qid}: source {source!r} precisa da forma <arquivo>#<indice 1-based>")
    pares = _qa_pairs((suite_dir / arquivo).resolve())
    posicao = int(indice)
    if not 1 <= posicao <= len(pares):
        raise SuiteError(
            f"{qid}: source {source!r} fora do intervalo -- a fonte tem {len(pares)} qa_pair"
        )
    return pares[posicao - 1]


def _tools(qid: str, bruto: Any) -> tuple[str | tuple[str, ...], ...]:
    """Cada item e um verbo exigido, ou uma LISTA de verbos dos quais basta um.

    A alternativa existe porque ha pergunta com mais de um caminho honesto --
    a matriz do Glue sai de `runtime detect` e de `release describe` -- e
    exigir os dois reprovaria o agente por nao ter feito trabalho redundante.
    """
    if not isinstance(bruto, list) or not bruto:
        raise SuiteError(f"{qid}: required_tools precisa ser lista nao vazia de verbos canonicos")
    itens: list[str | tuple[str, ...]] = []
    for item in bruto:
        alternativas = (
            isinstance(item, list)
            and len(item) >= 2
            and all(isinstance(t, str) and t for t in item)
        )
        if isinstance(item, str) and item:
            itens.append(item)
        elif alternativas:
            itens.append(tuple(item))
        else:
            raise SuiteError(
                f"{qid}: required_tools tem item que nao e verbo nem lista de "
                f"alternativas: {item!r}"
            )
    return tuple(itens)


def _order(
    qid: str, bruto: Any, tools: tuple[str | tuple[str, ...], ...]
) -> tuple[tuple[str, str], ...]:
    if bruto is None:
        return ()
    if not isinstance(bruto, list):
        raise SuiteError(f"{qid}: order precisa ser lista de pares [antes, depois]")
    simples = {t for t in tools if isinstance(t, str)}
    pares = []
    for par in bruto:
        if not (isinstance(par, list) and len(par) == 2 and all(isinstance(t, str) for t in par)):
            raise SuiteError(f"{qid}: order tem item que nao e par [antes, depois]: {par!r}")
        fora = [t for t in par if t not in simples]
        if fora:
            raise SuiteError(
                f"{qid}: order cita tool fora de required_tools (ou que so aparece "
                f"como alternativa): {fora}"
            )
        pares.append((par[0], par[1]))
    return tuple(pares)


def _question(suite_dir: Path, bruto: Any, posicao: int) -> Question:
    if not isinstance(bruto, dict):
        raise SuiteError(f"questions[{posicao}] nao e objeto")
    qid = bruto.get("id")
    if not isinstance(qid, str) or not QUESTION_ID.fullmatch(qid):
        raise SuiteError(
            f"questions[{posicao}]: id ausente ou fora de {QUESTION_ID.pattern} -- ele vira "
            "nome de arquivo de transcript, entao separador de caminho nao entra"
        )
    tem_fonte, tem_texto = "source" in bruto, "question" in bruto
    if tem_fonte == tem_texto:
        raise SuiteError(f"{qid}: declare exatamente um entre source e question")
    abstencao = bruto.get("expects_abstention", False)
    if not isinstance(abstencao, bool):
        raise SuiteError(f"{qid}: expects_abstention precisa ser booleano")
    tools = _tools(qid, bruto.get("required_tools"))
    ordem = _order(qid, bruto.get("order"), tools)

    if tem_fonte:
        if abstencao:
            raise SuiteError(f"{qid}: pergunta de abstencao nao vem de fonte com resposta")
        texto, esperada = _resolve_source(suite_dir, qid, str(bruto["source"]))
        return Question(qid, texto, esperada, tools, ordem)

    texto = bruto["question"]
    if not isinstance(texto, str) or not texto.strip():
        raise SuiteError(f"{qid}: question vazia")
    if abstencao:
        ancora = bruto.get("anchor")
        if not (
            isinstance(ancora, dict)
            and isinstance(ancora.get("fixture"), str)
            and isinstance(ancora.get("kind"), str)
        ):
            raise SuiteError(f"{qid}: pergunta de abstencao exige anchor com fixture e kind")
        return Question(qid, texto.strip(), None, tools, ordem, True, dict(ancora))
    esperada = bruto.get("answer")
    if not isinstance(esperada, str) or not esperada.strip():
        raise SuiteError(f"{qid}: pergunta inline sem abstencao exige answer")
    return Question(qid, texto.strip(), esperada.strip(), tools, ordem)


def load_suite(suite_dir: Path | str) -> Suite:
    raiz = Path(suite_dir)
    arquivo = raiz / SUITE_FILE
    try:
        bruto = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SuiteError(f"{SUITE_FILE} ausente em {raiz.name}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise SuiteError(f"{SUITE_FILE} nao e YAML valido: {exc}") from exc
    if not isinstance(bruto, dict):
        raise SuiteError(f"{SUITE_FILE} precisa ser objeto")
    if bruto.get("schema_version") != SCHEMA_VERSION:
        raise SuiteError(f"schema_version precisa ser {SCHEMA_VERSION}")
    sid = bruto.get("id")
    protocolo = bruto.get("answer_protocol")
    perguntas_brutas = bruto.get("questions")
    if not isinstance(sid, str) or not sid:
        raise SuiteError("id da suite ausente")
    if not isinstance(protocolo, str) or "ANSWER:" not in protocolo:
        raise SuiteError("answer_protocol precisa existir e citar a linha ANSWER:")
    if not isinstance(perguntas_brutas, list) or not perguntas_brutas:
        raise SuiteError("questions precisa ser lista nao vazia")

    perguntas = tuple(_question(raiz, q, i) for i, q in enumerate(perguntas_brutas))
    vistos: set[str] = set()
    for pergunta in perguntas:
        if pergunta.id in vistos:
            raise SuiteError(f"id duplicado: {pergunta.id}")
        vistos.add(pergunta.id)

    canonico = json.dumps(
        {
            "answer_protocol": " ".join(protocolo.split()),
            "questions": [q.canonical() for q in perguntas],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonico.encode("utf-8")).hexdigest()
    return Suite(sid, " ".join(protocolo.split()), perguntas, digest)
