#!/usr/bin/env python3
"""Gerador determinístico de datasets sintéticos `ForgeGraphView/v1` (spec lf-0020, §0.2).

Produz grafos sintéticos para homologação de escala do `graph ui` — o caso P0
relatado é `sparkforge-aws graph ui` sobre ~3.000 elementos cujos vértices se
espaçam e depois desaparecem. Os fixtures alimentam o harness de reprodução em
`the-forge/scripts/graphphysics_repro.py`, que executa o código de força real
extraído de `theforge/graphstudio.py`.

Determinismo: todo consumo de aleatoriedade passa por `random.Random` com seed
derivada do par (tamanho, topologia) — os nós usam `Random(size)`, então o
mesmo tamanho gera o MESMO conjunto de nós em qualquer topologia; só as arestas
mudam. `generated_at` é um carimbo sintético fixo, nunca o relógio. Reexecutar
o script produz saída byte a byte idêntica.

Uso:
    python tests/graph/make_fixtures.py                 # emite a matriz inteira
    python tests/graph/make_fixtures.py --sizes 3000    # só o tamanho do P0
    python tests/graph/make_fixtures.py --check         # confirma bytes no disco
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

SCHEMA_VIEW = "forge/ForgeGraphView/v1"
SCHEMA_DESCRIPTOR = "forge/GraphDescriptor/v1"
PROVIDER = "synthetic-fixtures"
# Carimbo sintético: um relógio real quebraria o determinismo byte a byte.
GENERATED_AT = "2026-01-01T00:00:00Z"

SIZES = (100, 500, 1000, 3000, 5000, 10000, 25000)
TOPOLOGIES = (
    "chain",
    "star",
    "tree",
    "mesh",
    "dense-communities",
    "disconnected",
    "high-degree-hubs",
    "heterogeneous",
    "isolated-components",
    "parallel-edges",
    "cycles",
    "long-labels",
    "heavy-metadata",
)

# Matriz de cobertura: as 13 topologias no tamanho do P0 (3000) e um conjunto
# representativo de 3 por tamanho nos demais — topologias leves nos tamanhos
# grandes para manter cada arquivo < 15 MB.
COVERAGE: dict[int, tuple[str, ...]] = {
    100: ("chain", "star", "tree"),
    500: ("chain", "mesh", "cycles"),
    1000: ("chain", "tree", "dense-communities"),
    3000: TOPOLOGIES,
    5000: ("mesh", "high-degree-hubs", "heterogeneous"),
    10000: ("chain", "tree", "disconnected"),
    25000: ("chain", "tree", "disconnected"),
}

NODE_KINDS = ("function", "class", "module", "table", "column", "job", "rule", "fact")
EDGE_KINDS = ("imports", "calls", "reads", "writes", "contains", "depends_on")
EPISTEMIC = ("observed", "declared", "inferred", "unknown")


# --- nós ----------------------------------------------------------------------


def _label(base: str, length: int) -> str:
    """Label exatamente com `length` caracteres, de forma determinística."""
    if len(base) >= length:
        return base[:length]
    return base + "-" + "x" * (length - len(base) - 1)


def make_nodes(size: int, topology: str) -> list[dict[str, Any]]:
    """Mesmo conjunto de nós para toda topologia do mesmo `size` (seed = size)."""
    rng = random.Random(size)  # noqa: S311 -- deterministico p/ fixture, nao cripto
    nodes: list[dict[str, Any]] = []
    long_labels = topology == "long-labels"
    heavy = topology == "heavy-metadata"
    for i in range(size):
        kind = NODE_KINDS[i % len(NODE_KINDS)]
        label = f"node-{i}"
        if long_labels:
            label = _label(f"node-{i}-qualified.name.with.long.path.segment", 300)
        attrs: dict[str, Any] = {
            "index": i,
            "group": i % 17,
            "path": f"src/pkg_{i % 41}/mod_{i % 97}.py",
        }
        evidence: list[str] = [f"fact://synthetic/node/{i}"]
        if heavy:
            attrs.update(
                {
                    f"attr_{j}": f"value-{i}-{j}-{rng.randrange(1_000_000)}"
                    for j in range(40)
                }
            )
            attrs["doc"] = _label(f"documentation for node {i}", 500)
            evidence += [f"fact://synthetic/node/{i}/ev/{j}" for j in range(10)]
        nodes.append(
            {
                "id": f"n{i:06d}",
                "kind": kind,
                "label": label,
                "domain": "synthetic",
                "source_provider": PROVIDER,
                "attributes": attrs,
                "epistemic_state": EPISTEMIC[i % len(EPISTEMIC)],
                "evidence_refs": evidence,
                "snapshot_ref": f"snap-{size}",
            }
        )
    return nodes


# --- arestas por topologia ----------------------------------------------------
# Cada builder devolve uma lista de (source_idx, target_idx, kind) com índices
# válidos em [0, size). IDs e contagens verdadeiros são materializados depois.


def _chain(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    return [(i, i + 1, "imports") for i in range(n - 1)]


def _star(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    return [(0, i, "contains") for i in range(1, n)]


def _tree(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    return [((i - 1) // 2, i, "contains") for i in range(1, n)]


def _mesh(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    cols = math.isqrt(n) + 1
    edges: list[tuple[int, int, str]] = []
    for i in range(n):
        if i % cols < cols - 1 and i + 1 < n:
            edges.append((i, i + 1, "imports"))
        if i + cols < n:
            edges.append((i, i + cols, "depends_on"))
    return edges


def _dense_communities(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    communities = max(4, n // 60)
    per = n // communities
    edges: list[tuple[int, int, str]] = []
    for c in range(communities):
        start = c * per
        end = n if c == communities - 1 else start + per
        members = list(range(start, end))
        k = min(6, len(members) - 1)
        for pos, src in enumerate(members):
            for step in range(1, k + 1):
                edges.append((src, members[(pos + step) % len(members)], "calls"))
        if members and c + 1 < communities:
            edges.append((members[0], members[0] + per, "depends_on"))
    return edges


def _disconnected(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    component = 25
    edges: list[tuple[int, int, str]] = []
    for start in range(0, n, component):
        end = min(n, start + component)
        edges.extend((i, i + 1, "imports") for i in range(start, end - 1))
    return edges


def _high_degree_hubs(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    hubs = max(2, n // 100)
    hub_ids = [i * (n // hubs) for i in range(hubs)]
    edges: list[tuple[int, int, str]] = []
    for i in range(n):
        if i in hub_ids:
            continue
        nearest = min(hub_ids, key=lambda h: abs(h - i))
        edges.append((nearest, i, "contains"))
    edges.extend((i, i + 1, "imports") for i in range(n - 1))
    return edges


def _heterogeneous(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    edges: set[tuple[int, int, str]] = set()
    for i in range(n):
        for _ in range(1 + rng.randrange(3)):
            target = rng.randrange(n)
            if target != i:
                edges.add((i, target, EDGE_KINDS[rng.randrange(len(EDGE_KINDS))]))
    return sorted(edges)


def _isolated_components(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    # ~90% singletons sem arestas; o restante em cliques pequenos isolados.
    edges: list[tuple[int, int, str]] = []
    cluster = 8
    active_start = n - n // 10  # último décimo carrega todos os componentes
    for start in range(active_start, n, cluster):
        members = list(range(start, min(n, start + cluster)))
        for a in members:
            for b in members:
                if a < b:
                    edges.append((a, b, "calls"))
    return edges


def _parallel_edges(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    edges = [(i, i + 1, "imports") for i in range(n - 1)]
    for i in range(0, n - 1, 10):
        edges.append((i, i + 1, "calls"))
        edges.append((i, i + 1, "reads"))
        edges.append((i + 1, i, "writes"))
    return edges


def _cycles(n: int, rng: random.Random) -> list[tuple[int, int, str]]:
    edges = [(i, (i + 1) % n, "imports") for i in range(n)]
    edges.extend((i, (i + 7) % n, "calls") for i in range(0, n, 11))
    return edges


_BUILDERS: dict[str, Callable[[int, random.Random], list[tuple[int, int, str]]]] = {
    "chain": _chain,
    "star": _star,
    "tree": _tree,
    "mesh": _mesh,
    "dense-communities": _dense_communities,
    "disconnected": _disconnected,
    "high-degree-hubs": _high_degree_hubs,
    "heterogeneous": _heterogeneous,
    "isolated-components": _isolated_components,
    "parallel-edges": _parallel_edges,
    "cycles": _cycles,
    "long-labels": _chain,  # topologia simples; o eixo sob teste é a label
    "heavy-metadata": _chain,  # idem: o eixo sob teste são os atributos
}


# --- documento ForgeGraphView/v1 ----------------------------------------------


def build_view(size: int, topology: str) -> dict[str, Any]:
    """Monta o documento ForgeGraphView/v1 completo para (size, topology)."""
    if topology not in _BUILDERS:
        raise ValueError(f"unknown topology {topology!r}")
    nodes = make_nodes(size, topology)
    rng = random.Random(f"{size}:{topology}")  # noqa: S311 -- idem
    triples = _BUILDERS[topology](size, rng)
    edges = [
        {
            "id": f"e{seq:07d}",
            "source": nodes[src]["id"],
            "target": nodes[tgt]["id"],
            "kind": kind,
            "direction": "directed",
            "provenance": "synthetic",
            "epistemic_state": "observed",
            "evidence_refs": [f"fact://synthetic/edge/{seq}"],
            "confidence": 1.0,
            "temporal": {},
            "attributes": {"index": seq},
        }
        for seq, (src, tgt, kind) in enumerate(triples)
    ]
    kinds = sorted({n["kind"] for n in nodes})
    return {
        "schema": SCHEMA_VIEW,
        "descriptor": {
            "graph_id": f"synthetic/{size}-{topology}",
            "provider_id": PROVIDER,
            "domain": "synthetic",
            "graph_schema": SCHEMA_DESCRIPTOR,
            "snapshot_id": f"snap-{size}-{topology}",
            "generated_at": GENERATED_AT,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "available_layers": kinds,
            "available_queries": [],
            "capabilities": ["node_inspect", "edge_inspect", "neighbors", "search"],
            "limitations": [
                "synthetic fixture — deterministic generator",
                f"seed={size}:{topology}",
            ],
        },
        "nodes": nodes,
        "edges": edges,
    }


def render(view: dict[str, Any]) -> bytes:
    """Serialização estável e compacta (< 15 MB até 25k nós).

    Sem indentação de propósito: fixtures são dados para o harness, não
    prosa — `jq` resolve a leitura quando alguém abre um arquivo.
    """
    text = json.dumps(view, ensure_ascii=False, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


def fixture_name(size: int, topology: str) -> str:
    return f"graph_{size}_{topology}.json"


def emit(
    out_dir: Path, sizes: tuple[int, ...], topologies: tuple[str, ...]
) -> list[tuple[str, int, int, int]]:
    """Gera a matriz; devolve linhas (arquivo, nós, arestas, bytes) p/ o relatório."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, int, int, int]] = []
    for size in sizes:
        wanted = COVERAGE.get(size, TOPOLOGIES[:3])
        for topology in wanted:
            if topologies and topology not in topologies:
                continue
            view = build_view(size, topology)
            blob = render(view)
            (out_dir / fixture_name(size, topology)).write_bytes(blob)
            rows.append(
                (
                    fixture_name(size, topology),
                    view["descriptor"]["node_count"],
                    view["descriptor"]["edge_count"],
                    len(blob),
                )
            )
    return rows


