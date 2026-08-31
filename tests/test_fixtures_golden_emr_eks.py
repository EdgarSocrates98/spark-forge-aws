"""Golden test do corpus de execucao EMR on EKS (`emr-containers`).

Arquivo dedicado, mesma razao de `test_fixtures_golden_emr_serverless.py`: a
fixture e um `*.json` sob `input/`, com as duas respostas
(`describe-virtual-cluster` e `describe-job-run`) sob chaves de topo, e nenhum
outro corpus extrai por essa porta.

Este modulo NAO e opcional, e a razao esta escrita em
`test_fixtures_kind_coverage.py::test_every_fixture_domain_has_a_golden_module`:
`scripts/verify_wheel.py` monta o gate de paridade a partir dos MODULOS
(`tests/test_fixtures_*.py`), nunca dos diretorios. Um `fixtures/emr_eks/` sem
modulo que o carregue existiria parecendo cobertura, e o gate de wheel nunca o
executaria contra o pacote instalado. O comentario daquele teste nomeia EMR on
EKS como o risco vivo; este arquivo e a resposta a ele, no mesmo commit em que o
corpus nasce.

A extracao usa `extract_emr_eks_tree`, e nao um laco sobre `*.json`, pela razao
escrita em `scripts/regen_fixtures.py:regen_emr_eks`: e a funcao que o produto
chama quando o `--path` e diretorio, e golden e teste precisam extrair pela
MESMA porta por onde o produto extrai.

**Todo `expects_rules` nasce vazio, e isso e projeto, nao lacuna.** A area
`SF-EMRK` e a Task 10; este corpus e a Task 7. Extrator e corpus antes de regra
e a ordem que o repositorio ja usou na Fase 5b (EMR on EC2), na 5d (EMR
Serverless) e na 4c (`SF-FVAL`): regra sem fixture e regra que nunca foi
provada, e escrever as duas coisas juntas apaga a chance de a fixture
contradizer a regra. Quando a Task 10 chegar, `python scripts/regen_fixtures.py`
reescreve os `findings.json` e os `[]` que sobrarem passam a ser goldens
NEGATIVOS reais.
"""
import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.emr_eks import EMITTED_KINDS, extract_emr_eks_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "emr_eks"

