"""As invariantes que o eval harness nao pode perder, provadas por AST.

Regra 23 do `CLAUDE.md`: o projeto nao chama provider nenhum. Ela era medida em
prosa ("`sparkforge/` nao importa `anthropic`, `openai`, `bedrock` nem
`litellm`") e nenhum teste a conferia -- ate aqui. O eval harness e o primeiro
modulo que lida com AGENTE de perto, e o lugar mais facil de alguem acrescentar
"so uma chamada de modelo para julgar a resposta". Este arquivo fecha a porta:
import de SDK de provider, cliente boto3 de Bedrock, e -- nos modulos do eval --
qualquer `subprocess`, que e como um grader passaria a disparar o host.

A varredura e por AST, e nao por texto, porque as docstrings deste repositorio
citam os nomes dos provedores justamente para dizer que nao os importam.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACOTE = ROOT / "sparkforge"
PROVIDERS = {"anthropic", "openai", "litellm", "google.generativeai", "mistralai", "cohere"}
BEDROCK = ("bedrock-runtime", "bedrock-agent-runtime", "bedrock-agentcore")
MODULOS_DO_EVAL = (
    PACOTE / "evals" / "suite.py",
    PACOTE / "evals" / "grade.py",
    PACOTE / "evals" / "compare.py",
    PACOTE / "evals" / "cli.py",
    PACOTE / "evals" / "__main__.py",
    PACOTE / "evals" / "debate_grade.py",
    PACOTE / "facts" / "host_transcript.py",
    # O executor de debate conduz uma geracao que acontece FORA do pacote: a
    # maquina de estados e a reextracao de evidencia nao podem abrir processo
    # nem chamar provider (regra 23), e a checagem de processo desta lista e a
    # que confere isso.
    PACOTE / "agentic" / "executor" / "debate_run.py",
    PACOTE / "agentic" / "executor" / "debate_evidence.py",
)


def _arvores():
    for arquivo in sorted(PACOTE.rglob("*.py")):
        yield arquivo, ast.parse(arquivo.read_text(encoding="utf-8"))


def _modulos_importados(arvore: ast.AST) -> set[str]:
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(alias.name for alias in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module:
            nomes.add(no.module)
    return nomes


def _e_provider(modulo: str) -> bool:
    return any(modulo == p or modulo.startswith(p + ".") for p in PROVIDERS)


def test_a_varredura_nao_e_vacua():
    arquivos = list(_arvores())
    assert len(arquivos) > 100
    assert all(m.is_file() for m in MODULOS_DO_EVAL)


def test_nenhum_modulo_do_pacote_importa_sdk_de_provider():
    achados = [
        f"{arquivo.relative_to(ROOT)}: {modulo}"
        for arquivo, arvore in _arvores()
        for modulo in _modulos_importados(arvore)
        if _e_provider(modulo)
    ]
    assert not achados, achados


def test_nenhum_modulo_do_pacote_abre_cliente_de_bedrock():
    achados = [
        f"{arquivo.relative_to(ROOT)}:{no.lineno}"
        for arquivo, arvore in _arvores()
        for no in ast.walk(arvore)
        if isinstance(no, ast.Constant)
        and isinstance(no.value, str)
        and no.value in BEDROCK
    ]
    assert not achados, achados


def test_os_modulos_do_eval_nao_disparam_processo():
    chamadas_de_processo = {"system", "popen", "execv", "execvp", "execve", "spawnv", "startfile"}
    for arquivo in MODULOS_DO_EVAL:
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        proibidos = _modulos_importados(arvore) & {"subprocess", "multiprocessing", "pty"}
        assert not proibidos, f"{arquivo.name}: {sorted(proibidos)}"
        atributos = {
            no.attr for no in ast.walk(arvore) if isinstance(no, ast.Attribute)
        } & chamadas_de_processo
        assert not atributos, f"{arquivo.name}: {sorted(atributos)}"


def test_o_runner_mora_fora_do_pacote():
    assert (ROOT / "scripts" / "run_agentic_eval.py").is_file()
    assert not (PACOTE / "evals" / "run_agentic_eval.py").exists()
    # O driver do debate tambem gasta token, e pelo mesmo motivo mora em scripts/.
    assert (ROOT / "scripts" / "run_debate.py").is_file()
    assert not (PACOTE / "evals" / "run_debate.py").exists()


def _chaves(valor, prefixo: str = "") -> list[str]:
    if isinstance(valor, dict):
        saida = []
        for chave, filho in valor.items():
            caminho = f"{prefixo}.{chave}" if prefixo else chave
            saida.append(caminho)
            saida.extend(_chaves(filho, caminho))
        return saida
    if isinstance(valor, list):
        return [c for item in valor for c in _chaves(item, prefixo)]
    return []


def test_scorecard_nao_soma_byte_com_token_nem_publica_nota():
    """Regra 22: byte e token lado a lado, nunca num campo comum. E o DEFINE
    recusou nota composta: nenhum campo `score`, `total_cost` ou afim."""
    golden = ROOT / "fixtures" / "host_transcript" / "run_full" / "expected" / "scorecard.json"
    scorecard = json.loads(golden.read_text(encoding="utf-8"))
    chaves = _chaves(scorecard)
    for chave in chaves:
        folha = chave.rsplit(".", 1)[-1]
        assert folha not in {"score", "total_cost", "cost_usd", "total_units"}, chave
        assert not ("byte" in folha and "token" in folha), chave
    assert any(c.endswith("tool_result_bytes") for c in chaves)
    assert any(c.endswith("tokens.output") for c in chaves)


def test_braco_suite_da_superficie_nega_so_o_que_o_gabarito_nao_exige():
    """`--surface suite` (2026-09-15) mede o TAMANHO da superficie: o agente ve
    a uniao de `required_tools` da suite, a mesma lista para toda pergunta, e o
    resto do registro sai por `--disallowedTools`. Verbo exigido que o registro
    nao conhece derrubaria o braco; tool nova no registro entra negada sem
    ninguem editar lista."""
    from scripts import run_agentic_eval as runner
    from sparkforge.adapters.tools import TOOLS
    from sparkforge.evals.suite import load_suite

    suite = load_suite(runner.SUITE_DIR)
    assert runner._negadas(suite, "full") == []
    negadas = runner._negadas(suite, "suite")
    assert all(nome.startswith(runner.MCP_PREFIX) for nome in negadas)
    visiveis = set(TOOLS) - {nome.removeprefix(runner.MCP_PREFIX) for nome in negadas}
    assert visiveis == {
        "sparkforge_analyze_event_log",
        "sparkforge_analyze_plan",
        "sparkforge_analyze_pyspark",
        "sparkforge_benchmark",
        "sparkforge_finops",
        "sparkforge_judge",
        "sparkforge_release_describe",
        "sparkforge_rules_lookup",
        "sparkforge_runtime_detect",
    }
