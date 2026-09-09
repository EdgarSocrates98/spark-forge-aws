"""A area SF-ERR, e o teste que decide se a integracao vale alguma coisa.

O matcher antigo casava a palavra `NoSuchMethodError` em QUALQUER log e afirmava
`confidence=0.98`, ignorando o `evidence_required` que a propria assinatura de
`knowledge/errors/` declara. A frente inteira existe para fechar isso: o
`evidence_required` vira `requires_facts` de verdade, e a regra fica muda
enquanto os facts que a assinatura pede nao estiverem no case.

**O `error.signature_match` destes testes NAO e escrito a mao.** Ele sai de
`build_signature_matches` sobre um `spark.exception` construido aqui, lendo o
catalogo real de `knowledge/errors/`. Um fact fabricado provaria que o YAML da
regra casa com o YAML do teste; passar pelo matcher prova que a regra casa com o
que o extrator REALMENTE emite -- que e a unica pergunta que interessa.

As formas de `mig.jar_binary` e `tf.attribute` foram MEDIDAS no corpus de
`fixtures/` antes de virarem helper, e a medida esta registrada em
`_jar_binary` e `_tf_attribute`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from sparkforge.errors.matcher import build_signature_matches
from sparkforge.findings.models import Fact
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
ASSINATURAS = ROOT / "knowledge" / "errors"

# `runtime_scope: {glue: ">=6.0"}` nas duas regras. Sem este runtime elas sao
# puladas por escopo, e todo teste de fronteira passaria por SKIP -- verde sem
# nunca ter olhado para a regra, que e o modo de falha que
# `tests/test_rules_emrs_boundary.py` documenta.
GLUE_60 = {"glue": "6.0"}

PROV = {"artifact": "eventlog.json", "artifact_sha256": "", "extractor": "test"}


# ---------------------------------------------------------------------------
# Helpers -- cada um com a forma medida no corpus, nao a forma imaginada.
# ---------------------------------------------------------------------------


def _excecao(classe: str, causas: list[str] | None = None) -> Fact:
    """Forma de `sparkforge/facts/exception.py`: classe, cabeca da mensagem,
    `is_chained` e `caused_by[]`."""
    return Fact(
        kind="spark.exception",
        subject={"type": "spark_stage", "stage": 7},
        measures={},
        attrs={
            "exception_class": classe,
            "message_head": "com.exemplo.Conector.abrir(Ljava/lang/String;)V",
            "is_chained": bool(causas),
            "caused_by": list(causas or []),
        },
        provenance=PROV,
    )


def _match(classe: str, causas: list[str] | None = None) -> list[Fact]:
    """`error.signature_match` REAL, produzido pelo matcher sobre o catalogo de
    assinaturas do repositorio."""
    return build_signature_matches([_excecao(classe, causas)])


def _jar_binary(scala: str = "2.12") -> Fact:
    """Forma MEDIDA em `fixtures/migration/jar_binary/expected/facts.json`:

        subject: {type: source_location, file: <nome do jar>, line: 0, col: 0,
                  symbol: "", snippet: ""}
        measures: {}
        attrs:    {scala: "2.12", scala_minor: 12}

    `scala_minor` so existe quando o major capturado e `2` -- um jar cujo nome
    nao encodifica versao de Scala fica SEM a chave, e e por isso que
    `_jar_opaco` existe separado.
    """
    attrs: dict[str, Any] = {"scala": scala}
    major, _, minor = scala.partition(".")
    if major == "2":
        attrs["scala_minor"] = int(minor)
    return Fact(
        kind="mig.jar_binary",
        subject={
            "type": "source_location",
            "file": f"conector_{scala}-1.4.0.jar",
            "line": 0,
            "col": 0,
            "symbol": "",
            "snippet": "",
        },
        measures={},
        attrs=attrs,
        provenance={"artifact": f"conector_{scala}-1.4.0.jar", "extractor": "test"},
    )


def _jar_opaco() -> Fact:
    """Jar cujo nome nao encodifica Scala nenhum: `attrs.scala_minor` AUSENTE.

    Pode ser Java puro. Caminho ausente vira `ExprError` no avaliador, logo
    `False` -- a regra fica muda em vez de mandar recompilar contra 2.13 um
    artefato que nunca teve Scala.
    """
    return Fact(
        kind="mig.jar_binary",
        subject={
            "type": "source_location",
            "file": "minhalib-1.0.jar",
            "line": 0,
            "col": 0,
            "symbol": "",
            "snippet": "",
        },
        measures={},
        attrs={"scala": ""},
        provenance={"artifact": "minhalib-1.0.jar", "extractor": "test"},
    )


def _tf_attribute(key: str, value: str, block: str = "root") -> Fact:
    """Forma MEDIDA em `fixtures/tfdiff/glue_job_novo/expected/facts.json`:

        subject: {type: tf_resource, file: main.tf, line: N, symbol: <tipo>.<nome>}
        attrs:   {key, value, present, literal, block, ...}

    `block` e `root` para atributo de raiz de `aws_glue_job` (`glue_version`) e
    `default_arguments` para argumento de job (`--user-jars-first`) -- os dois
    valores foram contados no corpus.
    """
    return Fact(
        kind="tf.attribute",
        subject={
            "type": "tf_resource",
            "file": "main.tf",
            "line": 8,
            "symbol": "aws_glue_job.etl_pedidos",
        },
        measures={},
        attrs={
            "key": key,
            "value": value,
            "present": True,
            "literal": True,
            "block": block,
        },
        provenance={"artifact": "main.tf", "extractor": "test"},
    )


_GLUE_VERSION = _tf_attribute("glue_version", "6.0")
_USER_JARS_FIRST = _tf_attribute("--user-jars-first", "true", block="default_arguments")


def _judge(facts, runtime=None) -> list:
    # `GLUE_60 if runtime is None` e nao `runtime or GLUE_60`: o dicionario
    # VAZIO e o caso de teste que interessa (runtime nao detectado), e ele e
    # falsy -- o `or` o trocaria em silencio pelo default e o teste passaria
    # medindo outra coisa.
    return judge(facts, load_catalog(), GLUE_60 if runtime is None else runtime)


def _skipped(facts, runtime=None) -> dict[str, dict]:
    _, pulados = judge(
        facts,
        load_catalog(),
        GLUE_60 if runtime is None else runtime,
        return_skipped=True,
    )
    return {p["rule_id"]: p for p in pulados}


def _ids(findings) -> list[str]:
    return sorted(f.rule_id for f in findings)


def _regras_da_area() -> list[dict]:
    return [r for r in load_catalog() if r["id"].startswith("SF-ERR-")]


def _kinds_emitidos() -> set[str]:
    """Todo kind que algum extrator do motor declara em `EMITTED_KINDS`.

    Varre `sparkforge/facts/*.py` E `sparkforge/errors/matcher.py`, porque o
    matcher mora fora de `facts/` e as varreduras automaticas do repositorio
    nao o alcancam -- ele so e visto pelas listas manuais.
    """
    import importlib
    import pkgutil

    import sparkforge.facts as pacote
    from sparkforge.errors.matcher import EMITTED_KINDS as MATCHER_KINDS

    kinds: set[str] = set(MATCHER_KINDS)
    for modulo in pkgutil.iter_modules(pacote.__path__):
        alvo = importlib.import_module(f"sparkforge.facts.{modulo.name}")
        kinds |= set(getattr(alvo, "EMITTED_KINDS", ()) or ())
    return kinds


# ---------------------------------------------------------------------------
# O teste que decide a entrega.
# ---------------------------------------------------------------------------


class TestRegraExigeAEvidenciaDaAssinatura:
    """`evidence_required` da assinatura vira `requires_facts` de verdade."""

    def test_nao_dispara_so_com_a_excecao(self):
        facts = [_excecao("java.lang.NoSuchMethodError"), *_match("java.lang.NoSuchMethodError")]
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-001"]

    def test_a_recusa_tem_nome_e_lista_o_que_falta(self):
        """Silencio nao basta: o motor precisa DIZER qual fact destrava."""
        facts = [_excecao("java.lang.NoSuchMethodError"), *_match("java.lang.NoSuchMethodError")]
        pulo = _skipped(facts)["SF-ERR-001"]
        assert pulo["reason"] == "requires_facts"
        assert pulo["missing"] == ["mig.jar_binary", "tf.attribute"]

    def test_dispara_com_a_evidencia_completa(self):
        facts = [
            _excecao("java.lang.NoSuchMethodError"),
            *_match("java.lang.NoSuchMethodError"),
            _jar_binary(scala="2.12"),
            _GLUE_VERSION,
        ]
        assert [f for f in _judge(facts) if f.rule_id == "SF-ERR-001"]

    def test_o_jar_sozinho_com_o_iac_tambem_nao_basta(self):
        """A direcao oposta: sem a excecao nao ha achado `confirmed`.

        `SF-SPARK4-004` continua afirmando o mesmo defeito de forma ESTRUTURAL
        sobre estes mesmos facts -- e por isso a assercao e sobre `SF-ERR-001`
        especificamente, nao sobre a lista inteira.
        """
        facts = [_jar_binary(scala="2.12"), _GLUE_VERSION]
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-001"]

    def test_sem_a_excecao_a_recusa_nomeia_o_match_ausente(self):
        pulo = _skipped([_jar_binary(scala="2.12"), _GLUE_VERSION])["SF-ERR-001"]
        assert pulo["reason"] == "requires_facts"
        assert pulo["missing"] == ["error.signature_match"]


class TestSegundaRegraExigeAEvidenciaDela:
    def test_nao_dispara_so_com_a_excecao(self):
        facts = [_excecao("java.lang.NoSuchFieldError"), *_match("java.lang.NoSuchFieldError")]
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-002"]

    def test_dispara_com_a_evidencia_completa(self):
        facts = [
            _excecao("java.lang.NoSuchFieldError"),
            *_match("java.lang.NoSuchFieldError"),
            _jar_binary(scala="2.13"),
            _USER_JARS_FIRST,
        ]
        assert [f for f in _judge(facts) if f.rule_id == "SF-ERR-002"]

    def test_sem_user_jars_first_a_regra_fica_muda(self):
        """`--user-jars-first` e o que faz o defeito existir: sem ele o SDK do
        runtime vence o classpath. `requires_facts` esta satisfeito -- e
        `tf.attribute` presente --, entao quem recusa aqui e o `when`."""
        facts = [
            _excecao("java.lang.NoSuchFieldError"),
            *_match("java.lang.NoSuchFieldError"),
            _jar_binary(scala="2.13"),
            _GLUE_VERSION,
        ]
        assert "SF-ERR-002" not in _skipped(facts)
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-002"]

    def test_a_flag_desligada_nao_e_a_flag_ligada(self):
        facts = [
            _excecao("java.lang.NoSuchFieldError"),
            *_match("java.lang.NoSuchFieldError"),
            _jar_binary(scala="2.13"),
            _tf_attribute("--user-jars-first", "false", block="default_arguments"),
        ]
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-002"]


class TestAAssinaturaCasadaDecideAQualRegra:
    """Duas regras, dois `signature_id`. Trocar um pelo outro nao pode acusar."""

    def test_no_such_method_nao_dispara_a_regra_do_sdk(self):
        facts = [
            _excecao("java.lang.NoSuchMethodError"),
            *_match("java.lang.NoSuchMethodError"),
            _jar_binary(scala="2.12"),
            _GLUE_VERSION,
            _USER_JARS_FIRST,
        ]
        assert _ids([f for f in _judge(facts) if f.rule_id.startswith("SF-ERR")]) == [
            "SF-ERR-001"
        ]

    def test_no_such_field_nao_dispara_a_regra_do_scala(self):
        facts = [
            _excecao("java.lang.NoSuchFieldError"),
            *_match("java.lang.NoSuchFieldError"),
            _jar_binary(scala="2.12"),
            _GLUE_VERSION,
            _USER_JARS_FIRST,
        ]
        assert _ids([f for f in _judge(facts) if f.rule_id.startswith("SF-ERR")]) == [
            "SF-ERR-002"
        ]

    def test_a_assinatura_casada_pela_causa_raiz_vale_igual(self):
        """`caused_by` entra na busca do matcher junto com a classe -- a
        assinatura que importa costuma estar na causa e nao no `SparkException`
        que a embrulha."""
        casados = _match("org.apache.spark.SparkException", ["java.lang.NoSuchMethodError"])
        assert [f.attrs["matched_on"] for f in casados] == ["caused_by"]
        facts = [
            _excecao("org.apache.spark.SparkException", ["java.lang.NoSuchMethodError"]),
            *casados,
            _jar_binary(scala="2.12"),
            _GLUE_VERSION,
        ]
        assert [f for f in _judge(facts) if f.rule_id == "SF-ERR-001"]


class TestOLimiarDeScalaMoraNaRegra:
    def test_jar_de_213_nao_acusa(self):
        facts = [
            _excecao("java.lang.NoSuchMethodError"),
            *_match("java.lang.NoSuchMethodError"),
            _jar_binary(scala="2.13"),
            _GLUE_VERSION,
        ]
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-001"]

    def test_jar_sem_versao_de_scala_no_nome_deixa_a_regra_muda(self):
        """Pode ser Java puro. Acusar um artefato que nunca teve Scala nenhum e
        acusar configuracao correta."""
        facts = [
            _excecao("java.lang.NoSuchMethodError"),
            *_match("java.lang.NoSuchMethodError"),
            _jar_opaco(),
            _GLUE_VERSION,
        ]
        assert "SF-ERR-001" not in _skipped(facts)
        assert not [f for f in _judge(facts) if f.rule_id == "SF-ERR-001"]


class TestEscopoDeVersao:
    def test_no_glue_51_a_recusa_e_de_escopo_e_nao_de_evidencia(self):
        """No Glue 5.1 o runtime e Scala 2.12.18 e o jar de 2.12 funciona. A
        regra nao pode acusar -- e a razao do silencio precisa ser o ESCOPO,
        nao falta de dado."""
        facts = [
            _excecao("java.lang.NoSuchMethodError"),
            *_match("java.lang.NoSuchMethodError"),
            _jar_binary(scala="2.12"),
            _tf_attribute("glue_version", "5.1"),
        ]
        pulados = _skipped(facts, runtime={"glue": "5.1"})
        assert pulados["SF-ERR-001"]["reason"] == "runtime_scope"
        assert not [f for f in _judge(facts, runtime={"glue": "5.1"}) if f.rule_id == "SF-ERR-001"]

    def test_sem_runtime_detectado_a_regra_falha_fechada(self):
        facts = [
            _excecao("java.lang.NoSuchMethodError"),
            *_match("java.lang.NoSuchMethodError"),
            _jar_binary(scala="2.12"),
            _GLUE_VERSION,
        ]
        assert _skipped(facts, runtime={})["SF-ERR-001"]["reason"] == "runtime_scope"


class TestOQueAAreaNaoCarrega:
    """`confidence=0.98` morreu na T2 e nao ressuscita no catalogo."""

    def test_nenhuma_regra_da_area_declara_confidence_numerico(self):
        for regra in _regras_da_area():
            confianca = regra.get("confidence")
            assert not isinstance(confianca, (int, float)), regra["id"]

    def test_toda_regra_da_area_e_confirmed(self):
        """Elas afirmam que a falha ACONTECEU, com o artefato ao lado."""
        assert [r["status"] for r in _regras_da_area()] == ["confirmed"] * 6

    def test_toda_regra_da_area_exige_o_match_MAIS_um_companheiro(self):
        """O contrato da area inteira, e o ponto da frente.

        A assinatura casada NAO basta em regra nenhuma: uma linha de log ou uma
        classe de excecao dizem que o texto apareceu, nunca que a acusacao se
        sustenta. Toda regra daqui exige `error.signature_match` E pelo menos um
        fact de OUTRO extrator -- o companheiro que a assinatura declara em
        `evidence_required`, ou o substituto medido quando o nome que ela
        declara nao existe neste motor.

        A assercao e generica de proposito. A anterior cobrava literalmente
        `mig.jar_binary` e `tf.attribute`, que sao os companheiros das DUAS
        primeiras -- e teria de crescer a cada regra nova, virando uma copia da
        tabela em vez de uma afirmacao sobre ela.
        """
        for regra in _regras_da_area():
            exigidos = set(regra["requires_facts"])
            assert "error.signature_match" in exigidos, regra["id"]
            assert exigidos - {"error.signature_match"}, regra["id"]

    def test_o_companheiro_de_cada_regra_e_kind_que_o_motor_EMITE(self):
        """A armadilha que esta area quase caiu, medida.

        Das SEIS assinaturas, so `ERR-GLUE-002`, `ERR-GLUE-003` e `ERR-ATH-001`
        declaram `evidence_required` cujos nomes existem como kind. As outras
        tres nomeiam `pyspark.skew_join`, `eventlog.executor_oom`,
        `spark.plan.cartesian_product`, `iceberg.commit_conflict`,
        `iceberg.concurrent_writer`, `lakeformation.missing_grant` e
        `ram.unaccepted_share` -- e NENHUM deles e emitido por este motor.

        Copiar esses nomes para `requires_facts` produziria regra que nunca
        dispara: `requires_facts` insatisfeito para sempre, `when` mudo,
        relatorio limpo. Este teste e o que impede a proxima regra da area de
        cair nisso.
        """
        emitidos = _kinds_emitidos()
        for regra in _regras_da_area():
            for kind in regra["requires_facts"]:
                assert kind in emitidos, f"{regra['id']}: {kind} nao e emitido por ninguem"


# ---------------------------------------------------------------------------
# A LACUNA FECHOU: as SEIS assinaturas tem regra (2026-09-09). O que continua
# medido aqui e a razao de as quatro de mensagem precisarem do caminho de LOG --
# por `spark.exception` elas nao casariam nunca, e a regra delas seria muda.
# ---------------------------------------------------------------------------


def _assinaturas() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(ASSINATURAS.rglob("*.json"))
    ]


def _ids_referenciados_pelas_regras() -> set[str]:
    referenciados: set[str] = set()
    for regra in _regras_da_area():
        for grupo in ("all", "any"):
            for condicao in (regra.get("when") or {}).get(grupo) or []:
                alvo = (condicao.get("where") or {}).get("attrs.signature_id")
                if alvo:
                    referenciados.add(alvo)
    return referenciados


def test_o_catalogo_de_assinaturas_nao_encolheu_sem_aviso():
    assert len(_assinaturas()) == 6, [s["id"] for s in _assinaturas()]


def test_as_seis_assinaturas_tem_regra():
    """A lacuna que a T3 declarou, fechada e medida.

    Uma assinatura sem regra e conhecimento que o motor carrega e nao usa: o
    match sai no `facts.json` e nenhum achado o le. O numero e SEIS, e ele e
    cobrado contra o catalogo de assinaturas e contra o de regras ao mesmo
    tempo -- acrescentar assinatura sem regra volta a derrubar este teste, que
    e exatamente o aviso que se quer.
    """
    assert _ids_referenciados_pelas_regras() == {s["id"] for s in _assinaturas()}


SO_PELO_LOG = {"ERR-ATH-001", "ERR-GLUE-001", "ERR-ICE-001", "ERR-LF-001"}


@pytest.mark.parametrize(
    "sig",
    [s for s in _assinaturas() if s["id"] in SO_PELO_LOG],
    ids=lambda s: s["id"],
)
def test_a_assinatura_de_mensagem_nao_casa_por_classe(sig):
    """POR QUE as quatro precisam do caminho de LOG, medido e nao lembrado.

    `build_signature_matches` casa a assinatura contra `attrs.exception_class` e
    contra `attrs.caused_by` -- CLASSE de excecao. Estas quatro sao trecho de
    MENSAGEM de log, entao por ESTE caminho elas nunca produzem
    `error.signature_match`, e `SF-ERR-003` a `SF-ERR-006` seriam mudas se
    dependessem dele. Elas dependem de `cloudwatch.log_event`, e
    `fixtures/cloudwatch_logs/` e onde isso vira golden.

    O teste alimenta a excecao com o proprio texto da assinatura na cabeca da
    mensagem -- que e onde ele aparece num log real -- e confirma que ela cai em
    `error.signature.unresolved`, nao em match.
    """
    excecao = Fact(
        kind="spark.exception",
        subject={"type": "spark_stage", "stage": 1},
        measures={},
        attrs={
            "exception_class": "org.apache.spark.SparkException",
            "message_head": sig["signature"],
            "is_chained": False,
            "caused_by": [],
        },
        provenance=PROV,
    )
    saida = build_signature_matches([excecao])
    assert [f.kind for f in saida] == ["error.signature.unresolved"]
    assert saida[0].attrs["reason"] == "nenhuma_assinatura_casou"
