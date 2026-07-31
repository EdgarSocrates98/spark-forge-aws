"""Testes de `scripts/refresh_knowledge.py`.

Nenhum toca a rede: `compare()` recebe o fetch como parametro exatamente para
isto. Um mecanismo de frescor que so pode ser testado com rede nao e testado
em CI, e um mecanismo de frescor que nao roda em CI apodrece igual ao
conhecimento que ele deveria vigiar.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.refresh_knowledge import (  # noqa: E402
    FetchFailed,
    compare,
    digest,
    is_pinned,
    normalize,
    render_report,
    watchlist,
)

TODAY = "2026-07-31"


def entry(pinned=False, rules=("SF-X-001",), retrieved=("2026-07-29",)):
    return {"pinned": pinned, "rules": list(rules), "retrieved": list(retrieved)}


class TestPinnedClassification:
    """Vigiar URL imutavel so produz ruido; deixar de vigiar URL movel deixa a
    regra citar um alvo que se moveu."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://spark.apache.org/docs/3.5.6/sql-performance-tuning.html",
            "https://github.com/apache/iceberg/blob/apache-iceberg-1.0.0/format/spec.md",
            "https://example.org/docs/2.13/guide.html",
        ],
    )
    def test_version_in_path_is_pinned(self, url):
        assert is_pinned(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://spark.apache.org/docs/latest/sql-performance-tuning.html",
            "https://docs.aws.amazon.com/glue/latest/dg/worker-types.html",
            "https://iceberg.apache.org/docs/latest/spark-procedures/",
        ],
    )
    def test_latest_is_never_pinned(self, url):
        assert is_pinned(url) is False

    def test_latest_wins_over_a_version_looking_segment(self):
        """`/latest/` decide sozinho: uma URL com `latest` E um numero no path
        continua movel, porque o `latest` e quem manda no conteudo."""
        assert is_pinned("https://x.dev/docs/latest/api/1.2/page.html") is False


class TestNormalize:
    def test_strips_tags_and_collapses_whitespace(self):
        assert normalize("<p>a</p>\n\n  <b>b</b>") == "a b"

    def test_drops_script_and_style_bodies(self):
        html = "<style>.a{color:red}</style><p>texto</p><script>var x=1</script>"
        assert normalize(html) == "texto"

    def test_drops_comments(self):
        assert normalize("<p>a</p><!-- build 12345 --><p>b</p>") == "a b"

    def test_hash_is_stable_across_cosmetic_differences(self):
        """O alarme falso permanente e o modo de falha que mata a ferramenta:
        se cada leitura da mesma pagina mudar o hash, o relatorio grita sempre e
        o operador para de ler."""
        a = "<html><body><p>Default: 10485760</p><script>nonce='aaa'</script></body></html>"
        b = (
            "<html>\n  <body>\n    <p>Default:   10485760</p>\n"
            "<script>nonce='zzz'</script>\n</body></html>"
        )
        assert digest(a) == digest(b)

    def test_hash_changes_when_the_visible_text_changes(self):
        a = "<p>Default: 10485760</p>"
        b = "<p>Default: 20971520</p>"
        assert digest(a) != digest(b)


