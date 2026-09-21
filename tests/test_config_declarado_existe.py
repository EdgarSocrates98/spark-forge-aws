"""Todo nome declarado num registro de `config/` aponta para algo que existe.

O SF_STUBS (`docs/sdd/SF_STUBS/`) apagou 19 agentes `sf-*` ocos, e dois incrementos
depois a mesma doenca foi encontrada uma camada abaixo, em `config/`: sete tools
declaradas que nao existem em `TOOLS`. Ela sobreviveu porque NADA impedia.

Este e o gate que impede. Ele nao afirma que aquelas sete sairam -- afirma que nada
declarado deixa de resolver, e por isso continua valendo para o proximo registro.

O mapa abaixo e declarado de proposito. Varrer todo YAML de `config/` e adivinhar quais
strings sao nomes a resolver produziria falso positivo em campo de politica
(`forbidden_by_default` nao e um agente), e um teste que precisa de lista de excecao
para nao mentir acaba desligado.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from sparkforge.adapters.tools import TOOLS

ROOT = Path(__file__).resolve().parents[1]

# As sete que a feature `docs/sdd/CONFIG_OCA/` removeu de `config/agentic-expansion.yaml`:
# nenhuma existia em `TOOLS`, e nenhuma tinha artefato coletavel definido.
TOOLS_QUE_SAIRAM = (
    "sparkforge_context_pack",
    "sparkforge_cost_estimate",
    "sparkforge_eval_golden_case",
    "sparkforge_lineage_extract",
    "sparkforge_offline_knowledge_search",
    "sparkforge_offline_knowledge_verify",
    "sparkforge_schema_compare",
)


def _agente_existe(nome: str) -> bool:
    return (ROOT / "agents" / f"{nome}.md").exists()


def _caminho_existe(rel: str) -> bool:
    return (ROOT / rel).exists()


def _tool_existe(nome: str) -> bool:
    return nome in TOOLS


# (registro, chave, resolvedor, o que o nome deveria apontar)
MAPA = (
    ("config/agentic-expansion.yaml", "agents", _agente_existe, "arquivo em agents/"),
    ("config/agentic-expansion.yaml", "knowledge", _caminho_existe, "caminho no repositorio"),
    (
        "config/agentic-expansion.yaml",
        "tools",
        _tool_existe,
        "entrada em sparkforge.adapters.tools.TOOLS",
    ),
)


def _declarados(registro: str, chave: str) -> list[str]:
    """Os nomes daquela chave, ou lista vazia se a chave nao existe.

    Chave ausente e resposta legitima: o D2 removeu o bloco `tools` inteiro em vez de
    deixar `tools: []`, porque chave vazia e convite a reencher sem criterio.
    """
    dados = yaml.safe_load((ROOT / registro).read_text(encoding="utf-8"))
    valor = (dados or {}).get(chave)
    return list(valor) if isinstance(valor, list) else []


def test_todo_nome_declarado_resolve():
    """AC2: a trava. A falha nomeia registro, chave e nome."""
    quebrados = []
    for registro, chave, resolve, alvo in MAPA:
        for nome in _declarados(registro, chave):
            if not resolve(nome):
                quebrados.append(f"{registro} :: {chave} :: {nome} (deveria ser {alvo})")
    assert not quebrados, (
        "nome declarado em config/ que nao resolve:\n  "
        + "\n  ".join(quebrados)
        + "\n\nColoque o artefato antes do nome, ou tire o nome. Ver "
        "docs/sdd/CONFIG_OCA/define.md."
    )


def test_toda_tool_declarada_existe():
    """AC1: as sete que sairam nao voltam, por nome.

    Esta asercao e o par NAO-VACUO do teste acima: com o bloco `tools` removido, aquele
    passa por ausencia. Este falha se qualquer uma das sete for reintroduzida em
    `config/`, tenha ou nao bloco.
    """
    texto = (ROOT / "config" / "agentic-expansion.yaml").read_text(encoding="utf-8")
    voltaram = [t for t in TOOLS_QUE_SAIRAM if t in texto]
    assert not voltaram, f"tool sem lastro de volta no registro: {voltaram}"
    assert all(t not in TOOLS for t in TOOLS_QUE_SAIRAM), (
        "uma das sete passou a existir de verdade: tire-a de TOOLS_QUE_SAIRAM e deixe o "
        "gate do declarado cuidar dela"
    )


SUBAGENTS_QUE_SAIRAM = (
    "benchmark-comparator",
    "cost-estimator",
    "cross-reviewer",
    "evidence-extractor",
    "experiment-designer",
    "handoff-preparer",
    "hypothesis-generator",
    "intake-packager",
    "lineage-impact-analyzer",
    "mutation-risk-checker",
    "regression-judge",
    "release-gate",
    "rollback-planner",
    "schema-compatibility-checker",
    "security-gate",
    "source-verifier",
)


def test_o_registro_de_subagents_saiu_e_ninguem_o_le():
    """AC3: os 16 stubs sairam, e a medida que autorizou continua valendo.

    Os contratos existiam -- 16 de 16 -- e eram BYTE-IDENTICOS abaixo de `## Contract`;
    a descricao de cada um era o proprio nome com o hifen trocado por espaco. Nenhum
    modulo de `sparkforge/`, `scripts/` ou `tests/` os lia, ao contrario de `skills/` e
    `agents/`, que varios leem. A lacuna U1 do define -- um consumidor FORA do
    repositorio -- nao e alcancavel daqui, e o rollback do D3 e a rede dela.
    """
    assert not (ROOT / "config" / "subagents.yaml").exists()
    assert not (ROOT / "subagents").exists()

    # E nenhum modulo passou a citar o que saiu.
    for diretorio in ("sparkforge", "scripts", "tests"):
        for arquivo in sorted((ROOT / diretorio).rglob("*.py")):
            if arquivo.name == "test_config_declarado_existe.py":
                continue
            texto = arquivo.read_text(encoding="utf-8")
            assert "config/subagents.yaml" not in texto, arquivo
            assert "subagents/" not in texto, arquivo
