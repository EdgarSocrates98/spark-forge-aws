"""Guarda do modulo auxiliar que le o Terraform de job Glue.

Os tres testes cobrem coisas diferentes: que a definicao e UNICA (AC1), que ela
responde o mesmo de antes (AC2), e que o modulo NAO e tratado como extrator (AC3).

O terceiro existe por causa de uma regra permanente do `CLAUDE.md` -- "Extrator novo
entra nas duas listas manuais de teste e na medida de snippet" -- que esta certa e NAO
se aplica aqui. Quem seguir o habito e acrescentar `glue_terraform` aquelas listas leva
um `AttributeError` dentro de um `frozenset().union(...)`, sem contexto nenhum. Este
teste transforma isso num vermelho que explica.
"""
from __future__ import annotations

from pathlib import Path

from sparkforge.facts import airflow_dag, glue_terraform, stepfunctions
from sparkforge.facts.glue_terraform import glue_jobs_por_nome, glue_max_retries
from sparkforge.findings.models import Fact

RAIZ = Path(__file__).resolve().parents[1]


def _tf_name(arquivo: str, simbolo: str, valor: str) -> Fact:
    return Fact(
        kind="tf.attribute",
        subject={"file": arquivo, "symbol": simbolo, "line": 1},
        attrs={"key": "name", "block": "root", "literal": True, "value": valor},
    )


def _tf_retries(arquivo: str, simbolo: str, valor, literal: bool = True) -> Fact:
    return Fact(
        kind="tf.attribute",
        subject={"file": arquivo, "symbol": simbolo, "line": 2},
        measures={"value": valor},
        attrs={"key": "max_retries", "block": "root", "literal": literal, "value": valor},
    )


def test_a_definicao_e_unica_e_os_dois_extratores_importam():
    """AC1: uma definicao, e os dois extratores usam ELA.

    A conferencia e por IDENTIDADE (`is`), nao por nome: um `from ... import` que
    trouxesse uma copia igual passaria num teste de nome e falha aqui.
    """
    assert stepfunctions.glue_jobs_por_nome is glue_terraform.glue_jobs_por_nome
    assert stepfunctions.glue_max_retries is glue_terraform.glue_max_retries
    assert airflow_dag.glue_jobs_por_nome is glue_terraform.glue_jobs_por_nome
    assert airflow_dag.glue_max_retries is glue_terraform.glue_max_retries

    # E nenhuma copia local sobreviveu.
    for nome in ("stepfunctions", "airflow_dag"):
        fonte = (RAIZ / "sparkforge" / "facts" / f"{nome}.py").read_text(encoding="utf-8")
        assert "def _glue_jobs_por_nome" not in fonte, nome
        assert "def _max_retries" not in fonte, nome


def test_as_tres_origens_de_max_retries_e_o_indice_por_nome():
    """AC2: o comportamento e o de antes, origem por origem."""
    facts = [
        _tf_name("a.tf", "aws_glue_job.carga", "carga-diaria"),
        _tf_retries("a.tf", "aws_glue_job.carga", 3),
        _tf_name("b.tf", "aws_glue_job.outro", "carga-diaria"),
        _tf_name("c.tf", "aws_glue_job.semretry", "sem-retry"),
        # Ruido que o indice tem de ignorar: outro recurso, outro bloco, nao literal.
        Fact(
            kind="tf.attribute",
            subject={"file": "d.tf", "symbol": "aws_s3_bucket.x", "line": 1},
            attrs={"key": "name", "block": "root", "literal": True, "value": "balde"},
        ),
        Fact(
            kind="tf.attribute",
            subject={"file": "d.tf", "symbol": "aws_glue_job.dinamico", "line": 1},
            attrs={"key": "name", "block": "root", "literal": False, "value": "${var.n}"},
        ),
    ]

    nomes = glue_jobs_por_nome(facts)
    assert set(nomes) == {"carga-diaria", "sem-retry"}
    assert [(a, s) for a, s, _ in nomes["carga-diaria"]] == [
        ("a.tf", "aws_glue_job.carga"),
        ("b.tf", "aws_glue_job.outro"),
    ]
    # O terceiro elemento e o id do fact lido, que entra em `derived_from`.
    assert nomes["sem-retry"][0][2] == facts[3].id

    # literal
    assert glue_max_retries(facts, "a.tf", "aws_glue_job.carga") == ("literal", 3, facts[1].id)
    # absent vale 0: atributo nao declarado nao pede retry
    assert glue_max_retries(facts, "c.tf", "aws_glue_job.semretry") == ("absent", 0, None)

    # not_literal pelo proprio atributo
    interpolado = [*facts, _tf_retries("e.tf", "aws_glue_job.interp", "${var.r}", literal=False)]
    origem, n, fid = glue_max_retries(interpolado, "e.tf", "aws_glue_job.interp")
    assert (origem, n) == ("not_literal", None)
    assert fid == interpolado[-1].id

    # not_literal CONSERVADOR: o tf.unresolved nao carrega o endereco do recurso, entao
    # qualquer um de `max_retries` no MESMO arquivo contamina o arquivo inteiro. Nunca
    # um zero que ninguem leu.
    contaminado = [
        _tf_name("f.tf", "aws_glue_job.sem", "sem-atributo"),
        Fact(
            kind="tf.unresolved",
            subject={"file": "f.tf", "symbol": "", "line": 9},
            attrs={"key": "max_retries", "reason": "interpolation"},
        ),
    ]
    assert glue_max_retries(contaminado, "f.tf", "aws_glue_job.sem") == ("not_literal", None, None)


def test_o_modulo_auxiliar_nao_conta_como_extrator():
    """AC3: `EMITTED_KINDS` e o que distingue extrator de auxiliar nas varreduras.

    A regra do `CLAUDE.md` que manda por extrator novo nas duas listas manuais NAO vale
    aqui, e este teste e o lugar onde isso esta escrito de forma executavel. A lista
    das varreduras conferidas esta no docstring de `sparkforge/facts/glue_terraform.py`;
    os tres arquivos varridos abaixo sao os que CITARIAM o modulo pelo nome, nao todas
    elas -- as que descobrem por `pkgutil`/`glob` ja o ignoram por nao ter o atributo.
    """
    assert not hasattr(glue_terraform, "EMITTED_KINDS")
    assert not hasattr(glue_terraform, "EXTRACTOR_ID")
    assert not [n for n in dir(glue_terraform) if n.startswith("extract_")]

    # As duas listas manuais fazem union de `EMITTED_KINDS` sobre `EXTRACTORS`, com
    # sintaxe diferente porque o container e diferente: em
    # test_rules_catalog_reachability.py e
    # `frozenset().union(*(m.EMITTED_KINDS for m in EXTRACTORS))`, e em
    # test_fixtures_kind_coverage.py e `... for m in EXTRACTORS.values())`, porque la
    # `EXTRACTORS` e dict. Mesmo efeito: o modulo la dentro levantaria AttributeError
    # na COLETA, e a mensagem nao diria por que. A conferencia e por texto para nao
    # importar os modulos de teste um do outro.
    for arquivo in (
        "tests/test_rules_catalog_reachability.py",
        "tests/test_fixtures_kind_coverage.py",
        "tests/test_harness_untrusted.py",
    ):
        fonte = (RAIZ / arquivo).read_text(encoding="utf-8")
        assert "glue_terraform" not in fonte, (
            f"{arquivo} cita glue_terraform. Ele NAO e extrator: nao emite kind, nao le "
            "artefato, e as listas manuais fazem union de EMITTED_KINDS. Ver AC3 de "
            "docs/sdd/GLUE_TERRAFORM/define.md."
        )
