"""`lakeformation.grant` -- o que a AWS respondeu, e a distincao que nao pode sumir.

Tres estados produzem a MESMA lista vazia de grants -- tabela sem grant, sem
permissao para ler os grants, e sem credencial --, e o que estes testes prendem e
que os tres continuem distinguiveis depois de virarem fact. Uma regra que os
trate igual acusa a tabela governada corretamente e a que ninguem conseguiu
inspecionar do mesmo jeito.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.facts.lakeformation_grants import (
    EMITTED_KINDS,
    extract_lakeformation_path,
)


def _artefato(tmp_path: Path, **blocos) -> Path:
    payload = {
        "catalog_id": "111111111111",
        "database": "curated",
        "table": "fato_venda",
        "status": "ok",
        "permissions": {
            "status": "ok",
            "principals": [],
            "grants_collected": 0,
            "truncated": False,
        },
        "registered_location": {
            "status": "ok",
            "resource_arn": "arn:aws:s3:::lake/curated/fato_venda",
            "registered": True,
            "role_arn": "arn:aws:iam::111111111111:role/lf-registration",
            "hybrid_access_enabled": False,
            "with_federation": False,
        },
        "data_lake_settings": {
            "status": "ok",
            "allow_full_table_external_data_access": True,
            "allow_external_data_filtering": True,
            "external_data_filtering_allow_list": ["111111111111"],
        },
    }
    payload.update(blocos)
    caminho = tmp_path / "lf.json"
    caminho.write_text(json.dumps(payload), encoding="utf-8")
    return caminho


def _grant(principal: str, permissoes: list[str]) -> dict:
    return {
        "Principal": {"DataLakePrincipalIdentifier": principal},
        "Permissions": permissoes,
        "PermissionsWithGrantOption": [],
        "Resource": {"Table": {"DatabaseName": "curated", "Name": "fato_venda"}},
    }


def _de(facts, kind):
    return [f for f in facts if f.kind == kind]


class TestGrant:
    def test_o_grant_sai_com_a_lista_verbatim(self, tmp_path):
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "ok",
                "principals": [_grant("arn:aws:iam::1:role/glue", ["SELECT", "DESCRIBE"])],
                "grants_collected": 1,
                "truncated": False,
            },
        )
        grants = _de(extract_lakeformation_path(arq), "lakeformation.grant")
        assert len(grants) == 1
        assert grants[0].attrs["permissions"] == ["DESCRIBE", "SELECT"]
        assert grants[0].attrs["has_select"] is True
        assert grants[0].attrs["has_all"] is False
        assert grants[0].measures["permission_count"] == 2

    def test_IAM_ALLOWED_PRINCIPALS_e_marcado_e_nao_normalizado(self, tmp_path):
        """Ele NAO e um role: e a ausencia de governanca fina.

        Reduzi-lo a um ARN qualquer apagaria a distincao mais importante desta
        area -- "concedido a este role" contra "concedido a qualquer principal".
        """
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "ok",
                "principals": [_grant("IAM_ALLOWED_PRINCIPALS", ["ALL"])],
                "grants_collected": 1,
                "truncated": False,
            },
        )
        grant = _de(extract_lakeformation_path(arq), "lakeformation.grant")[0]
        assert grant.attrs["is_iam_allowed_principals"] is True
        assert grant.attrs["principal"] == "IAM_ALLOWED_PRINCIPALS"

    def test_dois_principais_produzem_dois_facts_com_ids_distintos(self, tmp_path):
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "ok",
                "principals": [
                    _grant("arn:aws:iam::1:role/a", ["SELECT"]),
                    _grant("arn:aws:iam::1:role/b", ["ALL"]),
                ],
                "grants_collected": 2,
                "truncated": False,
            },
        )
        grants = _de(extract_lakeformation_path(arq), "lakeformation.grant")
        assert len(grants) == 2
        assert len({g.id for g in grants}) == 2

    def test_paginacao_truncada_sai_como_recusa_AO_LADO_dos_grants(self, tmp_path):
        """Lista parcial e valida e NAO e completa, e as duas coisas saem juntas."""
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "ok",
                "principals": [_grant("arn:aws:iam::1:role/a", ["SELECT"])],
                "grants_collected": 1,
                "truncated": True,
            },
        )
        facts = extract_lakeformation_path(arq)
        assert _de(facts, "lakeformation.grant")
        recusas = _de(facts, "lakeformation.grants.unresolved")
        assert [r.attrs["reason"] for r in recusas] == ["paginacao_truncada"]


class TestOsTresEstadosDaListaVazia:
    """O ponto do modulo, medido."""

    def test_tabela_SEM_grant_nao_emite_grant_e_nomeia_vazio(self, tmp_path):
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "vazio",
                "principals": [],
                "grants_collected": 0,
                "truncated": False,
            },
        )
        facts = extract_lakeformation_path(arq)
        assert not _de(facts, "lakeformation.grant")
        recusas = [
            r
            for r in _de(facts, "lakeformation.grants.unresolved")
            if r.attrs["block"] == "permissions"
        ]
        assert [r.attrs["reason"] for r in recusas] == ["vazio"]

    @pytest.mark.parametrize("status", ["sem_permissao", "sem_credencial"])
    def test_falha_de_coleta_NAO_vira_ausencia_de_permissao(self, tmp_path, status):
        arq = _artefato(
            tmp_path,
            permissions={
                "status": status,
                "principals": [],
                "grants_collected": 0,
                "truncated": False,
            },
        )
        facts = extract_lakeformation_path(arq)
        assert not _de(facts, "lakeformation.grant")
        recusas = [
            r
            for r in _de(facts, "lakeformation.grants.unresolved")
            if r.attrs["block"] == "permissions"
        ]
        assert [r.attrs["reason"] for r in recusas] == [status]
        assert recusas[0].attrs["unblocked_by"]


class TestLocalizacaoRegistrada:
    def test_registrada(self, tmp_path):
        facts = extract_lakeformation_path(_artefato(tmp_path))
        loc = _de(facts, "lakeformation.registered_location")
        assert len(loc) == 1
        assert loc[0].attrs["registered"] is True
        assert loc[0].attrs["role_arn"].endswith("lf-registration")

    def test_NAO_registrada_e_afirmacao_quando_a_AWS_respondeu(self, tmp_path):
        arq = _artefato(
            tmp_path,
            registered_location={
                "status": "nao_encontrado",
                "resource_arn": "arn:aws:s3:::lake/x",
                "registered": False,
                "role_arn": "",
            },
        )
        loc = _de(extract_lakeformation_path(arq), "lakeformation.registered_location")
        assert [f.attrs["registered"] for f in loc] == [False]

    @pytest.mark.parametrize("bloco", [
        {"status": "sem_permissao", "registered": None},
        {"status": "nao_coletado", "registered": None, "reason": "resource_arn_nao_informado"},
    ])
    def test_NINGUEM_MEDIU_nao_vira_nao_registrada(self, tmp_path, bloco):
        """O terceiro valor do ternario, e e ele que importa.

        E exatamente sobre localizacao REGISTRADA que a §6 do documento de
        conhecimento declara conflito entre quatro frases da AWS. Tratar
        `None` como `False` faria o motor afirmar "nao registrada" sobre uma
        pergunta que nao foi feita, e sair do conflito pela porta errada.
        """
        arq = _artefato(tmp_path, registered_location=bloco)
        facts = extract_lakeformation_path(arq)
        assert not _de(facts, "lakeformation.registered_location")
        recusas = [
            r
            for r in _de(facts, "lakeformation.grants.unresolved")
            if r.attrs["block"] == "registered_location"
        ]
        assert len(recusas) == 1


class TestDataLakeSettings:
    def test_o_passo_de_conta_sai_como_fact(self, tmp_path):
        """`AllowFullTableExternalDataAccess` e o que a documentacao de Full
        Table Access chama de *application integration* -- o passo de CONTA que
        precede qualquer grant, e que nenhum artefato do job revela."""
        s = _de(extract_lakeformation_path(_artefato(tmp_path)), "lakeformation.data_lake_settings")
        assert len(s) == 1
        assert s[0].attrs["allow_full_table_external_data_access"] is True

    def test_desligado_e_estado_e_nao_ausencia(self, tmp_path):
        arq = _artefato(
            tmp_path,
            data_lake_settings={
                "status": "ok",
                "allow_full_table_external_data_access": False,
                "allow_external_data_filtering": False,
                "external_data_filtering_allow_list": [],
            },
        )
        s = _de(extract_lakeformation_path(arq), "lakeformation.data_lake_settings")
        assert s[0].attrs["allow_full_table_external_data_access"] is False

    def test_sem_permissao_para_ler_settings_sai_recusa(self, tmp_path):
        arq = _artefato(tmp_path, data_lake_settings={"status": "sem_permissao"})
        facts = extract_lakeformation_path(arq)
        assert not _de(facts, "lakeformation.data_lake_settings")
        recusas = [
            r
            for r in _de(facts, "lakeformation.grants.unresolved")
            if r.attrs["block"] == "data_lake_settings"
        ]
        assert [r.attrs["reason"] for r in recusas] == ["sem_permissao"]


class TestContratoDoModulo:
    def test_a_sentinela_sai_SEMPRE(self, tmp_path):
        """Sem ela, "o artefato foi lido e nao tinha nada" e "ninguem leu
        artefato nenhum" seriam indistinguiveis."""
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "sem_credencial",
                "principals": [],
                "grants_collected": 0,
                "truncated": False,
            },
            registered_location={"status": "sem_credencial", "registered": None},
            data_lake_settings={"status": "sem_credencial"},
        )
        facts = extract_lakeformation_path(arq)
        assert len(_de(facts, "lakeformation.grants.analyzed")) == 1

    def test_todo_kind_emitido_esta_declarado(self, tmp_path):
        arq = _artefato(
            tmp_path,
            permissions={
                "status": "ok",
                "principals": [_grant("arn:aws:iam::1:role/a", ["SELECT"])],
                "grants_collected": 1,
                "truncated": True,
            },
        )
        assert {f.kind for f in extract_lakeformation_path(arq)} <= EMITTED_KINDS

    def test_nenhum_fact_carrega_juizo(self, tmp_path):
        proibidos = {"severity", "confidence", "fixes", "sufficient", "recommendation"}
        for fact in extract_lakeformation_path(_artefato(tmp_path)):
            assert not proibidos & set(fact.attrs), fact.kind
