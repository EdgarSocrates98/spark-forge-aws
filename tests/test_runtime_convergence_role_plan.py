"""FASE 4 do prompt_evo_runtime: RoleContextPlan governando selecao de contexto.

`RoleContextPlan` existia como dataclass com `allows()` puro -- nenhum caminho
de execucao o consultava. Aqui o plano vira input do Context Gateway: quem
pede contexto declara a role (ou o plano serializado), e a selecao aplica
least-context por kind, trust floor, cota de bytes (`context_share`) e
`required_context`. Toda negacao vira `unresolved` nomeado -- nunca sumico
silencioso, porque o plano e politica e politica deixa recibo.
"""

from __future__ import annotations

from sparkforge_aws.adapters.tools import TOOLS
from sparkforge_aws.agentic.trust import RoleContextPlan, TrustLabel
from sparkforge_aws.context.gateway import ContextGateway
from sparkforge_aws.context.gateway_models import GatewayProfile, GatewayRequest


def _request(items, **kw):
    return GatewayRequest(
        kw.pop("intent", "diagnose"),
        kw.pop("profile", GatewayProfile.ECONOMY),
        kw.pop("max_bytes", 5000),
        items=tuple(items),
        **kw,
    )


class TestRolePlanNaSelecao:
    def test_kind_fora_do_plano_e_negado_e_nomeado(self):
        plan = RoleContextPlan(role="sf-judge", allowed_context=("fact", "rule"))
        request = _request(
            [
                {"fact_id": "f1", "kind": "fact", "relevance": 90},
                {"id": "tool-out", "kind": "tool_output", "relevance": 80},
            ],
            role_plan=plan.to_dict(),
        )
        result = ContextGateway(TOOLS).start(request)

        kinds = {item["kind"] for item in result["context"]}
        assert "fact" in kinds and "tool_output" not in kinds
        negado = [u for u in result["unresolved"] if u["code"] == "context_denied_by_role_plan"]
        assert negado and "tool_output" in negado[0]["message"]

    def test_trust_abaixo_do_floor_e_negado(self):
        plan = RoleContextPlan(
            role="sf-judge",
            allowed_context=("fact", "tool_output"),
            trust_floor=TrustLabel.TOOL_OUTPUT,
        )
        request = _request(
            [
                {"fact_id": "f1", "kind": "fact", "trust": "VERIFIED_FACT"},
                {"id": "t", "kind": "tool_output", "trust": "EXTERNAL_UNTRUSTED"},
            ],
            role_plan=plan.to_dict(),
        )
        result = ContextGateway(TOOLS).start(request)

        ids = {item["id"] for item in result["context"]}
        assert "f1" in ids and "t" not in ids

    def test_item_sem_trust_declarado_e_UNKNOWN_e_cai_no_floor(self):
        plan = RoleContextPlan(
            role="sf-verifier",
            allowed_context=("fact",),
            trust_floor=TrustLabel.EXTERNAL_DATA,
        )
        request = _request(
            [{"fact_id": "f1", "kind": "fact"}],  # sem "trust"
            role_plan=plan.to_dict(),
        )
        result = ContextGateway(TOOLS).start(request)
        assert not result["context"]
        assert any(u["code"] == "context_denied_by_role_plan" for u in result["unresolved"])

    def test_role_desconhecida_nega_tudo_em_vez_de_abrir(self):
        request = _request(
            [{"fact_id": "f1", "kind": "fact"}],
            role="sf-role-inexistente",
        )
        result = ContextGateway(TOOLS).start(request)

        assert not result["context"]
        codigos = {u["code"] for u in result["unresolved"]}
        assert "role_plan_unknown" in codigos

    def test_context_share_encolhe_o_teto_de_bytes(self):
        plan = RoleContextPlan(
            role="sf-extractor", allowed_context=("fact",), context_share=0.1
        )
        request = _request(
            [{"fact_id": "f1", "kind": "fact", "relevance": 100, "payload": "x" * 4000}],
            max_bytes=5000,
            role_plan=plan.to_dict(),
        )
        result = ContextGateway(TOOLS).start(request)

        # teto efetivo = 500 (10% de 5000): o fato nao cabe, e a resposta
        # registra o teto REAL aplicado -- nao o pedido original.
        assert result["budget"]["max_bytes"] == 500
        assert result["status"] == "refused"

    def test_required_context_ausente_vira_unresolved(self):
        plan = RoleContextPlan(
            role="sf-judge",
            allowed_context=("fact", "rule"),
            required_context=("rule",),
        )
        request = _request(
            [{"fact_id": "f1", "kind": "fact"}],
            role_plan=plan.to_dict(),
        )
        result = ContextGateway(TOOLS).start(request)

        assert any(u["code"] == "required_context_missing" for u in result["unresolved"])

    def test_tool_access_filtra_capabilities_descobertas(self):
        # A descoberta e dirigida por intent: para "Glue job" a capability
        # `sparkforge_analyze_glue_job_runs` sai sempre. O plano so deixa ela
        # passar -- as outras descobertas somem todas.
        plan = RoleContextPlan(
            role="sf-extractor",
            tool_access=("sparkforge_analyze_glue_job_runs",),
        )
        request = _request(
            [], intent="diagnose Glue job", role_plan=plan.to_dict()
        )
        result = ContextGateway(TOOLS).start(request)

        nomes = {c["name"] for c in result["capabilities"]}
        assert nomes == {"sparkforge_analyze_glue_job_runs"}

    def test_sem_plano_a_selecao_e_exatamente_a_de_hoje(self):
        items = [{"fact_id": "f1", "kind": "fact"}, {"id": "x", "kind": "tool_output"}]
        result = ContextGateway(TOOLS).start(_request(items))
        assert {i["kind"] for i in result["context"]} == {"fact", "tool_output"}
        assert not any(
            u["code"] in {"context_denied_by_role_plan", "role_plan_unknown"}
            for u in result["unresolved"]
        )


