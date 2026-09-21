"""TOKEN_ESTIMATE_UNICO: uma estimativa de token por caracteres, e os sitios a usam.

AC1 a AC3 de docs/sdd/TOKEN_ESTIMATE_UNICO/define.md. O AC2 e medido contra a regra
antiga do funnel, reproduzida aqui (D4 do design), e nao argumentado.
"""

from __future__ import annotations

import inspect
import random

import sparkforge.tools as tools_pkg
from sparkforge.agents import budget as dono
from sparkforge.codeintel import budget as codeintel_budget
from sparkforge.context import funnel
from sparkforge.context.funnel import ContextChunk, ContextFunnel
from sparkforge.providers import mock
from sparkforge.providers.mock import MockModelProvider
from sparkforge.tools import cost


def _escolha_com_piso(chunks: list[ContextChunk], orcamento: int) -> list[ContextChunk]:
    """A regra antiga do funnel: piso de len/4 (minimo 1), para no primeiro que nao cabe."""
    ordenados = sorted(chunks, key=lambda c: c.relevance_score, reverse=True)
    vistos: set[str] = set()
    unicos: list[ContextChunk] = []
    for chunk in ordenados:
        if chunk.content_hash not in vistos:
            vistos.add(chunk.content_hash)
            unicos.append(chunk)
    escolhidos: list[ContextChunk] = []
    total = 0
    for chunk in unicos:
        custo = max(1, len(chunk.content) // 4)
        if total + custo > orcamento:
            break
        escolhidos.append(chunk)
        total += custo
    return escolhidos


def _caso_sintetico(semente: int) -> tuple[list[ContextChunk], int]:
    """Chunks de 0 a 40 caracteres (repetidos, para exercitar a deduplicacao) e um orcamento."""
    sorteio = random.Random(semente)  # noqa: S311 -- deterministico p/ teste, nao cripto
    chunks = [
        ContextChunk(
            source_file=f"f{indice}.py",
            chunk_id=f"c{indice}",
            content="x" * sorteio.randint(0, 40),
            relevance_score=sorteio.choice([0.1, 0.5, 0.9]),
        )
        for indice in range(sorteio.randint(1, 12))
    ]
    return chunks, sorteio.randint(0, 60)


def test_uma_definicao_e_os_sitios_a_usam(monkeypatch):
    # identidade, nao nome: os tres sitios e a reexportacao publica sao a funcao do dono
    assert cost.estimate_tokens is dono.estimate_tokens
    assert tools_pkg.estimate_tokens is dono.estimate_tokens
    assert funnel.estimate_tokens is dono.estimate_tokens
    assert mock.estimate_tokens is dono.estimate_tokens
    for modulo in (cost, funnel, mock):
        assert "// 4" not in inspect.getsource(modulo), modulo.__name__

    # e os sitios CHAMAM o nome: um espiao no lugar dele ve cada texto passar
    vistos: list[str] = []

    def espiao(valor):
        vistos.append(valor)
        return dono.estimate_tokens(valor)

    monkeypatch.setattr(funnel, "estimate_tokens", espiao)
    monkeypatch.setattr(mock, "estimate_tokens", espiao)
    ContextFunnel(max_tokens_budget=100).build_minimal_context(
        [ContextChunk(source_file="a.py", chunk_id="c1", content="abcde")]
    )
    MockModelProvider(default_response="ok").generate("prompt")
    assert vistos == ["abcde", "prompt", "ok"]

    # codeintel/budget.py fica fora, e a docstring dele diz por que
    assert not hasattr(codeintel_budget, "estimate_tokens")
    doc = codeintel_budget.__doc__ or ""
    assert "NAO REUSA `agents/budget.estimate_tokens`" in doc
    assert "continua devida" not in doc


def test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso():
    # o caso que separa: cinco caracteres custam 1 com piso e 2 com teto
    chunks = [
        ContextChunk(source_file="a.py", chunk_id=f"c{indice}", content=f"abcd{indice}")
        for indice in range(4)
    ]
    antigo = _escolha_com_piso(chunks, 4)
    novo = ContextFunnel(max_tokens_budget=4).build_minimal_context(chunks)
    assert [c.chunk_id for c in antigo] == ["c0", "c1", "c2", "c3"]
    assert [c.chunk_id for c in novo.chunks] == ["c0", "c1"]
    assert novo.total_tokens_estimate == 4

    for semente in range(500):
        chunks, orcamento = _caso_sintetico(semente)
        minimal = ContextFunnel(max_tokens_budget=orcamento).build_minimal_context(chunks)
        ids_novo = [c.chunk_id for c in minimal.chunks]
        ids_antigo = [c.chunk_id for c in _escolha_com_piso(chunks, orcamento)]
        assert ids_novo == ids_antigo[: len(ids_novo)], semente
        esperado = sum(dono.estimate_tokens(c.content) for c in minimal.chunks)
        assert minimal.total_tokens_estimate == esperado, semente
        assert minimal.total_tokens_estimate <= orcamento, semente


def test_mock_nunca_afirma_zero_token():
    for texto in ("", "a", "ab", "abc"):
        saida = MockModelProvider(default_response=texto).generate(texto)
        assert saida["input_tokens"] == 1, repr(texto)
        assert saida["output_tokens"] == 1, repr(texto)
    saida = MockModelProvider().generate("abcde")
    assert saida["input_tokens"] == 2
    assert saida["output_tokens"] == dono.estimate_tokens("Deterministic analysis completed.")
