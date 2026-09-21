---
sdd: 1
feature: TOKEN_ESTIMATE_UNICO
phase: plan
profile: dev
status: ready
upstream:
  path: docs/sdd/TOKEN_ESTIMATE_UNICO/design.md
  sha256: "16d46baba70ced63afe92989fd1822bb31c2f54bab188c930c332ddd087e0790"
tasks:
  - id: T1
    files: [tests/test_token_estimate_unico.py, sparkforge/agents/budget.py, sparkforge/tools/cost.py, sparkforge/context/funnel.py, sparkforge/providers/mock.py, sparkforge/codeintel/budget.py, docs/harness/CODEINTEL-GAP.md, docs/claims.lock.json]
    covers: [AC1, AC2, AC3, AC4, AC5]
    test: {path: tests/test_token_estimate_unico.py, name: test_uma_definicao_e_os_sitios_a_usam}
---

# TOKEN_ESTIMATE_UNICO — plano

Uma tarefa. O manifesto do design tem oito arquivos e uma mudança só: três sítios deixam a
fórmula própria e passam a chamar `sparkforge/agents/budget.py::estimate_tokens` (D1). Partir
em duas tarefas deixaria um commit com o código novo e a alegação auditada ainda dizendo
"quatro vezes" — o gate de lastro vermelho atravessando commit, que é o que a ordem de
dependência da skill proíbe.

Premissas (D1–D4 do design): o dono é `agents/budget.py` (teto de `len/4`, mínimo 1, não-string
vira JSON ordenado); `tools/cost.py` fica como alias pelo mesmo nome, porque `sparkforge.tools`
o reexporta e `sparkforge/tools/cli.py` o chama; `codeintel/budget.py` fica fora; a propriedade
de prefixo do AC2 é medida contra a fórmula antiga reproduzida no teste.

Uma diferença de comportamento de `tools.cost.estimate_tokens` que não aparece em nenhum
chamador: para valor que **não** é `str`, a função antiga contava `str(valor)`, e a do dono
conta `json.dumps(valor, sort_keys=True)`. Os dois chamadores do repositório
(`tools/cost.py::budget_report` e `tools/cli.py`) passam `str`, e para `str` as duas fórmulas
são idênticas (`max(1, (len + 3) // 4)`).

## T1 — uma estimativa, três sítios que a chamam

### 1. Escrever o teste que falha

`tests/test_token_estimate_unico.py`, inteiro:

```python
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
    sorteio = random.Random(semente)
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
```

`git add tests/test_token_estimate_unico.py` antes de rodar qualquer teste de árvore.

### 2. Rodar e ver falhar

```bash
python -m pytest tests/test_token_estimate_unico.py::test_uma_definicao_e_os_sitios_a_usam tests/test_token_estimate_unico.py::test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso tests/test_token_estimate_unico.py::test_mock_nunca_afirma_zero_token -q
```

Falha esperada, exit 1, três `AssertionError`, nenhum erro de import:

- `test_uma_definicao_e_os_sitios_a_usam`: `assert cost.estimate_tokens is dono.estimate_tokens`
  — `tools/cost.py` tem corpo próprio.
- `test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso`: a lista de ids do funnel é
  `["c0", "c1", "c2", "c3"]`, não `["c0", "c1"]` — o funnel ainda usa o piso.
- `test_mock_nunca_afirma_zero_token`: `input_tokens == 0` para `""`.

### 3. Código mínimo

`sparkforge/agents/budget.py` — a docstring do módulo e a da função; o corpo não muda:

```python
"""Deterministic context policies for token-efficient agent collaboration.

`estimate_tokens` e a UNICA estimativa de token por caracteres do pacote:
`sparkforge/tools/cost.py` a reexporta pelo mesmo nome, e `sparkforge/context/funnel.py`
e `sparkforge/providers/mock.py` a chamam. `sparkforge/codeintel/budget.py::estimar_tokens`
fica de fora de proposito -- mede bytes UTF-8 e nao decide corte; a docstring dele diz por que.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any


def estimate_tokens(value: Any) -> int:
    """Estimativa de token por caracteres: teto de `len/4`, minimo 1.

    O teto e o lado conservador. Quem corta por orcamento com ela cabe no maximo o que
    cabia com o piso, nunca mais, e texto curto nunca vale zero token. Valor que nao e
    texto vira JSON com chaves ordenadas antes da conta, para que o mesmo valor de o
    mesmo numero em qualquer execucao.

    E heuristica, nao medida: nunca se veste de token de provider (regra 24 do
    CLAUDE.md). E conta caractere, nao byte UTF-8, e por isso subestima texto acentuado.
    """
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return max(1, (len(text) + 3) // 4)
```

(o resto do arquivo — `fingerprint`, `deduplicate`, `select_context`, `compact_summary` — fica
como está.)

