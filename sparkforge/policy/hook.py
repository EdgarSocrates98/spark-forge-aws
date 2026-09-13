"""Hook `PreToolUse` do Claude Code: `python -m sparkforge.policy.hook`.

Contrato conferido na documentacao oficial (2026-09-13): o stdin traz
`tool_name`, `tool_input` e `cwd`; exit 2 BLOQUEIA a chamada e o stderr vira o
motivo; exit 0 sem saida segue o fluxo normal de permissao. O `PreToolUse` NAO
decide `ask` -- o `ask` da policy mora em `permissions.ask`, gerado por
`sparkforge policy sync-settings`. Aqui so `deny` bloqueia.

Falha: policy invalida sai 2 (quem a escreveu acredita que ela morde); stdin
ilegivel sai 2 (nao ha como decidir). Se o `sparkforge` nem importar, o Python
sai 1, que o Claude Code trata como erro nao-bloqueante -- um clone sem
instalacao nao trava o Bash.
"""
from __future__ import annotations

import json
import os
import sys


def main(stdin: str | None = None) -> int:
    from sparkforge.policy.decide import DENY, decidir_entrada
    from sparkforge.policy.load import PolicyError, carregar, raiz_do_projeto

    try:
        entrada = json.loads(sys.stdin.read() if stdin is None else stdin)
    except json.JSONDecodeError as exc:
        print(f"sparkforge policy: stdin do hook ilegivel: {exc}", file=sys.stderr)
        return 2
    if not isinstance(entrada, dict):
        print("sparkforge policy: stdin do hook nao e um objeto JSON", file=sys.stderr)
        return 2
    try:
        raiz = raiz_do_projeto(os.environ.get("CLAUDE_PROJECT_DIR") or entrada.get("cwd") or ".")
        politica = carregar(raiz)
    except PolicyError as exc:
        print(f"sparkforge policy invalida, nada roda ate corrigir: {exc}", file=sys.stderr)
        return 2
    if politica is None:
        return 0
    decisao = decidir_entrada(entrada, politica, raiz)
    if decisao.decision == DENY:
        print(
            f"bloqueado pela policy do repositorio ({decisao.rule}): "
            f"{decisao.reason or 'sem motivo declarado'}. Consulte: "
            f"sparkforge policy explain",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
