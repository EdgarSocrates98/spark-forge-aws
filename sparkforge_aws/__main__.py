"""``python -m sparkforge_aws`` — equivalente ao console script (§9.3 PATH-independence)."""

from sparkforge_aws.adapters.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
