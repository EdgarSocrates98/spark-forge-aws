#!/usr/bin/env python3
"""Gera e confere o lock reproduzivel do ambiente de CI e de release.

Por que este arquivo existe
===========================

`requirements.txt` e espelho de PISOS (`>=`), nao lock. Ele existe para que
ferramenta de SCA consiga LER as dependencias; ele nao diz que versao foi
instalada. Instalar por piso significa que o CI resolve a arvore de novo a cada
execucao: dois commits identicos podem instalar arvores diferentes, e um teste
que quebra por causa disso quebra sem que o diff explique nada. Auditar piso
tambem nao diz muito -- `PyYAML>=6.0` nao tem CVE, a versao instalada e que tem.

Este lock congela o ambiente. Cada entrada tem versao exata e os sha256 das
distribuicoes daquela versao, e o CI instala com `pip install --require-hashes`.

O que esse modo faz, exatamente -- e vale ser preciso, porque a versao vaga da
frase ("o pip nao resolve") e falsa: em modo hash-checking o pip continua
olhando as dependencias de cada pacote, mas EXIGE que cada uma delas ja esteja
pinada com `==` e com hash no proprio arquivo. Qualquer coisa que ele descubra e
que nao esteja na lista vira ERRO, nunca uma versao escolhida na hora. O efeito
pratico e o que se quer: ou o ambiente instalado e identico ao commitado, ou a
instalacao falha dizendo o que faltou. E por isso que o lock precisa ser o fecho
INTEIRO, e nao a lista de requisitos diretos.

O lock e do AMBIENTE, nunca do pacote publicado
-----------------------------------------------

`pyproject.toml` continua declarando piso (`>=`) para as dependencias de
runtime, e isso esta certo: uma biblioteca que pina teto congela a arvore de
quem a instala. O lock aqui nao contradiz aquilo -- ele congela o ambiente que
constroi e testa, que e exatamente o que a exigencia de supply chain pede.

Por que `uv` para resolver, e nao o proprio pip
-----------------------------------------------

O lock precisa valer para Linux/CPython 3.10 e 3.11, e ele e gerado de onde o
mantenedor estiver. O `--python-version` do pip so afeta compatibilidade de tag
de wheel e `Requires-Python`; ele NAO reavalia marcador de ambiente. Uma
resolucao feita no Windows com `--python-version 3.10` sai com `colorama` (que
so entra sob `sys_platform == "win32"`) e SEM `tomli` (que hatchling exige sob
`python_version < "3.11"`) -- ou seja, um lock que nao instala no runner e cujo
backend de build nao importa. `uv pip compile --python-platform`
`--python-version` reavalia os marcadores para o ambiente alvo, e por isso e
ele quem resolve aqui. E a mesma ferramenta que a exigencia nomeia.

`uv` e ferramenta de GERACAO. Ele nao entra em `pyproject.toml`, nao entra no
CI e nao e preciso para instalar nada: quem regenera o lock instala `uv`, quem
so confere nao precisa dele.

Um lock por versao de Python, e por que nao da para ser um so
-------------------------------------------------------------

A resolucao DIVERGE entre 3.10 e 3.11, e nao por capricho: `rpds-py` tem versao
cujo `requires-python` exclui 3.10, entao as duas linhas resolvem para versoes
diferentes do MESMO pacote; e `tomli`, `importlib-metadata` e `zipp` so existem
na linha 3.10. Um lock unico teria que mentir sobre uma das duas. Sao dois
arquivos, um por entrada da matriz do CI, e o nome do arquivo carrega a versao
para que o workflow os enderece sem tabela de conversao.

O alvo e Linux x86_64, que e onde o job `test` roda (`ubuntu-latest`). O job
`wheel`, que tambem roda no Windows, NAO usa este lock: ele instala so `build` e
constroi o artefato. Se um dia usar, vai precisar de um lock por plataforma
tambem, e a razao esta escrita aqui.

Mais de um hash por pacote e esperado
-------------------------------------

Uma versao publicada tem varios arquivos -- o sdist e um wheel por tag. O lock
carrega o sha256 de cada um, que e como `pip install --require-hashes` espera
receber: ele casa o arquivo que escolheu contra QUALQUER um dos hashes
listados. Um hash so tornaria o lock especifico do interpretador que o gerou.

Rede
====

Gerar exige rede: a resolucao vem do indice do PyPI e a licenca vem da API JSON
do PyPI. Conferir NAO exige rede -- `--check` le os arquivos commitados e
verifica forma, cobertura e consistencia. E por isso que o CI so roda `--check`:
um gate que precisa de rede para dizer "ok" e um gate que a queda do indice
transforma em falha vermelha sem defeito nenhum no repositorio.

O que `--check` NAO consegue provar, e vale dizer em vez de deixar implicito: que
o fecho esta COMPLETO para o ambiente alvo. Isso se verifica recompilando o
proprio lock com o mesmo alvo e comparando os pins --

    uv pip compile locks/py3.11.txt --python-version 3.11 \\
        --python-platform x86_64-manylinux2014 --only-binary :all: --no-annotate

Um lock completo e ponto fixo dessa operacao: sai o mesmo conjunto que entrou.
Se faltasse alguma transitiva, ela apareceria na saida e nao no arquivo. Exige
rede e `uv`, e por isso mora aqui como receita, e nao como gate.

Uso
===

    pip install uv                          # so para regenerar
    python scripts/gen_lock.py              # regenera os locks (EXIGE REDE)
    python scripts/gen_lock.py --check      # confere os locks commitados (offline)
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess  # noqa: S404 - argv fixo, sem shell; ver `_uv_compile`
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = ROOT / "locks"

# As duas entradas da matriz de `.github/workflows/ci.yml`. Uma lista aqui e a
# mesma lista la e drift esperando para acontecer -- `tests/test_supply_chain.py`
# le a matriz do workflow e compara com esta tupla, entao acrescentar 3.12 no CI
# sem gerar o lock correspondente quebra a suite em vez de quebrar o CI.
PYTHON_VERSIONS = ("3.10", "3.11")

# O alvo de `ubuntu-latest`, no vocabulario do `--python-platform` do uv.
PLATFORM = "x86_64-manylinux2014"

# `scope` no vocabulario do CycloneDX, que `scripts/gen_sbom.py` consome:
#   required -- fecho das dependencias de nucleo declaradas em `[project]`
#   optional -- entra so por extra que o usuario pode pedir (`aws`, `mcp`)
#   excluded -- ferramenta de build ou de desenvolvimento; existe no ambiente
#               que produz o release e nao dentro do que e publicado
SCOPE_REQUIRED = "required"
SCOPE_OPTIONAL = "optional"
SCOPE_EXCLUDED = "excluded"
SCOPES = (SCOPE_REQUIRED, SCOPE_OPTIONAL, SCOPE_EXCLUDED)

PYPI_JSON = "https://pypi.org/pypi/{name}/{version}/json"

# Requisito de build que NAO aparece em `[build-system] requires`, e que sem esta
# linha derrubaria o CI.
#
# O hatchling declara `editables~=0.3` dinamicamente, pelo hook
# `get_requires_for_build_editable` (PEP 660) -- `hatchling.builders.constants.
# EDITABLES_REQUIREMENT`. Com isolamento de build, o pip pergunta ao backend e
# baixa `editables` na hora; com `--no-build-isolation`, que e o que o CI usa
# para NAO baixar nada, ele nao baixa, e `build_editable_detection` falha no
# `from editables import EditableProject`.
#
# O valor espelha a constante do hatchling. Ele nao e derivavel offline (o
# hatchling nao esta instalado na maquina que gera o lock), entao um upgrade de
# hatchling que mude essa faixa exige conferir esta linha -- e por isso ela esta
# escrita aqui, e nao escondida no meio de uma lista.
BUILD_HELPERS = ("editables~=0.3",)

HEADER = """\
# GERADO por scripts/gen_lock.py -- NAO EDITE A MAO.
#
# Lock do AMBIENTE de CI e de release, resolvido por `uv pip compile` para
# CPython {python} em {platform}. Versao exata e sha256 de cada distribuicao
# publicada daquela versao; o CI instala com `pip install --require-hashes`,
# que trata como ERRO qualquer dependencia que nao esteja pinada aqui -- entao
# esta lista e o fecho INTEIRO do ambiente, e nao os requisitos diretos.
#
# O pacote publicado continua declarando PISO em pyproject.toml. Este lock
# congela quem constroi e testa, nao quem instala o pacote.
#
# Regenere com: pip install uv && python scripts/gen_lock.py   (exige rede)
# Confira com:  python scripts/gen_lock.py --check             (offline)
"""

# `# sparkforge-lock: scope=... license=...` na linha imediatamente anterior a
# cada pin. Comentario porque pip ignora; estruturado porque
# `scripts/gen_sbom.py` le: licenca e escopo sao dois campos que o SBOM precisa
# carregar e que nao cabem na sintaxe de um requirements.txt.
META_RE = re.compile(r"^# sparkforge-lock: scope=(?P<scope>\S+) license=(?P<license>.+)$")
PIN_RE = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)==(?P<version>[^\s\\]+) \\$")
HASH_RE = re.compile(r"^    --hash=sha256:(?P<digest>[0-9a-f]{64})(?P<cont> \\)?$")


class LockedPackage:
    """Uma entrada do lock: o que o pip precisa mais o que o SBOM precisa."""

    __slots__ = ("hashes", "license", "name", "scope", "version")

    def __init__(
        self, name: str, version: str, hashes: list[str], license: str, scope: str
    ) -> None:
        self.name = name
        self.version = version
        self.hashes = hashes
        self.license = license
        self.scope = scope

    def render(self) -> str:
        lines = [f"# sparkforge-lock: scope={self.scope} license={self.license}"]
        lines.append(f"{self.name}=={self.version} \\")
        for index, digest in enumerate(self.hashes):
            last = index == len(self.hashes) - 1
            lines.append(f"    --hash=sha256:{digest}" + ("" if last else " \\"))
        return "\n".join(lines) + "\n"


def lock_path(python_version: str) -> Path:
    return LOCK_DIR / f"py{python_version}.txt"


def _display(path: Path) -> str:
    """Caminho para a mensagem de erro: relativo a raiz quando cabe, absoluto
    quando nao. `relative_to` cru estoura `ValueError` para caminho fora da
    arvore -- e o teste que aponta `LOCK_DIR` para um `tmp_path` receberia um
    traceback de pathlib no lugar da divergencia que ele foi medir."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def canonical(name: str) -> str:
    """Nome canonico de pacote (PEP 503): `rpds-py`, `rpds_py` e `RPDS.PY` sao o
    mesmo pacote, e comparar sem normalizar deixaria o mesmo pacote entrar duas
    vezes com escopos diferentes."""
    return re.sub(r"[-_.]+", "-", name).lower()


