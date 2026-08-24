"""Todo modulo importado do pacote esta versionado no git.

POR QUE ESTE ARQUIVO EXISTE: `sparkforge/paths.py` ficou DEZ commits sem entrar
no git. O commit `4240035` acrescentou `from sparkforge.paths import
resolve_within` a `rules/loader.py`, `agents/autonomy.py` e `knowledge_ref.py`,
e nunca fez `git add` do arquivo. Um clone limpo de qualquer commit entre
`4240035` e `263917a` falha ao importar os tres.

E passou por TUDO: dez execucoes da suite completa, ruff, o gate de lastro, uma
revisao de conformidade e uma de qualidade. A razao e que o pacote esta
instalado em modo editavel, entao `sparkforge.paths` resolve para a arvore de
trabalho -- onde o arquivo existe. Nenhum gate deste repositorio olhava para o
que o GIT tem, so para o que o disco tem.

Foi encontrado por acidente, por alguem que conferiu num worktree limpo enquanto
media outra coisa.

Este gate compara as duas visoes. Ele nao substitui o teste de wheel
(`scripts/verify_wheel.py`), que exercita o pacote construido: aquele pega
arquivo que o BUILD nao leva, este pega arquivo que o COMMIT nao leva. Sao
falhas diferentes e o segundo e mais barato de rodar.
"""

from __future__ import annotations

import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def _versionados() -> set[str]:
    saida = subprocess.run(
        ["git", "ls-files", "sparkforge"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    return {linha.strip() for linha in saida.splitlines() if linha.strip().endswith(".py")}


def _no_disco() -> set[str]:
    achados = set()
    for caminho in (RAIZ / "sparkforge").rglob("*.py"):
        if "__pycache__" in caminho.parts:
            continue
        achados.add(caminho.relative_to(RAIZ).as_posix())
    return achados


def test_todo_py_do_pacote_esta_no_git():
    """Arquivo no disco e fora do git quebra clone limpo, e so ele.

    O install editavel esconde isso: o import resolve para a arvore de trabalho,
    entao a suite inteira fica verde enquanto o repositorio publicado nao
    importa.
    """
    faltando = sorted(_no_disco() - _versionados())
    assert faltando == [], (
        "modulo(s) no disco e fora do git -- clone limpo nao importaria: "
        f"{faltando}"
    )


def test_todo_py_versionado_existe_no_disco():
    """O inverso: arquivo apagado sem `git rm` deixa o git com fantasma."""
    fantasmas = sorted(_versionados() - _no_disco())
    assert fantasmas == [], f"versionado(s) sem arquivo no disco: {fantasmas}"
