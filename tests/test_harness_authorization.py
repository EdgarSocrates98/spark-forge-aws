"""Secao 40 e 76: classe de tool DERIVADA, e autorizacao com cadeia.

A classificacao nao e uma segunda lista mantida a mao. As anotacoes MCP de cada
tool ja carregam as tres dimensoes que a definem -- `readOnlyHint`,
`openWorldHint`, `destructiveHint` --, e derivar delas e a mesma disciplina de
`coordinators_by_skill()`: a relacao vem do que ja esta declarado, e nao de uma
tabela paralela que cresce em desacordo com a primeira.
"""
from __future__ import annotations

import pytest

from sparkforge.adapters.tools import TOOLS
from sparkforge.agents.autonomy import (
    AuthorizationDecision,
    ToolClass,
    authorize,
    tool_class,
)


class TestClasseDerivadaDaAnotacao:
    @pytest.mark.parametrize("nome", sorted(TOOLS))
    def test_toda_tool_tem_classe(self, nome):
        assert isinstance(tool_class(nome), ToolClass)

    def test_a_classe_vem_da_anotacao_e_nao_de_uma_lista(self):
        """Se alguem trocar a anotacao de uma tool, a classe TEM que mudar
        junto. Uma lista paralela nao mudaria, e o desacordo seria mudo."""
        leitura_local = [
            n
            for n, t in TOOLS.items()
            if t["annotations"]["readOnlyHint"] and not t["annotations"]["openWorldHint"]
        ]
        assert leitura_local, "o corpus precisa ter ao menos uma tool de leitura local"
        assert {tool_class(n) for n in leitura_local} == {ToolClass.READ_ONLY}

    def test_tool_que_toca_aws_nao_e_read_only(self):
        de_nuvem = [n for n, t in TOOLS.items() if t["annotations"]["openWorldHint"]]
        assert de_nuvem, "o corpus precisa ter ao menos uma tool de nuvem"
        assert {tool_class(n) for n in de_nuvem} == {ToolClass.CLOUD_READ}

    def test_tool_desconhecida_falha_fechada(self):
        """Nome que nao esta no catalogo de tools nao vira READ_ONLY por
        default. Default permissivo para o desconhecido e como uma tool nova
        entra sem classe."""
        with pytest.raises(KeyError):
            tool_class("sparkforge_tool_que_nao_existe")


class TestCadeiaDeAutorizacao:
    def test_leitura_local_e_autorizada_sem_aprovacao(self):
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool="sparkforge_analyze_pyspark",
            allowed_tools=["sparkforge_analyze_pyspark"],
            profile="ECO",
            approvals=(),
        )
        assert isinstance(decisao, AuthorizationDecision)
        assert decisao.authorized is True
        assert decisao.tool_class is ToolClass.READ_ONLY
        assert decisao.required_approval is None

    def test_a_decisao_nomeia_quem_autorizou_e_sob_qual_perfil(self):
        """E isto que separa cadeia de checagem de um nivel: a decisao carrega
        o perfil e a aprovacao que a sustentou, entao um trace consegue
        responder 'quem permitiu isso, e com base em que'."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool="sparkforge_analyze_pyspark",
            allowed_tools=["sparkforge_analyze_pyspark"],
            profile="ECO",
            approvals=(),
        )
        assert decisao.agent == "sf-runtime-specialist"
        assert decisao.profile == "ECO"

    def test_tool_fora_da_allowlist_do_agente_e_recusada(self):
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool="sparkforge_case_open",
            allowed_tools=["sparkforge_analyze_pyspark"],
            profile="ECO",
            approvals=(),
        )
        assert decisao.authorized is False
        assert "allowlist" in decisao.reason

    def test_mutacao_local_exige_aprovacao_nomeada(self):
        decisao = authorize(
            agent="sf-orchestrator",
            tool="sparkforge_case_open",
            allowed_tools=["sparkforge_case_open"],
            profile="ECO",
            approvals=(),
        )
        assert decisao.authorized is False
        assert decisao.required_approval is ToolClass.LOCAL_MUTATION

    def test_a_aprovacao_e_por_classe_e_nao_um_booleano_global(self):
        """Aprovar mutacao local NAO aprova escrita na nuvem. Um booleano
        `approval=True` aprovava as duas de uma vez, e era essa a lacuna."""
        decisao = authorize(
            agent="sf-orchestrator",
            tool="sparkforge_case_open",
            allowed_tools=["sparkforge_case_open"],
            profile="ECO",
            approvals=(ToolClass.LOCAL_MUTATION,),
        )
        assert decisao.authorized is True
        assert decisao.granted_by is ToolClass.LOCAL_MUTATION

    def test_perfil_OFFLINE_recusa_tool_de_nuvem_mesmo_com_aprovacao(self):
        """O perfil e um teto, nao uma preferencia. Aprovacao nao fura teto --
        senao OFFLINE deixaria de significar 'zero rede' na primeira
        aprovacao distraida."""
        decisao = authorize(
            agent="sf-runtime-specialist",
            tool="sparkforge_collect_glue_job",
            allowed_tools=["sparkforge_collect_glue_job"],
            profile="OFFLINE",
            approvals=(ToolClass.CLOUD_READ,),
        )
        assert decisao.authorized is False
        assert "OFFLINE" in decisao.reason


class TestCompatibilidade:
    def test_authorize_tool_continua_existindo_e_respondendo_igual(self):
        """`AutonomyController.authorize_tool` tem chamador hoje. A cadeia entra
        AO LADO, e nao no lugar: quebrar a assinatura antiga transformaria uma
        adicao de seguranca numa migracao."""
        from sparkforge.agents.autonomy import AutonomyController

        controlador = AutonomyController()
        ok, razao = controlador.authorize_tool(
            agent="a", tool="t", allowed_tools=["t"], mutating=False, approval=False
        )
        assert ok is True and razao == "authorized"