`sparkforge/tools/cost.py`, inteiro:

```python
"""Estimativa de custo em token.

`estimate_tokens` e heuristica -- 4 caracteres por token -- e nao substitui a
contagem do provedor. Todo retorno carrega `is_estimate: True` para que nenhum
consumidor trate o numero como medicao.

A funcao e a de `sparkforge.agents.budget`, reexportada pelo mesmo nome porque
`sparkforge.tools` a publica e `sparkforge/tools/cli.py` a chama: uma definicao so,
e `is` prova que e a mesma.
"""

from sparkforge.agents.budget import estimate_tokens

__all__ = ["budget_report", "estimate_tokens"]


def budget_report(messages, limit=12000):
    text = " ".join(str(m.get("content", m.get("text", ""))) for m in messages)
    estimated = estimate_tokens(text)
    return {
        "estimated_tokens": estimated,
        "limit": limit,
        "remaining": max(0, limit - estimated),
        "within_budget": estimated <= limit,
        "is_estimate": True,
    }
```

`sparkforge/context/funnel.py` — o import e o passo 3 de `build_minimal_context`:

```python
import hashlib
from dataclasses import dataclass, field

from sparkforge.agents.budget import estimate_tokens
```

```python
        # 3. Fit in budget, with the package's single token estimate (ceiling of len/4):
        # the ceiling fits at most what the old floor fitted, never more.
        fitted_chunks = []
        total_tokens = 0
        for c in unique_chunks:
            tokens_est = estimate_tokens(c.content)
            if total_tokens + tokens_est <= self.max_tokens_budget:
                fitted_chunks.append(c)
                total_tokens += tokens_est
            else:
                break
```

`sparkforge/providers/mock.py`, inteiro:

```python
"""Deterministic Mock LLM Provider for Testing and CI."""
from __future__ import annotations

from typing import Any

from sparkforge.agents.budget import estimate_tokens


class MockModelProvider:
    """Zero-cost, offline deterministic model provider."""

    def __init__(self, default_response: str = "Deterministic analysis completed.") -> None:
        self.default_response = default_response
        self.call_history: list[dict[str, Any]] = []

    def generate(self, prompt: str, tier: str = "tier_3_cheap_local") -> dict[str, Any]:
        self.call_history.append({"prompt": prompt, "tier": tier})
        return {
            "content": self.default_response,
            "input_tokens": estimate_tokens(prompt),
            "output_tokens": estimate_tokens(self.default_response),
            "cached_tokens": 0,
            "cost_usd": 0.0,
        }
```

`sparkforge/codeintel/budget.py` — dois trechos da docstring do módulo. O parágrafo que
contava as quatro estimativas (começa em "Token nao e mensuravel offline") passa a ser:

```text
Token nao e mensuravel offline. A secao 52 proibe tokenizer que baixe modelo, e
com razao -- baixar tokenizer quebra o "offline" inteiro da secao 7. O que sobra
e ESTIMATIVA. Havia quatro delas, divergindo no arredondamento; desde
TOKEN_ESTIMATE_UNICO ha uma so, `agents/budget.py:estimate_tokens` (teto de
`len/4`, minimo 1), que `tools/cost.py` reexporta e `context/funnel.py` e
`providers/mock.py` chamam. Ela conta caractere e nao byte UTF-8, o que a faz
subestimar qualquer texto acentuado, que e todo texto deste projeto.
```

E o fim da seção "POR QUE ESTE MODULO NAO REUSA `agents/budget.estimate_tokens`" (cujo título
fica) passa a ser:

```text
Porque a unidade e outra e o papel e outro: la a estimativa DECIDE o corte, aqui
o byte decide e a estimativa acompanha. Trocar `estimate_tokens` pela formula da
secao 52 mudaria o resultado de `select_context` para toda memoria de agente
deste repositorio -- registros diferentes seriam escolhidos, com o mesmo
orcamento. Isso e mudanca de comportamento, e mudanca de comportamento em
silencio e o que a regra de preservar semantica recusa. A consolidacao das
estimativas por caractere foi feita em TOKEN_ESTIMATE_UNICO (`docs/sdd/`) e
deixou este modulo de fora por esta razao.
```

`docs/harness/CODEINTEL-GAP.md` — cada troca mantém o número de linhas, para não mover a linha
das outras alegações:

- linha da tabela "Estimador de token local, conservador, sem download" (VNX-603) passa a:

  ```text
  | Estimador de token local, conservador, sem download | EXISTE PARCIAL | Existe **uma vez**: `sparkforge/agents/budget.py:estimate_tokens()` (teto de `len/4`, mínimo 1). `sparkforge/tools/cost.py` a reexporta pelo mesmo nome, e `sparkforge/context/funnel.py` e `sparkforge/providers/mock.py` a chamam — até TOKEN_ESTIMATE_UNICO eram quatro cópias, duas delas com piso. Parcial porque conta caractere e não byte UTF-8, e subestima texto acentuado; `sparkforge/codeintel/budget.py:estimar_tokens()` mede byte e fica fora de propósito, porque não decide corte | `tests/test_token_estimate_unico.py` |
  ```

