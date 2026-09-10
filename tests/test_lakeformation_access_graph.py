"""O grafo de acesso a partir de FACTS, e o que ele recusa acusar.

O §13 do prompt de origem pede que o diagnóstico produza um GRAFO e não uma
lista. `LakeFormationPermissionGraph.evaluate_access` já produzia um -- e era
ÓRFÃO: medido em 2026-09-10, os únicos chamadores em todo o repositório eram o
próprio teste e o `__init__.py`.

E o motivo não era esquecimento. **Chamá-lo com lista vazia ACUSA**, e o primeiro
teste desta suíte prende isso: é a razão pela qual o caminho antigo não podia ser
ligado como estava.
"""
from __future__ import annotations

import pathlib

import pytest

from sparkforge.facts.iam_access import extract_iam_access_tree
from sparkforge.facts.lakeformation_grants import extract_lakeformation_tree
from sparkforge.lakeformation.graph import (
    STATUS_BLOCKING,
    STATUS_GRANTED,
    STATUS_NOT_APPLICABLE,
    STATUS_UNRESOLVED,
    LakeFormationPermissionGraph,
    build_access_graph,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
LF = ROOT / "fixtures" / "lakeformation"
IAM = ROOT / "fixtures" / "iam_access"


def _facts(diretorio: pathlib.Path, extrator) -> list:
    entrada = diretorio / "input"
    return list(extrator(entrada, repo_root=entrada))


def _por_tipo(grafo: dict, tipo: str) -> dict:
    (aresta,) = [e for e in grafo["edges"] if e["permission_type"] == tipo]
    return aresta


class TestPorQueOCaminhoAntigoEraInseguro:
    def test_evaluate_access_acusa_a_partir_de_lista_vazia(self):
        """O defeito que manteve o grafo órfão, prendido por teste.

        Ninguém coletou RAM share -- nenhum coletor deste repositório produz esse
        shape --, e a resposta é "o compartilhamento não foi aceito", com
        `is_accessible: False`. É acusação a partir de ausência de artefato.

        Este teste NÃO pede que o comportamento mude: ele documenta por que
        `build_access_graph` existe ao lado, e falha se alguém "consertar" o
        caminho antigo sem migrar os chamadores.
        """
        analise = LakeFormationPermissionGraph().evaluate_access(
            principal_arn="arn:aws:iam::111111111111:role/glue",
            target_table="db.t",
            grants=[{"table": "db.t", "permissions": ["SELECT"]}],
            ram_shares=[],
            kms_keys=[],
            is_cross_account=True,
        )
        assert analise.is_accessible is False
        (faltando,) = analise.missing_permissions
        assert faltando.permission_type == "ram_share"
        assert "not accepted" in faltando.evidence


class TestOTernario:
    def test_perna_sem_produtor_sai_unresolved_e_nunca_missing(self):
        caso = LF / "grant_de_leitura_em_local_registrado"
        grafo = build_access_graph(_facts(caso, extract_lakeformation_tree))
        assert grafo["status"] == "ok"
        for tipo in ("ram_share", "resource_link", "kms_decrypt"):
            aresta = _por_tipo(grafo, tipo)
            assert aresta["status"] == STATUS_UNRESOLVED, tipo
            # A recusa nomeia o que destravaria, e não só que falta.
            assert aresta["evidence"]

    def test_sem_bloqueio_e_com_perna_nao_medida_o_acesso_e_None(self):
        """`None` é "o que eu consegui olhar não impede", e não "funciona"."""
        caso = LF / "grant_de_leitura_em_local_registrado"
        grafo = build_access_graph(_facts(caso, extract_lakeformation_tree))
        assert grafo["is_accessible"] is None
        assert grafo["effective_path"] == []
        assert grafo["counts"]["blocked"] == 0
        assert grafo["counts"]["unresolved"] >= 3

    def test_iam_negado_torna_o_acesso_conclusivamente_falso(self):
        """Com bloqueio MEDIDO, a resposta deixa de ser `None`."""
        lf = _facts(LF / "grant_de_leitura_em_local_registrado", extract_lakeformation_tree)
        iam = _facts(IAM / "escrita_negada_pelo_boundary", extract_iam_access_tree)
        grafo = build_access_graph(lf + iam)
        assert grafo["status"] == "ok"
        assert grafo["is_accessible"] is False
        assert grafo["blocked"]
        # Cada bloqueio nomeia a CAMADA que negou -- é o que `iam.access_decision`
        # traz em `denied_by`, e o que separa três consertos diferentes.
        camadas = {
            e["evidence"].split("negado por ", 1)[1].split(" sobre", 1)[0]
            for e in grafo["blocked"]
            if "negado por " in e["evidence"]
        }
        assert camadas <= {
            "permissions_boundary",
            "service_control_policy",
            "explicit_deny",
            "implicit_deny",
            "razao nao nomeada",
        }
        assert camadas


class TestLocalizacaoNaoRegistradaNaoEFaltaDePermissao:
    def test_registered_false_sai_not_applicable(self):
        """O defeito que a primeira versão deste módulo teve.

        Ela marcava `registered: False` como `missing`, e `is_accessible` saía
        `False`. Tabela fora do registro do Lake Formation é lida com a
        credencial do RUNTIME ROLE, direto -- o registro não é uma perna que
        faltou, é uma perna que não participa. `missing` ali acusava de negar
        acesso justamente o arranjo em que o acesso não depende do Lake
        Formation.
        """
        caso = LF / "conta_sem_full_table_access"
        grafo = build_access_graph(_facts(caso, extract_lakeformation_tree))
        aresta = _por_tipo(grafo, "s3_registration")
        assert aresta["status"] == STATUS_NOT_APPLICABLE
        assert "runtime role" in aresta["evidence"]
        # E ela NÃO conta como bloqueio nem como lacuna de medida.
        assert grafo["counts"]["not_applicable"] == 1
        assert aresta not in grafo["blocked"]
        assert aresta not in grafo["unmeasured"]

    def test_registered_true_sai_granted(self):
        caso = LF / "grant_de_leitura_em_local_registrado"
        grafo = build_access_graph(_facts(caso, extract_lakeformation_tree))
        assert _por_tipo(grafo, "s3_registration")["status"] == STATUS_GRANTED


class TestOQueEleNaoEscolhe:
    def test_mais_de_uma_tabela_e_unresolved_nomeado(self):
        """Escolher a primeira produziria um grafo sobre um par que ninguém
        pediu."""
        de_dois = []
        for caso in sorted(p for p in LF.iterdir() if p.is_dir())[:2]:
            de_dois.extend(_facts(caso, extract_lakeformation_tree))
        grafo = build_access_graph(de_dois)
        assert grafo["status"] == "unresolved"
        assert grafo["reason"] in {
            "mais_de_uma_tabela_no_case",
            "mais_de_um_principal_no_case",
        }
        assert len(grafo["candidates"]) > 1
        assert grafo["unblocked_by"]

    def test_case_vazio_e_unresolved_e_diz_o_que_coletar(self):
        grafo = build_access_graph([])
        assert grafo["status"] == "unresolved"
        assert "collect lakeformation" in grafo["unblocked_by"]

    def test_iam_allowed_principals_nao_e_um_principal(self):
        """Ele é o marcador de que a tabela está aberta a quem tem IAM
        (`SF-LF-008`), e tratá-lo como principal montaria um grafo sobre uma
        entidade que não existe."""
        caso = LF / "grant_de_leitura_em_local_registrado"
        grafo = build_access_graph(_facts(caso, extract_lakeformation_tree))
        if grafo["status"] == "ok":
            assert grafo["principal_arn"] != "IAM_ALLOWED_PRINCIPALS"


class TestARecusaViajaNaResposta:
    def test_refused_nomeia_as_tres_pernas_sem_coletor(self):
        caso = LF / "grant_de_leitura_em_local_registrado"
        grafo = build_access_graph(_facts(caso, extract_lakeformation_tree))
        (recusa,) = grafo["refused"]
        assert recusa["what"] == "acusar_perna_sem_produtor"
        for termo in ("RAM", "resource link", "KMS"):
            assert termo in recusa["why"] or termo.lower() in recusa["why"].lower()
        assert recusa["unblocked_by"]


@pytest.mark.parametrize(
    "caso", sorted(p.name for p in LF.iterdir() if p.is_dir()), ids=lambda n: n
)
def test_nenhuma_fixture_produz_acesso_conclusivamente_verdadeiro(caso):
    """Nenhum case deste corpus mede TODAS as pernas, então nenhum pode sair
    `True` -- e isso é a resposta honesta, não uma limitação a esconder.

    Se um dia um coletor de RAM, resource link e KMS existir, este teste é o que
    vai avisar que o `True` passou a ser alcançável.
    """
    grafo = build_access_graph(_facts(LF / caso, extract_lakeformation_tree))
    if grafo["status"] != "ok":
        pytest.skip(f"{caso}: {grafo['reason']}")
    assert grafo["is_accessible"] is not True
    assert any(e["status"] == STATUS_UNRESOLVED for e in grafo["edges"])
    assert not any(
        e["status"] == STATUS_BLOCKING and e["permission_type"] in {"ram_share", "kms_decrypt"}
        for e in grafo["edges"]
    )