def check(out_dir: Path) -> list[str]:
    """Regenera em memória e compara bytes com o disco; devolve divergências."""
    diffs: list[str] = []
    for size, tops in COVERAGE.items():
        for topology in tops:
            path = out_dir / fixture_name(size, topology)
            fresh = render(build_view(size, topology))
            if not path.is_file():
                diffs.append(f"{path.name}: missing")
            elif path.read_bytes() != fresh:
                diffs.append(f"{path.name}: bytes diverge")
    return diffs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=FIXTURES_DIR)
    parser.add_argument("--sizes", type=int, nargs="*", default=None)
    parser.add_argument("--topologies", type=str, nargs="*", default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenera em memória e compara byte a byte com o disco",
    )
    args = parser.parse_args(argv)

    if args.check:
        diffs = check(args.out)
        if diffs:
            print("DIVERGENT fixtures:")
            print("\n".join(f"  {d}" for d in diffs))
            return 1
        print("all fixtures byte-identical to a fresh regeneration")
        return 0

    sizes = tuple(args.sizes) if args.sizes else SIZES
    topologies = tuple(args.topologies) if args.topologies else ()
    rows = emit(args.out, sizes, topologies)
    print(f"{'file':<46} {'nodes':>7} {'edges':>8} {'bytes':>12}")
    total = 0
    for name, ncount, ecount, nbytes in rows:
        total += nbytes
        print(f"{name:<46} {ncount:>7} {ecount:>8} {nbytes:>12,}")
    print(f"{'TOTAL':<46} {'':>7} {'':>8} {total:>12,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
