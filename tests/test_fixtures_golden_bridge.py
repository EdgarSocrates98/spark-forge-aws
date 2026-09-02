"""Golden da ponte: o codigo lido cruzado com a execucao medida.

O corpus e o UNICO deste repositorio com DOIS artefatos por fixture --
`job.py` e `eventlog.jsonl` no mesmo `input/`. E a natureza da coisa: uma ponte
nao tem como ser exercitada por um lado so, e um corpus com um artefato so
provaria o extrator, nunca o cruzamento.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sparkforge.facts.bridge import build_bridge
from sparkforge.facts.event_log import extract_event_log_path
from sparkforge.facts.pyspark_ast import extract_tree
from sparkforge.findings.validate import validate_fact, validate_finding
from sparkforge.rules.engine import judge
from sparkforge.rules.loader import load_catalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "bridge"

REQUIRED_FIXTURES = {
    "collect_corroborado_pelo_stage",
    "collect_com_stage_de_outra_linha",
    "stage_nasceu_em_biblioteca_scala",
}


def fixture_dirs():
    return sorted(p for p in FIXTURES.iterdir() if p.is_dir())


def _derive(directory: Path):
    """Os facts dos DOIS lados, mais os derivados da ponte.

    A ordem importa para o golden e nao para o resultado: `build_bridge` le a
    uniao, e `sort_facts` ordena a saida dela. O que se concatena aqui e o
    corpus que uma execucao real teria em maos.
    """
    entrada = directory / "input"
    estaticos = extract_tree(entrada, repo_root=entrada)
    runtime = extract_event_log_path(entrada / "eventlog.jsonl", repo_root=entrada)
    uniao = list(estaticos) + list(runtime)
    return uniao + build_bridge(uniao, path_hint=directory.name)


def run_fixture(directory: Path):
    meta = yaml.safe_load((directory / "meta.yaml").read_text(encoding="utf-8"))
    derivados = _derive(directory)
    achados, pulados = judge(
        derivados, load_catalog(), meta.get("runtime") or {}, return_skipped=True
    )
    return meta, derivados, achados, pulados


def _kinds(facts, kind):
    return [f for f in facts if f.kind == kind]


def test_all_required_fixtures_exist():
    assert {p.name for p in fixture_dirs()} == REQUIRED_FIXTURES


@pytest.mark.parametrize("directory", fixture_dirs(), ids=lambda p: p.name)
class TestGolden:
    def test_facts_match_golden(self, directory):
        _, facts, _, _ = run_fixture(directory)
        esperado = json.loads(
            (directory / "expected" / "facts.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in facts] == esperado

    def test_findings_match_golden(self, directory):
        _, _, achados, _ = run_fixture(directory)
        esperado = json.loads(
            (directory / "expected" / "findings.json").read_text(encoding="utf-8")
        )
        assert [f.to_dict() for f in achados] == esperado

    def test_every_fact_validates(self, directory):
        _, facts, _, _ = run_fixture(directory)
        for fato in facts:
            validate_fact(fato.to_dict())

    def test_every_finding_validates(self, directory):
        _, _, achados, _ = run_fixture(directory)
        for achado in achados:
            validate_finding(achado.to_dict())

    def test_a_sentinela_da_ponte_sai_sempre(self, directory):
        """Zero corroboracoes e indistinguivel de "a ponte nao rodou" sem ela."""
        _, facts, _, _ = run_fixture(directory)
        assert len(_kinds(facts, "bridge.analyzed")) == 1


def _fixture(nome: str) -> Path:
    return FIXTURES / nome


class TestOCruzamento:
    def test_o_callsite_que_bate_produz_corroboracao(self):
        """O lado positivo: `job.py:9` no codigo e no nome do stage."""
        _, facts, achados, _ = run_fixture(_fixture("collect_corroborado_pelo_stage"))
        confirmados = _kinds(facts, "bridge.driver_collect_confirmed")
        assert len(confirmados) == 1
        assert confirmados[0].subject["line"] == 9
        assert "SF-BRIDGE-001" in {a.rule_id for a in achados}

    def test_a_regra_da_ponte_e_confirmed_e_a_estatica_e_structural(self):
        """A diferenca e de NATUREZA, e ela sai no `status` das duas regras."""
        _, _, achados, _ = run_fixture(_fixture("collect_corroborado_pelo_stage"))
        ids = {a.rule_id for a in achados}
        assert {"SF-PY-002", "SF-BRIDGE-001"} <= ids, (
            "as duas precisam disparar juntas: a estatica afirma o risco, a "
            "ponte afirma que a linha executou"
        )
        catalogo = {r["id"]: r for r in load_catalog()}
        assert catalogo["SF-PY-002"]["status"] == "structural"
        assert catalogo["SF-BRIDGE-001"]["status"] == "confirmed"

    def test_a_medida_do_stage_sai_com_prefixo_e_nao_como_custo_da_linha(self):
        """Regra 13: nunca atribua custo a uma causa.

        O prefixo `stage_` existe para que "este collect gastou X" nao seja uma
        leitura possivel do campo. O numero e do STAGE.
        """
        _, facts, _, _ = run_fixture(_fixture("collect_corroborado_pelo_stage"))
        medidas = _kinds(facts, "bridge.driver_collect_confirmed")[0].measures
        assert medidas, "o stage tinha metrica de entrada; ela precisa viajar junto"
        assert all(nome.startswith("stage_") for nome in medidas), medidas

    def test_a_linha_errada_nao_cruza(self):
        """O par adversarial: mesmo arquivo, mesmo metodo, linha 99 em vez de 9.

        Se a chave virar `basename` sozinho, esta fixture passa a corroborar e o
        golden quebra -- que e exatamente o falso positivo em que dois `collect`
        do mesmo modulo viram um.
        """
        _, facts, achados, _ = run_fixture(
            _fixture("collect_com_stage_de_outra_linha")
        )
        assert _kinds(facts, "bridge.driver_collect_confirmed") == []
        assert "SF-BRIDGE-001" not in {a.rule_id for a in achados}
        assert "SF-PY-002" in {a.rule_id for a in achados}, (
            "o codigo estatico nao mudou; a regra estatica tem de continuar "
            "disparando -- se ela parar, o par negativo esta provando outra coisa"
        )

    def test_o_contrafactual_e_o_par_das_duas_fixtures(self):
        """A prova de que a ponte CRUZA, e nao so passa adiante o lado estatico.

        O MESMO `job.py` nas duas fixtures. A unica diferenca no corpus inteiro e
        o numero na linha do nome do stage. Se os dois conjuntos de achados
        fossem iguais, o cruzamento nao estaria acontecendo.
        """
        _, _, com, _ = run_fixture(_fixture("collect_corroborado_pelo_stage"))
        _, _, sem, _ = run_fixture(_fixture("collect_com_stage_de_outra_linha"))
        assert {a.rule_id for a in com} != {a.rule_id for a in sem}
        assert {a.rule_id for a in com} - {a.rule_id for a in sem} == {"SF-BRIDGE-001"}

    def test_callsite_de_biblioteca_scala_recusa_com_nome(self):
        """V-BR-2 como corpus: o stage nasceu fora do codigo do operador."""
        _, facts, achados, _ = run_fixture(
            _fixture("stage_nasceu_em_biblioteca_scala")
        )
        callsites = _kinds(facts, "spark.stage.callsite")
        assert callsites, "a recusa e FATO, nunca ausencia"
        assert callsites[0].attrs["resolved"] is False
        assert callsites[0].attrs["reason"] == "arquivo_nao_python"

        recusas = _kinds(facts, "bridge.unresolved")
        assert len(recusas) == 1
        assert recusas[0].attrs["reason"] == "sem_callsite_resolvido"
        assert recusas[0].attrs["unblocked_by"], "recusa sem destrava e so um erro"
        assert "SF-BRIDGE-001" not in {a.rule_id for a in achados}
