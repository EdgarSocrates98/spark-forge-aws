#!/usr/bin/env python3
"""Vendoriza o ecossistema caveman para dentro de vendor/, com pin e gate.

Fonte da verdade: `vendor/PINS.json` (repo + sha + lista `keep` + patches).
Espelho gerado: `vendor/<dest>/...` e `vendor/MANIFEST.sha256`.

Uso:
    python scripts/vendor_caveman.py            # reclona nos SHAs pinados e regrava vendor/
    python scripts/vendor_caveman.py --check    # falha (exit 1) se a arvore divergir do manifest

O modo `--check` NAO toca a rede: ele compara o que esta em disco contra
`vendor/MANIFEST.sha256`. E o que roda em `tests/test_vendor_caveman.py` e no
CI. Reclonar exige rede e so acontece no modo default, que e manual.

Por que um manifest de sha256 e nao "confie no git": os arquivos vendorizados
sao codigo de terceiro que executa como hook em toda sessao de todo mundo que
clonar este repositorio. Um manifest torna qualquer edicao local visivel como
divergencia. Sem isso, "vendorizado" viraria "copiado uma vez e esquecido".

O que o manifest NAO faz, e a distincao importa: ele nao prova que os bytes em
disco sao os do SHA upstream. Ele e regravado por `write_manifest()` a partir do
que esta em disco e e commitado no mesmo tree, entao quem edita um arquivo
vendorizado E a linha correspondente do manifest passa no gate. O gate pega
divergencia acidental e edicao que esqueceu o manifest; contra um commit
deliberado, o controle e a revisao do diff, nao este arquivo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"
PINS = VENDOR / "PINS.json"
MANIFEST = VENDOR / "MANIFEST.sha256"

# Arquivos que sao NOSSOS dentro de vendor/ e por isso ficam fora do manifest
# do que veio de upstream.
OURS = frozenset({"PINS.json", "MANIFEST.sha256", "CREDITS.md", ".claude-plugin/marketplace.json"})


def load_pins() -> dict:
    return json.loads(PINS.read_text(encoding="utf-8"))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def iter_vendored_files() -> list[Path]:
    """Todo arquivo sob vendor/ que veio de upstream, em ordem estavel.

    Caminho relativo em POSIX para que o manifest seja o mesmo nos dois SOs.
    """
    if not VENDOR.exists():
        return []
    out = []
    for path in VENDOR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(VENDOR).as_posix()
        if rel in OURS:
            continue
        out.append(path)
    return sorted(out, key=lambda p: p.relative_to(VENDOR).as_posix())


def expected_manifest() -> dict[str, str]:
    if not MANIFEST.exists():
        return {}
    entries: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        entries[rel] = digest
    return entries


def actual_manifest() -> dict[str, str]:
    return {p.relative_to(VENDOR).as_posix(): sha256_of(p) for p in iter_vendored_files()}


def write_manifest(entries: dict[str, str], pins: dict) -> None:
    header = [
        "# Gerado por scripts/vendor_caveman.py -- nao editar a mao.",
        "# Cada linha e sha256 do arquivo vendorizado, exatamente como veio do SHA pinado",
        "# em vendor/PINS.json (mais os patches declarados la).",
    ]
    for entry in pins["vendored"]:
        header.append(f"# {entry['dest']}: {entry['repo']} @ {entry['sha']}")
    body = [f"{digest}  {rel}" for rel, digest in sorted(entries.items())]
    MANIFEST.write_text("\n".join(header + body) + "\n", encoding="utf-8")


def check() -> list[str]:
    """Divergencias entre a arvore em disco e o manifest. Lista vazia = OK."""
    problems: list[str] = []
    expected = expected_manifest()
    actual = actual_manifest()
    if not expected:
        return [f"AUSENTE {MANIFEST}"]
    for rel in sorted(set(expected) - set(actual)):
        problems.append(f"AUSENTE vendor/{rel}")
    for rel in sorted(set(actual) - set(expected)):
        problems.append(f"NAO DECLARADO vendor/{rel}")
    for rel in sorted(set(expected) & set(actual)):
        if expected[rel] != actual[rel]:
            problems.append(f"DIVERGENTE vendor/{rel}")
    return problems


def _run(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)  # noqa: S603


# `PINS.json` e config revisada, nao entrada de usuario -- e mesmo assim todo
# valor dele que vira CAMINHO passa por aqui antes de tocar o disco.
#
# A razao e o modo de falha, nao a origem do dado. `Path("vendor") / "/etc/x"`
# devolve `/etc/x`: o operador `/` do pathlib DESCARTA o lado esquerdo quando o
# direito e absoluto, e `..` nunca e normalizado. Um `to` de `../../.claude/
# settings.json` num PR de "bump de pin" escreveria fora de `vendor/` --
# e o `MANIFEST.sha256` nao veria, porque `actual_manifest()` so varre
# `VENDOR.rglob`. Arquivo escrito fora do vendor e invisivel para o unico gate
# que este script existe para sustentar.
#
# Mesma guarda que `install_skills.py::install_dest` e
# `verify_wheel.py::_artifact_dest` ja aplicam. Nao ter isto aqui era
# inconsistencia, nao decisao.
def _confinado(root: Path, valor: str, *, campo: str, entrada: str) -> Path:
    problema = None
    if not valor or not valor.strip():
        problema = "vazio"
    elif "\\" in valor:
        problema = "contem separador do Windows"
    elif PurePosixPath(valor).is_absolute() or PureWindowsPath(valor).is_absolute():
        problema = "e absoluto"
    elif ".." in PurePosixPath(valor).parts:
        problema = "contem `..`"
    if problema is None:
        alvo = root / valor
        if not alvo.resolve().is_relative_to(root.resolve()):
            problema = "resolve para fora do diretorio de destino"
        else:
            return alvo
    raise SystemExit(f"{entrada}: `{campo}` = {valor!r} {problema}. Recusado.")


# `repo` e `sha` vao para o argv do git. A validacao ja existia em
# `tests/test_vendor_caveman.py`, e teste nao protege quem roda o script antes
# da suite -- o valor e consumido aqui, entao a guarda mora aqui tambem.
REPO_PERMITIDO = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+$")
SHA_PERMITIDO = re.compile(r"^[0-9a-f]{40}$")


def clone_at(repo: str, sha: str, dest: Path) -> None:
    """Clona `repo` e faz checkout exato de `sha` em `dest`.

    `fetch --depth 1 <sha>` em vez de `clone --depth 1` porque um clone raso
    traz so a ponta do branch default -- e um pin so vale se buscar o commit
    pinado direto, mesmo que ele nao seja mais a ponta.

    `-c protocol.ext.allow=never` e redundante com o default do git desde
    v2.12, e fica explicito porque o custo e zero e o efeito de perde-lo seria
    uma URL `ext::<comando>` virar execucao.
    """
    if not REPO_PERMITIDO.match(repo):
        raise SystemExit(f"repo recusado: {repo!r}")
    if not SHA_PERMITIDO.match(sha):
        raise SystemExit(f"sha recusado: {sha!r}")
    git = ["git", "-c", "protocol.ext.allow=never"]
    dest.mkdir(parents=True, exist_ok=True)
    _run([*git, "init", "--quiet"], cwd=dest)
    _run([*git, "remote", "add", "origin", "--", repo], cwd=dest)
    _run([*git, "fetch", "--quiet", "--depth", "1", "--", "origin", sha], cwd=dest)
    _run([*git, "checkout", "--quiet", "FETCH_HEAD"], cwd=dest)


def materialize(entry: dict, src: Path, dest: Path) -> None:
    nome = entry["name"]
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in entry["keep"]:
        origin = _confinado(src, name, campo="keep", entrada=nome)
        if not origin.exists():
            raise SystemExit(
                f"{nome}: `keep` cita {name}, que nao existe em {entry['sha']}"
            )
        target = _confinado(dest, name, campo="keep", entrada=nome)
        target.parent.mkdir(parents=True, exist_ok=True)
        if origin.is_dir():
            shutil.copytree(origin, target)
        else:
            shutil.copy2(origin, target)
    for patch in entry.get("patches", []):
        origin = _confinado(src, patch["copy"], campo="patches[].copy", entrada=nome)
        if not origin.exists():
            raise SystemExit(
                f"{nome}: patch cita {patch['copy']}, ausente em {entry['sha']}"
            )
        target = _confinado(dest, patch["to"], campo="patches[].to", entrada=nome)
        if target.exists():
            shutil.rmtree(target) if target.is_dir() else target.unlink()
        target.parent.mkdir(parents=True, exist_ok=True)
        if origin.is_dir():
            shutil.copytree(origin, target)
        else:
            shutil.copy2(origin, target)


def sync() -> None:
    pins = load_pins()
    with tempfile.TemporaryDirectory() as tmp:
        for entry in pins["vendored"]:
            src = Path(tmp) / entry["name"]
            dest = _confinado(VENDOR, entry["dest"], campo="dest", entrada=entry["name"])
            print(f"clonando {entry['repo']} @ {entry['sha'][:12]}")
            clone_at(entry["repo"], entry["sha"], src)
            materialize(entry, src, dest)
            print(f"  -> vendor/{entry['dest']}")
    write_manifest(actual_manifest(), pins)
    print(f"manifest: {len(expected_manifest())} arquivos")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="so verifica a arvore contra vendor/MANIFEST.sha256; nao usa rede",
    )
    args = parser.parse_args()

    if args.check:
        problems = check()
        for problem in problems:
            print(problem)
        if problems:
            print(f"\n{len(problems)} divergencia(s). Rode: python scripts/vendor_caveman.py")
            return 1
        print(f"vendor/ OK -- {len(expected_manifest())} arquivos conferem com o manifest")
        return 0

    sync()
    return 0


if __name__ == "__main__":
    sys.exit(main())
