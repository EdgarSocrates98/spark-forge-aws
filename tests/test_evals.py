from pathlib import Path

from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "fase0.xml"


def pairs():
    tree = ET.parse(EVAL)
    return [
        (p.findtext("question", "").strip(), p.findtext("answer", "").strip())
        for p in tree.getroot().findall("qa_pair")
    ]


class TestShape:
    def test_file_exists(self):
        assert EVAL.is_file()

    def test_has_exactly_ten_pairs(self):
        assert len(pairs()) == 10

    def test_every_question_and_answer_is_non_empty(self):
        for question, answer in pairs():
            assert question and answer

    def test_answers_are_short_enough_for_string_comparison(self):
        for _, answer in pairs():
            assert len(answer) <= 80, answer

    def test_questions_are_unique(self):
        questions = [q for q, _ in pairs()]
        assert len(questions) == len(set(questions))


class TestAnswersAreDerivableFromTheFixtures:
    """Cada resposta e verificavel contra o corpus, nao contra opiniao."""

    def test_every_answer_is_reproduced_by_the_checker(self):
        import sys

        sys.path.insert(0, str(ROOT))
        from scripts.check_evals import verify_all

        assert not verify_all()