# Lista escrita a mao de proposito: fixture removida em silencio some do
# `parametrize` sem que nada reclame, e o corpus encolhe sem deixar rastro.
REQUIRED_FIXTURES = {
    # O negativo de referencia da area -- destino de log declarado, sem pod
    # template, sem contradicao consigo mesmo.
    "job_run_saudavel",
    # Zero destinos de log SEM que ninguem tenha desligado nada: no EMR on EKS o
    # bloco ausente JA e zero destino, ao contrario do Serverless.
    "sem_destino_de_log",
    # A sentinela e o ponto cego contado quando nada pode ser lido.
    "payload_vazio",
    # A recusa VISIVEL: o unico kind da area que nao alimenta regra nenhuma.
    "pod_template_declarado",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _extract(directory: Path):
    input_dir = directory / "input"
    return extract_emr_eks_tree(input_dir, repo_root=input_dir)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    facts = _extract(directory)
    findings, skipped = judge(facts, load_catalog(), meta["runtime"], return_skipped=True)
    return meta, facts, findings, skipped


def _by_kind(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


# ids como lista pre-computada, nunca `ids=lambda`: com o diretorio de fixtures
# vazio, o pytest 8.x invoca o callable sobre o sentinela interno NOTSET durante
# a coleta e aborta a sessao INTEIRA, nao so este arquivo. Mesma guarda de
# `test_fixtures_golden_emr.py`.
@pytest.mark.parametrize("directory", fixture_dirs(), ids=[p.name for p in fixture_dirs()])
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        expected = json.loads((directory / "expected" / "facts.json").read_text(encoding="utf-8"))
        assert [f.to_dict() for f in facts] == expected

    def test_findings_match_golden(self, directory):
        _, _, findings, _ = run_fixture(directory)
        expected = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in findings] == expected

    def test_declared_rules_all_fire(self, directory):
        meta, _, findings, _ = run_fixture(directory)
        assert sorted({f.rule_id for f in findings}) == sorted(meta.get("expects_rules", []))

    def test_declared_kinds_all_present(self, directory):
        meta, facts, _, _ = run_fixture(directory)
        assert {f.kind for f in facts} == set(meta.get("expects_kinds", []))

    def test_everything_validates_against_schema(self, directory):
        _, facts, findings, _ = run_fixture(directory)
        for fact in facts:
            validate_fact(fact.to_dict())
        for finding in findings:
            validate_finding(finding.to_dict())

    def test_extraction_is_deterministic(self, directory):
        first = [f.to_dict() for f in _extract(directory)]
        second = [f.to_dict() for f in _extract(directory)]
        assert first == second

    def test_sentinel_counts_what_it_says(self, directory):
        """`emrc.analyzed` e o que distingue "analisei e nao ha" de "nunca
        analisei". Um contador que para de contar devolve zero, e zero e
        exatamente o que uma extracao limpa devolve -- o apodrecimento seria
        invisivel."""
        _, facts, _, _ = run_fixture(directory)
        sentinelas = _by_kind(facts, "emrc.analyzed")
        arquivos = len(list((directory / "input").glob("*.json")))
        assert len(sentinelas) == arquivos, "uma sentinela por payload, sempre"
        for campo, kind in (
            ("virtual_cluster_count", "emrc.virtual_cluster"),
            ("job_run_count", "emrc.job_run"),
            ("configuration_count", "emrc.configuration"),
            ("conf_parameter_count", "emrc.spark_submit_parameters"),
            ("unresolved_count", "emrc.unresolved"),
        ):
            assert sum(s.measures[campo] for s in sentinelas) == len(_by_kind(facts, kind)), campo


class TestAdversarial:
    def test_every_emitted_kind_appears_in_this_corpus(self):
        """Recorte local do invariante global de
        `test_fixtures_kind_coverage.py`. Aqui ele falha com a mensagem certa:
        kind do EMR on EKS sem fixture do EMR on EKS."""
        vistos: set[str] = set()
        for directory in fixture_dirs():
            vistos.update(f.kind for f in _extract(directory))
        assert set(EMITTED_KINDS) - vistos == set(), sorted(set(EMITTED_KINDS) - vistos)

    def test_the_absent_monitoring_block_is_zero_destinations_not_a_missing_fact(self):
        """O par que separa "a API nao devolveu o bloco" de "nao ha destino".

        No EMR Serverless o armazenamento gerenciado tem default LIGADO, e
        ausencia significa protegido. No EMR on EKS nao ha equivalente: o bloco
        ausente JA e zero destino, e por isso `emrc.monitoring` sai SEMPRE, com
        `monitoring_declared: false`. Omitir o fact deixaria a regra da Task 10
        sem ingrediente justamente no caso mais comum do estado que ela acusa.
        """
        sem = [f for f in _extract(FIXTURES / "sem_destino_de_log") if f.kind == "emrc.monitoring"]
        com = [f for f in _extract(FIXTURES / "job_run_saudavel") if f.kind == "emrc.monitoring"]
        assert len(sem) == 1 and len(com) == 1
        assert sem[0].attrs["monitoring_declared"] is False
        assert sem[0].measures["log_destination_count"] == 0
        assert com[0].attrs["monitoring_declared"] is True
        assert com[0].measures["log_destination_count"] == 1

    def test_the_pod_template_refusal_is_one_per_role_and_carries_the_path(self):
        """A recusa e VISIVEL ou nao serve para nada.

        Duas propriedades declaradas, dois papeis, duas recusas -- cada uma com
        o path que nao foi lido. Uma recusa sem o path diria "nao olhei" sem
        dizer o que; nenhuma recusa faria o relatorio parecer completo, que e o
        defeito que o kind existe para impedir.
        """
        recusas = [
            f
            for f in _extract(FIXTURES / "pod_template_declarado")
            if f.kind == "emrc.pod_template.unresolved"
        ]
        assert [f.attrs["role"] for f in recusas] == ["driver", "executor"]
        assert all(f.attrs["path"].startswith("s3://") for f in recusas)
        assert {f.attrs["reason"] for f in recusas} == {"not_fetched"}
        # O negativo: sem as duas propriedades, nenhuma recusa. Recusa que sai
        # de graca nao informa nada.
        limpa = [
            f
            for f in _extract(FIXTURES / "job_run_saudavel")
            if f.kind == "emrc.pod_template.unresolved"
        ]
        assert limpa == []

    def test_the_empty_payload_names_the_missing_command_instead_of_raising(self):
        """Payload que nada sustenta nao pode derrubar a extracao nem sair
        calado: `emrc.unresolved` nomeia `missing_job_run` -- o comando que
        falta --, e a sentinela sai do mesmo jeito, com o ponto cego CONTADO."""
        facts = _extract(FIXTURES / "payload_vazio")
        pontos_cegos = [f for f in facts if f.kind == "emrc.unresolved"]
        assert [f.attrs["reason"] for f in pontos_cegos] == ["missing_job_run"]
        sentinela = [f for f in facts if f.kind == "emrc.analyzed"]
        assert len(sentinela) == 1
        assert sentinela[0].measures["unresolved_count"] == 1
