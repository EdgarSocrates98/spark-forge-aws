#!/usr/bin/env python3
"""Gera o SBOM CycloneDX do release, a partir do artefato construido e do lock.

Por que este arquivo existe
===========================

Um release publicado sem SBOM obriga quem o consome a redescobrir, pacote a
pacote, o que ele arrasta junto. A exigencia de supply chain enumera cinco
campos por componente -- pacote, versao, hash, licenca, origem -- e este gerador
produz exatamente esses cinco, sem inventar nenhum:

- pacote e versao vem do lock (`locks/py<versao>.txt`), que e resolvido, nao
  declarado: `PyYAML>=6.0` nao e uma versao, `PyYAML==6.0.3` e.
- hash vem do mesmo lock, um sha256 por distribuicao publicada daquela versao.
- licenca vem do lock, colhida da API do PyPI no momento da geracao dele.
- origem e o `purl` (`pkg:pypi/<nome>@<versao>`), que e o identificador
  canonico, mais a URL do projeto no indice.

O componente raiz nao e "o pacote": e **o artefato**. O sha256 do wheel e o do
sdist entram como componentes do tipo `file`, e e isso que torna o SBOM
associado a UM release e nao a uma versao no abstrato. Dois wheels da mesma
versao construidos de arvores diferentes teriam SBOMs diferentes -- que e a
propriedade que se quer.

Por que o SBOM lista `ruff` e `pytest`
--------------------------------------

Porque o lock e do ambiente inteiro, e omitir o que existe seria uma escolha
editorial dentro de um documento cuja unica serventia e ser completo. O que
distingue nao e a presenca, e o `scope`, que o CycloneDX define para isso:
`required` e o fecho das dependencias de nucleo, `optional` e o que entra so por
extra que o usuario pede, e `excluded` e ferramenta que existe no ambiente que
produz o release e nao dentro do que e publicado. Quem escaneia o SBOM le o
campo; quem receber a lista podada nao teria como saber o que foi tirado.

O escopo nao e adivinhado pelo nome: ele vem de tres resolucoes que
`scripts/gen_lock.py` faz na geracao do lock, porque atribuir escopo a pacote
TRANSITIVO exige percorrer o grafo com marcador de ambiente avaliado. `attrs`
entra por `jsonschema`, que e nucleo -- deduzir isso a mao marcaria dependencia
de runtime como ferramenta de desenvolvimento.

Sem dependencia nova
--------------------

So biblioteca padrao. Existe ferramenta pronta de CycloneDX, e ela faria isso
melhor; ela tambem precisaria estar instalada para o TESTE rodar, e um teste que
vira `skip` quando a ferramenta falta e um teste que deixa de vigiar sem avisar
-- o mesmo defeito que fez `build>=1.0` entrar no extra `dev`. O formato aqui e
um objeto JSON com campos fixos; o custo de escreve-lo e menor que o custo de um
gate que so roda as vezes.

Determinismo
------------

O repositorio constroi wheel reproduzivel bit a bit e prova isso a cada
execucao do gate. Um SBOM com `timestamp` do relogio e `serialNumber` sorteado
quebraria essa propriedade no unico arquivo do release que ninguem checa.
Entao:

- `timestamp` sai de `SOURCE_DATE_EPOCH` quando ela existe -- a MESMA variavel
  que o hatchling usa para os timestamps do zip. Sem ela, sai do relogio, e a
  saida deixa de ser reproduzivel, o que e aceitavel para uma geracao manual e
  nunca acontece no release (o workflow a define).
- `serialNumber` e um UUIDv5 derivado do purl do artefato mais os hashes dos
  arquivos: mesma entrada, mesmo numero de serie.

`tests/test_supply_chain.py` mede as duas coisas gerando duas vezes.

Conformidade com o schema, e por que ela nao e gate
---------------------------------------------------

A saida foi validada contra `bom-1.6.schema.json` oficial do projeto CycloneDX,
sem nenhum erro. Isso NAO virou teste: validar exigiria baixar o schema (e os
dois que ele referencia, `spdx` e `jsf-0.82`) ou commitar copia de terceiro, e
as duas coisas contrariam o resto deste repositorio -- rede em teste, e artefato
de terceiro sem manifesto de integridade. Para repetir a verificacao a mao:

    pip install jsonschema
    # baixe bom-1.6.schema.json, spdx.schema.json e jsf-0.82.schema.json de
    # github.com/CycloneDX/specification/tree/master/schema e valide a saida

O que a suite prova sem rede e o que importa no dia a dia: os campos
obrigatorios existem, cada componente carrega os cinco campos exigidos, e a
saida e deterministica.

Uso
===

    python scripts/gen_sbom.py --dist dist --output dist/sbom.cdx.json
    python scripts/gen_sbom.py --dist dist --python-version 3.10 -o sbom.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gen_lock import load as load_lock  # noqa: E402

SPEC_VERSION = "1.6"
BOM_FORMAT = "CycloneDX"

# A versao de Python do job que produz o release (`.github/workflows/release.yml`
# usa 3.11). O SBOM descreve o fecho de dependencia daquele ambiente, e por isso
# a escolha vai declarada numa propriedade da saida em vez de ficar implicita.
DEFAULT_PYTHON = "3.11"

PROJECT_NAME = "sparkforge-aws"
# Nome do pacote como aparece no NOME DE ARQUIVO do artefato: a normalizacao de
# nome de wheel troca `-` por `_`.
DIST_STEM = PROJECT_NAME.replace("-", "_")

PYPI_PROJECT = "https://pypi.org/project/{name}/{version}/"

# Namespace fixo para o UUIDv5 do `serialNumber`. Um UUID sorteado uma vez e
# escrito aqui como constante: qualquer namespace serve, desde que nao mude --
# mudar renomearia todos os SBOMs ja publicados.
SERIAL_NAMESPACE = uuid.UUID("6f3f1f7e-9f3a-5a2b-8c41-2a7c0d5b9e10")


def project_version() -> str:
    """A versao declarada em `pyproject.toml`.

    Lida do TOML e nao de `sparkforge.__version__` de proposito: o SBOM descreve
    o que o BUILD produziu, e quem define isso e o `pyproject.toml`. Importar o
    pacote traria a versao do que estivesse no `sys.path`, que pode ser outra
    coisa -- e o gate de procedencia deste repositorio existe justamente porque
    esse engano ja aconteceu.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise SystemExit("pyproject.toml sem `version` em [project]")
    return match.group(1)


