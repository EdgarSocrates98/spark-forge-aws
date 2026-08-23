#!/usr/bin/env python3
"""Gate do artefato: o pacote instalado reproduz os goldens byte a byte?

Constroi sdist e wheel, instala o wheel num venv limpo, e roda os modulos de
golden ja existentes SOB O PYTHON DO VENV. Se o pacote instalado produz os
mesmos facts e findings que o repositorio, o canal pip esta em paridade.

Por que reaproveitar os modulos de golden em vez de reimplementar a comparacao:
o corpus de fixtures JA e o contrato, verificado no CI a cada commit. Um
comparador proprio seria um segundo contrato para manter divergir do primeiro --
e o primeiro a divergir seria o novo, porque ninguem o le.

O numero de fixtures nao e citado aqui de proposito. Ele estava, dizia 74, e o
corpus passou de 100 sem que nada acendesse -- este docstring foi a ORIGEM do
mesmo numero errado no README, que sobreviveu a duas fases. Contagem em prosa
nao tem invariante que a defenda; quem quiser o numero de hoje roda
`ls -d fixtures/*/*/ | wc -l`.

A guarda que sustenta tudo esta em `tests/test_installed_provenance.py`, ligada
aqui por `SPARKFORGE_VERIFY_INSTALLED=1`. Sem ela, um `sys.path` errado faria o
pytest importar o repositorio e comparar o codigo-fonte consigo mesmo.

O gate tambem constroi DUAS vezes a mesma arvore e compara os artefatos por
sha256. Ver `compare_builds` para por que a comparacao mora aqui, e nao na
suite.

Uso:
    python scripts/verify_wheel.py                # constroi, instala e verifica
    python scripts/verify_wheel.py --keep         # nao apaga o diretorio temporario
    python scripts/verify_wheel.py --outdir DIR   # copia o wheel e o sdist
                                                    # PROVADOS para DIR, so
                                                    # depois do gate passar

Por que `--outdir` existe: sem ele, o unico exemplar que passou pelos
testes de golden e apagado no `finally` (o diretorio e temporario), e o passo
de publicacao teria que rodar `python -m build` de novo para ter o que anexar.

A build E reproduzivel bit-a-bit -- e este gate prova isso a cada execucao --
entao um segundo build produziria hoje o MESMO arquivo. `--outdir` continua
sendo o desenho certo assim mesmo, por uma razao que sobrevive a
reprodutibilidade: ele torna "o byte publicado e o byte testado" uma
propriedade ESTRUTURAL, nao uma inferencia. A igualdade bit-a-bit vale sob
condicoes (mesma versao de hatchling, mesmo zlib, mesmo `SOURCE_DATE_EPOCH`
no ambiente); um passo de publicacao que reconstroi depende dessas condicoes
se manterem entre dois passos do mesmo workflow, e uma delas -- a versao do
backend, que `python -m pip install build` resolve sem pin -- pode mudar entre
duas invocacoes. Copiar nao depende de condicao nenhuma.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# `test_fixtures_*.py`, e nao `test_fixtures_golden*.py`: o corpus de cenario
# da Fase G6 (`fixtures/scenarios/`) e exercitado por
# `tests/test_fixtures_scenarios.py`, que nao tem "golden" no nome porque o
# golden dele nao e `facts`+`findings` -- e o `to_dict()` de um
# `MigrationAssessment`, produzido por `sparkforge.migration.assessment.assess`.
# Esse e justamente um contrato que vale checar contra o PACOTE INSTALADO, e o
# padrao antigo o deixaria de fora em silencio. O alargamento tambem traz
# `test_fixtures_kind_coverage.py`, que passa a comparar o catalogo instalado
# contra o corpus do repositorio -- ganho, nao efeito colateral.
GOLDEN_MODULES = sorted(p.name for p in (ROOT / "tests").glob("test_fixtures_*.py"))
PROVENANCE_MODULE = "test_installed_provenance.py"

ARTIFACT_PATTERNS = ("*.whl", "*.tar.gz")
# Teto do relatorio de divergencia: um zip com 78 entradas que diverge em todas
# viraria uma parede de log onde o primeiro exemplo -- que e o que se lê -- fica
# soterrado. O numero total de entradas divergentes vai na linha de resumo.
MAX_REPORTED_ENTRIES = 10


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(1 << 16):
            digest.update(chunk)
    return digest.hexdigest()


def _artifacts(directory: Path) -> dict[str, Path]:
    """Artefatos publicaveis de um diretorio de build, por nome de arquivo."""
    found: dict[str, Path] = {}
    for pattern in ARTIFACT_PATTERNS:
        for path in sorted(directory.glob(pattern)):
            found[path.name] = path
    return found


def zip_divergence(first: Path, second: Path) -> list[str]:
    """ONDE, dentro de dois zips, as construcoes diferem.

    "Os hashes diferem" nao diz o que consertar. Cada eixo de nao-determinismo
    do zip aparece num campo diferente do cabecalho da entrada, e o campo que
    diverge nomeia o eixo:

      `date_time`      -> timestamp (`SOURCE_DATE_EPOCH` / `reproducible`)
      `external_attr`  -> modo/permissao herdado do umask ou do sistema
      `compress_type`  -> metodo de compressao
      ordem dos nomes  -> ordem de caminhada do sistema de arquivos
      `CRC`/`file_size`-> o CONTEUDO mudou; nao e o empacotador, e a arvore

    `.tar.gz` nao e decomposto: o membro que diverge exigiria descompactar
    dois tars inteiros, e na pratica a causa e sempre visivel no wheel, que
    passa pelo mesmo empacotador.
    """
    if first.suffix != ".whl" or second.suffix != ".whl":
        return []

    def entries(path: Path) -> dict[str, tuple] | None:
        # Um `.whl` ilegivel e uma divergencia a mais para relatar, nao um
        # traceback: esta funcao roda DEPOIS de os hashes ja terem divergido,
        # e o gate ja esta reprovando. Estourar aqui trocaria um relatorio
        # acionavel por um `BadZipFile` que nao diz qual dos dois quebrou.
        try:
            with zipfile.ZipFile(path) as archive:
                return {
                    info.filename: (
                        info.date_time,
                        hex(info.external_attr),
                        info.compress_type,
                        info.CRC,
                        info.file_size,
                    )
                    for info in archive.infolist()
                }
        except (zipfile.BadZipFile, OSError):
            return None

    a, b = entries(first), entries(second)
    unreadable = [str(p) for p, e in ((first, a), (second, b)) if e is None]
    if unreadable:
        return [f"nao e um zip legivel: {', '.join(unreadable)}"]
    lines: list[str] = []

    if list(a) != list(b):
        only_a = sorted(set(a) - set(b))
        only_b = sorted(set(b) - set(a))
        if only_a or only_b:
            lines.append(f"conjunto de entradas diverge: so na 1a {only_a}, so na 2a {only_b}")
        else:
            lines.append("mesmas entradas, ORDEM diferente (ordem de caminhada do FS)")

    differing = [name for name in a if name in b and a[name] != b[name]]
    for name in differing[:MAX_REPORTED_ENTRIES]:
        lines.append(f"{name}: 1a {a[name]} != 2a {b[name]}")
    if len(differing) > MAX_REPORTED_ENTRIES:
        lines.append(f"... e mais {len(differing) - MAX_REPORTED_ENTRIES} entradas divergentes")

    if not lines:
        # Entradas identicas em nome, ordem, metadado e CRC, mas os bytes do
        # arquivo diferem: sobrou o proprio fluxo de deflate (implementacao ou
        # nivel de zlib) ou o cabecalho gzip. Dizer isso e mais util do que
        # devolver lista vazia e deixar o leitor achar que nao ha divergencia.
        lines.append(
            "entradas identicas em metadado e CRC -- diverge no fluxo comprimido "
            "(implementacao/nivel de zlib) ou fora das entradas"
        )
    return lines


def compare_builds(first: Path, second: Path) -> list[str]:
    """Divergencias entre dois diretorios de build da MESMA arvore.

    Lista vazia significa reproduzivel bit-a-bit. Cada string e uma linha de
    relatorio pronta para o stderr.

    Por que a comparacao mora no gate e nao na suite: ela custa uma segunda
    construcao completa, e a suite roda a cada commit. O gate ja gasta minutos
    construindo, instalando num venv limpo e rodando os goldens, e o `ci.yml` o
    executa em ubuntu E windows a cada push e PR -- entao a checagem tem
    cobertura de CI incondicional sem transformar `pytest -q` num teste de
    build. A suite cobre os INVARIANTES baratos sobre o wheel que ja construiu
    (`tests/test_artifact_contents.py`) e esta funcao com dublês
    (`tests/test_verify_wheel.py`), que e onde a logica erra.
    """
    a, b = _artifacts(first), _artifacts(second)
    problems: list[str] = []

    if not a:
        problems.append(f"nenhum artefato para comparar em {first}")
        return problems

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    if only_a or only_b:
        problems.append(
            f"conjunto de artefatos diverge: so na 1a build {only_a}, so na 2a build {only_b}"
        )

    for name in sorted(set(a) & set(b)):
        first_hash, second_hash = sha256_of(a[name]), sha256_of(b[name])
        if first_hash != second_hash:
            problems.append(f"{name}: 1a build sha256={first_hash}, 2a build sha256={second_hash}")
            problems.extend(f"    {line}" for line in zip_divergence(a[name], b[name]))

    return problems


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


def safe_outdir(raw: Path) -> Path:
    """Normaliza `--outdir` uma vez, no ponto de entrada, e nunca mais.

    `scripts/install_skills.py::install_dest` resolve o mesmo problema confinando
    o destino a uma raiz. Aqui NAO ha raiz de contencao, e isso e proposital: o
    proposito do `--outdir` e depositar o artefato onde o chamador quiser --
    `dist/` no CI, um diretorio de staging, um volume montado. Confinar quebraria
    a funcao. Quem "consertar" isto confinando a uma raiz vai quebrar o release.

    O que substitui a garantia e quebrar a cadeia de contaminacao, em dois pontos:

    1. Aqui: `resolve()` elimina a semantica de `..` antes de qualquer acesso a
       disco, e o resultado passa a ser um caminho absoluto normalizado. Depois
       desta linha, nenhum valor cru da linha de comando circula pelo programa.
    2. Em `_artifact_dest`: o unico componente concatenado ao destino e um
       basename provado, vindo do glob do diretorio de build -- nunca de argv.

    Symlink: SEGUE, nao recusa. `install_dest` recusa symlink que aponte para
    fora da raiz de contencao dele -- mas aqui nao ha raiz para escapar. Um
    `--outdir` que seja symlink e so mais uma forma legitima do operador
    apontar para onde ele quer os artefatos (um volume montado via link, por
    exemplo). `resolve()` ja segue o symlink e devolve o caminho real; e esse
    caminho real que recebe `mkdir` e `copy2`, e e ele que aparece na mensagem
    "artefatos provados copiados para ..." impressa no fim de `main` -- o
    operador nunca fica sem saber onde os artefatos foram parar, entao nao ha
    superficie de confusao para recusar.

    Recusa arquivo existente no lugar do diretorio: `mkdir(parents=True,
    exist_ok=True)` levantaria `FileExistsError` cru mais adiante, e o operador
    receberia um traceback em vez da causa.
    """
    resolved = Path(raw).expanduser().resolve()
    if resolved.exists() and not resolved.is_dir():
        raise SystemExit(f"--outdir aponta para {resolved}, que existe e nao e diretorio")
    return resolved


def _artifact_dest(outdir: Path, artifact: Path) -> Path:
    """Destino de um artefato: `<outdir normalizado>/<basename>`.

    `artifact.name` vem do glob de `dist/` construido por este script, entao ja e
    basename. A assercao existe para que a quebra da cadeia fique VISIVEL aqui,
    em vez de depender de o leitor rastrear a origem do valor tres funcoes acima.
    """
    name = artifact.name
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise SystemExit(f"nome de artefato inesperado, recusado por seguranca: {name!r}")
    return outdir / name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--keep", action="store_true", help="Nao apaga o diretorio temporario.")
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Copia o wheel e o sdist PROVADOS para este diretorio, so depois do gate passar.",
    )
    args = parser.parse_args(argv)

    if args.outdir is not None:
        args.outdir = safe_outdir(args.outdir)

    # Guarda de corpus, DENTRO do gate -- nao basta o teste da suite
    # (`tests/test_verify_wheel.py::test_there_is_more_than_one`). Aquele
    # teste roda sob o pytest do REPOSITORIO, nunca dentro desta execucao: se
    # `tests/test_fixtures_golden*.py` for renomeado ou apagado do disco,
    # `GOLDEN_MODULES` vira `[]` aqui, `pytest_command()` devolve so o modulo
    # de procedencia, ele passa (nada para comparar), e o gate imprimiria
    # "OK: em paridade com os goldens" tendo verificado ZERO assercao de
    # golden. Um gate que so prova a si mesmo -- sem numero
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
    rebuild = workdir / "rebuild"
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

        # Segunda construcao da MESMA arvore. Vem logo depois da primeira, e
        # nao no fim, porque uma build nao-reproduzivel invalida a leitura de
        # tudo que vem depois: "provamos que ESTE wheel reproduz os goldens"
        # so vale como afirmacao sobre o pacote se o wheel for uma funcao da
        # arvore, e nao do instante em que foi construido.
        if _run([sys.executable, "-m", "build", "--outdir", str(rebuild), str(ROOT)]).returncode:
            print("segunda build (checagem de reprodutibilidade) falhou", file=sys.stderr)
            return 1

        divergences = compare_builds(dist, rebuild)
        if divergences:
            print("build NAO e reproduzivel bit-a-bit:", file=sys.stderr)
            for line in divergences:
                print(f"  {line}", file=sys.stderr)
            return 1
        print(f"reprodutibilidade OK: {len(_artifacts(dist))} artefatos identicos em duas builds")

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

        if args.outdir is not None:
            # So chega aqui se build, instalacao, golden E twine check ja
            # passaram -- um artefato reprovado nunca pode aparecer num
            # diretorio de onde alguem publicaria por engano. `copy2` (nao
            # `move`) porque `--keep` preserva o workdir inteiro para
            # inspecao; os dois sinalizadores nao devem brigar por posse do
            # arquivo.
            args.outdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(wheels[0], _artifact_dest(args.outdir, wheels[0]))
            shutil.copy2(sdists[0], _artifact_dest(args.outdir, sdists[0]))
            print(f"artefatos provados copiados para {args.outdir}")

        print(f"\nOK: {wheels[0].name} e {sdists[0].name} em paridade com os goldens.")
        return 0
    finally:
        if args.keep:
            print(f"artefatos preservados em {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
