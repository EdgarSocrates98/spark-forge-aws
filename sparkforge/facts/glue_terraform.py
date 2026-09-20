"""Leitura do Terraform de job Glue, compartilhada pelos extratores de orquestracao.

ESTE MODULO NAO E EXTRATOR. Ele nao le artefato, nao tem `EXTRACTOR_ID`, nao tem
`EMITTED_KINDS` e nao emite `Fact` nenhum: ele LE facts que `terraform.py` ja extraiu
(`tf.attribute`, `tf.unresolved`) e devolve estrutura Python que as derivacoes
`build_sfn_glue_link` (`stepfunctions.py`) e `build_af_glue_link` (`airflow_dag.py`)
usam para montar os facts delas.

A ausencia de `EMITTED_KINDS` e o que o mantem fora das TRES varreduras do repositorio:
a de `scripts/check_status_numbers.py::_extratores`, a de `pkgutil` em
`tests/test_harness_untrusted.py`, e as duas listas manuais
(`tests/test_rules_catalog_reachability.py`, `tests/test_fixtures_kind_coverage.py`),
cujo `EMITTABLE` faz `frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))` e
levantaria `AttributeError` se alguem o acrescentasse la. O precedente do lugar sao
`runtime_matrix` e `pricing`, que moram em `facts/` pelo mesmo motivo.

As duas funcoes moraram duplicadas em `stepfunctions.py` e `airflow_dag.py` do
incremento do Step Functions ate este: a copia foi deliberada, esta registrada em
`docs/sdd/AIRFLOW_DAG/ship.md`, e tres revisoes finais seguidas conferiram a mao que
elas nao tinham divergido.
"""
from __future__ import annotations

from collections.abc import Sequence

from sparkforge.findings.models import Fact

__all__ = ["glue_jobs_por_nome", "glue_max_retries"]


def glue_jobs_por_nome(facts: Sequence[Fact]) -> dict[str, list[tuple[str, str, str]]]:
    """Nome literal do job -> [(arquivo, endereco, id do fact)], de `tf.attribute` `name`.

    Um mesmo nome pode vir de mais de um recurso, e por isso o valor e LISTA: quem
    chama decide o que fazer com a ambiguidade, e as duas derivacoes a nomeiam em
    `job_definition_ambiguous` em vez de escolher uma.
    """
    nomes: dict[str, list[tuple[str, str, str]]] = {}
    for fact in facts:
        if fact.kind != "tf.attribute":
            continue
        subject = fact.subject or {}
        attrs = fact.attrs or {}
        simbolo = str(subject.get("symbol") or "")
        if not simbolo.startswith("aws_glue_job."):
            continue
        if attrs.get("key") != "name" or attrs.get("block") != "root" or not attrs.get("literal"):
            continue
        arquivo = str(subject.get("file") or "")
        nomes.setdefault(str(attrs.get("value")), []).append((arquivo, simbolo, fact.id))
    return nomes


def glue_max_retries(
    facts: Sequence[Fact], arquivo: str, simbolo: str
) -> tuple[str, int | None, str | None]:
    """(`literal`, n, id), (`absent`, 0, None) ou (`not_literal`, None, id|None).

    O terceiro elemento e o id do `tf.attribute` lido, que entra em `derived_from`.

    `absent` vale 0 porque o atributo nao declarado nao pede retry. Valor interpolado
    vira `tf.unresolved` sem o endereco do recurso (`terraform.py`); por isso qualquer
    `tf.unresolved` de `max_retries` no MESMO arquivo torna a resposta `not_literal` --
    conservador de proposito: nunca um zero que ninguem leu.
    """
    for fact in facts:
        subject = fact.subject or {}
        if fact.kind != "tf.attribute" or subject.get("symbol") != simbolo:
            continue
        if subject.get("file") != arquivo:
            continue
        attrs = fact.attrs or {}
        if attrs.get("key") != "max_retries" or attrs.get("block") != "root":
            continue
        valor = (fact.measures or {}).get("value")
        if attrs.get("literal") and isinstance(valor, int | float) and not isinstance(valor, bool):
            return "literal", int(valor), fact.id
        return "not_literal", None, fact.id
    interpolado = any(
        f.kind == "tf.unresolved"
        and (f.attrs or {}).get("key") == "max_retries"
        and (f.subject or {}).get("file") == arquivo
        for f in facts
    )
    return ("not_literal", None, None) if interpolado else ("absent", 0, None)
