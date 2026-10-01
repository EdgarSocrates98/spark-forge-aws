"""A comparacao dos dois lados do simulate."""
from __future__ import annotations

import pytest

from sparkforge.findings.models import Fact
from sparkforge.proof import load_policy
from sparkforge.simulate import DERIVED_KINDS, diff, strip_derived


@pytest.fixture(scope="module")
def chaves():
    return load_policy()["stable_keys"]


SUB = {"type": "source_location", "file": "job.py", "symbol": "f", "line": 3, "snippet": "x"}


def achado(rule_id, subject=None):
    return {"rule_id": rule_id, "subject": subject or SUB}


def test_strip_tira_so_os_derivados():
    fatos = [Fact(kind="lakeformation.access_model", subject={"type": "job_run", "symbol": "j"}),
             Fact(kind="tf.attribute", subject={"type": "tf_resource", "symbol": "j#k"})]
    assert [f.kind for f in strip_derived(fatos)] == ["tf.attribute"]
    derivados = {"lakeformation.access_model", "spark.timeout.relation", "fusion.summary"}
    assert derivados <= DERIVED_KINDS


def test_mesmo_conjunto_da_diff_vazia(chaves):
    saida = diff([achado("SF-A")], [achado("SF-A")], [], [], chaves)
    assert saida["disappeared"] == [] and saida["appeared"] == []
    assert saida["persisted_count"] == 1


def test_some_e_aparece(chaves):
    saida = diff([achado("SF-A")], [achado("SF-B")], [], [], chaves)
    assert [d["rule_id"] for d in saida["disappeared"]] == ["SF-A"]
    assert [a["rule_id"] for a in saida["appeared"]] == ["SF-B"]


def test_linha_e_snippet_nao_criam_diferenca(chaves):
    depois = {**SUB, "line": 99, "snippet": "outro"}
    saida = diff([achado("SF-A")], [achado("SF-A", depois)], [], [], chaves)
    assert saida["disappeared"] == [] and saida["appeared"] == []


def test_mesma_regra_em_outro_simbolo_e_aparicao(chaves):
    saida = diff([achado("SF-A")], [achado("SF-A"), achado("SF-A", {**SUB, "symbol": "g"})],
                 [], [], chaves)
    assert [a["subject"]["symbol"] for a in saida["appeared"]] == ["g"]


def test_skipped_delta_nomeia_a_mudanca_de_estado(chaves):
    antes = [{"rule_id": "SF-A", "reason": "requires_facts"}]
    depois = [{"rule_id": "SF-A", "reason": "runtime_scope"}, {"rule_id": "SF-B", "reason": "x"}]
    saida = diff([], [], antes, depois, chaves)
    assert saida["skipped_delta"] == [
        {"rule_id": "SF-A", "before": "requires_facts", "after": "runtime_scope"},
        {"rule_id": "SF-B", "before": "evaluated", "after": "x"},
    ]
