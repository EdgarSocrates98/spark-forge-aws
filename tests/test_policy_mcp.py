"""A policy no servidor MCP: carga, recusa, aprovacoes, raizes e policy invalida."""
from __future__ import annotations

from pathlib import Path

from sparkforge.adapters import mcp as mcp_adapter
from sparkforge.adapters import tools
from sparkforge.adapters.tools import call_tool
from sparkforge.policy.load import Politica, carregar
from sparkforge.policy.mcp import para_call_policy, tools_por_classe

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PY = ROOT / "fixtures" / "pyspark" / "python_udf" / "input" / "lib" / "job.py"


def test_policy_padrao_nao_recusa_leitura_dentro_do_repo():
    policy = para_call_policy(carregar(ROOT), ROOT)
    resultado = call_tool("sparkforge_analyze_pyspark", {"path": str(FIXTURE_PY)}, policy=policy)
    assert "error" not in resultado, resultado


def test_policy_padrao_pre_aprova_as_classes_de_hoje():
    policy = para_call_policy(carregar(ROOT), ROOT)
    for classe, nomes in tools_por_classe().items():
        if classe in {"LOCAL_MUTATION", "CLOUD_READ", "CLOUD_MUTATION"}:
            decisao = policy.decide(nomes[0], {})
            assert decisao.authorized, (nomes[0], decisao.reason)


def test_caminho_fora_da_raiz_e_recusado_e_extra_root_libera(tmp_path):
    alvo = tmp_path / "job.py"
    alvo.write_text(FIXTURE_PY.read_text(encoding="utf-8"), encoding="utf-8")
    sem_extra = para_call_policy(Politica(approvals=("LOCAL_MUTATION",)), ROOT)
    recusa = call_tool("sparkforge_analyze_pyspark", {"path": str(alvo)}, policy=sem_extra)
    assert recusa.get("error_code") == "UNAUTHORIZED", recusa
    com_extra = para_call_policy(Politica(extra_roots=(str(tmp_path),)), ROOT)
    assert "error" not in call_tool("sparkforge_analyze_pyspark", {"path": str(alvo)},
                                    policy=com_extra)


def test_tool_negada_nao_roda_o_handler(monkeypatch):
    chamadas = []
    original = tools._HANDLERS["sparkforge_judge"]
    monkeypatch.setitem(tools._HANDLERS, "sparkforge_judge",
                        lambda args: chamadas.append(args) or original(args))
    policy = para_call_policy(Politica(denied=("sparkforge_judge",)), ROOT)
    resultado = call_tool("sparkforge_judge", {"facts": []}, policy=policy)
    assert resultado.get("error_code") == "UNAUTHORIZED" and chamadas == []


def test_servidor_sem_policy_e_com_policy_invalida(tmp_path):
    assert mcp_adapter.carregar_policy_do_servidor(tmp_path) == (None, None)
    (tmp_path / ".sparkforge").mkdir()
    (tmp_path / ".sparkforge" / "policy.yaml").write_text("version: 9\n", encoding="utf-8")
    policy, erro = mcp_adapter.carregar_policy_do_servidor(tmp_path)
    assert policy is None and "version" in erro
    recusa = mcp_adapter._recusa_por_policy_invalida(erro)("sparkforge_judge", {})
    assert recusa["error_code"] == "POLICY_INVALID" and "sparkforge policy check" in recusa["error"]


def test_servidor_com_a_policy_do_repositorio():
    policy, erro = mcp_adapter.carregar_policy_do_servidor(ROOT)
    assert erro is None and policy is not None and policy.agent == "policy.yaml"