class TestRegistryDeRoles:
    def test_os_cinco_executores_tem_plano_declarado(self):
        from sparkforge_aws.agentic.role_plans import ROLE_PLANS

        esperados = {
            "sf-inventory",
            "sf-extractor",
            "sf-judge",
            "sf-verifier",
            "sf-synthesizer",
        }
        assert esperados <= set(ROLE_PLANS)
        for nome, plano in ROLE_PLANS.items():
            assert plano.role == nome
            assert plano.allowed_context, f"{nome}: least-context exige lista nao vazia"

    def test_role_conhecida_resolve_pelo_nome(self):
        request = _request(
            [
                {"fact_id": "f1", "kind": "fact"},
                {"id": "t", "kind": "tool_output", "relevance": 1},
            ],
            role="sf-judge",
        )
        result = ContextGateway(TOOLS).start(request)
        # o plano do juiz le fact+rule; tool_output cru nao entra
        assert {i["kind"] for i in result["context"]} == {"fact"}

    def test_plan_serializado_e_o_mesmo_da_role(self):
        from sparkforge_aws.agentic.role_plans import ROLE_PLANS

        plan = ROLE_PLANS["sf-judge"]
        items = [{"fact_id": "f1", "kind": "fact"}]
        por_nome = ContextGateway(TOOLS).start(_request(items, role="sf-judge"))
        por_dict = ContextGateway(TOOLS).start(
            _request(items, role_plan=plan.to_dict())
        )
        assert [i["id"] for i in por_nome["context"]] == [
            i["id"] for i in por_dict["context"]
        ]

    def test_plan_dict_invalido_nao_abre_contexto(self):
        request = _request(
            [{"fact_id": "f1", "kind": "fact"}],
            role_plan={"role": "x", "context_share": 9},
        )
        result = ContextGateway(TOOLS).start(request)
        assert not result["context"]
        assert any(u["code"] == "role_plan_invalid" for u in result["unresolved"])
