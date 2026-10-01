#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def install_dest(base: Path, relative: Path | str) -> Path:
    """Monta o destino de uma copia, sempre RELATIVO ao diretorio de instalacao.

    `main` valida `--target` uma vez e entra nele com `chdir`. Dai em diante
    nenhum caminho derivado da linha de comando alcanca `shutil.copy2`: o
    destino e montado so a partir de nomes literais e de nomes varridos da
    arvore do proprio repositorio, e resolvido pelo processo contra o cwd.

    Duas guardas, porque escapar da arvore tem dois caminhos distintos:

    - componente `..` ou caminho absoluto -- pego no caminho LOGICO, antes de
      qualquer acesso ao disco;
    - diretorio do destino que seja symlink apontando para fora -- so aparece
      no caminho RESOLVIDO, e por isso a segunda checagem existe.

    A checagem usa o caminho resolvido, mas quem vai para `copy2` e o
    relativo: resolver e ato de verificacao, nao de construcao do destino.
    """
    candidate = Path(base) / relative
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"destino invalido: {candidate}")

    root = Path.cwd().resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise ValueError(f"destino escapa de {root}: {resolved}")
    return candidate

def copy_tree(src: Path, dst: Path, force: bool) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        dest = install_dest(dst, item.relative_to(src))
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not force:
            print(f"SKIP {Path.cwd() / dest} (use --force)")
            continue
        shutil.copy2(item, dest)
        print(f"COPY {Path.cwd() / dest}")

def check_target(raw: Path | None) -> None:
    """Confere que `--target` e o diretorio atual -- e NUNCA o usa como caminho.

    A instalacao escreve sempre no diretorio de onde o script foi chamado. O
    argumento sobrevive so como confirmacao explicita de destino, comparado
    como texto: ele nao vira caminho de escrita, nao vira `chdir`, nao chega a
    nenhuma chamada de filesystem. Com isso o destino de toda copia e o cwd do
    processo, que o operador ja escolheu ao rodar o comando, e a unica coisa
    montada a partir de dado externo e uma mensagem de erro.

    Escolher outro diretorio continua possivel, com uma linha a mais e sem
    ambiguidade nenhuma sobre onde os arquivos vao cair:

        cd /caminho/do/repositorio && python /caminho/scripts/install_skills.py --all
    """
    if raw is None:
        return
    requested = os.path.realpath(os.path.expanduser(str(raw)))
    if requested != os.path.realpath(os.getcwd()):
        raise SystemExit(
            f"--target precisa ser o diretorio atual. Rode a instalacao de dentro dele:\n"
            f"    cd {raw} && python {Path(__file__).name} ..."
        )

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install SparkForge AWS skills into the current directory"
    )
    parser.add_argument(
        "--target",
        type=Path,
        help="confirmacao opcional do destino; precisa ser o diretorio atual (ex.: `.`)",
    )
    parser.add_argument("--claude", action="store_true")
    parser.add_argument("--devin", action="store_true")
    parser.add_argument("--copilot", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    check_target(args.target)
    selected = args.all or not (args.claude or args.devin or args.copilot)

    def copy_docs(names: tuple[str, ...]) -> None:
        for name in names:
            dest = install_dest(Path("."), name)
            if not dest.exists() or args.force:
                shutil.copy2(ROOT / name, dest)

    if args.all or args.claude or selected:
        copy_tree(ROOT / ".claude", Path(".claude"), args.force)
        copy_docs(("CLAUDE.md", "PROMPT_INICIAL_MESTRE.md", "GUIA_DE_USO.md"))

    if args.all or args.devin or selected:
        copy_tree(ROOT / ".agents", Path(".agents"), args.force)
        copy_docs(("AGENTS.md", "PROMPT_INICIAL_MESTRE.md", "GUIA_DE_USO.md"))

    if args.all or args.copilot or selected:
        copy_tree(ROOT / ".github", Path(".github"), args.force)

    # Shared references are needed by the skills.
    for folder in ("knowledge", "templates", "checklists", "skills"):
        copy_tree(ROOT / folder, Path(folder), args.force)

    print("SparkForge AWS installed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
