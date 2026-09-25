"""Os guardrails do §25, e o gate que os torna conferíveis.

O §25 do prompt de origem diz, literalmente: *"Qualquer recomendação que reduza
segurança deve possuir `security_impact` e `governance_decision_required`."*

Medido em 2026-09-10: **nenhum dos dois campos existia** em lugar nenhum do
repositório. A informação existia — em PROSA, nos `risks` e `tradeoffs` das
regras (`SF-LF-005`: *"Nos dois sentidos é mudança de postura de segurança, e
precisa de dono declarado"*) — e nenhum gate podia conferi-la.

## Por que campo declarado e não varredura de prosa

A primeira tentativa varreu `proposed_change` por regex das nove ações que o §25
proíbe. Ela achou "remover FGAC" em `SF-LF-001`, `SF-LF-002` e `SF-LF-005` — e
nas três é **um braço de bifurcação explícita**, com o outro braço apresentado
primeiro e o custo declarado. O regex confundiu a apresentação legítima da
escolha com o defeito que o §25 recorta.

Campo declarado resolve os dois lados: a regra diz, e o gate cobra.

## O recorte, e por que ele é por área e por namespace

`SF-LF`, `SF-IAM`, `SF-KMS`, `SF-XACC` — mais qualquer regra com `action.kind` no
namespace `security.`. Os dois critérios são **fechados e conferíveis**; texto
não é. Medido: 25 regras caem no recorte.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sparkforge.findings.models import area_of
from sparkforge.rules.loader import catalog_dir, load_catalog

VOCAB_FILE = "governance.yaml"


def _vocabulario() -> dict:
    caminho = catalog_dir() / VOCAB_FILE
    return yaml.safe_load(open(caminho, encoding="utf-8").read())


def _no_recorte() -> list[dict]:
    vocab = _vocabulario()
    areas = set(vocab["areas_de_governanca"])
    namespace = vocab["namespace_de_acao"]
    return [
        regra
        for regra in load_catalog()
        if area_of(regra["id"]) in areas
        or str((regra.get("action") or {}).get("kind", "")).startswith(namespace)
    ]


class TestOVocabulario:
    def test_o_arquivo_existe_e_nao_declara_regra(self):
        """`governance.yaml` é vocabulário, como `action_kinds.yaml`. Se ele
        declarasse regra, `load_catalog()` a contaria e o número publicado
        mudaria sem que ninguém tivesse escrito uma."""
        vocab = _vocabulario()
        assert "rules" not in vocab
        assert vocab["schema_version"] == 1

    def test_as_nove_acoes_proibidas_estao_declaradas_com_o_que_se_perde(self):
        """Listar a proibição sem dizer o que se perde produz uma lista que
        ninguém sabe aplicar."""
        nunca = _vocabulario()["nunca_automaticamente"]
        assert len(nunca) == 9
        for item in nunca:
            assert item["id"]
            assert item["descricao"]
            assert item["perde"], item["id"]

    def test_o_vocabulario_de_impacto_e_fechado_e_diz_quem_exige_dono(self):
        impactos = _vocabulario()["security_impact"]
        assert set(impactos) == {
            "none",
            "reduces_scope",
            "widens_scope",
            "changes_mechanism",
            "radius_beyond_job",
        }
        # `none` é o ÚNICO que não exige dono, e essa é a assimetria que o
        # vocabulário existe para tornar explícita.
        assert impactos["none"]["exige_dono"] is False
        for chave, valor in impactos.items():
            if chave == "none":
                continue
            assert valor["exige_dono"] is True, chave
            assert valor["descricao"]


class TestOGate:
    def test_o_recorte_nao_esta_vazio(self):
        """Gate que não cobre nada passa por vacuidade."""
        assert len(_no_recorte()) >= 25

    @pytest.mark.parametrize("regra", _no_recorte(), ids=lambda r: r["id"])
    def test_toda_regra_do_recorte_declara_os_dois_campos(self, regra):
        assert "governance_decision_required" in regra, regra["id"]
        assert isinstance(regra["governance_decision_required"], bool)
        assert "security_impact" in regra, regra["id"]

    @pytest.mark.parametrize("regra", _no_recorte(), ids=lambda r: r["id"])
    def test_o_impacto_esta_no_vocabulario(self, regra):
        assert regra["security_impact"] in _vocabulario()["security_impact"]

    @pytest.mark.parametrize("regra", _no_recorte(), ids=lambda r: r["id"])
    def test_impacto_que_exige_dono_declara_governance_true(self, regra):
        """A consistência entre os dois campos, e ela é o ponto do gate.

        Um `security_impact: widens_scope` com
        `governance_decision_required: false` seria uma regra dizendo "isto
        alarga o acesso e ninguém precisa aprovar" -- exatamente o que o §25
        proíbe.
        """
        impacto = _vocabulario()["security_impact"][regra["security_impact"]]
        assert regra["governance_decision_required"] is impacto["exige_dono"], (
            regra["id"],
            regra["security_impact"],
        )

    @pytest.mark.parametrize("regra", _no_recorte(), ids=lambda r: r["id"])
    def test_toda_declaracao_traz_a_razao(self, regra):
        """`security_impact` sem razão é etiqueta. A razão é o que permite
        revisar a classificação sem reler a regra inteira."""
        assert regra.get("security_impact_reason", "").strip(), regra["id"]

    def test_regra_fora_do_recorte_nao_e_obrigada_a_declarar(self):
        """O recorte é declarado, e o gate não vaza para fora dele: uma regra de
        `SF-PY` não tem por que falar de postura de segurança."""
        dentro = {r["id"] for r in _no_recorte()}
        fora = [r for r in load_catalog() if r["id"] not in dentro]
        assert fora
        # Nenhuma delas é obrigada -- mas se alguma declarar, o valor tem de ser
        # do vocabulário, porque campo com valor livre não é campo.
        vocab = _vocabulario()["security_impact"]
        for regra in fora:
            if "security_impact" in regra:
                assert regra["security_impact"] in vocab, regra["id"]


class TestAsQuatroAreasDeGovernanca:
    def test_as_areas_declaradas_existem_no_catalogo(self):
        """Área declarada que não existe é ponteiro para o nada."""
        do_catalogo = {area_of(r["id"]) for r in load_catalog()}
        for area in _vocabulario()["areas_de_governanca"]:
            assert area in do_catalogo, area

    def test_toda_regra_de_lf_iam_kms_e_xacc_esta_no_recorte(self):
        areas = set(_vocabulario()["areas_de_governanca"])
        do_recorte = {r["id"] for r in _no_recorte()}
        for regra in load_catalog():
            if area_of(regra["id"]) in areas:
                assert regra["id"] in do_recorte, regra["id"]

    def test_a_distribuicao_medida_do_recorte(self):
        """O número publicado, com a composição -- para que uma área nova de
        governança não entre sem ninguém notar."""
        import collections

        por_area = collections.Counter(area_of(r["id"]) for r in _no_recorte())
        # 10 -> 11 em 2026-09-25 com `SF-LF-011`, a permissão que falta atrás de
        # `ERR-LF-001`. Entra no recorte pela ÁREA.
        assert por_area["SF-LF"] == 11
        assert por_area["SF-IAM"] == 3
        assert por_area["SF-KMS"] == 2
        # 1 -> 3 em 2026-09-10 com `SF-XACC-002` e `SF-XACC-003`, as duas do
        # resource link. Elas entram no recorte pela ÁREA, como a primeira.
        assert por_area["SF-XACC"] == 3
        # As restantes vêm pelo NAMESPACE da ação e não pela área -- cinco
        # `SF-ERR` que julgam negação em runtime, e quatro de segredo em texto
        # claro (`security.move_secret_to_manager`).
        assert por_area["SF-ERR"] == 5
        assert sum(por_area.values()) == 28


def test_o_arquivo_de_vocabulario_nao_move_a_contagem_de_regras():
    """`governance.yaml` mora em `rules/catalog/` e NÃO é regra.

    `load_catalog()` ignora arquivo sem `rules:`, como já ignora
    `action_kinds.yaml` e `routing.yaml`. Este teste prende isso: se o loader
    passar a contá-lo, o número publicado de regras muda sem que ninguém tenha
    escrito uma.
    """
    # A primeira versao deste teste cobrava `not any(id.startswith("SF-GOV"))` e
    # falhou: `SF-GOVERNANCE-001` JA EXISTIA, de outra area. A assercao era
    # cega -- ela media o prefixo em vez do arquivo.
    #
    # O que importa e que `governance.yaml` nao contribua com regra NENHUMA, e
    # isso se mede pelo `_source_file` que o loader anexa.
    de_governance_yaml = [
        r["id"] for r in load_catalog() if r.get("_source_file") == VOCAB_FILE
    ]
    assert de_governance_yaml == []
    assert (Path(catalog_dir()) / VOCAB_FILE).is_file()
    assert (Path(catalog_dir()) / VOCAB_FILE).stat().st_size > 0
