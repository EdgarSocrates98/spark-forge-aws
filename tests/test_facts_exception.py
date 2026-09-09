"""`spark.exception` estrutura o texto que `spark.stage.failure` ja carrega.

O artefato nao falta: `attrs.reason` E a excecao com a pilha, ja redigida por
`secrets.redact`. O que faltava era estrutura.
"""

from __future__ import annotations

from sparkforge.facts.exception import build_exceptions
from sparkforge.findings.models import Fact

_PILHA = (
    "org.apache.spark.SparkException: Job aborted due to stage failure\n"
    "\tat org.apache.spark.scheduler.DAGScheduler"
    ".failJobAndIndependentStages(DAGScheduler.scala:2668)\n"
    "\tat org.apache.spark.scheduler.DAGScheduler.abortStage(DAGScheduler.scala:2604)\n"
    "Caused by: java.lang.NoSuchMethodError: scala.collection.immutable.List.map\n"
    "\tat com.exemplo.Job.run(Job.scala:42)\n"
)


def _falha(reason: str, **attrs) -> Fact:
    return Fact(
        kind="spark.stage.failure",
        subject={"stage_id": 3, "stage_name": "map at Job.scala:42"},
        measures={},
        attrs={"reason": reason, **attrs},
    )


class TestExcecaoEstruturada:
    def test_classe_e_cabeca_da_mensagem(self):
        facts = build_exceptions([_falha(_PILHA)])
        exc = [f for f in facts if f.kind == "spark.exception"]
        assert len(exc) == 1
        assert exc[0].attrs["exception_class"] == "org.apache.spark.SparkException"
        assert "Job aborted" in exc[0].attrs["message_head"]

    def test_encadeamento_na_ordem(self):
        facts = build_exceptions([_falha(_PILHA)])
        exc = [f for f in facts if f.kind == "spark.exception"][0]
        assert exc.attrs["is_chained"] is True
        assert exc.attrs["caused_by"] == ["java.lang.NoSuchMethodError"]

    def test_frames_do_topo(self):
        facts = build_exceptions([_falha(_PILHA)])
        frames = [f for f in facts if f.kind == "spark.exception.frame"]
        assert frames
        topo = frames[0]
        assert topo.attrs["class"].startswith("org.apache.spark.scheduler.DAGScheduler")
        assert topo.attrs["file"] == "DAGScheduler.scala"
        assert topo.attrs["line"] == 2668


class TestRecusaNomeada:
    def test_texto_sem_forma_de_stacktrace(self):
        facts = build_exceptions([_falha("Container killed by YARN")])
        un = [f for f in facts if f.kind == "spark.exception.unresolved"]
        assert len(un) == 1
        assert un[0].attrs["reason"] == "sem_forma_de_stacktrace"
        assert not [f for f in facts if f.kind == "spark.exception"]

    def test_texto_redigido_nao_vira_excecao(self):
        facts = build_exceptions([_falha("jdbc://h?password=[REDACTED]", redacted=True)])
        un = [f for f in facts if f.kind == "spark.exception.unresolved"]
        assert un and un[0].attrs["reason"] == "reason_redigida"

    def test_sem_falha_no_case_nao_emite_nada(self):
        assert build_exceptions([]) == []


# ---------------------------------------------------------------------------
# O SEGUNDO padrao: a classe depois do prefixo do `DAGScheduler` (2026-09-09).
#
# `fixtures/exception/classe_no_meio_da_linha/` prendia a recusa como
# comportamento ATUAL e dizia que alargar o parser seria diff de golden. Este e
# o diff, e estes sao os testes que separam alargar de afrouxar.
# ---------------------------------------------------------------------------

_DAGSCHEDULER = (
    "Job aborted due to stage failure: Task 3 in stage 5.0 failed 4 times, "
    "most recent failure: Lost task 3.3 in stage 5.0 "
    "(TID 42, ip-10-0-0-12.ec2.internal, executor 2): "
    "java.lang.OutOfMemoryError: Java heap space"
)


class TestClasseDepoisDoPrefixoDoEscalonador:
    def test_a_classe_do_meio_da_linha_e_alcancada(self):
        facts = build_exceptions([_falha(_DAGSCHEDULER)])
        exc = [f for f in facts if f.kind == "spark.exception"]
        assert len(exc) == 1
        assert exc[0].attrs["exception_class"] == "java.lang.OutOfMemoryError"
        assert exc[0].attrs["message_head"] == "Java heap space"

    def test_a_procedencia_do_parse_sai_no_fact(self):
        """Sem `parsed_by`, duas procedencias diferentes ficariam
        indistinguiveis -- a mesma razao de `matched_on` existir no matcher."""
        facts = build_exceptions([_falha(_DAGSCHEDULER)])
        exc = [f for f in facts if f.kind == "spark.exception"][0]
        assert exc.attrs["parsed_by"] == "after_executor"

    def test_a_pilha_normal_continua_entrando_pelo_primeiro_padrao(self):
        exc = [f for f in build_exceptions([_falha(_PILHA)]) if f.kind == "spark.exception"]
        assert exc[0].attrs["parsed_by"] == "head_of_line"

    def test_a_ancora_do_primeiro_padrao_NAO_foi_afrouxada(self):
        """O que o segundo padrao NAO pode ter trazido junto.

        `chave.pontuada: valor` no meio de mensagem livre nao e excecao, e
        continua nao sendo: sem o prefixo `executor <algo>):` do escalonador,
        nenhum dos dois padroes casa.
        """
        livre = "Job falhou porque o parametro app.config.timeout: 30 nao foi aceito"
        facts = build_exceptions([_falha(livre)])
        assert [f.kind for f in facts] == ["spark.exception.unresolved"]
        assert facts[0].attrs["reason"] == "sem_forma_de_stacktrace"

    def test_texto_redigido_nao_entra_nem_pelo_segundo_padrao(self):
        """A redacao vem ANTES do parse, e o segundo padrao nao a desfaz."""
        facts = build_exceptions([_falha(_DAGSCHEDULER, redacted=True)])
        assert [f.kind for f in facts] == ["spark.exception.unresolved"]
        assert facts[0].attrs["reason"] == "reason_redigida"