def project_license() -> str:
    """A licenca do proprio pacote, pelo classificador de `pyproject.toml`.

    O classificador e o unico lugar do `pyproject.toml` que nomeia a licenca em
    vocabulario fechado -- `license = { file = "LICENSE" }` aponta para um texto,
    e ler o texto para adivinhar qual licenca e seria exatamente o chute que este
    repositorio recusa em toda parte.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for match in re.finditer(r'"(License :: [^"]+)"', text):
        return match.group(1).split(" :: ")[-1].strip()
    raise SystemExit("pyproject.toml sem classificador `License ::`")


def project_repository() -> str:
    """A URL do repositorio, lida de `[project.urls]`.

    Lida, e nao escrita aqui: a URL ja existe no `pyproject.toml`, e uma segunda
    copia num script e um endereco que continua apontando para o lugar antigo no
    dia em que o repositorio mudar de dono ou de nome.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^Repository\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if match is None:
        raise SystemExit("pyproject.toml sem `Repository` em [project.urls]")
    return match.group(1)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_files(dist: Path, version: str) -> list[Path]:
    """Os arquivos do release, com o nome conferido contra a versao do projeto.

    A conferencia existe porque `--dist` e um diretorio apontado de fora: um
    diretorio errado -- ou um `dist/` velho de outra versao -- produziria um SBOM
    que descreve bytes que ninguem vai publicar. Um SBOM que descreve o artefato
    errado e pior que nenhum, porque parece prova.
    """
    if not dist.is_dir():
        raise SystemExit(f"--dist aponta para {dist}, que nao e diretorio")

    wheels = sorted(dist.glob(f"{DIST_STEM}-{version}-*.whl"))
    sdists = sorted(dist.glob(f"{DIST_STEM}-{version}.tar.gz"))
    if not wheels or not sdists:
        achado = sorted(p.name for p in dist.iterdir())
        raise SystemExit(
            f"esperava wheel e sdist de {PROJECT_NAME} {version} em {dist}, achei {achado}"
        )
    return wheels + sdists


