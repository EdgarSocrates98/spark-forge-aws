#!/usr/bin/env python3
"""Detecta quando uma fonte oficial citada pelo catalogo mudou.

Fecha a divida da secao 16 (Fase 2) da spec da Fase 0: `refresh_knowledge`, o
harvest das docs oficiais que **nunca commita sozinho** -- abre PR com o
resultado para revisao humana. Conhecimento entra por revisao, nao por scraper.

O QUE ESTE SCRIPT NAO FAZ, e por que
====================================

Nao baixa o texto das docs para dentro do repositorio. A tentacao obvia era
guardar um snapshot de cada pagina e diffar texto contra texto. Tres razoes
contra, na ordem em que pesam:

1. O diff de texto de uma pagina da AWS e quase todo ruido -- navegacao,
   breadcrumb, "was this page helpful", ids gerados. O sinal util (mudou o
   valor default de um parametro) fica enterrado, e um relatorio que grita a
   cada execucao treina o operador a ignora-lo. E a mesma falha que a fixture
   `clean_job` existe para impedir no analisador.
2. Copiar documentacao de terceiro para o repositorio e decisao de licenciamento
   que ninguem tomou.
3. O objetivo nao e ter a doc; e saber QUANDO reler a doc, e QUAIS regras
   dependem dela. Isso um hash resolve.

Entao o que se guarda e `knowledge/sources.lock.json`: por URL, o hash do texto
normalizado, a data da ultima conferencia, e a lista de `rule_id` que citam
aquela URL. O relatorio nao diz "a doc mudou assim"; diz "a doc mudou, e as
regras SF-X-001 e SF-Y-003 dependem dela -- releia".

URL FIXA versus URL MOVEL
=========================

Nem toda fonte precisa ser vigiada. O catalogo cita dois tipos:

  fixa   https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html
         https://github.com/apache/iceberg/blob/apache-iceberg-1.0.0/format/spec.md
         Versao no path. O conteudo nao muda; se mudar, mudou o passado.
         Vigiar so produziria ruido.

  movel  https://spark.apache.org/docs/latest/sql-performance-tuning.html
         https://docs.aws.amazon.com/glue/latest/dg/worker-types.html
         `latest`. O conteudo muda sob os pes da regra, e a data em
         `sources[].retrieved` e a UNICA coisa que ancora o que foi lido.

So as moveis sao buscadas. As fixas aparecem no relatorio como uma contagem,
porque saber que N regras citam fonte imutavel tambem e informacao: e a parte
do catalogo que nao pode envelhecer em silencio.

Uso
===

    python scripts/refresh_knowledge.py --check     # so relata; exit 1 se mudou
    python scripts/refresh_knowledge.py --update    # reescreve o lock

    --out CAMINHO   escreve o relatorio markdown num arquivo alem do stdout
    --offline       nao acessa a rede; util para inspecionar a watchlist

Nenhum modo escreve no git. O workflow
`.github/workflows/refresh-knowledge.yml` roda `--update`, cria um branch e
abre PR; merge e decisao humana.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LOCK_PATH = ROOT / "knowledge" / "sources.lock.json"
USER_AGENT = "sparkforge-refresh-knowledge/1.0 (+https://github.com/EdgarSocrates98/spark-forge-aws)"
TIMEOUT_S = 30

# Um segmento de versao no path torna a URL imutavel. Cobre os tres formatos que
# o catalogo usa hoje: `/docs/3.5.6/`, `apache-iceberg-1.10.0`, e sha/tag do
# GitHub em `/blob/<ref>/`.
_PINNED_PATTERNS = (
    re.compile(r"/\d+\.\d+(\.\d+)?/"),
    re.compile(r"-\d+\.\d+\.\d+"),
    re.compile(r"/blob/[0-9a-f]{7,40}/"),
)

_SCRIPT_STYLE = re.compile(
    r"<(script|style|noscript|svg)\b.*?</\1>", re.IGNORECASE | re.DOTALL
)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")


class FetchFailed(RuntimeError):
    """A URL nao pode ser lida. Nunca e tratada como 'nao mudou'."""


def is_pinned(url: str) -> bool:
    """True quando a URL aponta para uma versao imutavel."""
    if "/latest/" in url:
        return False
    return any(pattern.search(url) for pattern in _PINNED_PATTERNS)


def normalize(payload: str) -> str:
    """Reduz HTML ao texto visivel, colapsado.

    Nao e um parser de HTML e nao precisa ser: o objetivo e um hash estavel
    entre duas leituras da MESMA pagina inalterada, nao uma renderizacao fiel.
    Script, style e comentario saem porque costumam carregar nonce e timestamp,
    que mudariam o hash a cada leitura e produziriam alarme falso permanente.
    """
    text = _SCRIPT_STYLE.sub(" ", payload)
    text = _COMMENT.sub(" ", text)
    text = _TAG.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip()


def digest(payload: str) -> str:
    return hashlib.sha256(normalize(payload).encode("utf-8")).hexdigest()


ALLOWED_SCHEMES = frozenset({"http", "https"})


def http_fetch(url: str) -> str:
    """Busca `url`. Levanta FetchFailed em qualquer erro.

    O esquema e validado antes de abrir, e nao por formalidade: a URL vem de
    `sources[].url` do catalogo, que e dado editavel -- a mesma superficie que
    obriga o avaliador de `expr` a ter whitelist de nos AST. Sem esta checagem,
    uma regra com `url: file:///etc/passwd` faria `urlopen` ler arquivo local, e
    `url: http://169.254.169.254/...` alcancaria o metadata do runner de CI, que
    e onde o workflow roda com token. Ver secao 13 da spec da Fase 0.
    """
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise FetchFailed(f"{url}: esquema {scheme!r} nao permitido (use http ou https)")

    # noqa S310 nas duas linhas: o esquema ja foi restrito a http/https acima,
    # que e exatamente o que a regra pede. Silenciar sem a checagem seria o
    # antipadrao; a checagem sem o silenciamento nao passa no lint.
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:  # noqa: S310
            raw = response.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        raise FetchFailed(f"{url}: {exc}") from exc
    return raw.decode("utf-8", errors="replace")


def watchlist() -> dict[str, dict]:
    """URL -> {rules, retrieved, pinned}, derivada do proprio catalogo.

    A watchlist nao e uma lista mantida a mao: ela E o conjunto de `sources[].url`
    das regras. Regra nova com fonte nova passa a ser vigiada sem ninguem
    lembrar de registrar a URL em outro lugar -- que e exatamente o tipo de
    passo esquecido que faz um mecanismo de frescor apodrecer.
    """
    from sparkforge.rules.loader import load_catalog

    found: dict[str, dict] = {}
    citing: dict[str, list[str]] = defaultdict(list)
    dates: dict[str, set[str]] = defaultdict(set)

    for rule in load_catalog():
        for source in rule.get("sources") or []:
            url = source.get("url")
            if not url:
                continue
            citing[url].append(rule["id"])
            if source.get("retrieved"):
                dates[url].add(str(source["retrieved"]))

    for url, rules in citing.items():
        found[url] = {
            "rules": sorted(set(rules)),
            "retrieved": sorted(dates[url]),
            "pinned": is_pinned(url),
        }
    return dict(sorted(found.items()))


def load_lock() -> dict:
    if not LOCK_PATH.is_file():
        return {"schema_version": 1, "sources": {}}
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def write_lock(lock: dict) -> None:
    text = json.dumps(lock, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCK_PATH.write_text(text, encoding="utf-8", newline="\n")


def compare(
    entries: dict[str, dict],
    lock: dict,
    fetch: Callable[[str], str],
    today: str,
) -> tuple[list[dict], dict]:
    """Confere cada URL movel. Devolve (eventos, lock novo).

    Um evento por URL que mudou, que nunca foi vista, ou que nao pode ser lida.
    URL ilegivel vira evento `unreachable` e NAO herda o hash antigo em
    silencio: hash preservado depois de um 404 significaria "conferida hoje,
    igual", que e mentira -- a doc pode ter sido movida justamente porque mudou.
    """
    events: list[dict] = []
    stored = dict(lock.get("sources") or {})

    for url, meta in entries.items():
        if meta["pinned"]:
            stored[url] = {
                "pinned": True,
                "rules": meta["rules"],
                "retrieved": meta["retrieved"],
            }
            continue

        previous = stored.get(url) or {}
        try:
            payload = fetch(url)
        except FetchFailed as exc:
            events.append({"kind": "unreachable", "url": url, "detail": str(exc), **meta})
            entry = dict(previous)
            entry.update(
                {
                    "pinned": False,
                    "rules": meta["rules"],
                    "retrieved": meta["retrieved"],
                    "last_error": str(exc),
                }
            )
            stored[url] = entry
            continue

        current = digest(payload)
        before = previous.get("sha256")
        if before is None:
            events.append({"kind": "new", "url": url, **meta})
        elif before != current:
            events.append({"kind": "changed", "url": url, "was": before, "now": current, **meta})

        stored[url] = {
            "pinned": False,
            "sha256": current,
            "checked_at": today,
            "rules": meta["rules"],
            "retrieved": meta["retrieved"],
        }

    for url in list(stored):
        if url not in entries:
            del stored[url]

    return events, {"schema_version": 1, "sources": stored}


def render_report(events: Iterable[dict], entries: dict[str, dict], today: str) -> str:
    events = list(events)
    moving = [u for u, m in entries.items() if not m["pinned"]]
    pinned = [u for u, m in entries.items() if m["pinned"]]

    lines = [
        "# refresh_knowledge — conferência de fontes",
        "",
        f"Data: {today}",
        f"Fontes citadas pelo catálogo: {len(entries)} "
        f"({len(moving)} móveis, {len(pinned)} fixas por versão)",
        "",
    ]

    if not events:
        lines += [
            "Nenhuma fonte móvel mudou desde a última conferência.",
            "",
            "Nada a revisar. O lock foi carimbado com a data de hoje.",
            "",
        ]
    else:
        lines += [
            "## O que mudou",
            "",
            "Cada item abaixo exige **leitura humana da fonte** e, se o conteúdo que a",
            "regra cita tiver mudado, atualização da regra e da data em `sources[].retrieved`.",
            "",
        ]
        for event in events:
            label = {
                "changed": "MUDOU",
                "new": "NOVA (sem hash anterior — primeira conferência)",
                "unreachable": "ILEGÍVEL",
            }[event["kind"]]
            lines.append(f"### {label} — {event['url']}")
            lines.append("")
            lines.append(f"- Regras que citam: {', '.join(event['rules'])}")
            if event.get("retrieved"):
                lines.append(f"- `retrieved` declarado nas regras: {', '.join(event['retrieved'])}")
            if event.get("detail"):
                lines.append(f"- Erro: `{event['detail']}`")
            lines.append("")

    if pinned:
        lines += [
            "## Fontes fixas por versão (não conferidas, por construção)",
            "",
            "Conteúdo imutável: a versão está no path. Aparecem aqui para que a parcela",
            "do catálogo ancorada em fonte imutável seja visível, não para revisão.",
            "",
        ]
        lines += [f"- {url} — {', '.join(entries[url]['rules'])}" for url in pinned]
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Confere e relata; nao escreve o lock.")
    mode.add_argument("--update", action="store_true", help="Confere e reescreve o lock.")
    parser.add_argument("--offline", action="store_true", help="Nao acessa a rede.")
    parser.add_argument("--out", type=Path, help="Escreve o relatorio markdown neste caminho.")
    parser.add_argument("--today", default="", help="Data ISO a carimbar (default: hoje, UTC).")
    args = parser.parse_args(argv)

    if not args.check and not args.update:
        args.check = True

    today = args.today
    if not today:
        from datetime import datetime, timezone

        today = datetime.now(timezone.utc).date().isoformat()

    entries = watchlist()

    if args.offline:
        moving = sum(1 for m in entries.values() if not m["pinned"])
        print(f"{len(entries)} fontes ({moving} móveis, {len(entries) - moving} fixas)")
        for url, meta in entries.items():
            marker = "fixa " if meta["pinned"] else "movel"
            print(f"  [{marker}] {url} — {', '.join(meta['rules'])}")
        return 0

    events, lock = compare(entries, load_lock(), http_fetch, today)
    report = render_report(events, entries, today)
    print(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8", newline="\n")

    if args.update:
        write_lock(lock)
        print(f"lock atualizado: {LOCK_PATH.relative_to(ROOT)}", file=sys.stderr)

    # Exit 1 quando ha algo para revisar. E o que faz o workflow abrir PR, e o
    # que faria um `--check` local falhar de proposito.
    return 1 if events else 0


if __name__ == "__main__":
    raise SystemExit(main())
