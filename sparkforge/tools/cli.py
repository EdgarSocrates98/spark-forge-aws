"""Interface de linha de comando do ferramental de apoio.

Registrada como `sparkforge-tools` em `[project.scripts]`. Toda saida e JSON no
stdout para que o consumidor seja um programa, nao um humano lendo texto.
"""
import argparse
import json
from pathlib import Path

from .cost import estimate_tokens
from .lineage import extract_lineage_edges
from .offline import OfflineKnowledgeIndex


def main():
    parser = argparse.ArgumentParser(prog="sparkforge-tools")
    sub = parser.add_subparsers(dest="command", required=True)

    off = sub.add_parser("offline")
    off.add_argument("action", choices=["verify", "search"])
    off.add_argument("query", nargs="?")
    off.add_argument("--repo", default=".")
    off.add_argument("--limit", type=int, default=5)

    cost = sub.add_parser("cost")
    cost.add_argument("text")

    lin = sub.add_parser("lineage")
    lin.add_argument("file")

    args = parser.parse_args()
    if args.command == "offline":
        idx = OfflineKnowledgeIndex(args.repo)
        if args.action == "verify":
            result = idx.verify()
        else:
            result = idx.search(args.query or "", args.limit)
    elif args.command == "cost":
        result = {"estimated_tokens": estimate_tokens(args.text), "is_estimate": True}
    else:
        result = extract_lineage_edges(Path(args.file).read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
