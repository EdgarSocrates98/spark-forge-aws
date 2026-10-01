"""Migracao entre versoes de Control-M: o caminho, as fronteiras e as recusas.

O contrafactual central deste arquivo e o par `9.0.21.300` <-> `9.0.22.005` com um
job que usa `Job:DetachedEmbeddedScript`: subindo e ganho, descendo e quebra. Se
os dois lados derem o mesmo veredito, o motor esta passando adiante o conjunto de
capacidades sem cruzar com a matriz.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sparkforge.controlm import matrix as cm_matrix
from sparkforge.controlm.migration import (
    SEVERIDADE_POR_FRONTEIRA,
    ControlMMigrationError,
    avaliar,
    caminho,
)
from sparkforge.facts.controlm_jobs import extract_controlm_jobs_path

ROOT = Path(__file__).resolve().parents[1]
# A fixture que o incremento 2 ja usa como prova do cruzamento: um job com
# `Job:DetachedEmbeddedScript`, cuja fronteira e `9.0.22.005`.
CORPUS = ROOT / "fixtures" / "controlm" / "capacidade_abaixo_da_fronteira" / "input"

ANTES = "9.0.21.300"
DEPOIS = "9.0.22.005"
CAPACIDADE = "job_detached_embedded_script"


@pytest.fixture(scope="module")
def facts():
    arquivo = next(CORPUS.glob("*.json"))
    return extract_controlm_jobs_path(arquivo, repo_root=CORPUS, declared_version=DEPOIS)


class TestOCaminho:
    def test_sobe_pelos_degraus_adjacentes_da_matriz(self):
        degraus = caminho(ANTES, DEPOIS)
        assert degraus
        assert degraus[0][0] == ANTES
        assert degraus[-1][1] == DEPOIS
        for (_, chegada), (partida, _) in zip(degraus, degraus[1:], strict=False):
            assert chegada == partida, "os degraus precisam ser adjacentes"

    def test_desce_tambem_e_isso_e_caso_legitimo(self):
        """`migration.version_path.steps` recusa alvo anterior a origem.

        Aqui descer e legitimo: um cliente pode estar levando um job para um
        ambiente mais antigo, e e exatamente onde `introduced_in` morde. Recusar
        a descida esconderia metade dos casos em que a fronteira importa.
        """
        descendo = caminho(DEPOIS, ANTES)
        subindo = caminho(ANTES, DEPOIS)
        assert len(descendo) == len(subindo)
        assert descendo[0][0] == DEPOIS
        assert descendo[-1][1] == ANTES

    def test_origem_igual_ao_alvo_nao_tem_degrau_e_isso_e_resposta(self):
        assert caminho(ANTES, ANTES) == []

    def test_versao_fora_da_matriz_recusa_com_a_faixa(self):
        """A fonte anda de 5 em 5: `9.0.21.301` nao existe, e a recusa diz isso."""
        with pytest.raises(ControlMMigrationError) as erro:
            caminho("9.0.21.301", DEPOIS)
        assert "9.0.21.301" in str(erro.value)
        assert "5 em 5" in str(erro.value)

    def test_a_ordem_e_de_VERSAO_e_nao_a_editorial_da_fonte(self):
        """`known_versions()` devolve na ordem do YAML, que e a da fonte -- mais
        nova primeiro. Ordem editorial nao e ordem de caminho: quem migra sobe."""
        degraus = caminho(ANTES, DEPOIS)
        chave = lambda v: tuple(int(p) for p in v.split("."))  # noqa: E731
        for de, para in degraus:
            assert chave(de) < chave(para)


class TestOContrafactualDaDirecao:
    def test_subindo_a_capacidade_que_nasce_e_GANHO(self, facts):
        a = avaliar(facts, ANTES, DEPOIS)
        assert a.direcao == "forward"
        mudancas = [m for d in a.degraus for m in d.mudancas if m.capability == CAPACIDADE]
        assert len(mudancas) == 1
        assert mudancas[0].severity == "gain"
        assert mudancas[0].boundary == "introduced_in"
        assert a.gate == "compatible"
        assert a.quebras == ()

    def test_descendo_a_MESMA_capacidade_e_QUEBRA(self, facts):
        """O contrafactual. Se os dois lados derem o mesmo veredito, o motor nao
        esta cruzando com a matriz -- esta repetindo o conjunto do job."""
        a = avaliar(facts, DEPOIS, ANTES)
        assert a.direcao == "backward"
        assert a.gate == "incompatible"
        assert [m.capability for m in a.quebras] == [CAPACIDADE]

    def test_os_dois_sentidos_nao_dao_o_mesmo_resultado(self, facts):
        subindo = avaliar(facts, ANTES, DEPOIS)
        descendo = avaliar(facts, DEPOIS, ANTES)
        assert subindo.gate != descendo.gate

    def test_nao_ha_inversao_por_direcao_e_a_razao_esta_medida(self):
        """A primeira versao deste modulo invertia a severidade ao descer, e o
        teste acima a pegou: dava `gain` onde a capacidade nao existe no destino.

        `descriptor.describe(v)` e CUMULATIVO -- lista o que esta disponivel EM
        `v` --, entao presenca e ausencia ja codificam a direcao. Medido:
        `9.0.22.000` tem 34 capacidades sem a do teste, `9.0.22.005` tem 35 com
        ela. Inverter depois disso era inverter duas vezes a mesma coisa.

        Este teste existe para que a "correcao" obvia -- reintroduzir a inversao
        — tenha de passar por cima de uma medicao.
        """
        from sparkforge.controlm import migration

        assert not hasattr(migration, "_inverter")
        from sparkforge.controlm import descriptor as d

        antes = dict(d.describe("9.0.22.000").capabilities)
        depois = dict(d.describe("9.0.22.005").capabilities)
        assert CAPACIDADE not in antes
        assert CAPACIDADE in depois
        assert len(depois) > len(antes), "o descritor precisa ser cumulativo"


class TestAsQuatroFronteiras:
    def test_as_quatro_estao_declaradas_e_nao_valem_o_mesmo(self):
        assert set(SEVERIDADE_POR_FRONTEIRA) == set(cm_matrix.BOUNDARIES)
        assert len(set(SEVERIDADE_POR_FRONTEIRA.values())) > 1, (
            "somar as quatro num rotulo so esconderia a unica que derruba o job"
        )

    def test_discontinued_e_changed_quebram_e_deprecated_avisa(self):
        """`changed_in` e `break` de proposito: a capacidade continua la, o job
        continua chamando, e o comportamento e outro. Um aviso convidaria a
        adiar a leitura -- que e o caso em que ela morde."""
        assert SEVERIDADE_POR_FRONTEIRA["discontinued_in"] == "break"
        assert SEVERIDADE_POR_FRONTEIRA["changed_in"] == "break"
        assert SEVERIDADE_POR_FRONTEIRA["deprecated_from"] == "warn"
        assert SEVERIDADE_POR_FRONTEIRA["introduced_in"] == "gain"


class TestORelatorio:
    def test_so_reporta_capacidade_que_o_JOB_usa(self, facts):
        """Reportar toda capacidade da matriz faria o relatorio crescer com a
        fonte em vez de com o artefato."""
        a = avaliar(facts, ANTES, DEPOIS)
        assert a.capacidades_do_job == (CAPACIDADE,)
        for d in a.degraus:
            for m in d.mudancas:
                assert m.capability in a.capacidades_do_job

    def test_o_gate_do_relatorio_e_o_pior_dos_degraus(self, facts):
        a = avaliar(facts, DEPOIS, ANTES)
        assert a.gate == "incompatible"
        assert any(d.gate == "incompatible" for d in a.degraus)

    def test_cada_mudanca_carrega_a_fronteira_e_onde_ela_foi_declarada(self, facts):
        a = avaliar(facts, ANTES, DEPOIS)
        for d in a.degraus:
            for m in d.mudancas:
                assert m.boundary in cm_matrix.BOUNDARIES
                assert m.declared_at, "sem `declared_at` a fronteira nao e conferivel"
                assert m.summary, "sem resumo o achado nao diz o que mudou"

    def test_as_recusas_do_extrator_viajam_junto(self, facts):
        """Recusa que vira ausencia no relatorio se le como 'nada a declarar'."""
        a = avaliar(facts, ANTES, DEPOIS)
        for r in a.unresolved:
            assert r["capability"] or r["reason"]
            assert r["reason"], "recusa sem razao e so um buraco"

    def test_job_sem_capacidade_conhecida_nao_inventa_mudanca(self, facts, tmp_path):
        """Um job que a matriz nao data produz zero mudancas, e nao um verde."""
        vazio = tmp_path / "jobs.json"
        vazio.write_text('{"Defaults": {}}', encoding="utf-8")
        f = extract_controlm_jobs_path(vazio, repo_root=tmp_path, declared_version=ANTES)
        a = avaliar(f, ANTES, DEPOIS)
        assert a.capacidades_do_job == ()
        assert all(not d.mudancas for d in a.degraus)
        assert a.gate == "compatible"