def timestamp() -> str:
    """Instante do SBOM, de `SOURCE_DATE_EPOCH` quando ela existir.

    Mesma variavel que o hatchling usa para tornar o zip reproduzivel: um SBOM
    com relogio dentro seria o unico arquivo nao-reproduzivel de um release que
    prova reprodutibilidade em todos os outros.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.strip().isdigit():
        moment = dt.datetime.fromtimestamp(int(epoch.strip()), tz=dt.timezone.utc)
    else:
        moment = dt.datetime.now(tz=dt.timezone.utc)
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _license_entry(value: str) -> list[dict]:
    """Sempre `license.name`, nunca `license.id`.

    `id` no CycloneDX significa "este e um identificador SPDX valido", e provar
    isso exigiria a lista SPDX dentro do repositorio -- dado de terceiro para
    manter atualizado, offline, so para escolher entre dois nomes de campo. O
    valor que se tem e o texto que o indice publicou; ele vai como `name`, que e
    o campo que nao afirma mais do que se sabe.
    """
    return [{"license": {"name": value}}]


def component_for(package) -> dict:  # noqa: ANN001 - LockedPackage de gen_lock
    purl = f"pkg:pypi/{package.name.lower()}@{package.version}"
    return {
        "type": "library",
        "bom-ref": purl,
        "name": package.name,
        "version": package.version,
        "purl": purl,
        "scope": package.scope,
        "licenses": _license_entry(package.license),
        # Mais de um hash por componente e o dado real, nao um defeito do
        # gerador: uma versao publicada tem varios arquivos (sdist e um wheel
        # por tag), e o lock carrega o sha256 de cada um porque e assim que
        # `pip install --require-hashes` espera receber.
        "hashes": [{"alg": "SHA-256", "content": digest} for digest in package.hashes],
        "externalReferences": [
            {
                "type": "distribution",
                "url": PYPI_PROJECT.format(name=package.name, version=package.version),
            }
        ],
    }


def build_sbom(dist: Path, python_version: str = DEFAULT_PYTHON) -> dict:
    version = project_version()
    files = artifact_files(dist, version)
    file_hashes = {path.name: sha256_of(path) for path in files}

    root_purl = f"pkg:pypi/{PROJECT_NAME}@{version}"
    serial_seed = root_purl + "|" + "|".join(f"{n}:{h}" for n, h in sorted(file_hashes.items()))
    serial = uuid.uuid5(SERIAL_NAMESPACE, serial_seed)

    packages = load_lock(python_version)

    components: list[dict] = [
        {
            "type": "file",
            "bom-ref": f"file:{name}",
            "name": name,
            "hashes": [{"alg": "SHA-256", "content": digest}],
        }
        for name, digest in sorted(file_hashes.items())
    ]
    components.extend(component_for(package) for package in packages)

    return {
        "bomFormat": BOM_FORMAT,
        "specVersion": SPEC_VERSION,
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "timestamp": timestamp(),
            # A versao do gerador E a versao do projeto: ele nao e distribuido
            # separadamente, mora nesta arvore e muda com ela. Dizer isso aqui
            # evita a leitura errada de que `gen_sbom.py` tem versionamento
            # proprio.
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "scripts/gen_sbom.py",
                        "version": version,
                    }
                ]
            },
            "component": {
                "type": "library",
                "bom-ref": root_purl,
                "name": PROJECT_NAME,
                "version": version,
                "purl": root_purl,
                "licenses": _license_entry(project_license()),
                "externalReferences": [{"type": "vcs", "url": project_repository()}],
            },
            "properties": [
                # O fecho depende da versao de Python e da plataforma para que
                # ele foi resolvido. Sem esta linha, quem le o SBOM leria a
                # lista como se ela valesse em qualquer ambiente -- e ela nao
                # vale: `rpds-py` resolve para versoes diferentes em 3.10 e 3.11.
                {"name": "sparkforge:lock", "value": f"locks/py{python_version}.txt"},
                {"name": "sparkforge:resolved-for", "value": f"cpython-{python_version}"},
            ],
        },
        "components": components,
    }


def render(sbom: dict) -> str:
    """JSON estavel: chaves na ordem em que foram montadas, indentacao fixa e
    `ensure_ascii=False`. Reordenar chaves a cada geracao produziria diff onde
    nada mudou."""
    return json.dumps(sbom, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--dist",
        type=Path,
        required=True,
        help="Diretorio com o wheel e o sdist ja construidos e provados.",
    )
    parser.add_argument(
        "--python-version",
        default=DEFAULT_PYTHON,
        help=f"Qual lock descrever (default: {DEFAULT_PYTHON}, o Python do job de release).",
    )
    parser.add_argument("-o", "--output", type=Path, required=True, help="Arquivo de saida.")
    args = parser.parse_args(argv)

    sbom = build_sbom(args.dist.resolve(), args.python_version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(sbom), encoding="utf-8", newline="\n")
    print(f"{args.output}: {len(sbom['components'])} componentes, spec CycloneDX {SPEC_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
