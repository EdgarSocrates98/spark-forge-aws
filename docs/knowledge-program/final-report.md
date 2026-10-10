# Forge Knowledge Program — final report

| Campo | Valor |
|---|---|
| repository | `spark-forge-aws` |
| branch | `feat/knowledge-experience` |
| commit | `acc497c0` |
| docs inventoried | 2074 (excl. GENERATED mirrors: 1262; vendored upstream: 68) |

## Review levels (honest)

- `INVENTORIED`: 0
- `AUTOMATICALLY_CHECKED`: 2074
- `TECHNICALLY_VERIFIED`: 0
- `SEMANTICALLY_REVIEWED`: 0
- `USER_JOURNEY_VALIDATED`: 0

Automatic checks ran on every row; semantic review is recorded only where a human/verified pass happened — nothing is inflated.

## Category counts

- `GENERATED`: 812
- `SDD_ARTIFACT`: 594
- `UNKNOWN`: 252
- `REFERENCE`: 150
- `INTERNAL`: 69
- `SKILL`: 63
- `CONCEPT`: 40
- `USER_GUIDE`: 37
- `HOW_TO`: 23
- `ADR`: 13
- `ARCHITECTURE`: 6
- `CONTRACT`: 4
- `GETTING_STARTED`: 4
- `AGENT_INSTRUCTIONS`: 3
- `TEST_EVIDENCE`: 2
- `TUTORIAL`: 1
- `RELEASE_REPORT`: 1

## Findings

- duplicate groups (non-generated): 0
- broken internal links total: 10 (active docs: 0; remainder in frozen/historical trees)
- documented-but-missing commands: 3 (active docs: 0)
- undocumented public commands: 0

## Educational layer delivered

- first-run/quickstart docs: 3
- docs/learn/ entries: 4
- docs/hub/ entries: 0

## Documentation changes this program

- `docs/INDEX.md` — generated canonical index (7-section IA)
- `docs/learn/` — learning track + problem-oriented recipes
- `docs/knowledge-program/` — inventory + 8 reports + context map

## Tests / gates

- `tests/test_doc_manifest.py` — zero broken links in active docs (frozen trees exempt)
- `check_docs`/`doc_inventory` — command drift gate, parser-walked

## Limitations & remaining gaps

- Semantic review of the full corpus is not claimed — review levels in `inventory.jsonl` say which docs were actually reviewed.
- Historical/frozen trees keep their broken links by design (§4.5 preservation) — they are reported, not repaired.
- Hub site build not executed (dev-only, `mkdocs-material`); the markdown hub is the verified deliverable.
- Screen-reader and POSIX-terminal validation remain UNVERIFIED on this host.

## Final status: **PASS**
