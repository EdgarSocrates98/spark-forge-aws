"""O extrator de resource link, bloco a bloco.

O golden (`tests/test_fixtures_golden_resource_link.py`) prende tres artefatos
inteiros. Aqui ficam os estados que nenhum deles alcanca -- e sao justamente os
que separam "nao ha" de "nao consegui":

    sem_permissao / sem_credencial   a chamada nao respondeu
    objeto que NAO e link            medido, e nao e defeito
    `verify_target` desligado        ninguem perguntou pela origem
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.facts.glue_resource_link import (
    EMITTED_KINDS,
    extract_glue_resource_link_path,
)
from sparkforge.findings.validate import validate_fact


def _escrever(tmp_path: Path, payload: dict) -> Path:
    alvo = tmp_path / "artefato.json"
    alvo.write_text(json.dumps(payload), encoding="utf-8")
    return alvo


def _extrair(tmp_path: Path, payload: dict):
    facts = extract_glue_resource_link_path(_escrever(tmp_path, payload))
    for fact in facts:
        validate_fact(fact.to_dict())
    return list(facts)


def _por_kind(facts, kind: str):
    """Um por kind -- e ERRO se houver dois.

    `glue.resource_link.unresolved` sai uma vez POR BLOCO, e indexar por kind
    faria a segunda recusa apagar a primeira em silencio. Quem quer recusa usa
    `_recusa`.
    """
    achados = [f for f in facts if f.kind == kind]
    assert len(achados) == 1, f"{kind}: {len(achados)}"
    return achados[0]


def _kinds(facts) -> set[str]:
    return {f.kind for f in facts}


def _recusa(facts, bloco: str):
    achados = [
        f
        for f in facts
        if f.kind == "glue.resource_link.unresolved" and f.attrs["block"] == bloco
    ]
    assert len(achados) == 1, f"{bloco}: {len(achados)}"
    return achados[0]


def _link_ok(**overrides) -> dict:
    bloco = {
        "status": "ok",
        "aws_error_code": "",
        "target_type": "table",
        "requested_catalog_id": "111111111111",
        "requested_database": "analytics",
        "requested_table": "fato_venda",
        "is_resource_link": True,
        "link_name": "fato_venda",
        "link_database": "analytics",
        "link_catalog_id": "111111111111",
        "target_catalog_id": "999999999999",
        "target_database": "curated",
        "target_name": "fato_venda",
        "target_region": "us-east-1",
    }
    bloco.update(overrides)
    return bloco


def _payload(link: dict, target: dict) -> dict:
    return {
        "catalog_id": "111111111111",
        "database": "analytics",
        "table": "fato_venda",
        "target_type": link.get("target_type", "table"),
        "status": "ok",
        "link": link,
        "target": target,
    }


class TestASentinelaSaiSempre:
    def test_ate_com_os_dois_blocos_recusados(self, tmp_path):
        facts = _extrair(
            tmp_path,
            _payload(
                {"status": "sem_credencial", "aws_error_code": "NoCredentialsError"},
                {"status": "sem_credencial"},
            ),
        )
        assert "glue.resource_link.analyzed" in _kinds(facts)
        # E os DOIS blocos viram recusa NOMEADA, nunca ausencia silenciosa.
        assert _recusa(facts, "link").attrs["reason"] == "sem_credencial"
        assert _recusa(facts, "target").attrs["reason"] == "sem_credencial"

    def test_todo_kind_emitido_esta_declarado(self, tmp_path):
        facts = _extrair(tmp_path, _payload(_link_ok(), {"status": "ok", "name": "fato_venda"}))
        assert _kinds(facts) <= EMITTED_KINDS


class TestOQueNaoFoiMedidoNaoVIRAAcusacao:
    @pytest.mark.parametrize("status", ["sem_permissao", "sem_credencial"])
    def test_link_que_nao_respondeu_nao_emite_topologia(self, tmp_path, status):
        facts = _extrair(tmp_path, _payload({"status": status}, {"status": "nao_coletado"}))
        assert "glue.resource_link" not in _kinds(facts)
        assert _recusa(facts, "link").attrs["reason"] == status
        assert _recusa(facts, "link").attrs["unblocked_by"]

    def test_verify_target_desligado_nomeia_a_lacuna(self, tmp_path):
        facts = _extrair(
            tmp_path,
            _payload(
                _link_ok(),
                {"status": "nao_coletado", "reason": "verify_target_desligado"},
            ),
        )
        assert "glue.resource_link.target" not in _kinds(facts)
        assert _recusa(facts, "target").attrs["reason"] == "verify_target_desligado"


class TestObjetoQueNaoELink:
    """Tabela comum NAO tem recurso de origem, e responder `False` em
    `name_matches_source` acusaria de nome divergente algo que nao tem nome com o
    que divergir."""

    def test_name_matches_source_sai_nulo(self, tmp_path):
        facts = _extrair(
            tmp_path,
            _payload(
                _link_ok(
                    is_resource_link=False,
                    target_catalog_id="",
                    target_database="",
                    target_name="",
                    target_region="",
                ),
                {"status": "nao_coletado", "reason": "sem_alvo_medido_no_link"},
            ),
        )
        link = _por_kind(facts, "glue.resource_link")
        assert link.attrs["is_resource_link"] is False
        assert link.attrs["name_matches_source"] is None
        assert link.attrs["cross_account"] is None
        assert link.attrs["source_resource_name"] == ""


class TestAComparacaoDeNomePorTipo:
    def test_tabela_compara_contra_target_name(self, tmp_path):
        facts = _extrair(
            tmp_path,
            _payload(
                _link_ok(link_name="fato_venda_prod"),
                {"status": "ok", "name": "fato_venda"},
            ),
        )
        assert _por_kind(facts, "glue.resource_link").attrs["name_matches_source"] is False
        assert _por_kind(facts, "glue.resource_link").attrs["source_resource_name"] == "fato_venda"

    def test_banco_compara_contra_target_database(self, tmp_path):
        """`TargetDatabase` nao tem campo `Name`. Comparar contra `target_name`
        daria `False` em todo link de banco correto."""
        facts = _extrair(
            tmp_path,
            _payload(
                _link_ok(
                    target_type="database",
                    link_name="curated",
                    link_database="curated",
                    target_database="curated",
                    target_name="",
                ),
                {"status": "ok", "name": ""},
            ),
        )
        link = _por_kind(facts, "glue.resource_link")
        assert link.attrs["target_name"] == ""
        assert link.attrs["source_resource_name"] == "curated"
        assert link.attrs["name_matches_source"] is True


class TestCrossAccountSaiDeDoisCampoMedidos:
    def test_contas_diferentes(self, tmp_path):
        facts = _extrair(tmp_path, _payload(_link_ok(), {"status": "ok", "name": "fato_venda"}))
        assert _por_kind(facts, "glue.resource_link").attrs["cross_account"] is True

    def test_mesma_conta(self, tmp_path):
        facts = _extrair(
            tmp_path,
            _payload(
                _link_ok(target_catalog_id="111111111111"),
                {"status": "ok", "name": "fato_venda"},
            ),
        )
        assert _por_kind(facts, "glue.resource_link").attrs["cross_account"] is False

    def test_catalogo_ausente_nao_vira_False(self, tmp_path):
        """Preencher com a conta da credencial seria inventar o dado que a
        pergunta pede."""
        facts = _extrair(
            tmp_path,
            _payload(
                _link_ok(link_catalog_id=""),
                {"status": "ok", "name": "fato_venda"},
            ),
        )
        assert _por_kind(facts, "glue.resource_link").attrs["cross_account"] is None
