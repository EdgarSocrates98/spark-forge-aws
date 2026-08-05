#!/usr/bin/env python3
"""Detecta quando uma fonte oficial que este repositorio cita mudou.

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
normalizado, a data da ultima conferencia, e QUEM DEPENDE dela. O relatorio nao
diz "a doc mudou assim"; diz "a doc mudou, e as regras SF-X-001 e SF-Y-003
dependem dela -- releia".

DUAS ORIGENS, e a segunda existe porque a primeira sozinha mentia
=================================================================

A watchlist nasceu derivada SO das regras (`sources[].url` do catalogo), e o
desenho era bom pela razao que continua valendo: lista mantida a mao apodrece.
Mas ele tinha um efeito que ninguem tinha medido -- conhecimento que nenhuma
regra cita nunca entrava. A pesquisa de subagentes do Devin
(`knowledge/devin/agents-and-subagents.md`) e o caso limite: ela nao sustenta
regra nenhuma, sustenta PERFIL DE AGENTE, e as suas 24 URLs de `docs.devin.ai`
envelheciam sem alarme sobre uma superficie que a propria fonte declara
experimental. A pagina que mais provavelmente muda era a unica que ninguem
vigiava.

Entao a watchlist tem duas origens, as duas DERIVADAS e nenhuma mantida a mao:

  regra      `sources[].url` de cada regra do catalogo   -> campo `rules`
  knowledge  URL na secao `Fontes` de `knowledge/**.md`  -> campo `docs`

A segunda paga o preco que a primeira cobra: fonte vigiada precisa de VINCULO DE
VOLTA, senao um alarme chega sem dizer o que reler. Uma URL citada pelas duas
origens carrega os dois campos, e as datas `retrieved` das duas -- divergencia
entre elas fica VISIVEL no relatorio em vez de ser resolvida por chute.

O leitor da secao `Fontes` e deliberadamente simples: heading cujo texto e
exatamente `Fontes`, URL nua no corpo da secao, `(retrieved AAAA-MM-DD)` opcional
ao lado. URL dentro de crase e PADRAO, e nao citacao -- a §2 de
`knowledge/emr-serverless/runtime-matrix.md` escreve
`release-version-<N>.html` para descrever 24 paginas, e vigiar esse texto
produziria um 404 permanente, que e o alarme falso que mata a ferramenta.

URL FIXA versus URL MOVEL
=========================

Nem toda fonte precisa ser vigiada. As duas origens citam dois tipos:

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

    python scripts/refresh_knowledge.py --check              # so relata; exit 1 se mudou
    python scripts/refresh_knowledge.py --update             # reescreve o lock
    python scripts/refresh_knowledge.py --update --offline   # so sincroniza o lock

    --out CAMINHO   escreve o relatorio markdown num arquivo alem do stdout
    --offline       nao acessa a rede; lista a watchlist, e com `--update`
                    sincroniza o lock (entra fonte nova SEM hash, sai fonte que
                    ninguem cita mais) sem carimbar conferencia nenhuma. E o
                    caminho para o lock acompanhar regra ou pagina de knowledge
                    nova em ambiente sem rede -- CI de fork, maquina offline --,
                    e ele nunca inventa `sha256`: fonte sem hash aparece na
                    proxima conferencia com rede como NOVA, que e a verdade.

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


def knowledge_sources() -> dict[str, dict]:
    """URL -> {docs, retrieved}, lida das secoes `Fontes` de `knowledge/**.md`.

    Derivada, como a origem de regra: pagina nova de knowledge com fonte nova
    passa a ser vigiada sem ninguem registrar a URL em outro lugar.

    O formato do rodape e prosa, e nao tem schema -- por isso o leitor e o mais
    simples que resolve o corpus, e cada estreitamento tem razao medida:

    - Heading cujo texto e EXATAMENTE `Fontes`. `## Fontes e frescor` do
      `INDEX.md` fala SOBRE o mecanismo e nao cita fonte nenhuma; casar por
      prefixo o transformaria em origem.
    - A secao vai ate o proximo heading de nivel IGUAL OU MAIOR. Duas paginas
      tem `### O que estas fontes NAO sustentam` dentro do bloco, e a subsecao
      pertence a secao.
    - URL dentro de crase e PADRAO, nao citacao: a §2 de
      `emr-serverless/runtime-matrix.md` escreve `release-version-<N>.html` para
      descrever 24 paginas, e o trecho antes do `<` e uma URL sintaticamente
      valida que devolveria 404 para sempre. Alarme permanente e o modo de falha
      que faz o operador parar de ler o relatorio.
    """
    heading = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
    inline_code = re.compile(r"`[^`]*`")
    url_pattern = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
    retrieved_pattern = re.compile(r"retrieved[:\s]+(\d{4}-\d{2}-\d{2})")

    docs: dict[str, set[str]] = defaultdict(set)
    dates: dict[str, set[str]] = defaultdict(set)
    for path in sorted((ROOT / "knowledge").rglob("*.md")):
        anchor = path.relative_to(ROOT).as_posix()
        level: int | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            match = heading.match(line)
            if match is not None:
                current = len(match.group(1))
                if match.group(2).strip() == "Fontes":
                    level = current
                elif level is not None and current <= level:
                    level = None
                continue
            if level is None:
                continue
            body = inline_code.sub(" ", line)
            declared = set(retrieved_pattern.findall(body))
            for raw in url_pattern.findall(body):
                url = raw.rstrip(".,;:")
                docs[url].add(anchor)
                dates[url] |= declared
    return {
        url: {"docs": sorted(anchors), "retrieved": sorted(dates[url])}
        for url, anchors in sorted(docs.items())
    }


def watchlist() -> dict[str, dict]:
    """URL -> {rules, docs, retrieved, pinned}, das DUAS origens derivadas.

    Nenhuma das duas e mantida a mao, e e isso que impede o mecanismo de
    apodrecer: regra nova com fonte nova, ou pagina de knowledge nova com fonte
    nova, passam a ser vigiadas sem ninguem lembrar de registrar a URL noutro
    lugar. O passo que alguem esquece e o que mata frescor.

    `rules` e `docs` sao o VINCULO DE VOLTA, e sem eles a segunda origem seria
    ruido: quando uma fonte muda, o relatorio precisa dizer o que reler. Uma URL
    citada pelas duas origens carrega os dois -- e `retrieved` acumula as datas
    das duas, em vez de escolher uma. Divergencia entre a data que a regra
    declara e a que a pagina declara e informacao sobre qual das duas citacoes
    esta velha; resolve-la aqui seria apagar a pergunta.
    """
    from sparkforge.rules.loader import load_catalog

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

    documented = knowledge_sources()
    for url, meta in documented.items():
        dates[url] |= set(meta["retrieved"])

    found: dict[str, dict] = {}
    for url in set(citing) | set(documented):
        found[url] = {
            "rules": sorted(set(citing.get(url, ()))),
            "docs": list(documented.get(url, {}).get("docs", ())),
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
                "docs": meta["docs"],
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
                    "docs": meta["docs"],
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
            "docs": meta["docs"],
            "retrieved": meta["retrieved"],
        }

    for url in list(stored):
        if url not in entries:
            del stored[url]

    return events, {"schema_version": 1, "sources": stored}


def sync_metadata(entries: dict[str, dict], lock: dict) -> dict:
    """Alinha o lock a watchlist SEM rede: quem cita, quando, e quem saiu.

    Existe porque a watchlist tem duas origens derivadas, e as duas mexem no
    CONJUNTO de URLs: uma regra nova ou uma pagina de knowledge nova mudam o
    lock sem que nada tenha sido conferido. Sem este caminho, alinhar o lock
    exigiria rede -- e num fork sem segredo, ou numa maquina offline, o
    invariante `set(lock) == set(watchlist())` viraria um teste que so passa com
    internet.

    O QUE ELE NUNCA FAZ e inventar `sha256` ou `checked_at`. Fonte nova entra
    SEM hash, e a proxima conferencia com rede a relata como NOVA -- que e a
    verdade: ninguem a leu ainda. Carimbar hash aqui seria dizer "conferida",
    que e a mesma mentira que `unreachable` existe para nao contar.
    """
    stored = dict(lock.get("sources") or {})
    for url, meta in entries.items():
        entry = dict(stored.get(url) or {})
        entry.update(
            {
                "pinned": meta["pinned"],
                "rules": meta["rules"],
                "docs": meta["docs"],
                "retrieved": meta["retrieved"],
            }
        )
        if meta["pinned"]:
            # Fonte fixa nunca e buscada, entao hash e data de conferencia sao
            # campos sem sentido nela -- e o `compare` tambem nao os grava.
            entry.pop("sha256", None)
            entry.pop("checked_at", None)
            entry.pop("last_error", None)
        stored[url] = entry
    for url in list(stored):
        if url not in entries:
            del stored[url]
    return {"schema_version": 1, "sources": stored}


def render_report(events: Iterable[dict], entries: dict[str, dict], today: str) -> str:
    events = list(events)
    moving = [u for u, m in entries.items() if not m["pinned"]]
    pinned = [u for u, m in entries.items() if m["pinned"]]

    lines = [
        "# refresh_knowledge — conferência de fontes",
        "",
        f"Data: {today}",
        f"Fontes vigiadas: {len(entries)} "
        f"({len(moving)} móveis, {len(pinned)} fixas por versão)",
        f"Origem: {sum(1 for m in entries.values() if m['rules'])} citadas por regra, "
        f"{sum(1 for m in entries.values() if m['docs'])} citadas por `knowledge/`",
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
            # As duas linhas sao o VINCULO DE VOLTA, e pelo menos uma sempre
            # existe: a URL entrou na watchlist por alguma das duas origens.
            # Fonte vigiada sem dizer o que reler seria alarme sem endereco.
            if event.get("rules"):
                lines.append(f"- Regras que citam: {', '.join(event['rules'])}")
            if event.get("docs"):
                lines.append(f"- Páginas de `knowledge/` que citam: {', '.join(event['docs'])}")
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
            "ancorada em fonte imutável seja visível, não para revisão.",
            "",
        ]
        lines += [
            f"- {url} — {', '.join(entries[url]['rules'] + entries[url]['docs'])}"
            for url in pinned
        ]
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
        by_rule = sum(1 for m in entries.values() if m["rules"])
        by_doc = sum(1 for m in entries.values() if m["docs"])
        print(f"{len(entries)} fontes ({moving} móveis, {len(entries) - moving} fixas)")
        print(f"origem: {by_rule} citadas por regra, {by_doc} citadas por knowledge/")
        for url, meta in entries.items():
            marker = "fixa " if meta["pinned"] else "movel"
            print(f"  [{marker}] {url} — {', '.join(meta['rules'] + meta['docs'])}")
        if args.update:
            write_lock(sync_metadata(entries, load_lock()))
            print(f"lock sincronizado (sem rede): {LOCK_PATH.relative_to(ROOT)}", file=sys.stderr)
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