class TestCompare:
    def test_first_sight_is_reported_as_new(self):
        entries = {"https://x.dev/latest/a": entry()}
        events, lock = compare(entries, {"sources": {}}, lambda url: "<p>a</p>", TODAY)
        assert [e["kind"] for e in events] == ["new"]
        assert lock["sources"]["https://x.dev/latest/a"]["sha256"] == digest("<p>a</p>")

    def test_unchanged_content_produces_no_event(self):
        url = "https://x.dev/latest/a"
        lock = {"sources": {url: {"sha256": digest("<p>a</p>"), "pinned": False}}}
        events, _ = compare({url: entry()}, lock, lambda u: "<p>a</p>", TODAY)
        assert events == []

    def test_changed_content_reports_the_citing_rules(self):
        url = "https://x.dev/latest/a"
        lock = {"sources": {url: {"sha256": digest("<p>antigo</p>"), "pinned": False}}}
        events, _ = compare(
            {url: entry(rules=("SF-A-001", "SF-B-002"))}, lock, lambda u: "<p>novo</p>", TODAY
        )
        assert len(events) == 1
        assert events[0]["kind"] == "changed"
        assert events[0]["rules"] == ["SF-A-001", "SF-B-002"]

    def test_pinned_urls_are_never_fetched(self):
        def explode(url):
            raise AssertionError(f"nao devia buscar fonte fixa: {url}")

        entries = {"https://x.dev/docs/1.2.3/a": entry(pinned=True)}
        events, lock = compare(entries, {"sources": {}}, explode, TODAY)
        assert events == []
        assert lock["sources"]["https://x.dev/docs/1.2.3/a"]["pinned"] is True

    def test_unreachable_is_an_event_and_never_stamps_a_fresh_check(self):
        """404 nao pode virar "conferida hoje, igual".

        Preservar o hash antigo e carimbar a data diria que a fonte foi
        conferida e esta igual -- quando a doc pode ter sido movida justamente
        porque mudou. O hash antigo fica (e a ultima verdade conhecida), mas
        `checked_at` nao avanca e o erro fica registrado.
        """
        url = "https://x.dev/latest/some"
        previous = {"sha256": "abc", "checked_at": "2026-01-01", "pinned": False}

        def fails(_url):
            raise FetchFailed("https://x.dev/latest/some: HTTP Error 404")

        events, lock = compare({url: entry()}, {"sources": {url: previous}}, fails, TODAY)
        assert [e["kind"] for e in events] == ["unreachable"]
        stored = lock["sources"][url]
        assert stored["sha256"] == "abc"
        assert stored["checked_at"] == "2026-01-01"
        assert "404" in stored["last_error"]

    def test_url_no_longer_cited_is_dropped_from_the_lock(self):
        """Regra removida leva a fonte junto; lock nao acumula fantasma."""
        lock = {"sources": {"https://x.dev/latest/velha": {"sha256": "abc", "pinned": False}}}
        _, new_lock = compare({}, lock, lambda u: "", TODAY)
        assert new_lock["sources"] == {}


class TestReport:
    def test_clean_run_says_nothing_to_review(self):
        text = render_report([], {"https://x.dev/latest/a": entry()}, TODAY)
        assert "Nenhuma fonte móvel mudou" in text

    def test_changed_source_lists_the_rules_to_reread(self):
        events = [
            {"kind": "changed", "url": "https://x.dev/latest/a", **entry(rules=("SF-A-001",))}
        ]
        text = render_report(events, {"https://x.dev/latest/a": entry()}, TODAY)
        assert "MUDOU" in text
        assert "SF-A-001" in text

    def test_pinned_sources_are_listed_but_not_as_review_items(self):
        entries = {"https://x.dev/docs/1.2.3/a": entry(pinned=True, rules=("SF-P-001",))}
        text = render_report([], entries, TODAY)
        assert "fixas por versão" in text
        assert "SF-P-001" in text


class TestWatchlistComesFromTheCatalog:
    """A watchlist nao e mantida a mao: regra nova com fonte nova entra
    sozinha. Lista paralela e o passo que alguem esquece."""

    def test_every_url_in_the_catalog_is_watched(self):
        from sparkforge.rules.loader import load_catalog

        expected = {
            source["url"]
            for rule in load_catalog()
            for source in (rule.get("sources") or [])
            if source.get("url")
        }
        assert set(watchlist()) == expected

    def test_each_entry_names_the_rules_that_cite_it(self):
        for url, meta in watchlist().items():
            assert meta["rules"], url
            assert meta["rules"] == sorted(set(meta["rules"])), url

    def test_the_committed_lock_matches_the_catalog(self):
        """O lock commitado nao pode citar fonte que o catalogo nao cita mais,
        nem faltar fonte que ele passou a citar. Sem isto, o lock envelhece em
        silencio e o primeiro `--check` depois de meses relata "novas" que na
        verdade nunca foram vigiadas."""
        lock_path = ROOT / "knowledge" / "sources.lock.json"
        if not lock_path.is_file():
            pytest.skip("lock ainda nao gerado")
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        assert set(lock["sources"]) == set(watchlist())
