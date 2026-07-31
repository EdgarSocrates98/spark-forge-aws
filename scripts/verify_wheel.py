#!/usr/bin/env python3
"""Gate do artefato: o pacote instalado reproduz os goldens byte a byte?

Constroi sdist e wheel, instala o wheel num venv limpo, e roda os modulos de
golden ja existentes SOB O PYTHON DO VENV. Se o pacote instalado produz os
mesmos facts e findings que o repositorio, o canal pip esta em paridade.

Por que reaproveitar os modulos de golden em vez de reimplementar a comparacao:
as 74 fixtures ja sao o contrato, verificado no CI a cada commit. Um comparador
proprio seria um segundo contrato para manter divergir do primeiro -- e o
primeiro a divergir seria o novo, porque ninguem o le.

A guarda que sustenta tudo esta em `tests/test_installed_provenance.py`, ligada
aqui por `SPARKFORGE_VERIFY_INSTALLED=1`. Sem ela, um `sys.path` errado faria o
pytest importar o repositorio e comparar o codigo-fonte consigo mesmo.

Uso:
    python scripts/verify_wheel.py                # constroi, instala e verifica
    python scripts/verify_wheel.py --keep         # nao apaga o diretorio temporario
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GOLDEN_MODULES = sorted(p.name for p in (ROOT / "tests").glob("test_fixtures_golden*.py"))
PROVENANCE_MODULE = "test_installed_provenance.py"


def venv_python(venv: Path) -> Path:
    """Interpretador do venv, nos dois layouts."""
    windows = venv / "Scripts" / "python.exe"
    return windows if windows.exists() else venv / "bin" / "python"


def pytest_command(python: Path, root: Path) -> list[str]:
    """Comando do gate.

    `-o pythonpath=` sobrescreve o `pythonpath = ["."]` do pyproject. Sem isso o
    repositorio entra no sys.path e vence o site-packages -- e o gate passaria
    comparando o repo consigo mesmo.

    A procedencia vem PRIMEIRO: se o import veio do lugar errado, comparar
    golden nao significa nada.
    """
    modules = [str(root / "tests" / PROVENANCE_MODULE)]
    modules += [str(root / "tests" / name) for name in GOLDEN_MODULES]
    return [str(python), "-m", "pytest", "-q", "-o", "pythonpath=", *modules]


def _reproduce_line(command: list, cwd: str | None, env: dict[str, str] | None) -> str:
    """Monta uma linha copiavel que reproduz esta chamada a mao.

    So o argv nao bastava: um revisor copiou o comando `pytest` impresso numa
    corrida com `--keep`, rodou do repositorio (sem o `cwd` do gate) e obteve
    "90 passed, 5 skipped" -- os 5 testes de procedencia pulados em silencio
    porque `SPARKFORGE_VERIFY_INSTALLED` nao estava setado. Reproduziu OUTRA
    chamada, nao a que falhou.

    Formato `cd <dir> && VAR=val cmd`: dialeto POSIX (bash/Git Bash), o mesmo
    que os exemplos deste repositorio (heredocs, CLAUDE.md) ja assumem.
    cmd.exe e PowerShell usam sintaxe diferente (`set`/`$env:`) -- quem estiver
    nesses shells adapta a mao, mas o conteudo que faltava era o `cwd` e QUAIS
    variaveis mudaram em relacao ao ambiente herdado, nao a sintaxe exata de
    um shell especifico. Variaveis REMOVIDAS (`env.pop` no chamador) tambem
    entram, como `unset` -- reproduzir sem tirar `SPARKFORGE_CATALOG` do
    ambiente e reproduzir um gate que pode passar escondendo o defeito que
    ele existe para pegar (ver comentario no chamador).
    """
    parts = []
    if cwd is not None:
        parts.append(f"cd {cwd} &&")
    if env is not None:
        removed = sorted(set(os.environ) - set(env))
        if removed:
            parts.append("unset " + " ".join(removed) + " &&")
        changed = {k: v for k, v in sorted(env.items()) if os.environ.get(k) != v}
        parts.extend(f"{k}={v}" for k, v in changed.items())
    parts.append(" ".join(str(c) for c in command))
    return " ".join(parts)


def _run(
    command: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Roda um subprocesso e imprime uma linha que reproduz a chamada a mao.

    `cwd` e `env` sao parametros explicitos (nao **kwargs) precisamente para
    que esta funcao possa inclui-los na linha impressa -- ver `_reproduce_line`.
    """
    print(f"$ {_reproduce_line(command, cwd, env)}", flush=True)
    return subprocess.run(command, check=False, cwd=cwd, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--keep", action="store_true", help="Nao apaga o diretorio temporario.")
    args = parser.parse_args(argv)

    # Guarda de corpus, DENTRO do gate -- nao basta o teste da suite
    # (`tests/test_verify_wheel.py::test_there_is_more_than_one`). Aquele
    # teste roda sob o pytest do REPOSITORIO, nunca dentro desta execucao: se
    # `tests/test_fixtures_golden*.py` for renomeado ou apagado do disco,
    # `GOLDEN_MODULES` vira `[]` aqui, `pytest_command()` devolve so o modulo
    # de procedencia, ele passa (nada para comparar), e o gate imprimiria
    # "OK: em paridade com os goldens" tendo verificado ZERO das 539
    # assercoes de golden. Um gate que so prova a si mesmo -- sem numero
    # minimo exigido DENTRO da propria execucao -- e o antipadrao que este
    # repositorio existe para evitar (a razao de reusar os goldens em vez de
    # reimplementar a comparacao, ver docstring do modulo).
    if len(GOLDEN_MODULES) < 15:
        print(
            f"GOLDEN_MODULES tem {len(GOLDEN_MODULES)} modulos, esperava >=15 -- "
            f"corpus renomeado ou apagado?",
            file=sys.stderr,
        )
        return 1

    workdir = Path(tempfile.mkdtemp(prefix="sparkforge-gate-"))
    dist = workdir / "dist"
    venv = workdir / "venv"

    try:
        if _run([sys.executable, "-m", "build", "--outdir", str(dist), str(ROOT)]).returncode:
            print("build falhou", file=sys.stderr)
            return 1

        wheels = sorted(dist.glob("*.whl"))
        sdists = sorted(dist.glob("*.tar.gz"))
        if not wheels or not sdists:
            # `dist.iterdir()` cru lançaria FileNotFoundError se `--outdir` nunca
            # tivesse sido criado (build retornou 0 sem produzir nada, caso raro
            # mas possivel) -- trocaria a mensagem limpa por um traceback. `[]`
            # quando o diretorio nao existe mantem a mensagem legivel nesse caso.
            found = sorted(p.name for p in dist.iterdir()) if dist.exists() else []
            print(f"esperava wheel e sdist em {dist}, achei {found}", file=sys.stderr)
            return 1

        if _run([sys.executable, "-m", "venv", str(venv)]).returncode:
            return 1

        python = venv_python(venv)
        install = [str(python), "-m", "pip", "install", "--quiet", str(wheels[0]), "pytest"]
        if _run(install).returncode:
            return 1

        # `cwd` fora do repositorio e a primeira guarda; a assercao de
        # procedencia e a que sustenta. As duas, porque configuracao se perde.
        env = dict(os.environ)
        env["SPARKFORGE_VERIFY_INSTALLED"] = "1"
        env["PYTHONSAFEPATH"] = "1"
        # Remover SPARKFORGE_CATALOG/SPARKFORGE_KNOWLEDGE nao e limpeza de
        # ambiente -- e a segunda metade da guarda de procedencia. `.mcp.json`
        # deste repositorio seta as duas, entao um shell de dev que rode este
        # gate plausivelmente as herda apontando para `rules/catalog` e
        # `knowledge` DENTRO do checkout: validos, completos, e nada a ver com
        # o que o wheel empacotou. Se o `force-include` do wheel estivesse
        # quebrado -- como esteve ate o commit imediatamente anterior a este
        # gate, quando o sdist relocava `knowledge` antes do wheel conseguir
        # encontra-lo -- `load_catalog()`/`knowledge_dir()` teriam sucesso
        # mesmo assim, so que pelo OVERRIDE herdado do ambiente: os goldens
        # comparariam o pacote instalado contra o catalogo do REPOSITORIO, nao
        # contra o que veio dentro do wheel, e o gate passaria escondendo
        # exatamente o defeito que ele existe para pegar. Remover as duas
        # variaveis fecha esse buraco: o codigo instalado so pode enxergar o
        # que veio dentro do artefato.
        env.pop("SPARKFORGE_CATALOG", None)
        env.pop("SPARKFORGE_KNOWLEDGE", None)

        result = _run(pytest_command(python, ROOT), cwd=str(workdir), env=env)
        if result.returncode:
            print("gate de paridade REPROVOU", file=sys.stderr)
            return 1

        if _run([str(python), "-m", "pip", "install", "--quiet", "twine"]).returncode:
            return 1
        if _run([str(python), "-m", "twine", "check", str(wheels[0]), str(sdists[0])]).returncode:
            print("twine check reprovou", file=sys.stderr)
            return 1

        print(f"\nOK: {wheels[0].name} e {sdists[0].name} em paridade com os goldens.")
        return 0
    finally:
        if args.keep:
            print(f"artefatos preservados em {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
