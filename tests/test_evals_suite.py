"""O gabarito agentico: carga, resolucao contra `fase0.xml`, hash e ancoras.

O que este arquivo prova, e que nenhum golden prova sozinho:

  * as dez perguntas de `evals/agentic/fase0/suite.yaml` sao EXATAMENTE as de
    `evals/fase0.xml`, lidas por um segundo parser (`defusedxml`, o mesmo de
    `scripts/check_evals.py`);
  * o hash nao muda com reformatacao e muda quando uma resposta muda -- a
    Decision 3 do DESIGN;
  * toda pergunta de abstencao ancora num fact `*.unresolved` que a fixture
    citada REALMENTE emite. Sem isto, "a resposta certa e recusar" seria
    afirmacao do gabarito, e nao do corpus.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from defusedxml import ElementTree as DefusedET

from sparkforge.evals.suite import SuiteError, load_suite

ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = ROOT / "evals" / "agentic" / "fase0"
FIXTURE_SUITE = ROOT / "fixtures" / "host_transcript" / "_suite"


def _copia(tmp_path: Path) -> Path:
    destino = tmp_path / "evals" / "agentic" / "fase0"
    destino.mkdir(parents=True)
    shutil.copy(SUITE_DIR / "suite.yaml", destino / "suite.yaml")
    shutil.copy(ROOT / "evals" / "fase0.xml", tmp_path / "evals" / "fase0.xml")
    return destino


def _suite_inline(tmp_path: Path, corpo: str) -> Path:
    (tmp_path / "suite.yaml").write_text(
        "schema_version: 1\nid: t\nanswer_protocol: 'ANSWER: x'\n" + corpo, encoding="utf-8"
    )
    return tmp_path


class TestAFonte:
    def test_as_dez_perguntas_sao_as_do_xml(self):
        pares = [
            (p.findtext("question").strip(), p.findtext("answer").strip())
            for p in DefusedET.parse(ROOT / "evals" / "fase0.xml").getroot().findall("qa_pair")
        ]
        suite = load_suite(SUITE_DIR)
        da_fonte = [q for q in suite.questions if q.id.startswith("fase0-")]
        assert [(q.question, q.expected) for q in da_fonte] == pares

    def test_toda_pergunta_exige_ao_menos_uma_tool(self):
        for pergunta in load_suite(SUITE_DIR).questions:
            assert pergunta.required_tools, pergunta.id

    def test_ha_ao_menos_tres_perguntas_de_abstencao(self):
        abstencao = [q for q in load_suite(SUITE_DIR).questions if q.expects_abstention]
        assert len(abstencao) >= 3
        assert all(q.expected is None for q in abstencao)


@pytest.mark.parametrize("suite_dir", [SUITE_DIR, FIXTURE_SUITE], ids=["fase0", "fixtures"])
def test_toda_ancora_de_abstencao_existe_no_corpus(suite_dir):
    for pergunta in load_suite(suite_dir).questions:
        if not pergunta.expects_abstention:
            continue
        golden = ROOT / "fixtures" / pergunta.anchor["fixture"] / "expected" / "facts.json"
        kinds = {f["kind"] for f in json.loads(golden.read_text(encoding="utf-8"))}
        assert pergunta.anchor["kind"] in kinds, (pergunta.id, pergunta.anchor)
        assert pergunta.anchor["kind"].endswith(".unresolved"), pergunta.id


class TestOHash:
    def test_reformatar_o_yaml_nao_muda_o_hash(self, tmp_path):
        original = load_suite(SUITE_DIR).sha256
        copia = _copia(tmp_path)
        texto = (copia / "suite.yaml").read_text(encoding="utf-8")
        (copia / "suite.yaml").write_text(
            "# comentario novo\n\n" + texto.replace("schema_version: 1", "schema_version:   1"),
            encoding="utf-8",
        )
        assert load_suite(copia).sha256 == original

    def test_mudar_uma_resposta_no_xml_muda_o_hash(self, tmp_path):
        original = load_suite(SUITE_DIR).sha256
        copia = _copia(tmp_path)
        xml = tmp_path / "evals" / "fase0.xml"
        xml.write_text(
            xml.read_text(encoding="utf-8").replace("SF-PY-005:2", "SF-PY-005:3"),
            encoding="utf-8",
        )
        assert load_suite(copia).sha256 != original

    def test_mudar_as_tools_exigidas_muda_o_hash(self, tmp_path):
        original = load_suite(SUITE_DIR).sha256
        copia = _copia(tmp_path)
        texto = (copia / "suite.yaml").read_text(encoding="utf-8")
        (copia / "suite.yaml").write_text(
            texto.replace("required_tools: [finops]", "required_tools: [finops, judge]"),
            encoding="utf-8",
        )
        assert load_suite(copia).sha256 != original


ERROS = {
    "fonte_e_texto_juntos": (
        "questions:\n  - id: a\n    source: x.xml#1\n    question: q\n    answer: r\n"
        "    required_tools: [judge]\n",
        "exatamente um",
    ),
    "abstencao_sem_ancora": (
        "questions:\n  - id: a\n    question: q\n    expects_abstention: true\n"
        "    required_tools: [judge]\n",
        "anchor",
    ),
    "ordem_fora_das_tools": (
        "questions:\n  - id: a\n    question: q\n    answer: r\n    required_tools: [judge]\n"
        "    order: [[analyze_pyspark, judge]]\n",
        "fora de required_tools",
    ),
    "ordem_sobre_alternativa": (
        "questions:\n  - id: a\n    question: q\n    answer: r\n"
        "    required_tools: [[judge, finops]]\n    order: [[judge, finops]]\n",
        "alternativa",
    ),
    "id_duplicado": (
        "questions:\n  - id: a\n    question: q\n    answer: r\n    required_tools: [judge]\n"
        "  - id: a\n    question: q2\n    answer: r\n    required_tools: [judge]\n",
        "duplicado",
    ),
    "tools_vazias": (
        "questions:\n  - id: a\n    question: q\n    answer: r\n    required_tools: []\n",
        "required_tools",
    ),
    "id_com_caminho": (
        "questions:\n  - id: ../a\n    question: q\n    answer: r\n    required_tools: [judge]\n",
        "separador",
    ),
    "inline_sem_resposta": (
        "questions:\n  - id: a\n    question: q\n    required_tools: [judge]\n",
        "answer",
    ),
}


@pytest.mark.parametrize("nome", sorted(ERROS))
def test_defeito_de_schema_e_erro_nomeado(tmp_path, nome):
    corpo, trecho = ERROS[nome]
    with pytest.raises(SuiteError, match=trecho):
        load_suite(_suite_inline(tmp_path, corpo))


def test_indice_fora_do_intervalo(tmp_path):
    (tmp_path / "f.xml").write_text(
        "<evaluation><qa_pair><question>q</question><answer>a</answer></qa_pair></evaluation>",
        encoding="utf-8",
    )
    corpo = "questions:\n  - id: a\n    source: f.xml#2\n    required_tools: [judge]\n"
    with pytest.raises(SuiteError, match="fora do intervalo"):
        load_suite(_suite_inline(tmp_path, corpo))


def test_fonte_com_dtd_e_recusada(tmp_path):
    (tmp_path / "f.xml").write_text(
        '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "boom">]>'
        "<evaluation><qa_pair><question>&e;</question><answer>a</answer></qa_pair></evaluation>",
        encoding="utf-8",
    )
    corpo = "questions:\n  - id: a\n    source: f.xml#1\n    required_tools: [judge]\n"
    with pytest.raises(SuiteError, match="DTD"):
        load_suite(_suite_inline(tmp_path, corpo))


@pytest.mark.parametrize(
    "xml, trecho",
    [
        ("<outra><qa_pair><question>q</question><answer>a</answer></qa_pair></outra>", "raiz"),
        (
            "<evaluation><lixo/><qa_pair><question>q</question><answer>a</answer></qa_pair>"
            "</evaluation>",
            "fora de <qa_pair>",
        ),
        (
            "<evaluation><qa_pair><question><b>q</b></question><answer>a</answer></qa_pair>"
            "</evaluation>",
            "elemento dentro",
        ),
    ],
    ids=["raiz_errada", "conteudo_solto", "elemento_aninhado"],
)
def test_leitor_sem_parser_recusa_estrutura_inesperada(tmp_path, xml, trecho):
    (tmp_path / "f.xml").write_text(xml, encoding="utf-8")
    corpo = "questions:\n  - id: a\n    source: f.xml#1\n    required_tools: [judge]\n"
    with pytest.raises(SuiteError, match=trecho):
        load_suite(_suite_inline(tmp_path, corpo))


def test_entidade_padrao_e_desescapada(tmp_path):
    (tmp_path / "f.xml").write_text(
        "<evaluation><qa_pair><question>a &lt; b &amp;&amp; c</question>"
        "<answer>x&gt;y</answer></qa_pair></evaluation>",
        encoding="utf-8",
    )
    corpo = "questions:\n  - id: a\n    source: f.xml#1\n    required_tools: [judge]\n"
    pergunta = load_suite(_suite_inline(tmp_path, corpo)).questions[0]
    assert (pergunta.question, pergunta.expected) == ("a < b && c", "x>y")


def test_schema_version_errado(tmp_path):
    (tmp_path / "suite.yaml").write_text(
        "schema_version: 2\nid: t\nanswer_protocol: 'ANSWER: x'\nquestions: []\n", encoding="utf-8"
    )
    with pytest.raises(SuiteError, match="schema_version"):
        load_suite(tmp_path)


def test_protocolo_sem_a_linha_answer(tmp_path):
    (tmp_path / "suite.yaml").write_text(
        "schema_version: 1\nid: t\nanswer_protocol: responda\nquestions:\n"
        "  - id: a\n    question: q\n    answer: r\n    required_tools: [judge]\n",
        encoding="utf-8",
    )
    with pytest.raises(SuiteError, match="ANSWER:"):
        load_suite(tmp_path)