# ------------------------------------------------------------ requisitos declarados


def _pyproject_arrays() -> tuple[list[str], list[str], list[str]]:
    """Nucleo, extras de usuario e requisitos de build, lidos de `pyproject.toml`.

    Usa a MESMA rotina que gera `requirements.txt` (`scripts/gen_requirements.py`)
    em vez de um segundo parser de TOML: o repositorio ja pagou uma vez o preco
    de duas leituras do mesmo arquivo divergindo em silencio.

    `dev` fica fora do grupo "extras de usuario" de proposito: ele e ferramenta
    de desenvolvimento, e no vocabulario do CycloneDX isso e `excluded`, nao
    `optional`. Quem instala `sparkforge-aws[dev]` esta desenvolvendo, nao
    consumindo o release.

    O grupo de build devolvido inclui `BUILD_HELPERS` -- requisito que o backend
    declara pelo hook do PEP 660 e nao em `[build-system] requires`. Ver a
    constante para o porque de ele existir e do que ele quebra sem ela.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.gen_requirements import _scan_array, _section  # noqa: PLC0415

    raw = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project = _section(raw)

    core_match = re.search(r"^dependencies\s*=\s*\[", project, re.MULTILINE)
    if core_match is None:
        raise SystemExit("pyproject.toml sem `dependencies` em [project]")
    core, _ = _scan_array(project, core_match.end() - 1)

    optional: list[str] = []
    optional_start = project.find("[project.optional-dependencies]")
    if optional_start != -1:
        block = project[optional_start:]
        for match in re.finditer(r"^(?P<extra>[A-Za-z][\w-]*)\s*=\s*\[", block, re.MULTILINE):
            if match.group("extra") == "dev":
                continue
            values, _ = _scan_array(block, match.end() - 1)
            optional.extend(values)

    # `[build-system] requires` entra no lock por uma razao especifica: sem ele,
    # `pip install -e .` no CI baixaria o backend de build do indice EM TEMPO DE
    # CI -- resolucao, que e o que este lock existe para eliminar. Com hatchling
    # pinado, o workflow instala com `--no-build-isolation` e nada e resolvido.
    # O comentario de `[tool.hatch.build]` no `pyproject.toml` ja registrava o
    # custo de o backend nao estar pinado: a versao dele vaza para o `WHEEL`
    # como `Generator: hatchling X.Y.Z`.
    build_match = re.search(r"^requires\s*=\s*\[", raw, re.MULTILINE)
    if build_match is None:
        raise SystemExit("pyproject.toml sem `requires` em [build-system]")
    build, _ = _scan_array(raw, build_match.end() - 1)

    return core, optional, [*build, *BUILD_HELPERS]


def declared_names() -> set[str]:
    """Nome canonico de todo requisito declarado diretamente em `pyproject.toml`."""
    core, optional, build = _pyproject_arrays()
    return {requirement_name(req) for req in core + optional + build}


def requirement_name(requirement: str) -> str:
    """O nome canonico dentro de um requisito -- `mcp>=1.0,<2` vira `mcp`.

    Existe como funcao publica porque `tests/test_supply_chain.py` faz a mesma
    pergunta ao derivar o que deveria estar no lock. Duas implementacoes da
    mesma divisao de string divergem no dia em que alguem escrever um extra ou
    um marcador que so uma das duas entende.
    """
    return canonical(re.split(r"[<>=!~\[;\s]", requirement, maxsplit=1)[0])


# ------------------------------------------------------------------- resolucao


def _uv() -> str:
    path = shutil.which("uv")
    if path is None:
        raise SystemExit(
            "uv nao encontrado no PATH. Ele so e preciso para REGENERAR o lock: "
            "`pip install uv`. Conferir (`--check`) nao usa uv nem rede."
        )
    return path


def _uv_compile(requirements: list[str], python_version: str) -> list[tuple[str, str, list[str]]]:
    """Resolve com `uv pip compile` e devolve `(nome, versao, [sha256, ...])`.

    `--only-binary :all:` e deliberado, e tem custo declarado: um pacote que so
    publique sdist faz a resolucao FALHAR aqui em vez de entrar no lock. A falha
    e preferivel -- instalar por sdist obriga o runner a CONSTRUIR o pacote, e
    construir e executar codigo de terceiro dentro do CI.

    Sem shell: argv e lista e nenhum elemento vem de entrada de usuario -- os
    requisitos sao lidos de `pyproject.toml`, versao de Python e plataforma sao
    constantes deste modulo, e o arquivo de entrada e temporario escrito aqui.
    """
    with tempfile.TemporaryDirectory(prefix="sparkforge-lock-") as tmp:
        entrada = Path(tmp) / "requirements.in"
        entrada.write_text("\n".join(requirements) + "\n", encoding="utf-8")
        argv = [
            _uv(),
            "pip",
            "compile",
            str(entrada),
            "--python-version",
            python_version,
            "--python-platform",
            PLATFORM,
            "--only-binary",
            ":all:",
            "--generate-hashes",
            "--no-header",
            "--no-annotate",
            "--quiet",
        ]
        result = subprocess.run(argv, capture_output=True, text=True)  # noqa: S603
        if result.returncode != 0:
            raise SystemExit(
                f"uv nao resolveu para {python_version}: {result.stderr.strip()[-1200:]}"
            )
        return _parse_uv_output(result.stdout)


def _parse_uv_output(text: str) -> list[tuple[str, str, list[str]]]:
    resolved: list[tuple[str, str, list[str]]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("--hash=sha256:"):
            if not resolved:
                raise SystemExit(f"uv devolveu hash antes de pin: {stripped!r}")
            resolved[-1][2].append(stripped.removeprefix("--hash=sha256:").rstrip(" \\"))
            continue
        pin = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==([^\s\\]+)", stripped)
        if pin is None:
            raise SystemExit(f"linha inesperada na saida do uv: {stripped!r}")
        resolved.append((pin.group(1), pin.group(2), []))
    return resolved


def normalize_license(payload: dict) -> str:
    """A licenca de um pacote, num token so, sem inventar quando nao ha.

    Tres fontes, nesta ordem, que e a ordem da especificacao de metadados:

    1. `license_expression` (metadados 2.4) -- ja e identificador SPDX.
    2. O classificador `License :: ...` -- vocabulario fechado do PyPI. Quando
       ha mais de um, os dois entram separados por ` OR `, porque escolher um
       seria decidir por conta propria uma questao juridica.
    3. O campo `license` livre, e SO quando ele e curto. Pacote antigo costuma
       colar o texto INTEIRO da licenca ali; um SBOM com quilobytes de texto num
       campo de identificador nao e melhor, e ilegivel.

    Sem nenhuma das tres, o valor e `NOASSERTION` -- o termo que o SPDX define
    para "nao afirmo nada", e nao um branco que o leitor confundiria com "sem
    licenca". Ponto cego declarado vale mais que campo preenchido no chute.
    """
    expression = (payload.get("license_expression") or "").strip()
    if expression:
        return expression

    classifiers = [c for c in (payload.get("classifiers") or []) if c.startswith("License ::")]
    if classifiers:
        return " OR ".join(c.split(" :: ")[-1].strip() for c in classifiers)

    raw = (payload.get("license") or "").strip()
    if raw and "\n" not in raw and len(raw) <= 40:
        return raw

    return "NOASSERTION"


def fetch_license(name: str, version: str, cache: dict[tuple[str, str], str]) -> str:
    """Licenca de `name==version`, pela API JSON do PyPI, com cache por versao.

    Rede aqui, e so aqui na geracao: `uv` devolve o que instalar, nao sob que
    licenca. Falha de rede NAO vira licenca inventada -- vira `NOASSERTION`, com
    aviso no stderr, pela mesma razao que o resto do repositorio prefere ponto
    cego declarado a campo preenchido no chute.
    """
    key = (canonical(name), version)
    if key in cache:
        return cache[key]
    url = PYPI_JSON.format(name=name, version=version)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310 - https fixo
            payload = json.load(response)["info"]
        value = normalize_license(payload)
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as error:
        print(f"aviso: licenca de {name}=={version} nao consultada ({error})", file=sys.stderr)
        value = "NOASSERTION"
    cache[key] = value
    return value


def resolve_locked(
    python_version: str, cache: dict[tuple[str, str], str] | None = None
) -> list[LockedPackage]:
    """Resolve tres vezes e devolve o ambiente inteiro, cada pacote com escopo.

    Tres resolucoes, e nao uma com atribuicao de escopo por conta propria: o
    escopo de um pacote TRANSITIVO so se sabe percorrendo o grafo com os
    marcadores de ambiente avaliados, e quem ja faz isso corretamente e o
    resolvedor. `attrs` entra por `jsonschema`, que e nucleo -- deduzir isso a
    mao exigiria reimplementar avaliacao de marcador, e errar ali marcaria
    dependencia de runtime como ferramenta de desenvolvimento no SBOM.
    """
    cache = {} if cache is None else cache
    core, optional, build = _pyproject_arrays()

    core_names = {canonical(n) for n, _, _ in _uv_compile(core, python_version)}
    runtime_names = {canonical(n) for n, _, _ in _uv_compile(core + optional, python_version)}

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.gen_requirements import requirements_from_pyproject  # noqa: PLC0415

    todos = requirements_from_pyproject() + build

    locked: list[LockedPackage] = []
    for name, version, hashes in _uv_compile(todos, python_version):
        key = canonical(name)
        if key in core_names:
            scope = SCOPE_REQUIRED
        elif key in runtime_names:
            scope = SCOPE_OPTIONAL
        else:
            scope = SCOPE_EXCLUDED
        locked.append(
            LockedPackage(
                name=name,
                version=version,
                hashes=sorted(hashes),
                license=fetch_license(name, version, cache),
                scope=scope,
            )
        )
    # Ordem por nome canonico: a ordem da resolucao nao e estavel entre
    # execucoes, e um lock que reordena a cada regeneracao produz diff de
    # centenas de linhas onde mudou uma versao.
    locked.sort(key=lambda pkg: canonical(pkg.name))
    return locked


# ------------------------------------------------------------- render e parse


def render(python_version: str, locked: list[LockedPackage]) -> str:
    head = HEADER.format(python=python_version, platform=PLATFORM)
    return head + "".join(pkg.render() for pkg in locked)


def parse(text: str) -> list[LockedPackage]:
    """Le um lock commitado.

    Recusa qualquer linha que nao seja das formas previstas -- comentario,
    metadado, pin ou hash. Uma linha solta num arquivo que o pip instala e uma
    dependencia que ninguem reviu, e o parser e o unico lugar onde ela ainda
    pode ser recusada de graca.
    """
    packages: list[LockedPackage] = []
    meta: re.Match[str] | None = None
    pin: re.Match[str] | None = None
    hashes: list[str] = []

    def fechar() -> None:
        nonlocal meta, pin, hashes
        packages.append(
            LockedPackage(
                name=pin.group("name"),
                version=pin.group("version"),
                hashes=hashes,
                license=meta.group("license"),
                scope=meta.group("scope"),
            )
        )
        meta = None
        pin = None
        hashes = []

    for number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        candidate_meta = META_RE.match(line)
        if candidate_meta:
            if pin is not None:
                raise ValueError(f"linha {number}: metadado antes de fechar o pin anterior")
            meta = candidate_meta
            continue
        if line.startswith("#"):
            continue
        candidate_pin = PIN_RE.match(line)
        if candidate_pin:
            if meta is None:
                raise ValueError(f"linha {number}: pin sem linha `# sparkforge-lock:` antes")
            if pin is not None:
                raise ValueError(f"linha {number}: pin sem nenhum hash antes do proximo")
            pin = candidate_pin
            continue
        candidate_hash = HASH_RE.match(line)
        if candidate_hash:
            if pin is None:
                raise ValueError(f"linha {number}: hash sem pin")
            hashes.append(candidate_hash.group("digest"))
            if not candidate_hash.group("cont"):
                fechar()
            continue
        raise ValueError(f"linha {number}: forma nao reconhecida: {line!r}")

    if meta is not None or pin is not None:
        raise ValueError("arquivo termina no meio de uma entrada")
    return packages


def load(python_version: str) -> list[LockedPackage]:
    path = lock_path(python_version)
    if not path.is_file():
        raise SystemExit(f"lock ausente: {_display(path)}")
    return parse(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------- checagem


def check(python_version: str) -> list[str]:
    """Confere um lock commitado SEM rede. Devolve as divergencias.

    O que da para provar offline: que o arquivo esta na forma prevista, que todo
    pin tem pelo menos um hash, que os escopos usam o vocabulario declarado, que
    nenhum pacote aparece duas vezes e que todo requisito declarado em
    `pyproject.toml` tem entrada correspondente. O que NAO da para provar
    offline: que a versao pinada continua sendo a que o indice serve, e se ela
    tem vulnerabilidade conhecida -- isso e trabalho da auditoria, que consulta
    base externa por natureza e por isso mora num job separado do CI.
    """
    path = lock_path(python_version)
    nome = _display(path)
    if not path.is_file():
        return [f"{nome}: ausente; rode python scripts/gen_lock.py"]

    try:
        packages = parse(path.read_text(encoding="utf-8"))
    except ValueError as error:
        return [f"{nome}: {error}"]

    if not packages:
        return [f"{nome}: vazio"]

    problems: list[str] = []
    seen: set[str] = set()
    for pkg in packages:
        key = canonical(pkg.name)
        if key in seen:
            problems.append(f"{pkg.name}: aparece mais de uma vez")
        seen.add(key)
        if pkg.scope not in SCOPES:
            problems.append(f"{pkg.name}: scope desconhecido {pkg.scope!r}")
        if not pkg.license.strip():
            problems.append(f"{pkg.name}: sem licenca declarada")
        if not pkg.hashes:
            problems.append(f"{pkg.name}: pin sem hash")

    missing = sorted(declared_names() - seen)
    if missing:
        problems.append(
            f"declarado em pyproject.toml e ausente do lock: {', '.join(missing)}; "
            "rode python scripts/gen_lock.py"
        )

    if not any(pkg.scope == SCOPE_REQUIRED for pkg in packages):
        problems.append("nenhum pacote com scope=required; a atribuicao de escopo quebrou")

    return [f"{nome}: {problem}" for problem in problems]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="Confere os locks; nao usa rede.")
    args = parser.parse_args(argv)

    if args.check:
        problems: list[str] = []
        for version in PYTHON_VERSIONS:
            problems.extend(check(version))
        if problems:
            for problem in problems:
                print(problem, file=sys.stderr)
            return 1
        total = sum(len(load(version)) for version in PYTHON_VERSIONS)
        print(f"OK: {len(PYTHON_VERSIONS)} locks, {total} entradas pinadas com hash.")
        return 0

    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    cache: dict[tuple[str, str], str] = {}
    for version in PYTHON_VERSIONS:
        locked = resolve_locked(version, cache)
        path = lock_path(version)
        path.write_text(render(version, locked), encoding="utf-8", newline="\n")
        print(f"{_display(path)}: {len(locked)} pacotes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
