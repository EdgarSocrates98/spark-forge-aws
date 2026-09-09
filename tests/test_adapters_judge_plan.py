"""O bloco de plano na resposta do adapter.

O `judge` continua READ_ONLY: ele CALCULA o plano e nao grava nada.
"""

from __future__ import annotations

import json

from sparkforge.adapters._core import judge_findings

# A fixture de event log e a unica do corpus que produz mais de um punhado de
# findings a partir de um `facts.json` que `judge` consegue ler direto -- seis
# achados, e uma ordem de aplicacao que NAO e a ordem em que eles saem. As
# fixtures de `waste/` e `capacity/` guardam facts crus, que so viram achado
# depois de `fuse`, e por isso julgam zero aqui.
_FACTS = "fixtures/eventlog/skewed_stage/expected/facts.json"


class TestBlocoNaResposta:
    def test_resposta_traz_o_bloco_plan(self):
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        assert "plan" in r
        assert r["plan"]["persisted"] is False

    def test_cada_item_traz_evidence_standing_com_os_insumos(self):
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        assert r["items"], "a fixture precisa produzir ao menos um finding"
        for item in r["items"]:
            s = item["evidence_standing"]
            assert set(s) == {
                "value",
                "source_tier",
                "in_version_scope",
                "measures_present",
            }

    def test_evidence_standing_nao_substitui_o_confidence_da_regra(self):
        """Sao dois campos com semantica diferente: `confidence` vem da regra,
        `evidence_standing` e computado a partir de tier, escopo e medida."""
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        item = r["items"][0]
        assert isinstance(item["confidence"], str)
        assert isinstance(item["evidence_standing"], dict)
        assert item["confidence"] in {"high", "medium", "low"}
        assert item["evidence_standing"]["value"] in {"high", "medium", "low"}

    def test_a_ordem_e_do_conjunto_e_nao_da_pagina(self):
        inteiro = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        pagina = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4", limit=1)
        assert pagina["returned_count"] <= 1
        assert pagina["plan"]["order"] == inteiro["plan"]["order"]
        assert str(inteiro["total_count"]) in pagina["plan"]["scope"]

    def test_resposta_nao_carrega_score(self):
        r = judge_findings(facts_path=_FACTS, glue="5.0", spark="3.5.4")
        assert "score" not in json.dumps(r)

    def test_judge_nao_escreve_nada(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        antes = set(tmp_path.rglob("*"))
        judge_findings(
            facts=[{"kind": "glue.utilization.summary", "subject": {}, "measures": {}}],
            glue="5.0",
        )
        assert set(tmp_path.rglob("*")) == antes
