"""`lakeformation.*` -- o modelo de acesso que a definicao do job DECLARA.

## A lacuna que este modulo fecha, medida em 2026-09-09

O motor emite 200 kinds. Busca por `lakeformation` entre eles devolve **zero**:
o SparkForge tem duas regras `SF-LF-*`, e as duas leem `tf.attribute` cru --
comparam a chave `--enable-lakeformation-fine-grained-access` com o literal
`"true"` dentro do proprio `when`. Funciona para as duas porque as duas
perguntam por uma chave EXATA.

Tres perguntas desta area **nao** sao de chave exata, e nenhuma delas e
escrevivel no DSL de regra:

  1. "este catalogo Iceberg e o session catalog?"  -- a chave e
     `spark.sql.catalog.<nome>`, e o `<nome>` e o dado;
  2. "este job declara FGAC e FTA ao mesmo tempo?" -- o marcador de FTA e
     `spark.sql.catalog.<nome>.glue.lakeformation-enabled`, mesmo problema;
  3. "o EMRFS foi restaurado?"                     -- exige saber que
     `spark.hadoop.fs.s3.impl` vale a classe do EMRFS E que o resolver de
     credencial do Lake Formation foi pedido, que sao dois facts distintos.

`sparkforge/rules/expr.py::_CMP_OPS` tem `==`, `!=`, `<`, `<=`, `>`, `>=` e mais
nada -- sem `in`, sem `startswith`, sem chamada de funcao (`ast.Call` levanta
`ExprError` por construcao, e isso e desenho de seguranca, nao lacuna). `where`
compara igualdade e so. **Escrever a regra primeiro produziria regra que nao
consegue dizer o que precisa dizer**, e a saida nao e afrouxar o avaliador de
expressao: e derivar o predicado num fact, que e onde predicado mora neste
motor.

## Derivacao pura, no molde de `bridge.py` e `exception.py`

Nao le artefato. Le a UNIAO dos facts que os extratores ja resolveram, e as
tres superficies de configuracao chegam com a mesma forma (`attrs.key`,
`attrs.value`):

    tf.spark_conf        `--conf` do `aws_glue_job`          (Terraform)
    pyspark.conf_set     `spark.conf.set(...)` no codigo     (codigo)
    spark.conf_effective `SparkListenerEnvironmentUpdate`    (execucao)

`attrs.source` diz por qual delas o fato entrou, e o campo existe porque as
tres **nao valem o mesmo**: a de execucao foi medida, as outras duas foram
pedidas. Este modulo nao elege vencedora -- eleger seria decidir precedencia
calada, e precedencia e julgamento. Quem quiser so a medida filtra por
`source: event_log`.

## O que ele NAO afirma

- **Nao diz se a configuracao esta certa.** `is_session_catalog: false` e
  observacao sobre o nome do catalogo, nao acusacao: a restricao de session
  catalog e de FGAC, e a propria AWS publica exemplo de FTA com catalogo de
  nome arbitrario (`knowledge/glue/lakeformation-fgac.md` §4 e §5).
- **Nao decide o filesystem default.** Ele registra o que foi DECLARADO. Que o
  default virou S3A no Glue 5.1 e fronteira de versao, e fronteira de versao
  mora no `runtime_scope` da regra.
- **Nao infere permissao nenhuma.** Grant do Lake Formation e policy de IAM nao
  entram em nenhum artefato que este motor colete hoje, e inventar
  `lakeformation.grant` a partir de configuracao de Spark seria afirmar o que
  ninguem mediu. A lacuna sai nomeada em `lakeformation.unresolved`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sparkforge.findings.models import Fact, sort_facts

EXTRACTOR_ID = "lakeformation@0.1.0"

EMITTED_KINDS = frozenset(
    {
        "lakeformation.access_model",
        "lakeformation.iceberg_catalog",
        "lakeformation.filesystem",
        "lakeformation.unresolved",
    }
)

# O argumento de job que liga FGAC. E argumento, nunca conf de Spark -- a
# documentacao o descreve em `default_arguments`, e e por isso que ele entra por
# `tf.attribute` e nao pelas tres superficies de conf.
FGAC_ARGUMENT = "--enable-lakeformation-fine-grained-access"

# O nome do session catalog em Spark. Nao e configuravel: `spark_catalog` e o
# identificador que o proprio Spark reserva para o catalogo de sessao, e a
# restricao da AWS ("only ... session catalog and not arbitrarily named
# catalogs") se resolve nesse literal.
SESSION_CATALOG = "spark_catalog"

# As tres superficies de conf, e o rotulo de procedencia de cada uma.
_CONF_KINDS = {
    "spark.conf_effective": "event_log",
    "tf.spark_conf": "terraform",
    "pyspark.conf_set": "code",
}

_CATALOG_PREFIX = "spark.sql.catalog."

# Sufixo que marca o catalogo como participante do credential vending do Lake
# Formation. A chave aparece na pagina de Full Table Access; na de FGAC ela nao
# aparece, e o que isso significa sob FGAC esta na §7 do documento de
# conhecimento, como a verificar.
_LF_ENABLED_SUFFIX = ".glue.lakeformation-enabled"

# Chave de EMRFS, e ela e literal. Sob S3A esta chave nao existe e nao produz
# erro: o valor e simplesmente ignorado. E esse silencio que a torna interessante
# de registrar.
_RESOLVER_KEY = "spark.hadoop.fs.s3.credentialsResolverClass"
_LF_RESOLVER = "AWSLakeFormationCredentialResolver"

_FS_IMPL_KEY = "spark.hadoop.fs.s3.impl"
_EMRFS_IMPL = "com.amazon.ws.emr.hadoop.fs.EmrFileSystem"


def build_lakeformation(facts: Sequence[Fact]) -> list[Fact]:
    """Deriva `lakeformation.*` da uniao dos facts. Sem artefato, sem juizo."""
    saida: list[Fact] = []
    saida.extend(_access_models(facts))
    saida.extend(_iceberg_catalogs(facts))
    saida.extend(_filesystems(facts))
    saida.extend(_unresolved(facts, saida))
    return sort_facts(saida)


def _conf_facts(facts: Sequence[Fact]) -> list[tuple[Fact, str]]:
    """Os facts de conf das tres superficies, cada um com seu rotulo de origem.

    Valor redigido nao entra. `secrets.redact` roda ANTES de qualquer parse
    (`event_log.py`, `terraform.py`), e um valor que virou `<redigido>` nao
    sustenta afirmacao nenhuma sobre classe de catalogo ou de filesystem --
    compara-lo com `_EMRFS_IMPL` daria `False` por um motivo que nao e o
    verdadeiro.
    """
    saida: list[tuple[Fact, str]] = []
    for fact in facts:
        origem = _CONF_KINDS.get(fact.kind)
        if origem is None:
            continue
        if (fact.attrs or {}).get("redacted"):
            continue
        if not (fact.attrs or {}).get("key"):
            continue
        saida.append((fact, origem))
    return saida


def _access_models(facts: Sequence[Fact]) -> list[Fact]:
    """Um fact por recurso que DECLARA o argumento de FGAC.

    O valor entra verbatim em `attrs.declared_value` e a leitura booleana fica
    em `fgac_enabled`. Os dois existem porque `"false"` declarado nao e o mesmo
    que ausente: o primeiro e uma decisao que alguem escreveu, e ha regra que
    precisa distinguir os dois (o molde e `SF-ERR-002`, que separa a flag
    desligada da flag ausente).
    """
    saida: list[Fact] = []
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        attrs = fact.attrs or {}
        if attrs.get("key") != FGAC_ARGUMENT:
            continue
        if attrs.get("block") != "default_arguments":
            continue
        valor = str(attrs.get("value", ""))
        saida.append(
            Fact(
                kind="lakeformation.access_model",
                subject=dict(fact.subject or {}),
                measures={},
                attrs={
                    "model": "fgac" if valor == "true" else "none",
                    "fgac_enabled": valor == "true",
                    "declared_value": valor,
                    "source": "terraform",
                    "extractor": EXTRACTOR_ID,
                },
                provenance=fact.provenance,
            )
        )
    return saida


def _catalog_name(key: str) -> str | None:
    """`spark.sql.catalog.<nome>` -> `<nome>`; qualquer outra coisa -> None.

    So a forma de DOIS segmentos depois do prefixo e nome de catalogo:
    `spark.sql.catalog.foo` declara o catalogo `foo`, e
    `spark.sql.catalog.foo.warehouse` e propriedade dele. A excecao sao as
    chaves que a AWS publica sem catalogo nenhum no meio --
    `spark.sql.catalog.dropDirectoryBeforeTable.enabled` e as irmas dela --, e
    elas caem fora por terem sufixo, que e o mesmo criterio.
    """
    if not key.startswith(_CATALOG_PREFIX):
        return None
    resto = key[len(_CATALOG_PREFIX) :]
    if not resto or "." in resto:
        return None
    return resto


def _iceberg_catalogs(facts: Sequence[Fact]) -> list[Fact]:
    """Um fact por (catalogo, superficie), com o que a superficie declarou dele.

    O nome do catalogo e a chave da agregacao porque e ele que a restricao da
    AWS nomeia. `impl` e `lakeformation_enabled` sao propriedades DELE, e chegam
    por chaves diferentes -- juntar as duas aqui e o que torna a regra
    escrevivel com igualdade pura.
    """
    # (nome, origem) -> {impl, lakeformation_enabled, anchor}
    acumulado: dict[tuple[str, str], dict[str, Any]] = {}

    for fact, origem in _conf_facts(facts):
        attrs = fact.attrs or {}
        key = str(attrs["key"])
        valor = str(attrs.get("value", ""))

        nome = _catalog_name(key)
        if nome is not None:
            entrada = acumulado.setdefault((nome, origem), {})
            entrada["impl"] = valor
            entrada.setdefault("anchor", fact)
            continue

        if key.startswith(_CATALOG_PREFIX) and key.endswith(_LF_ENABLED_SUFFIX):
            miolo = key[len(_CATALOG_PREFIX) : -len(_LF_ENABLED_SUFFIX)]
            if not miolo or "." in miolo:
                continue
            entrada = acumulado.setdefault((miolo, origem), {})
            entrada["lakeformation_enabled"] = valor == "true"
            entrada.setdefault("anchor", fact)

    saida: list[Fact] = []
    for (nome, origem), dados in acumulado.items():
        anchor: Fact = dados["anchor"]
        saida.append(
            Fact(
                kind="lakeformation.iceberg_catalog",
                subject=dict(anchor.subject or {}),
                measures={},
                attrs={
                    "catalog_name": nome,
                    "is_session_catalog": nome == SESSION_CATALOG,
                    "catalog_impl": dados.get("impl", ""),
                    "lakeformation_enabled": bool(dados.get("lakeformation_enabled")),
                    "source": origem,
                    "extractor": EXTRACTOR_ID,
                },
                provenance=anchor.provenance,
            )
        )
    return saida


def _filesystems(facts: Sequence[Fact]) -> list[Fact]:
    """Um fact por superficie que declara alguma coisa sobre o filesystem S3.

    As duas chaves sao literais e independentes, e e a combinacao delas que
    interessa: pedir o resolver de credencial do Lake Formation SEM restaurar o
    EMRFS e a configuracao que nao produz erro e nao produz efeito.
    """
    # origem -> {resolver, impl, anchor}
    acumulado: dict[str, dict[str, Any]] = {}

    for fact, origem in _conf_facts(facts):
        attrs = fact.attrs or {}
        key = str(attrs["key"])
        valor = str(attrs.get("value", ""))
        if key == _RESOLVER_KEY:
            entrada = acumulado.setdefault(origem, {})
            entrada["resolver"] = valor
            entrada.setdefault("anchor", fact)
        elif key == _FS_IMPL_KEY:
            entrada = acumulado.setdefault(origem, {})
            entrada["impl"] = valor
            entrada.setdefault("anchor", fact)

    saida: list[Fact] = []
    for origem, dados in acumulado.items():
        anchor: Fact = dados["anchor"]
        resolver = str(dados.get("resolver", ""))
        impl = str(dados.get("impl", ""))
        saida.append(
            Fact(
                kind="lakeformation.filesystem",
                subject=dict(anchor.subject or {}),
                measures={},
                attrs={
                    "lf_credentials_resolver_declared": _LF_RESOLVER in resolver,
                    "emrfs_restored": impl == _EMRFS_IMPL,
                    "fs_s3_impl": impl,
                    "source": origem,
                    "extractor": EXTRACTOR_ID,
                },
                provenance=anchor.provenance,
            )
        )
    return saida


def _unresolved(facts: Sequence[Fact], derivados: Sequence[Fact]) -> list[Fact]:
    """A lacuna, nomeada -- e ela e sobre PERMISSAO, que nenhum artefato traz.

    A recusa e emitida quando o case tem modelo de acesso declarado: sem isso,
    todo case do repositorio ganharia uma recusa sobre Lake Formation, e recusa
    que aparece sempre nao informa nada. Com FGAC ou FTA declarado, a ausencia
    de grant e de policy passa a ser uma lacuna REAL do diagnostico, porque a
    autorizacao da escrita mora exatamente ali (§2 e §6 do documento de
    conhecimento).
    """
    modelos = [f for f in derivados if f.kind == "lakeformation.access_model"]
    catalogos_lf = [
        f
        for f in derivados
        if f.kind == "lakeformation.iceberg_catalog"
        and (f.attrs or {}).get("lakeformation_enabled")
    ]
    if not modelos and not catalogos_lf:
        return []

    ancora = (modelos or catalogos_lf)[0]
    return [
        Fact(
            kind="lakeformation.unresolved",
            subject=dict(ancora.subject or {}),
            measures={},
            attrs={
                "reason": "permissoes_nao_coletadas",
                "missing": [
                    "lake_formation_grants",
                    "iam_role_policy",
                    "s3_registered_location",
                ],
                "unblocked_by": (
                    "coletar os grants do Lake Formation sobre a tabela alvo, a "
                    "policy do runtime role e o registro da localizacao S3 -- "
                    "nenhum dos tres entra em artefato que este motor colete hoje"
                ),
                "extractor": EXTRACTOR_ID,
            },
            provenance=ancora.provenance,
        )
    ]


__all__ = [
    "EMITTED_KINDS",
    "EXTRACTOR_ID",
    "FGAC_ARGUMENT",
    "SESSION_CATALOG",
    "build_lakeformation",
]