- "Os quatro estimadores de token deste / repositório dividem o comprimento por uma constante e
  divergem entre si no arredondamento: byte é" passa a "A estimativa de token deste repositório /
  divide o comprimento por uma constante e conta caractere, não byte: byte é";
- "Os estimadores de token deste repositório dividem / o comprimento do texto por uma constante e
  divergem entre si no arredondamento: byte é" passa a "A estimativa de token deste repositório
  divide / o comprimento do texto por uma constante e conta caractere, não byte: byte é";
- o item "Orçamento de token medido em vez de estimado" passa a "A estimativa de token virou uma
  só / (`agents/budget.py:estimate_tokens`, TOKEN_ESTIMATE_UNICO), e ela ainda divide comprimento
  / por quatro; nada mede. Não é preciso um tokenizer baixado para melhorar: o estimador único /
  já é o ganho menor, e o que falta é ele contar byte e não caractere.";
- "e as quatro de estimativa de token são o" passa a "(e as quatro de estimativa de token, já
  uma só) são o";
- "e quatro estimadores de token. Um objeto de contexto novo" passa a "; os estimadores de token
  já são um só. Um objeto de contexto novo";
- "e os quatro estimadores de token e os três empacotadores de contexto / continuam sendo quatro
  e três." passa a "e os três empacotadores de contexto continuam sendo três (os estimadores / de
  token viraram um só em TOKEN_ESTIMATE_UNICO).";
- "projeção de campo e o estimador único de token, não." passa a "o estimador único de token
  também (TOKEN_ESTIMATE_UNICO); projeção de campo, não.";
- "parcial — continua havendo quatro, e / elas divergem no arredondamento." passa a "parcial — há
  um só desde / TOKEN_ESTIMATE_UNICO, e ele conta caractere, não byte UTF-8.".

`docs/claims.lock.json` — a VNX-603 ganha o `context` novo (a linha da tabela acima) e a prova
passa a ser o teste desta feature:
`{"kind": "artifact", "path": "sparkforge/agents/budget.py", "symbol": "estimate_tokens",
"test": "tests/test_token_estimate_unico.py"}`, com `note` datada dizendo a troca. Toda outra
entrada que `python scripts/check_vnext_claims.py` listar é remediada pelo id da saída — editar
`text`, `context` e `proof.expect.value` via `json.load`/`json.dump` com `ensure_ascii=False` e
`indent` do arquivo, sem `sort_keys`, e o `cmd` quebrado por `shlex.split` para rodar e ler o
valor medido. VNX-587 e VNX-604 são conferidas: a 587 fala de colisão de id de nó, a 604 da
docstring de `tools/cost.py` que continua dizendo "quatro caracteres por token é heurística" e
`is_estimate: True`.

### 4. Rodar e ver passar

```bash
python -m pytest tests/test_token_estimate_unico.py::test_uma_definicao_e_os_sitios_a_usam tests/test_token_estimate_unico.py::test_funnel_com_teto_escolhe_prefixo_da_escolha_com_piso tests/test_token_estimate_unico.py::test_mock_nunca_afirma_zero_token -q
```

Exit 0, três passam.

### 5. Gates vizinhos

Testes existentes dos sítios tocados (SC2: toda expectativa numérica que mudar é registrada com
o antes e o depois, nunca apagada):

```bash
python -m pytest tests/test_context_funnel.py tests/test_offline_expansion.py tests/test_agent_runtime.py tests/test_model_and_observability.py tests/test_codeintel_budget.py tests/test_codeintel_context.py -q
python -m pytest tests/test_fixtures_golden*.py -q
python scripts/check_vnext_claims.py
python -m pytest tests/test_vnext_claims.py -q
python -m pytest tests/test_docs_coverage.py tests/test_installed_provenance.py -q
ruff check tests/test_token_estimate_unico.py sparkforge/agents/budget.py sparkforge/tools/cost.py sparkforge/context/funnel.py sparkforge/providers/mock.py sparkforge/codeintel/budget.py
```

A dos goldens (AC4) roda sem regenerar; se algum golden de achado mudar, pare: a afirmação do
define está errada. O gate de lastro (AC5) roda com a árvore final.

### 6. Commit

```text
refactor(tokens): give the character token estimate a single definition

tools/cost, context/funnel and providers/mock now call
agents/budget.estimate_tokens (ceiling of len/4, minimum 1). The funnel
fits a prefix of what it fitted with the floor, and the mock no longer
claims zero tokens. codeintel/budget stays out, with the reason in its
docstring. VNX-603 describes the single estimator.
```
