"""`iam.access_decision` -- a camada que negou, e nao apenas que negou.

O que estes testes prendem: `EvalDecision` tem quatro respostas e as tres de
negacao exigem consertos DIFERENTES. Colapsa-las num booleano faria "adicione a
permissao" virar o conselho unico -- e ele e errado em tres dos quatro casos.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sparkforge.facts.iam_access import EMITTED_KINDS, extract_iam_access_path


def _artefato(tmp_path: Path, resultados: list[dict], **extra) -> Path:
    payload = {
        "role_arn": "arn:aws:iam::111111111111:role/glue-curated",
        "status": "ok",
        "actions_requested": ["s3:PutObject"],
        "resource_arns": ["arn:aws:s3:::lake/curated/*"],
        "scoped_to_resource": True,
        "results": resultados,
        "results_collected": len(resultados),
        "truncated": False,
    }
    payload.update(extra)
    caminho = tmp_path / "iam.json"
    caminho.write_text(json.dumps(payload), encoding="utf-8")
    return caminho


def _r(decisao: str, **extra) -> dict:
    base = {
        "action": "s3:PutObject",
        "resource": "arn:aws:s3:::lake/curated/*",
        "decision": decisao,
        "matched_statements": 1,
        "missing_context_values": [],
        "allowed_by_organizations": None,
        "allowed_by_permissions_boundary": None,
    }
    base.update(extra)
    return base


def _de(facts, kind):
    return [f for f in facts if f.kind == kind]


class TestAsQuatroRespostas:
    def test_allowed(self, tmp_path):
        artefato = _artefato(tmp_path, [_r("allowed")])
        d = _de(extract_iam_access_path(artefato), "iam.access_decision")[0]
        assert d.attrs["allowed"] is True
        assert d.attrs["denied_by"] == ""

    def test_implicit_deny_o_conserto_e_ACRESCENTAR(self, tmp_path):
        artefato = _artefato(tmp_path, [_r("implicitDeny")])
        d = _de(extract_iam_access_path(artefato), "iam.access_decision")[0]
        assert d.attrs["allowed"] is False
        assert d.attrs["denied_by"] == "implicit_deny"

    def test_explicit_deny_ACRESCENTAR_nao_resolve(self, tmp_path):
        """Alguma policy NEGA. Adicionar `Allow` nao muda nada -- `Deny` vence."""
        artefato = _artefato(tmp_path, [_r("explicitDeny")])
        d = _de(extract_iam_access_path(artefato), "iam.access_decision")[0]
        assert d.attrs["denied_by"] == "explicit_deny"

    def test_service_control_policy_vence_a_policy_do_role(self, tmp_path):
        """A negacao veio de CIMA. Editar a policy do role nao decide nada, e
        reportar `explicit_deny` aqui mandaria o operador ao documento errado."""
        d = _de(
            extract_iam_access_path(
                _artefato(tmp_path, [_r("explicitDeny", allowed_by_organizations=False)])
            ),
            "iam.access_decision",
        )[0]
        assert d.attrs["denied_by"] == "service_control_policy"

    def test_permissions_boundary_tambem_vence(self, tmp_path):
        d = _de(
            extract_iam_access_path(
                _artefato(
                    tmp_path, [_r("implicitDeny", allowed_by_permissions_boundary=False)]
                )
            ),
            "iam.access_decision",
        )[0]
        assert d.attrs["denied_by"] == "permissions_boundary"

    def test_a_ordem_e_SCP_antes_de_boundary_antes_da_policy(self, tmp_path):
        """Com os dois negando, a camada mais alta e a que sai."""
        d = _de(
            extract_iam_access_path(
                _artefato(
                    tmp_path,
                    [
                        _r(
                            "explicitDeny",
                            allowed_by_organizations=False,
                            allowed_by_permissions_boundary=False,
                        )
                    ],
                )
            ),
            "iam.access_decision",
        )[0]
        assert d.attrs["denied_by"] == "service_control_policy"


class TestOEscopoDaPergunta:
    def test_sem_recurso_o_fact_DIZ_que_foi_sobre_estrela(self, tmp_path):
        """`allowed` sobre `*` nao e `allowed` naquela tabela.

        Sem `scoped_to_resource`, os dois seriam o mesmo fact -- e a regra que
        os lesse concluiria autorizacao sobre um recurso que ninguem simulou.
        """
        arq = _artefato(
            tmp_path, [_r("allowed", resource="*")], scoped_to_resource=False, resource_arns=[]
        )
        d = _de(extract_iam_access_path(arq), "iam.access_decision")[0]
        assert d.attrs["scoped_to_resource"] is False

    def test_contexto_que_faltou_viaja_no_fact(self, tmp_path):
        """A simulacao nao e a execucao, e `missing_context_values` e onde essa
        diferenca fica visivel."""
        arq = _artefato(
            tmp_path, [_r("implicitDeny", missing_context_values=["aws:SourceIp"])]
        )
        d = _de(extract_iam_access_path(arq), "iam.access_decision")[0]
        assert d.attrs["missing_context_values"] == ["aws:SourceIp"]


class TestOLimiteQueSaiSEMPRE:
    def test_policy_de_recurso_nao_avaliada_sai_ate_com_tudo_ok(self, tmp_path):
        """Um `allowed` aqui com bucket policy negando ainda falha.

        Publicar o limite em TODO artefato e o que impede o achado de prometer
        mais do que mediu.
        """
        facts = extract_iam_access_path(_artefato(tmp_path, [_r("allowed")]))
        razoes = [f.attrs["reason"] for f in _de(facts, "iam.access.unresolved")]
        assert "policy_de_recurso_nao_avaliada" in razoes

    @pytest.mark.parametrize("status", ["sem_permissao", "sem_credencial", "nao_encontrado"])
    def test_falha_de_coleta_nao_vira_negacao(self, tmp_path, status):
        arq = _artefato(tmp_path, [], status=status)
        facts = extract_iam_access_path(arq)
        assert not _de(facts, "iam.access_decision")
        razoes = [f.attrs["reason"] for f in _de(facts, "iam.access.unresolved")]
        assert status in razoes

    def test_paginacao_truncada_sai_ao_lado_das_decisoes(self, tmp_path):
        arq = _artefato(tmp_path, [_r("allowed")], truncated=True)
        facts = extract_iam_access_path(arq)
        assert _de(facts, "iam.access_decision")
        razoes = [f.attrs["reason"] for f in _de(facts, "iam.access.unresolved")]
        assert "paginacao_truncada" in razoes


class TestContratoDoModulo:
    def test_a_sentinela_sai_sempre_e_conta_as_decisoes(self, tmp_path):
        facts = extract_iam_access_path(
            _artefato(tmp_path, [_r("allowed"), _r("implicitDeny", action="kms:Decrypt")])
        )
        s = _de(facts, "iam.access.analyzed")
        assert len(s) == 1
        assert s[0].measures["decisions"] == 2

    def test_duas_decisoes_tem_ids_distintos(self, tmp_path):
        facts = extract_iam_access_path(
            _artefato(tmp_path, [_r("allowed"), _r("allowed", action="kms:Decrypt")])
        )
        d = _de(facts, "iam.access_decision")
        assert len({f.id for f in d}) == 2

    def test_todo_kind_emitido_esta_declarado(self, tmp_path):
        facts = extract_iam_access_path(_artefato(tmp_path, [_r("allowed")], truncated=True))
        assert {f.kind for f in facts} <= EMITTED_KINDS

    def test_nenhum_fact_carrega_juizo(self, tmp_path):
        proibidos = {"severity", "confidence", "fixes", "recommendation", "sufficient"}
        for f in extract_iam_access_path(_artefato(tmp_path, [_r("explicitDeny")])):
            assert not proibidos & set(f.attrs), f.kind
