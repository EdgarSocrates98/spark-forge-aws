"""Compoe os artefatos de um job num unico `list[Fact]` para `assess()`.

POR QUE FORA DE `assess()`. `assess()` e puro sobre facts, e e isso que torna
testavel julgar uma migracao sem tocar disco -- um teste monta os facts a mao e
pergunta o veredito. Composicao e I/O, e I/O tem lugar proprio: o mesmo motivo
pelo qual `extract_migration_tree` nao vive dentro de `judge`.

O QUE ENTRA, E POR QUE CADA UM E DECIDIDO DIFERENTE.

- Codigo, `requirements*.txt` e `.jar` entram SEMPRE. Sao o job.
- `.tf` entra quando existe. Um arquivo com extensao `.tf` E Terraform -- nao ha
  o que adivinhar --, e sem ele a area `SF-LF` fica sem produtor: a topologia de
  FGAC e declarada no Terraform do job, nunca no codigo Python.
- O dump de metadados Iceberg entra so do diretorio em que o COLETOR o grava
  (`.sparkforge/artifacts/iceberg/`). Um `.json` qualquer da arvore nao e dump:
  varrer a arvore inteira faria `package-lock.json` e `tsconfig.json` passarem
  pelo parser de metadados e virarem `iceberg.unresolved` -- ruido que afirma
  que alguem tentou ler metadados de um arquivo que ninguem disse ser metadado.
  E o dump e o que traz IDENTIDADE DE TABELA: `mig.table_format` observa
  `format-version` numa linha de fonte Python e nao sabe de que tabela ela
  fala; `iceberg.table_property` sabe, e e o que faz `SF-ENV-002` acusar por
  tabela em vez de o gate bloquear por job.
- O inventario de consumidores entra so na CONVENCAO que
  `sparkforge/facts/consumers.py` declara (`.sparkforge/consumers.yaml`, ou
  `.sparkforge/consumers/` dividido por dominio). Varrer todo `*.yaml` da arvore
  acharia o inventario e, junto com ele, todo workflow de CI e todo arquivo de
  configuracao -- cada um virando um `env.consumers_analyzed` que afirma
  "inventario lido" sobre arquivo que nao e inventario. Fact e observacao
  ancorada; afirmar que um `docker-compose.yaml` e um inventario com zero
  consumidores e afirmacao falsa, nao silencio.

O LIMITE, DECLARADO. Inventario fora da convencao nao e lido, e o silencio
aparece: sem `env.consumer`, o eixo `consumidor` de `assess()` nasce `BLOCKED`
nomeando o arquivo que o preencheria. Nao ler e diferente de ler e nao achar
nada, e as duas coisas continuam distinguiveis.
"""
from __future__ import annotations

from pathlib import Path

from sparkforge.facts.consumers import extract_consumers_path, extract_consumers_tree
from sparkforge.facts.iceberg_metadata import extract_iceberg_metadata_tree
from sparkforge.facts.migration import extract_migration_path, extract_migration_tree
from sparkforge.facts.terraform import extract_terraform_tree
from sparkforge.findings.models import Fact, sort_facts

# Onde o inventario de consumidores e procurado, relativo a raiz do job. Os dois
# caminhos sao a convencao declarada no docstring de `sparkforge/facts/
# consumers.py` -- arquivo unico, ou diretorio dividido por dominio.
INVENTARIO_ARQUIVO = Path(".sparkforge") / "consumers.yaml"
INVENTARIO_DIRETORIO = Path(".sparkforge") / "consumers"

# Onde `sparkforge collect iceberg-metadata` GRAVA o dump de metadados -- ver
# `sparkforge/collect/aws.py`, que monta
# `.sparkforge/artifacts/iceberg/<db_tabela>.json`. Ler dai nao inventa
# convencao nova: usa a que o coletor ja publica.
DUMPS_ICEBERG = Path(".sparkforge") / "artifacts" / "iceberg"


def collect(path: Path | str, repo_root: Path | None = None) -> list[Fact]:
    """Uniao ordenada dos facts de todo artefato do job sob `path`.

    Aceita DIRETORIO ou arquivo `.py`, a mesma convencao de `analyze_*`: o
    diretorio e o caso que interessa, porque um pin de dependencia e um binario
    de Scala nao tem linha de fonte Python e sobrevivem a troca de runtime, mas
    um `.py` sozinho continua respondido.

    `repo_root` ancora o path relativo dos facts. Sem ele, a ancora e a propria
    raiz -- que e o que a CLI quer, porque o usuario aponta para o diretorio do
    job e nao para o repositorio que o contem.
    """
    raiz = Path(path)
    base = repo_root or (raiz if raiz.is_dir() else raiz.parent)

    if not raiz.is_dir():
        return extract_migration_path(raiz, base)

    facts: list[Fact] = list(extract_migration_tree(raiz, repo_root=base))

    # `any()` sobre o gerador, nao `list()`: basta saber que existe um.
    if any(raiz.rglob("*.tf")):
        facts.extend(extract_terraform_tree(raiz, repo_root=base))

    inventario = raiz / INVENTARIO_ARQUIVO
    if inventario.is_file():
        facts.extend(extract_consumers_path(inventario, base))

    diretorio = raiz / INVENTARIO_DIRETORIO
    if diretorio.is_dir():
        facts.extend(extract_consumers_tree(diretorio, repo_root=base))

    dumps = raiz / DUMPS_ICEBERG
    if dumps.is_dir():
        facts.extend(extract_iceberg_metadata_tree(dumps, repo_root=base))

    return sort_facts(facts)
