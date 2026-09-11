"""Golden do corpus `fixtures/host_transcript/`: extrator, grade e compare.

Tres modos, declarados no `meta.yaml` de cada caso e regenerados por
`scripts/regen_fixtures.py::regen_host_transcript`:

  * `transcript` -- um `input/<qid>.jsonl`. Confere os facts `host.*` e o
    veredito daquela pergunta contra `_suite/suite.yaml`.
  * `run` -- uma execucao inteira, pelo mesmo caminho da CLI.
  * `compare` -- dois diretorios de scorecards.

Nenhum caso tem `findings.json`: `host.*` nao passa por `judge`.

`TestAdversarial` le cada golden contra o que o nome da pasta afirma. Igualdade
com o golden prova que nada mudou; nao prova que o golden diz o que a fixture
promete, e fixture cujo nome diz uma coisa e cujo veredito diz outra passaria
em todos os testes de igualdade.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.evals.cli import eval_compare, eval_grade
from sparkforge.evals.grade import grade_question
from sparkforge.evals.suite import load_suite
from sparkforge.facts.host_transcript import (
    ANSWER_MAX_CHARS,
    EMITTED_KINDS,
    UNRESOLVED_REASONS,
    extract_host_transcript_path,
)
from sparkforge.findings.validate import validate_fact

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "host_transcript"
SUITE_DIR = FIXTURES / "_suite"


def _cases(mode: str | None = None) -> list[Path]:
    casos = []
    for pasta in sorted(p for p in FIXTURES.iterdir() if p.is_dir() and not p.name.startswith("_")):
        meta = yaml.safe_load((pasta / "meta.yaml").read_text(encoding="utf-8"))
        if mode is None or meta["mode"] == mode:
            casos.append(pasta)
    return casos


def _meta(pasta: Path) -> dict:
    return yaml.safe_load((pasta / "meta.yaml").read_text(encoding="utf-8"))


def _expected(pasta: Path, nome: str):
    return json.loads((pasta / "expected" / nome).read_text(encoding="utf-8"))


def _derive_transcript(pasta: Path):
    question = load_suite(SUITE_DIR).by_id()[_meta(pasta)["question"]]
    facts = extract_host_transcript_path(pasta / "input" / f"{question.id}.jsonl")
    return facts, grade_question(question, facts)


def _grade_of(nome: str) -> dict:
    return _expected(FIXTURES / nome, "grade.json")


def test_o_corpus_tem_os_tres_modos():
    assert len(_cases("transcript")) >= 14
    assert len(_cases("run")) >= 1
    assert len(_cases("compare")) >= 5


@pytest.mark.parametrize("pasta", _cases("transcript"), ids=lambda p: p.name)
class TestTranscript:
    def test_facts_batem_com_o_golden(self, pasta):
        facts, _ = _derive_transcript(pasta)
        assert [f.to_dict() for f in facts] == _expected(pasta, "facts.json")

    def test_veredito_bate_com_o_golden(self, pasta):
        _, veredito = _derive_transcript(pasta)
        assert veredito == _expected(pasta, "grade.json")

    def test_todo_fact_passa_no_schema(self, pasta):
        facts, _ = _derive_transcript(pasta)
        for fact in facts:
            validate_fact(fact.to_dict())
            assert fact.kind in EMITTED_KINDS

    def test_extracao_e_deterministica(self, pasta):
        primeira, segunda = _derive_transcript(pasta), _derive_transcript(pasta)
        assert json.dumps([f.to_dict() for f in primeira[0]]) == json.dumps(
            [f.to_dict() for f in segunda[0]]
        )
        assert json.dumps(primeira[1], sort_keys=True) == json.dumps(segunda[1], sort_keys=True)

    def test_nenhum_fact_cita_caminho_absoluto(self, pasta):
        facts, _ = _derive_transcript(pasta)
        for fact in facts:
            assert fact.subject["file"] == f"{_meta(pasta)['question']}.jsonl"
            assert str(ROOT) not in json.dumps(fact.to_dict())


def test_run_bate_com_o_golden():
    for pasta in _cases("run"):
        scorecard = eval_grade(str(SUITE_DIR), str(pasta / "input"))
        assert scorecard == _expected(pasta, "scorecard.json")


@pytest.mark.parametrize("pasta", _cases("compare"), ids=lambda p: p.name)
def test_compare_bate_com_o_golden(pasta):
    resultado = eval_compare(
        str(pasta / "input" / "baseline"), str(pasta / "input" / "candidate")
    )
    assert resultado == _expected(pasta, "compare.json")


def test_toda_razao_de_lacuna_e_exercitada():
    vistas: set[str] = set()
    for pasta in _cases("transcript"):
        for fact in _expected(pasta, "facts.json"):
            if fact["kind"] == "host.transcript.unresolved":
                vistas.add(fact["attrs"]["reason"])
    assert vistas == set(UNRESOLVED_REASONS)


class TestAdversarial:
    def test_acerto_e_erro_diferem_so_na_resposta(self):
        certo, errado = _grade_of("correct_mcp"), _grade_of("wrong_answer")
        assert (certo["answer"], errado["answer"]) == ("correct", "wrong")
        assert certo["tools"] == errado["tools"] == {
            "verdict": "ok",
            "missing": [],
            "order_violated": [],
        }

    def test_sem_linha_answer_nao_e_erro(self):
        assert _grade_of("answer_absent")["answer"] == "answer_absent"

    def test_recusa_indevida_nao_e_erro(self):
        assert _grade_of("over_abstention")["answer"] == "over_abstention"

    def test_abstencao_tem_eixo_proprio(self):
        assert _grade_of("abstained")["abstention"] == "abstained"
        assert _grade_of("false_certainty")["abstention"] == "false_certainty"
        assert _grade_of("abstained")["answer"] is None

    def test_tool_faltando_e_ordem_violada_sao_nomeadas(self):
        assert _grade_of("tool_missing")["tools"]["missing"] == ["analyze_pyspark"]
        assert _grade_of("order_violated")["tools"]["order_violated"] == ["analyze_pyspark<judge"]

    def test_tool_extra_conta_e_nao_reprova(self):
        veredito = _grade_of("extra_tool")
        assert veredito["tools"]["verdict"] == "ok"
        assert veredito["cost"]["tool_calls"] == 4
        assert veredito["cost"]["other_calls"] == 1

    def test_os_dois_canais_viram_o_mesmo_verbo(self):
        calls = [
            f["attrs"]
            for f in _expected(FIXTURES / "mixed_channels", "facts.json")
            if f["kind"] == "host.tool_call"
        ]
        assert [(c["channel"], c["verb"]) for c in calls] == [
            ("other", None),
            ("bash", "analyze_pyspark"),
            ("mcp", "judge"),
            ("bash", "judge"),
        ]
        assert _grade_of("mixed_channels")["cost"]["tool_errors"] == 1

    def test_dano_total_e_ungraded_nunca_wrong(self):
        for nome in ("broken_envelope", "not_a_transcript"):
            veredito = _grade_of(nome)
            assert veredito["status"] == "ungraded"
            assert veredito["answer"] is None

    def test_dano_parcial_ainda_pontua(self):
        veredito = _grade_of("partial_damage")
        assert veredito["status"] == "graded"
        assert veredito["answer"] == "correct"
        assert len(veredito["unresolved"]) == len(UNRESOLVED_REASONS)

    def test_sem_usage_e_tokens_unresolved_nao_zero(self):
        custo = _grade_of("no_usage")["cost"]
        assert custo["tokens_unresolved"] is True
        assert custo["tokens"] is None
        assert _grade_of("no_usage")["tools"]["verdict"] == "ok"

    def test_resposta_longa_e_truncada(self):
        finais = [
            f
            for f in _expected(FIXTURES / "truncated_answer", "facts.json")
            if f["kind"] == "host.final_answer"
        ]
        assert len(finais[0]["attrs"]["answer"]) == ANSWER_MAX_CHARS
        assert finais[0]["attrs"]["truncated"] is True

    def test_run_conta_cada_coluna(self):
        scorecard = _expected(FIXTURES / "run_full", "scorecard.json")
        totais = scorecard["totals"]
        assert (totais["graded"], totais["ungraded"], totais["correct"], totais["abstained"]) == (
            2,
            1,
            1,
            1,
        )
        assert scorecard["unmatched_transcripts"] == ["stray"]
        assert scorecard["run"]["id"] == "input"
        assert "score" not in json.dumps(scorecard)

    def test_compare_nao_conclui(self):
        virada = _expected(FIXTURES / "compare_flip", "compare.json")
        por_id = {q["id"]: q["answer"] for q in virada["questions"]}
        assert por_id["q-mcp"] == {
            "baseline": "3/3",
            "candidate": "1/3",
            "transition": "pass->mixed",
        }
        texto = json.dumps(virada)
        for palavra in ("improved", "regressed", "better", "worse", "melhor", "pior"):
            assert palavra not in texto

    def test_compare_recusa_gabarito_diferente(self):
        recusa = _expected(FIXTURES / "compare_suite_mismatch", "compare.json")
        assert recusa["refused"]["reason"] == "suite_mismatch"
        assert recusa["questions"] == []

    def test_compare_avisa_amostra_unica_e_modelo_diferente(self):
        unica = _expected(FIXTURES / "compare_single_sample", "compare.json")
        outro_modelo = _expected(FIXTURES / "compare_model_differs", "compare.json")
        assert unica["single_sample"] is True
        assert outro_modelo["differs"]["models"] is True
