"""Quando o SparkForge deixou de saber: o estado de cada fonte citada.

Uma regra cita a documentacao que a sustenta, com a data em que alguem a leu
(`sources[].retrieved`). `knowledge/sources.lock.json` diz, por URL, se a pagina
tem versao no caminho (`pinned`), se ja foi conferida por hash (`sha256`,
`checked_at`) e, desde esta frente, QUANDO o hash mudou pela ultima vez
(`changed_at`, gravado por `scripts/refresh_knowledge.py --update`). Com as duas
coisas, o estado da fonte e calculavel, e nao opiniao:

  unresolved  o lock nao existe, nao le, ou nao tem a URL
  fixed       versao no caminho: o conteudo nao muda
  stale       o hash mudou DEPOIS da data em que a regra validou a fonte
  unverified  URL movel que nunca foi conferida por hash
  aging       conferida, sem mudanca, mas ha mais de `AGING_DAYS`
  fresh       conferida, sem mudanca, dentro de `AGING_DAYS`

A ordem acima e a precedencia. `conflicted` nao e estado: e um atributo ao lado
dele, quando o lock registra para a mesma URL uma leitura em data diferente da
que a regra declara. Trocar o estado inteiro por ele esconderia `unverified` e
`fixed` atras de uma divergencia de data que quase sempre e so releitura.

O LIMIAR E ESCOLHA. Nao existe fonte que diga quantos dias uma conferencia leva
para envelhecer. `AGING_DAYS` e convencao, declarada com a razao em
`AGING_BASIS`, e as duas saem junto do estado (regra 11: limiar e decisao, e
decisao se declara).

O ESTADO DEPENDE DO LOCK E DO DIA, e por isso nunca entra no `Finding`: um
achado e deterministico, e isto nao e. Os verbos calculam na leitura, e so
quando pedido (`source_freshness`).

Nenhuma rede: o lock e so lido.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sparkforge.facts.scan import iter_source_files

AGING_DAYS = 14
AGING_BASIS = (
    "convencao: duas rodadas perdidas do refresh semanal "
    "(refresh-knowledge.yml, cron segunda 06:00 UTC)"
)
LOCK_NAME = "sources.lock.json"
LOCK_ENV = "SPARKFORGE_SOURCES_LOCK"
ESTADOS = ("unresolved", "fixed", "stale", "unverified", "aging", "fresh")


@dataclass(frozen=True)
class Estado:
    state: str
    reason: str
    validated: str | None = None
    checked_at: str | None = None
    changed_at: str | None = None
    age_days: int | None = None
    conflicted: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def hoje_utc() -> date:
    return datetime.now(timezone.utc).date()


def data(valor: Any) -> date | None:
    """`date` do YAML, ou texto ISO `AAAA-MM-DD`; qualquer outra coisa e `None`."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def carregar_lock(root: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    """As entradas do lock, ou `None` com o motivo (`lock_ausente`/`lock_ilegivel`).

    `SPARKFORGE_SOURCES_LOCK` aponta um lock avulso e vence `root`: e o que deixa
    um golden usar lock sintetico sem trocar a raiz de knowledge inteira -- trocar
    `SPARKFORGE_KNOWLEDGE` quebraria toda outra leitura de knowledge no caminho
    (a matriz do Control-M, por exemplo), medido no caso `fixtures/sarif/freshness`.
    """
    avulso = os.environ.get(LOCK_ENV)
    if avulso:
        # So LEITURA, e da mesma confianca de `SPARKFORGE_KNOWLEDGE`: variavel do
        # operador. Mesmo assim o caminho e resolvido e so um `.json` existente e
        # aceito -- qualquer outra coisa vira `lock_ilegivel`, com nome, e nao uma
        # leitura de arquivo arbitrario.
        caminho = Path(avulso).expanduser().resolve()
        if caminho.suffix != ".json" or not caminho.is_file():
            return None, "lock_ilegivel"
    elif root is None:
        return None, "lock_ausente"
    else:
        caminho = Path(root) / LOCK_NAME
    if not caminho.is_file():
        return None, "lock_ausente"
    try:
        dado = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "lock_ilegivel"
    fontes = dado.get("sources") if isinstance(dado, dict) else None
    if not isinstance(fontes, dict):
        return None, "lock_ilegivel"
    return fontes, None


def _conflito(validado: date | None, entrada: Mapping[str, Any]) -> dict[str, Any] | None:
    leituras = sorted({str(d) for d in entrada.get("retrieved") or [] if data(d) is not None})
    if validado is None:
        return None
    outras = [d for d in leituras if d != validado.isoformat()]
    if not outras:
        return None
    return {"validated": validado.isoformat(), "other_readings": outras}


def estado(
    url: str,
    validado_em: Any,
    lock: Mapping[str, Mapping[str, Any]] | None,
    as_of: date,
    *,
    motivo_sem_lock: str = "lock_ausente",
    aging_days: int = AGING_DAYS,
) -> Estado:
    """O estado de UMA fonte, na precedencia do docstring do modulo."""
    if lock is None:
        return Estado("unresolved", motivo_sem_lock)
    entrada = lock.get(url)
    if not isinstance(entrada, Mapping):
        return Estado("unresolved", "fora_do_lock")
    validado = data(validado_em)
    base = {
        "validated": validado.isoformat() if validado else None,
        "conflicted": _conflito(validado, entrada),
    }
    if entrada.get("pinned"):
        return Estado("fixed", "versao_no_caminho", **base)

    mudou = data(entrada.get("changed_at"))
    conferido = data(entrada.get("checked_at"))
    datas = {
        "checked_at": conferido.isoformat() if conferido else None,
        "changed_at": mudou.isoformat() if mudou else None,
    }
    if mudou is not None and (validado is None or validado < mudou):
        return Estado("stale", "mudou_depois_da_validacao", **base, **datas)
    if not entrada.get("sha256") or conferido is None:
        return Estado("unverified", "nunca_conferida", **base)
    idade = (as_of - conferido).days
    nome = "aging" if idade > aging_days else "fresh"
    return Estado(nome, f"conferida_ha_{idade}_dias", age_days=idade, **base, **datas)


def mapa(
    citacoes: Iterable[tuple[str | None, Any]],
    lock: Mapping[str, Mapping[str, Any]] | None,
    as_of: date,
    *,
    motivo_sem_lock: str = "lock_ausente",
) -> dict[str, Any]:
    """`source_freshness` (URL para estado) e `freshness_policy` de um conjunto
    de citacoes `(url, validado_em)`.

    A mesma URL citada com datas de validacao diferentes (duas regras, ou regra e
    documento) usa a MAIS ANTIGA: se a pagina mudou depois de qualquer validacao,
    alguem precisa reler. Citacao sem URL nao recebe estado e conta como
    `sem_url`.
    """
    sem_url = 0
    por_url: dict[str, list[date | None]] = defaultdict(list)
    for url, validado_em in citacoes:
        if not url:
            sem_url += 1
            continue
        por_url[url].append(data(validado_em))
    estados: dict[str, dict[str, Any]] = {}
    for url in sorted(por_url):
        datas_validas = [d for d in por_url[url] if d is not None]
        validado = min(datas_validas) if datas_validas else None
        estados[url] = estado(url, validado, lock, as_of, motivo_sem_lock=motivo_sem_lock).to_dict()
    contagem = Counter(e["state"] for e in estados.values())
    return {
        "source_freshness": estados,
        "freshness_policy": {
            "aging_days": AGING_DAYS,
            "basis": AGING_BASIS,
            "as_of": as_of.isoformat(),
            "counts": {**{nome: contagem.get(nome, 0) for nome in ESTADOS}, "sem_url": sem_url},
        },
    }


def citacoes_de(itens: Iterable[Mapping[str, Any]]) -> list[tuple[str | None, Any]]:
    """`(url, retrieved)` de cada `sources[]` de findings ou regras."""
    return [
        (fonte.get("url"), fonte.get("retrieved"))
        for item in itens
        for fonte in item.get("sources") or []
        if isinstance(fonte, Mapping)
    ]


_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_INLINE_CODE = re.compile(r"`[^`]*`")
_URL = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
_RETRIEVED = re.compile(r"retrieved[:\s]+(\d{4}-\d{2}-\d{2})")


def fontes_de_knowledge(root: Path) -> tuple[dict[str, dict], dict[str, dict[str, list[str]]]]:
    """As URLs da secao `Fontes` de cada `knowledge/**.md`.

    Devolve `(por_url, por_doc)`: `por_url` e o formato que
    `scripts/refresh_knowledge.py` sempre usou (`url -> {docs, retrieved}`), e
    `por_doc` e `doc -> {url: [datas]}`, a data de leitura que CADA documento
    declara -- o lock junta as datas das duas origens numa lista so, e sem isto
    o estado por documento nao teria de onde tirar a validacao.

    O leitor e deliberadamente o mais simples que resolve o corpus:

    - heading cujo texto e EXATAMENTE `Fontes` (`## Fontes e frescor` do
      `INDEX.md` fala SOBRE o mecanismo e nao cita fonte);
    - a secao vai ate o proximo heading de nivel igual ou maior, entao uma
      subsecao `### ...` dentro dela pertence a ela;
    - URL dentro de crase e padrao, nao citacao (`release-version-<N>.html`
      descreve 24 paginas e devolveria 404 para sempre).

    O `doc` sai como `knowledge/<caminho relativo>`, o mesmo formato do campo
    `docs` do lock, onde quer que `root` esteja instalado.
    """
    docs: dict[str, set[str]] = defaultdict(set)
    datas: dict[str, set[str]] = defaultdict(set)
    por_doc: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for caminho in sorted(iter_source_files(root, "*.md")):
        ancora = "knowledge/" + caminho.relative_to(root).as_posix()
        nivel: int | None = None
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            casou = _HEADING.match(linha)
            if casou is not None:
                atual = len(casou.group(1))
                if casou.group(2).strip() == "Fontes":
                    nivel = atual
                elif nivel is not None and atual <= nivel:
                    nivel = None
                continue
            if nivel is None:
                continue
            corpo = _INLINE_CODE.sub(" ", linha)
            declaradas = set(_RETRIEVED.findall(corpo))
            for bruta in _URL.findall(corpo):
                url = bruta.rstrip(".,;:")
                docs[url].add(ancora)
                datas[url] |= declaradas
                por_doc[ancora][url] |= declaradas
    por_url = {
        url: {"docs": sorted(ancoras), "retrieved": sorted(datas[url])}
        for url, ancoras in sorted(docs.items())
    }
    return por_url, {
        doc: {url: sorted(ds) for url, ds in sorted(urls.items())}
        for doc, urls in sorted(por_doc.items())
    }


def citacoes_do_doc(
    por_doc: Mapping[str, Mapping[str, list[str]]], doc: str
) -> list[tuple[str, Any]]:
    """`(url, validacao)` de um documento: a data mais antiga que ele declara,
    ou `None` quando a linha da fonte nao traz `retrieved`."""
    return [(url, min(datas) if datas else None) for url, datas in (por_doc.get(doc) or {}).items()]
