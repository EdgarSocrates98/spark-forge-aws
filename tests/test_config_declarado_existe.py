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
