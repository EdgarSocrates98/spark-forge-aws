"""Gate da garantia offline: todo documento do manifest existe e confere.

Roda no CI. `--check` e aceito e ignorado de proposito -- o script nao tem outro
modo, e a flag existe porque `docs/operations-guide.md` documenta a invocacao
com ela junto dos demais gates. Recusar o argumento faria a linha documentada
falhar por parsing, e nao por integridade.
"""
import argparse
import json

from sparkforge.tools import OfflineKnowledgeIndex


def main() -> int:
    parser = argparse.ArgumentParser(prog="verify_offline_bundle")
    parser.add_argument("--check", action="store_true", help="aceito por compatibilidade")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    result = OfflineKnowledgeIndex(args.repo).verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
