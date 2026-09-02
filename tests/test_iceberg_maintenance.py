"""O plano de manutencao deriva do CATALOGO, e nao de limiar escrito nele.

Ate 2026-09-02 `generate_plan` recebia contagens cruas e decidia com
`small_files_count > 20`, `delete_files_count > 5`, `snapshots_count > 50` --
quatro numeros sem fonte, dos quais tres duplicavam `SF-ICE-001`, `SF-ICE-002` e
`SF-ICE-003`, que ja julgam a mesma coisa com `severity_by` medido e `sources`
citadas.

Estes testes travam a volta desse defeito.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from sparkforge.iceberg.maintenance import (
    ACOES_POR_REGRA,
    DESTRUTIVAS,
    IcebergMaintenancePlanner,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))


class _Achado:
    """O minimo que o planner le de um `Finding`: o `rule_id`."""

    def __init__(self, rule_id: str) -> None:
        self.rule_id = rule_id


@pytest.fixture
def planner():
    return IcebergMaintenancePlanner()


class TestOPlanoDerivaDoCatalogo:
    def test_sem_achado_nao_ha_acao(self, planner):
        """Uma tabela sa nao recebe plano. Antes, `rewrite_manifests` saia
        INCONDICIONALMENTE -- a unica acao do plano proposta sem evidencia
        nenhuma, num comando que o operador executaria."""
        plano = planner.plan_from_findings([], "db.sa", retention_days=7)
        assert plano.actions == []

    def test_cada_acao_cita_a_regra_que_a_autorizou(self, planner):
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-001")], "db.t", retention_days=7
        )
        assert plano.actions
        for a in plano.actions:
            assert a.authorized_by, "acao sem `authorized_by` nao deveria existir"
            assert a.authorized_by in ACOES_POR_REGRA

    def test_uma_regra_pode_autorizar_duas_acoes(self, planner):
        """`SF-ICE-002` pede `rewrite_data_files` para materializar os deletes E
        `expire_snapshots` para que os arquivos antigos possam sair."""
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-002")], "db.t", retention_days=7
        )
        tipos = {a.action_type for a in plano.actions}
        assert tipos == {"rewrite_data_files", "expire_snapshots"}

    def test_duas_regras_que_pedem_a_mesma_acao_nao_a_duplicam(self, planner):
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-002"), _Achado("SF-ICE-003")], "db.t", retention_days=7
        )
        tipos = [a.action_type for a in plano.actions]
        assert len(tipos) == len(set(tipos)), f"acao duplicada: {tipos}"
        expira = next(a for a in plano.actions if a.action_type == "expire_snapshots")
        assert "SF-ICE-002" in expira.authorized_by
        assert "SF-ICE-003" in expira.authorized_by

    def test_achado_de_regra_que_nao_pede_manutencao_nao_gera_acao(self, planner):
        """`SF-ICE-005` (distribution-mode) e defeito de ESCRITA, nao de layout
        acumulado. Nenhuma procedure o corrige."""
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-005")], "db.t", retention_days=7
        )
        assert plano.actions == []

    def test_nao_ha_limiar_escrito_no_modulo(self):
        """O limiar mora na REGRA, com fonte. Aqui mora a traducao para SQL.

        Por AST e nao por texto: a docstring do modulo CITA os limiares antigos
        (`small_files_count > 20`) como registro do defeito, e uma busca textual
        os acharia ali. O que se proibe e a COMPARACAO EXECUTAVEL contra numero,
        que e o que decide -- e ela e um `ast.Compare` com literal numerico de um
        lado, nao uma linha de prosa.
        """
        import ast

        from sparkforge.iceberg import maintenance

        arvore = ast.parse(Path(maintenance.__file__).read_text(encoding="utf-8"))
        culpados = [
            f"linha {no.lineno}"
            for no in ast.walk(arvore)
            if isinstance(no, ast.Compare)
            and any(
                isinstance(c, ast.Constant) and isinstance(c.value, (int, float))
                and not isinstance(c.value, bool)
                for c in no.comparators
            )
        ]
        assert not culpados, (
            f"comparacao contra numero de volta no modulo, em {culpados}. O limiar "
            f"mora na regra, com `severity_by` e `sources`; um numero decidindo "
            f"aqui seria a segunda verdade sobre a mesma pergunta."
        )


class TestARetencaoNaoTemDefault:
    def test_sem_retention_days_a_acao_destrutiva_e_RECUSADA(self, planner):
        """Reter N dias e escolha de negocio, nao medida.

        Um default aqui produziria um `expire_snapshots` com uma janela que
        ninguem declarou -- e ele apagaria snapshots de verdade. A regra 10 do
        CLAUDE.md proibe manutencao destrutiva sem escopo e retencao explicitos.
        """
        plano = planner.plan_from_findings([_Achado("SF-ICE-003")], "db.t")
        assert not [a for a in plano.actions if a.action_type == "expire_snapshots"]
        recusa = next(
            x for x in plano.refused if x.action_type == "expire_snapshots"
        )
        assert "retencao" in recusa.reason
        assert "retention_days" in recusa.unblocked_by

    def test_a_acao_reversivel_da_MESMA_regra_continua_saindo(self, planner):
        """Recusar a destrutiva nao pode calar a outra: `SF-ICE-002` pede duas,
        e so uma delas apaga."""
        plano = planner.plan_from_findings([_Achado("SF-ICE-002")], "db.t")
        tipos = {a.action_type for a in plano.actions}
        assert tipos == {"rewrite_data_files"}
        assert any(x.action_type == "expire_snapshots" for x in plano.refused)

    def test_com_retention_days_ela_sai_marcada_como_destrutiva(self, planner):
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-003")], "db.t", retention_days=30
        )
        acao = next(a for a in plano.actions if a.action_type == "expire_snapshots")
        assert acao.risk_level == "destructive"
        assert "30 DAYS" in acao.sql_command
        assert "DESTRUTIVO" in acao.estimated_impact
        assert plano.has_destructive is True


class TestARecusaSemRegra:
    def test_rewrite_manifests_sai_recusado_com_a_medida_que_o_destrava(self, planner):
        """Nenhuma regra julga o estado dos manifests hoje. Antes desta
        reescrita a acao saia sempre; agora ela sai na lista de recusas, com o
        que a destravaria."""
        plano = planner.plan_from_findings([], "db.t", retention_days=7)
        recusa = next(x for x in plano.refused if x.action_type == "rewrite_manifests")
        assert "nenhuma regra" in recusa.reason
        assert "manifests_summary" in recusa.reason
        assert recusa.unblocked_by

    def test_toda_recusa_tem_razao_e_destrava(self, planner):
        plano = planner.plan_from_findings([_Achado("SF-ICE-003")], "db.t")
        assert plano.refused
        for x in plano.refused:
            assert x.reason and x.unblocked_by


class TestOContratoDeSeguranca:
    def test_o_plano_e_sempre_dry_run_e_pede_aprovacao(self, planner):
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-001")], "db.t", retention_days=7
        )
        assert plano.is_dry_run is True
        assert plano.approval_required is True

    def test_has_destructive_e_false_quando_nada_apaga(self, planner):
        plano = planner.plan_from_findings(
            [_Achado("SF-ICE-001")], "db.t", retention_days=7
        )
        assert plano.has_destructive is False

    def test_as_destrutivas_estao_nomeadas(self):
        """`expire_snapshots` remove a possibilidade de time travel;
        `remove_orphan_files` apagaria arquivos que um metadata corrompido faz
        parecer orfaos."""
        assert "expire_snapshots" in DESTRUTIVAS
        assert "remove_orphan_files" in DESTRUTIVAS
        assert "rewrite_data_files" not in DESTRUTIVAS


class TestSobreOCorpusReal:
    """O contrafactual: as fixtures que disparam regra produzem plano, a sa nao."""

    @pytest.mark.parametrize(
        ("fixture", "esperado"),
        [
            ("small_files", {"rewrite_data_files"}),
            ("delete_debt", {"rewrite_data_files", "expire_snapshots"}),
            ("snapshot_churn", {"expire_snapshots"}),
            ("healthy_table", set()),
        ],
    )
    def test_o_plano_bate_com_o_que_o_catalogo_achou(self, planner, fixture, esperado):
        import test_fixtures_golden_iceberg as g

        resultado = g.run_fixture(g.FIXTURES / fixture)
        achados = resultado[2] if len(resultado) > 2 else []
        plano = planner.plan_from_findings(achados, f"db.{fixture}", retention_days=7)
        assert {a.action_type for a in plano.actions} == esperado
