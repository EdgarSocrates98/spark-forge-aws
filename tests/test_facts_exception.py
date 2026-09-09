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
